"""
Motor-native Async MongoDB repository.

This module provides `AsyncMongoRepository`, a fully async implementation
of the persistence operations used by the application. It is intentionally
guarded so importing the module does not raise if `motor` is not installed
— attempts to instantiate the class will raise a clear error.

The repository mirrors the sync `MongoRepository` API but with async methods.
"""

from __future__ import annotations

import logging
import os
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple, cast

from bson.binary import Binary
from pymongo import UpdateOne
from src.utils.time_utils import get_current_time

_mongo_to_bson_friendly: Any

try:
    # reuse helper to normalize data
    from src.infrastructure.repositories.mongo_repository import (
        _to_bson_friendly as _mongo_to_bson_friendly_impl,
    )

    _mongo_to_bson_friendly = _mongo_to_bson_friendly_impl
except Exception:
    _mongo_to_bson_friendly = None

_MotorAsyncIOMotorClient: Any

try:
    from motor.motor_asyncio import AsyncIOMotorClient as _MotorAsyncIOMotorClientImpl

    _MotorAsyncIOMotorClient = _MotorAsyncIOMotorClientImpl
except Exception:
    _MotorAsyncIOMotorClient = None

MotorAsyncIOMotorClient: Any = _MotorAsyncIOMotorClient
HAS_MOTOR = _MotorAsyncIOMotorClient is not None

if _mongo_to_bson_friendly is None:
    # Fallback: minimal serializer if import fails for some reason.
    def _to_bson_friendly(value: Any) -> Any:
        return value

else:
    _to_bson_friendly = _mongo_to_bson_friendly


logger = logging.getLogger(__name__)


def _to_prediction_result(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Expose active prediction docs in the shape expected by callers."""
    return {
        "match_id": doc["match_id"],
        "league_id": doc.get("league_id"),
        "prediction": doc.get("data"),
        "last_updated": doc.get("last_updated"),
    }


class AsyncMongoRepository:
    """Async Motor-based repository exposing the same operations as the
    existing sync `MongoRepository` but with async methods.

    Raises RuntimeError if Motor is not available when instantiated.
    """

    def __init__(self, mongo_uri: Optional[str] = None, db_name: Optional[str] = None):
        if not HAS_MOTOR or MotorAsyncIOMotorClient is None:
            raise RuntimeError(
                "motor (AsyncIOMotorClient) is not available; install motor "
                "to use AsyncMongoRepository"
            )

        mongo_uri = mongo_uri or os.getenv(
            "MONGO_URI", "mongodb://admin:adminpassword@localhost:27017/"
        )
        db_name = db_name or os.getenv("MONGO_DB_NAME", "bjj_betsports")

        self.client = MotorAsyncIOMotorClient(mongo_uri)
        if db_name is None:
            raise ValueError(
                "db_name must be provided or set via MONGO_DB_NAME env var"
            )
        self.db = self.client[db_name]

        # Collections
        self.training_results = self.db["training_results"]
        self.match_predictions = self.db["match_predictions"]
        self.api_cache = self.db["api_cache"]
        self.app_state = self.db["app_state"]
        self.binary_artifacts = self.db["binary_artifacts"]

        logger.info("AsyncMongoRepository initialized (Motor)")

    async def save_training_result(self, key: str, data: dict) -> None:
        normalized = _to_bson_friendly(data)
        await self.training_results.update_one(
            {"key": key},
            {"$set": {"data": normalized, "last_updated": get_current_time()}},
            upsert=True,
        )

    async def get_training_result(self, key: str) -> Optional[dict]:
        doc = await self.training_results.find_one({"key": key})
        return doc.get("data") if doc else None

    async def get_training_result_with_timestamp(
        self, key: str
    ) -> Tuple[Optional[dict], Optional[Any]]:
        doc = await self.training_results.find_one({"key": key})
        if doc:
            return doc.get("data"), doc.get("last_updated")
        return None, None

    async def get_training_results_by_pattern(self, pattern: str) -> dict:
        regex_pattern = pattern.replace("%", ".*")
        cursor = self.training_results.find({"key": {"$regex": f"^{regex_pattern}$"}})
        out = {}
        async for doc in cursor:
            out[doc["key"]] = doc["data"]
        return out

    async def save_match_prediction(
        self, match_id: str, league_id: str, data: dict, ttl_seconds: int = 86400
    ) -> None:
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
            pass

        expires_at = get_current_time() + timedelta(seconds=ttl_seconds)
        await self.match_predictions.update_one(
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

    async def get_match_prediction(self, match_id: str) -> Optional[dict]:
        doc = await self.match_predictions.find_one({"match_id": match_id})
        if doc and doc.get("expires_at") and doc["expires_at"] > get_current_time():
            return cast(Optional[dict], doc.get("data"))
        return None

    async def get_match_prediction_document(self, match_id: str) -> Optional[dict]:
        """Return the full match_predictions document (including league_id)."""
        doc = await self.match_predictions.find_one({"match_id": match_id})
        return cast(Optional[dict], doc)

    async def get_match_predictions_bulk(self, match_ids: List[str]) -> Dict[str, dict]:
        if not match_ids:
            return {}
        cursor = self.match_predictions.find(
            {"match_id": {"$in": match_ids}, "expires_at": {"$gt": get_current_time()}}
        )
        result: Dict[str, dict] = {}
        async for doc in cursor:
            mid = doc.get("match_id")
            if mid:
                result[mid] = doc.get("data")
        return result

    async def bulk_save_predictions(self, predictions_data: List[dict]) -> None:
        if not predictions_data:
            return

        operations = []
        for p in predictions_data:
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
                            "league_id": p.get("league_id"),
                            "data": data_payload,
                            "expires_at": expires_at,
                            "last_updated": get_current_time(),
                        }
                    },
                    upsert=True,
                )
            )

        if operations:
            await self.match_predictions.bulk_write(operations)

    async def get_all_active_predictions(self) -> List[dict]:
        cursor = self.match_predictions.find(
            {"expires_at": {"$gt": get_current_time()}}
        )
        out = []
        async for doc in cursor:
            out.append(_to_prediction_result(doc))
        return out

    async def get_league_predictions(self, league_id: str) -> List[dict]:
        cursor = self.match_predictions.find(
            {
                "league_id": league_id,
                "expires_at": {"$gt": get_current_time()},
            }
        )
        out = []
        async for doc in cursor:
            out.append(_to_prediction_result(doc))
        return out

    async def save_cached_response(
        self,
        endpoint: str,
        data: dict,
        params: Optional[dict] = None,
        ttl_seconds: int = 3600,
    ) -> None:
        key = f"{endpoint}:{str(params)}"
        expires_at = get_current_time() + timedelta(seconds=ttl_seconds)
        await self.api_cache.update_one(
            {"key": key},
            {"$set": {"data": data, "expires_at": expires_at}},
            upsert=True,
        )

    async def get_cached_response(
        self, endpoint: str, params: Optional[dict] = None
    ) -> Optional[dict]:
        key = f"{endpoint}:{str(params)}"
        doc = await self.api_cache.find_one({"key": key})
        if doc and doc.get("expires_at") and doc["expires_at"] > get_current_time():
            return cast(Optional[dict], doc.get("data"))
        return None

    async def clear_all_predictions(
        self, league_ids: Optional[List[str]] = None
    ) -> bool:
        if league_ids:
            await self.match_predictions.delete_many({"league_id": {"$in": league_ids}})
        else:
            await self.match_predictions.delete_many({})
        return True

    async def clear_all_data(self) -> Dict[str, int]:
        training_deleted = (await self.training_results.delete_many({})).deleted_count
        predictions_deleted = (
            await self.match_predictions.delete_many({})
        ).deleted_count
        cache_deleted = (await self.api_cache.delete_many({})).deleted_count
        app_state_deleted = (await self.app_state.delete_many({})).deleted_count
        artifacts_deleted = (await self.binary_artifacts.delete_many({})).deleted_count

        return {
            "training_results": training_deleted,
            "match_predictions": predictions_deleted,
            "api_cache": cache_deleted,
            "app_state": app_state_deleted,
            "binary_artifacts": artifacts_deleted,
        }

    async def save_app_state(self, key: str, data: dict) -> None:
        normalized = _to_bson_friendly(data)
        await self.app_state.update_one(
            {"key": key},
            {"$set": {"data": normalized, "last_updated": get_current_time()}},
            upsert=True,
        )

    async def get_app_state(self, key: str) -> Optional[dict]:
        doc = await self.app_state.find_one({"key": key})
        return doc.get("data") if doc else None

    async def save_binary_artifact(self, key: str, binary_data: bytes) -> None:
        await self.binary_artifacts.update_one(
            {"key": key},
            {"$set": {"data": Binary(binary_data), "last_updated": get_current_time()}},
            upsert=True,
        )

    async def get_binary_artifact(self, key: str) -> Optional[bytes]:
        doc = await self.binary_artifacts.find_one({"key": key})
        if doc and "data" in doc:
            return bytes(doc["data"])
        return None

    def close(self) -> None:
        try:
            # Motor client supports close()
            self.client.close()
            logger.info("AsyncMongoRepository client closed")
        except Exception as e:
            logger.debug("Error closing Motor client: %s", e)
