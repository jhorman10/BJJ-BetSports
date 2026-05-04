import logging
import os
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from pymongo import MongoClient
from src.utils.time_utils import get_current_time, is_future_time

logger = logging.getLogger(__name__)


def _to_bson_friendly(value: Any) -> Any:
    """Convert nested Python/domain objects into BSON-friendly primitives."""
    if is_dataclass(value):
        return _to_bson_friendly(asdict(value))

    if hasattr(value, "model_dump"):
        return _to_bson_friendly(value.model_dump())

    if isinstance(value, dict):
        return {key: _to_bson_friendly(item) for key, item in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_to_bson_friendly(item) for item in value]

    if hasattr(value, "__dict__") and not isinstance(value, type):
        return _to_bson_friendly(vars(value))

    return value


def _to_prediction_result(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Expose active prediction docs in the shape expected by callers."""
    return {
        "match_id": doc["match_id"],
        "league_id": doc.get("league_id"),
        "prediction": doc.get("data"),
        "last_updated": doc.get("last_updated"),
    }


class MongoRepository:
    """Drop-in replacement for PostgreSQL PersistenceRepository using MongoDB."""

    def __init__(self) -> None:
        self.client: MongoClient
        mongo_uri = os.getenv(
            "MONGO_URI", "mongodb://admin:adminpassword@localhost:27017/"
        )
        db_name = os.getenv("MONGO_DB_NAME", "bjj_betsports")

        try:
            self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            self.client.admin.command("ping")
            self.db = self.client[db_name]

            # Initialize collections
            self.training_results = self.db["training_results"]
            self.match_predictions = self.db["match_predictions"]
            self.api_cache = self.db["api_cache"]
            self.app_state = self.db["app_state"]
            self.binary_artifacts = self.db["binary_artifacts"]

            # Create indexes
            self.training_results.create_index("key", unique=True)
            self.match_predictions.create_index("match_id", unique=True)
            self.api_cache.create_index("key", unique=True)
            self.app_state.create_index("key", unique=True)
            self.binary_artifacts.create_index("key", unique=True)

            logger.info(f"✅ Successfully connected to MongoDB database: {db_name}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise e

    def create_tables(self) -> None:
        """No-op for MongoDB, collections are created implicitly."""
        pass

    def save_training_result(self, key: str, data: Dict[str, Any]) -> None:
        normalized_data = _to_bson_friendly(data)
        self.training_results.update_one(
            {"key": key},
            {"$set": {"data": normalized_data, "last_updated": get_current_time()}},
            upsert=True,
        )

    def get_training_result(self, key: str) -> Optional[dict]:
        doc = self.training_results.find_one({"key": key})
        return doc.get("data") if doc else None

    def get_training_result_with_timestamp(
        self, key: str
    ) -> Tuple[Optional[dict], Optional[datetime]]:
        doc = self.training_results.find_one({"key": key})
        if doc:
            return doc.get("data"), doc.get("last_updated")
        return None, None

    def get_training_results_by_pattern(self, pattern: str) -> dict:
        """Approximation of SQL LIKE pattern matching for MongoDB"""
        regex_pattern = pattern.replace("%", ".*")
        docs = self.training_results.find({"key": {"$regex": f"^{regex_pattern}$"}})
        return {doc["key"]: doc["data"] for doc in docs}

    def save_match_prediction(
        self,
        match_id: str,
        league_id: str,
        data: Dict[str, Any],
        ttl_seconds: int = 86400,
    ) -> None:
        # Ensure traceability metadata exists
        try:
            if not isinstance(data, dict):
                data = {"payload": data}
            data.setdefault(
                "model_metadata",
                {
                    "model_version": os.getenv("MODEL_VERSION", "unknown"),
                    "generated_by": "prediction-service",
                },
            )
        except Exception:
            # Best-effort only
            pass

        expires_at = get_current_time() + timedelta(seconds=ttl_seconds)
        self.match_predictions.update_one(
            {"match_id": match_id},
            {
                "$set": {
                    "league_id": league_id,
                    "data": data,
                    "expires_at": expires_at,
                    "last_updated": get_current_time(),
                }
            },
            upsert=True,
        )

    def get_match_prediction(self, match_id: str) -> Optional[Dict[str, Any]]:
        doc = self.match_predictions.find_one({"match_id": match_id})
        if doc and is_future_time(doc.get("expires_at")):
            res = doc.get("data")
            return res if isinstance(res, dict) else None
        return None

    def get_match_predictions_bulk(self, match_ids: List[str]) -> Dict[str, dict]:
        """Return active prediction data keyed by match id.

        Expired documents are excluded from the result.
        """
        if not match_ids:
            return {}
        docs = self.match_predictions.find(
            {"match_id": {"$in": match_ids}, "expires_at": {"$gt": get_current_time()}}
        )
        result: Dict[str, dict] = {}
        for doc in docs:
            mid = doc.get("match_id")
            if mid:
                result[mid] = doc.get("data")
        return result

    def bulk_save_predictions(self, predictions_data: List[Dict[str, Any]]) -> None:
        if not predictions_data:
            return
        from pymongo import UpdateOne

        operations = []
        for p in predictions_data:
            # Ensure model metadata exists on each payload
            data_payload = p.get("data") or {}
            try:
                if not isinstance(data_payload, dict):
                    data_payload = {"payload": data_payload}
                data_payload.setdefault(
                    "model_metadata",
                    {
                        "model_version": os.getenv("MODEL_VERSION", "unknown"),
                        "generated_by": "prediction-service",
                    },
                )
            except Exception:
                pass

            expires_at = get_current_time() + timedelta(
                seconds=p.get("ttl_seconds", 86400)
            )
            operations.append(
                UpdateOne(
                    {"match_id": p["match_id"]},
                    {
                        "$set": {
                            "league_id": p["league_id"],
                            "data": data_payload,
                            "expires_at": expires_at,
                            "last_updated": get_current_time(),
                        }
                    },
                    upsert=True,
                )
            )
        self.match_predictions.bulk_write(operations)

    def get_all_active_predictions(self) -> List[dict]:
        docs = self.match_predictions.find({"expires_at": {"$gt": get_current_time()}})
        return [_to_prediction_result(doc) for doc in docs]

    def get_league_predictions(self, league_id: str) -> List[dict]:
        docs = self.match_predictions.find(
            {
                "league_id": league_id,
                "expires_at": {"$gt": get_current_time()},
            }
        )
        return [_to_prediction_result(doc) for doc in docs]

    def save_cached_response(
        self,
        endpoint: str,
        data: Dict[str, Any],
        params: Optional[Dict[str, Any]] = None,
        ttl_seconds: int = 3600,
    ) -> None:
        key = f"{endpoint}:{str(params)}"
        expires_at = get_current_time() + timedelta(seconds=ttl_seconds)
        self.api_cache.update_one(
            {"key": key},
            {"$set": {"data": data, "expires_at": expires_at}},
            upsert=True,
        )

    def get_cached_response(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        key = f"{endpoint}:{str(params)}"
        doc = self.api_cache.find_one({"key": key})
        if doc and is_future_time(doc.get("expires_at")):
            res = doc.get("data")
            return res if isinstance(res, dict) else None
        return None

    def clear_all_predictions(self, league_ids: Optional[List[str]] = None) -> bool:
        if league_ids:
            self.match_predictions.delete_many({"league_id": {"$in": league_ids}})
        else:
            self.match_predictions.delete_many({})
        return True

    def clear_all_data(self) -> Dict[str, int]:
        """Clear training, predictions and API cache collections."""
        training_deleted = self.training_results.delete_many({}).deleted_count
        predictions_deleted = self.match_predictions.delete_many({}).deleted_count
        cache_deleted = self.api_cache.delete_many({}).deleted_count
        app_state_deleted = self.app_state.delete_many({}).deleted_count
        artifacts_deleted = self.binary_artifacts.delete_many({}).deleted_count

        return {
            "training_results": training_deleted,
            "match_predictions": predictions_deleted,
            "api_cache": cache_deleted,
            "app_state": app_state_deleted,
            "binary_artifacts": artifacts_deleted,
        }

    def save_app_state(self, key: str, data: Dict[str, Any]) -> None:
        """Save general application state (JSON)."""
        normalized_data = _to_bson_friendly(data)
        self.app_state.update_one(
            {"key": key},
            {"$set": {"data": normalized_data, "last_updated": get_current_time()}},
            upsert=True,
        )

    def get_app_state(self, key: str) -> Optional[dict]:
        """Retrieve general application state."""
        doc = self.app_state.find_one({"key": key})
        return doc.get("data") if doc else None

    def save_binary_artifact(self, key: str, binary_data: bytes) -> None:
        """Save heavy binary data (e.g. ML model) as BSON Binary."""
        from bson.binary import Binary

        self.binary_artifacts.update_one(
            {"key": key},
            {
                "$set": {
                    "data": Binary(binary_data),
                    "last_updated": get_current_time(),
                }
            },
            upsert=True,
        )

    def get_binary_artifact(self, key: str) -> Optional[bytes]:
        """Retrieve binary data from MongoDB."""
        doc = self.binary_artifacts.find_one({"key": key})
        if doc and "data" in doc:
            return bytes(doc["data"])
        return None


# Singleton accessor with old name alias to avoid changing dependencies everywhere
_mongo_repo = None


def get_mongo_repository() -> MongoRepository:
    global _mongo_repo
    if _mongo_repo is None:
        _mongo_repo = MongoRepository()
    return _mongo_repo
