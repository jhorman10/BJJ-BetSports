import logging
import os
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from pymongo import MongoClient, ReturnDocument
from pymongo.errors import DuplicateKeyError, OperationFailure
from src.core.constants import ML_MODEL_FILENAME
from src.utils.time_utils import get_current_time, is_future_time

logger = logging.getLogger(__name__)

# Serving pointer lives in app_state; the legacy fixed-key blob keeps loading
# pre-change artifacts read-only until the first gated promotion swaps it out.
ML_SERVING_POINTER_KEY = "ml_picks_classifier/serving"
ML_LEGACY_BLOB_KEY = ML_MODEL_FILENAME


def _to_bson_friendly(value: Any) -> Any:
    """Convert nested Python/domain objects into BSON-friendly primitives."""
    if is_dataclass(value) and not isinstance(value, type):
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
        "sport": doc.get("sport", "soccer"),
        "prediction": doc.get("data"),
        "last_updated": doc.get("last_updated"),
    }


def _is_index_options_conflict(exc: Exception) -> bool:
    """True when a Mongo error is an IndexOptionsConflict (codes 85/86/67)."""
    if not isinstance(exc, OperationFailure):
        return False
    if exc.code in (85, 86, 67):
        return True
    message = str(exc)
    return "IndexOptionsConflict" in message or (
        "index already exists with different options" in message
    )


def _is_index_not_found(exc: Exception) -> bool:
    """True when a Mongo error is an IndexNotFound (code 27)."""
    if not isinstance(exc, OperationFailure):
        return False
    return exc.code == 27 or "IndexNotFound" in str(exc)


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

            # TTL indexes: expired docs are physically purged by MongoDB.
            # expireAfterSeconds=0 purges at expires_at (see design D2).
            # match_predictions uses a PARTIAL TTL index: only unlabeled docs
            # are purged at expires_at — labeled docs survive for the
            # auto-labeler and analytics (metrics_baseline) (C1).
            # MongoDB partial indexes do NOT support $ne, $not, or $exists:False
            # in partialFilterExpression — only $eq, $exists:True, $type, $in, $and.
            # {"labeled": {"$eq": False}} matches unlabeled docs (save_match_prediction
            # and bulk_save_predictions set "labeled": False via $setOnInsert on
            # insert; the auto-labeler overwrites to True afterward).  See D2 / C1.
            self._ensure_ttl_index(
                self.match_predictions, partial_filter={"labeled": {"$eq": False}}
            )
            self._ensure_ttl_index(self.api_cache)
            self.match_predictions.create_index(
                [("league_id", 1), ("expires_at", 1)], unique=False
            )

            logger.info(f"✅ Successfully connected to MongoDB database: {db_name}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise e

    def _ensure_ttl_index(
        self,
        collection: Any,
        field: str = "expires_at",
        seconds: int = 0,
        partial_filter: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Create a TTL index idempotently, optionally partial (C1).

        A pre-existing index with conflicting options raises
        ``OperationFailure`` (Mongo IndexOptionsConflict, codes 85/86/67);
        in that case the old index is dropped and the TTL index is recreated
        so initialization never crashes on drift. Failures inside the
        drop/recreate path are logged, never raised — the repository must
        boot even when the index cannot be reconciled (W1).
        """
        index_options: Dict[str, Any] = {"expireAfterSeconds": seconds}
        if partial_filter is not None:
            index_options["partialFilterExpression"] = partial_filter

        try:
            collection.create_index([(field, 1)], **index_options)
            return
        except OperationFailure as exc:
            if not _is_index_options_conflict(exc):
                raise
            logger.warning(
                "TTL index %s_1 conflicts with an existing index; rebuilding.",
                field,
            )

        try:
            collection.drop_index(f"{field}_1")
        except OperationFailure as exc:
            # The index may have been dropped concurrently; the recreate below
            # still converges. Log and continue — the app must keep booting.
            if not _is_index_not_found(exc):
                logger.warning("Failed to drop index %s_1: %s", field, exc)

        try:
            collection.create_index([(field, 1)], **index_options)
        except Exception as exc:
            logger.warning("Failed to recreate TTL index %s_1: %s", field, exc)

    def create_tables(self) -> None:
        """No-op for MongoDB, collections are created implicitly."""
        pass

    def get_league_ids_with_predictions(self, sport: str | None = None) -> List[str]:
        """Get distinct league_ids that have active (non-expired) predictions."""
        match_stage: Dict[str, Any] = {"expires_at": {"$gt": get_current_time()}}
        if sport:
            match_stage["sport"] = sport
        pipeline = [
            {"$match": match_stage},
            {"$group": {"_id": "$league_id"}},
            {"$sort": {"_id": 1}},
        ]
        cursor = self.match_predictions.aggregate(pipeline)
        return [doc["_id"] for doc in cursor if doc.get("_id")]

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
        sport: str = "soccer",
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
                    "sport": sport,
                    "data": data,
                    "expires_at": expires_at,
                    "last_updated": get_current_time(),
                },
                "$setOnInsert": {
                    "labeled": False,
                },
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
            sport = p.get("sport", "soccer")
            operations.append(
                UpdateOne(
                    {"match_id": p["match_id"]},
                    {
                        "$set": {
                            "league_id": p["league_id"],
                            "sport": sport,
                            "data": data_payload,
                            "expires_at": expires_at,
                            "last_updated": get_current_time(),
                        },
                        "$setOnInsert": {
                            "labeled": False,
                        },
                    },
                    upsert=True,
                )
            )
        self.match_predictions.bulk_write(operations)

    def get_all_active_predictions(
        self,
        skip: int = 0,
        limit: int = 100,
        league_id: str | None = None,
        sport: str | None = None,
    ) -> List[dict]:
        query: Dict[str, Any] = {"expires_at": {"$gt": get_current_time()}}
        if league_id is not None:
            query["league_id"] = league_id
        if sport is not None:
            query["sport"] = sport
        docs = self.match_predictions.find(query).skip(skip).limit(limit)
        return [_to_prediction_result(doc) for doc in docs]

    def get_league_predictions(
        self, league_id: str, skip: int = 0, limit: int = 100
    ) -> List[dict]:
        docs = (
            self.match_predictions.find(
                {
                    "league_id": league_id,
                    "expires_at": {"$gt": get_current_time()},
                }
            )
            .skip(skip)
            .limit(limit)
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
        """Clear transient collections, preserving the currently-serving model.

        Training results, predictions and the API cache are wiped. The serving
        pointer document and its target artifact (plus the legacy fixed-key
        blob) MUST survive so a failed or interrupted training run never leaves
        serving without a loadable model (ml-artifact-lifecycle).
        """
        pointer = self.get_app_state(ML_SERVING_POINTER_KEY) or {}
        protected_keys = {ML_LEGACY_BLOB_KEY}
        if pointer.get("artifact_key") and pointer.get("version"):
            protected_keys.add(
                self._versioned_doc_key(pointer["artifact_key"], pointer["version"])
            )

        training_deleted = self.training_results.delete_many({}).deleted_count
        predictions_deleted = self.match_predictions.delete_many({}).deleted_count
        cache_deleted = self.api_cache.delete_many({}).deleted_count
        app_state_deleted = self.app_state.delete_many(
            {"key": {"$ne": ML_SERVING_POINTER_KEY}}
        ).deleted_count
        artifacts_deleted = self.binary_artifacts.delete_many(
            {"key": {"$nin": sorted(protected_keys)}}
        ).deleted_count

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

    # ------------------------------------------------------------------
    # Versioned ML artifacts + atomic serving pointer
    # ------------------------------------------------------------------

    @staticmethod
    def _versioned_doc_key(key: str, version: str) -> str:
        """Full document key for a versioned artifact (design D1 layout)."""
        return f"{key}/{version}"

    def save_binary_artifact_versioned(
        self, key: str, version: str, binary_data: bytes, meta: Dict[str, Any]
    ) -> None:
        """Insert-once write of a versioned artifact (bytes + meta envelope).

        Raises ValueError when the same version already exists — promoted
        artifacts are immutable; retraining always produces a fresh key.
        """
        from bson.binary import Binary

        try:
            self.binary_artifacts.insert_one(
                {
                    "key": self._versioned_doc_key(key, version),
                    "artifact_key": key,
                    "version": version,
                    "data": Binary(binary_data),
                    "meta": _to_bson_friendly(meta or {}),
                    "last_updated": get_current_time(),
                }
            )
        except DuplicateKeyError as exc:
            raise ValueError(
                f"Artifact {key!r} version {version!r} already exists"
            ) from exc

    def get_versioned_artifact(
        self, key: str, version: str
    ) -> Tuple[Optional[bytes], Optional[dict]]:
        """Return (bytes, metadata envelope) for a versioned artifact."""
        doc = self.binary_artifacts.find_one(
            {"key": self._versioned_doc_key(key, version)}
        )
        if not doc or "data" not in doc:
            return None, None
        return bytes(doc["data"]), doc.get("meta")

    def list_versions(self, key_prefix: str) -> List[str]:
        """List stored versions for an artifact key, oldest first."""
        docs = self.binary_artifacts.find({"artifact_key": key_prefix}, {"version": 1})
        return sorted(doc["version"] for doc in docs if "version" in doc)

    def delete_binary_artifact(self, key: str) -> bool:
        """Delete one artifact document by exact key (retention pruning only)."""
        result = self.binary_artifacts.delete_one({"key": key})
        return bool(result.deleted_count > 0)

    def promote_serving_pointer(
        self,
        pointer_key: str = ML_SERVING_POINTER_KEY,
        artifact_key: str = "",
        version: str = "",
        metrics: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """Atomically repoint serving to a promoted version (find-and-modify).

        Readers via ``get_app_state`` observe complete old-or-new state —
        never partial or null — because this is exactly one document update.
        """
        pointer_data: dict = {
            "artifact_key": artifact_key,
            "version": version,
            "promoted_at": get_current_time().isoformat(),
            "metrics": _to_bson_friendly(metrics or {}),
        }
        doc = self.app_state.find_one_and_update(
            {"key": pointer_key},
            {"$set": {"data": pointer_data, "last_updated": get_current_time()}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        logger.info(
            "Serving pointer %s promoted to %s@%s",
            pointer_key,
            artifact_key,
            version,
        )
        if doc and "data" in doc:
            return dict(doc["data"])
        return pointer_data


# Singleton accessor with old name alias to avoid changing dependencies everywhere
_mongo_repo = None


def get_mongo_repository() -> MongoRepository:
    global _mongo_repo
    if _mongo_repo is None:
        _mongo_repo = MongoRepository()
    return _mongo_repo
