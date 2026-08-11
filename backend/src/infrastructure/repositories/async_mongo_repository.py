"""
Motor-native Async MongoDB repository.

This module provides `AsyncMongoRepository`, a fully async implementation
of the persistence operations used by the application. It is intentionally
guarded so importing the module does not raise if `motor` is not installed
— attempts to instantiate the class will raise a clear error.

The repository mirrors the sync `MongoRepository` API but with async methods.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple, cast

from bson.binary import Binary
from pymongo import UpdateOne
from pymongo.errors import OperationFailure
from src.infrastructure.repositories.mongo_repository import (
    _is_index_not_found,
    _is_index_options_conflict,
)
from src.utils.time_utils import get_current_time, is_future_time

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
        self._indexes_ready = False
        self._index_init_task: Optional[asyncio.Task[None]] = None
        self._index_lock = asyncio.Lock()

        self._initialize_indexes()

        logger.info("AsyncMongoRepository initialized (Motor)")

    def _initialize_indexes(self) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self._ensure_indexes())
            return

        self._index_init_task = loop.create_task(self._ensure_indexes())

    async def _await_if_needed(self, value: Any) -> Any:
        if inspect.isawaitable(value):
            return await value
        return value

    async def _ensure_indexes(self) -> None:
        if self._indexes_ready:
            return

        async with self._index_lock:
            if self._indexes_ready:
                return

            await self._await_if_needed(
                self.training_results.create_index("key", unique=True)
            )
            await self._await_if_needed(
                self.match_predictions.create_index("match_id", unique=True)
            )
            await self._await_if_needed(self.api_cache.create_index("key", unique=True))
            await self._await_if_needed(self.app_state.create_index("key", unique=True))
            await self._await_if_needed(
                self.binary_artifacts.create_index("key", unique=True)
            )
            # TTL indexes (expireAfterSeconds=0 — design D2): expired docs are
            # physically purged by MongoDB exactly at expires_at.
            # match_predictions uses a PARTIAL TTL index: only unlabeled docs
            # are purged — labeled docs survive for analytics (C1).
            # MongoDB partial indexes do NOT support $ne, $not, or $exists:False
            # in partialFilterExpression — only $eq, $exists:True, $type, $in, $and.
            # {"labeled": {"$eq": False}} matches unlabeled docs (save_match_prediction
            # and bulk_save_predictions set "labeled": False via $setOnInsert on
            # insert; the auto-labeler overwrites to True afterward).  See D2 / C1.
            await self._ensure_ttl_index(
                self.match_predictions, partial_filter={"labeled": {"$eq": False}}
            )
            await self._ensure_ttl_index(self.api_cache)
            await self._ensure_index(
                self.match_predictions,
                [("league_id", 1), ("expires_at", 1)],
                unique=False,
            )
            self._indexes_ready = True

    async def _ensure_ttl_index(
        self,
        collection: Any,
        field: str = "expires_at",
        seconds: int = 0,
        partial_filter: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Create a TTL index idempotently, optionally partial (C1).

        Async mirror of the sync helper: only a genuine IndexOptionsConflict
        (codes 85/86/67) triggers drop+recreate; IndexNotFound during the
        drop and any recreate failure are logged, never raised (W1).
        """
        index_options: Dict[str, Any] = {"expireAfterSeconds": seconds}
        if partial_filter is not None:
            index_options["partialFilterExpression"] = partial_filter

        try:
            await self._await_if_needed(
                collection.create_index([(field, 1)], **index_options)
            )
            return
        except OperationFailure as exc:
            if not _is_index_options_conflict(exc):
                raise
            logger.warning(
                "TTL index %s_1 conflicts with an existing index; rebuilding.",
                field,
            )

        try:
            await self._await_if_needed(collection.drop_index(f"{field}_1"))
        except OperationFailure as exc:
            # Index may have been dropped concurrently; recreate below still
            # converges. Log and continue — the app must keep booting.
            if not _is_index_not_found(exc):
                logger.warning("Failed to drop index %s_1: %s", field, exc)

        try:
            await self._await_if_needed(
                collection.create_index([(field, 1)], **index_options)
            )
        except Exception as exc:
            logger.warning("Failed to recreate TTL index %s_1: %s", field, exc)

    async def _ensure_index(
        self,
        collection: Any,
        keys: List[Tuple[str, int]],
        unique: bool,
    ) -> None:
        try:
            await self._await_if_needed(collection.create_index(keys, unique=unique))
        except OperationFailure as exc:
            if not _is_index_options_conflict(exc):
                raise
            logger.warning(
                "Index %s conflicts with an existing index; rebuilding.",
                keys,
            )
        except Exception as exc:
            logger.warning("Failed to create index %s: %s", keys, exc)

    async def _ensure_ready(self) -> None:
        if self._indexes_ready:
            return

        if self._index_init_task is not None:
            await self._index_init_task
            return

        await self._ensure_indexes()

    async def save_training_result(self, key: str, data: dict) -> None:
        await self._ensure_ready()
        normalized = _to_bson_friendly(data)
        await self.training_results.update_one(
            {"key": key},
            {"$set": {"data": normalized, "last_updated": get_current_time()}},
            upsert=True,
        )

    async def get_training_result(self, key: str) -> Optional[dict]:
        await self._ensure_ready()
        doc = await self.training_results.find_one({"key": key})
        return doc.get("data") if doc else None

    async def get_training_result_with_timestamp(
        self, key: str
    ) -> Tuple[Optional[dict], Optional[Any]]:
        await self._ensure_ready()
        doc = await self.training_results.find_one({"key": key})
        if doc:
            return doc.get("data"), doc.get("last_updated")
        return None, None

    async def get_training_results_by_pattern(self, pattern: str) -> dict:
        await self._ensure_ready()
        regex_pattern = pattern.replace("%", ".*")
        cursor = self.training_results.find({"key": {"$regex": f"^{regex_pattern}$"}})
        out = {}
        async for doc in cursor:
            out[doc["key"]] = doc["data"]
        return out

    async def save_match_prediction(
        self, match_id: str, league_id: str, data: dict, ttl_seconds: int = 86400
    ) -> None:
        await self._ensure_ready()
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
                },
                "$setOnInsert": {
                    "labeled": False,
                },
            },
            upsert=True,
        )

    async def get_match_prediction(self, match_id: str) -> Optional[dict]:
        await self._ensure_ready()
        doc = await self.match_predictions.find_one({"match_id": match_id})
        if doc and is_future_time(doc.get("expires_at")):
            return cast(Optional[dict], doc.get("data"))
        return None

    async def get_match_prediction_document(self, match_id: str) -> Optional[dict]:
        """Return the full match_predictions document (including league_id)."""
        await self._ensure_ready()
        doc = await self.match_predictions.find_one({"match_id": match_id})
        return cast(Optional[dict], doc)

    async def get_match_predictions_bulk(self, match_ids: List[str]) -> Dict[str, dict]:
        await self._ensure_ready()
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
        await self._ensure_ready()
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
                        },
                        "$setOnInsert": {
                            "labeled": False,
                        },
                    },
                    upsert=True,
                )
            )

        if operations:
            await self.match_predictions.bulk_write(operations)

    async def get_all_active_predictions(
        self,
        skip: int = 0,
        limit: int = 100,
        league_id: str | None = None,
    ) -> List[dict]:
        await self._ensure_ready()
        query: Dict[str, Any] = {"expires_at": {"$gt": get_current_time()}}
        if league_id is not None:
            query["league_id"] = league_id
        cursor = self.match_predictions.find(query).skip(skip).limit(limit)
        out = []
        async for doc in cursor:
            out.append(_to_prediction_result(doc))
        return out

    async def get_league_predictions(
        self, league_id: str, skip: int = 0, limit: int = 100
    ) -> List[dict]:
        await self._ensure_ready()
        cursor = (
            self.match_predictions.find(
                {
                    "league_id": league_id,
                    "expires_at": {"$gt": get_current_time()},
                }
            )
            .skip(skip)
            .limit(limit)
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
        await self._ensure_ready()
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
        await self._ensure_ready()
        key = f"{endpoint}:{str(params)}"
        doc = await self.api_cache.find_one({"key": key})
        if doc and is_future_time(doc.get("expires_at")):
            return cast(Optional[dict], doc.get("data"))
        return None

    async def clear_all_predictions(
        self, league_ids: Optional[List[str]] = None
    ) -> bool:
        await self._ensure_ready()
        if league_ids:
            await self.match_predictions.delete_many({"league_id": {"$in": league_ids}})
        else:
            await self.match_predictions.delete_many({})
        return True

    async def clear_all_data(self) -> Dict[str, int]:
        await self._ensure_ready()
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
        await self._ensure_ready()
        normalized = _to_bson_friendly(data)
        await self.app_state.update_one(
            {"key": key},
            {"$set": {"data": normalized, "last_updated": get_current_time()}},
            upsert=True,
        )

    async def get_app_state(self, key: str) -> Optional[dict]:
        await self._ensure_ready()
        doc = await self.app_state.find_one({"key": key})
        return doc.get("data") if doc else None

    async def save_binary_artifact(self, key: str, binary_data: bytes) -> None:
        await self._ensure_ready()
        await self.binary_artifacts.update_one(
            {"key": key},
            {"$set": {"data": Binary(binary_data), "last_updated": get_current_time()}},
            upsert=True,
        )

    async def get_binary_artifact(self, key: str) -> Optional[bytes]:
        await self._ensure_ready()
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
