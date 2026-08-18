"""
Async Mongo Adapter (DEPRECATED - para cleanup post-validación)

Provides an async-friendly adapter for Mongo operations. If `motor` is
available, it uses `AsyncIOMotorClient`. Otherwise it wraps the existing
`MongoRepository` and offloads calls to a threadpool using
`asyncio.to_thread`.

This allows gradual migration to Motor while keeping a backwards-compatible
sync `MongoRepository` in place.

DEPRECATION NOTE:
    Este adapter será eliminado post-validación de AsyncMongoRepository.
    Una vez que el benchmark y staged rollout confirmen estabilidad, usar
    solo AsyncMongoRepository (Motor-native) y remover este fallback.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple, cast

from src.utils.time_utils import get_current_time, is_future_time

logger = logging.getLogger(__name__)

try:
    from motor.motor_asyncio import AsyncIOMotorClient as MotorClient

    HAS_MOTOR = True
except Exception:
    HAS_MOTOR = False


class AsyncMongoAdapter:
    """Async adapter that exposes async methods used by async codepaths.

    If Motor is available it performs native async DB calls. Otherwise it
    delegates to the sync `MongoRepository` using `asyncio.to_thread`.
    """

    def __init__(self, mongo_uri: Optional[str] = None, db_name: Optional[str] = None):
        mongo_uri = mongo_uri or os.getenv(
            "MONGO_URI", "mongodb://admin:adminpassword@localhost:27017/"
        )
        db_name = db_name or os.getenv("MONGO_DB_NAME", "bjj_betsports")

        self._use_motor = HAS_MOTOR
        self._motor_client: Optional[MotorClient] = None
        self._db = None
        self._sync_repo = None

        if self._use_motor:
            try:
                if db_name is None:
                    raise ValueError("db_name must be provided")
                self._motor_client = MotorClient(mongo_uri)
                self._db = self._motor_client[db_name]
                # Note: indexes are expected to exist already (created by sync repo),
                # or will be created later during migration.
                self.training_results = self._db["training_results"]
                self.match_predictions = self._db["match_predictions"]
                self.api_cache = self._db["api_cache"]
                self.app_state = self._db["app_state"]
                self.binary_artifacts = self._db["binary_artifacts"]
                logger.info("AsyncMongoAdapter: using Motor (async) MongoDB client")
            except Exception as e:
                logger.warning(
                    "AsyncMongoAdapter: Motor init failed, falling back: %s", e
                )
                self._use_motor = False

        if not self._use_motor:
            # Lazy import to avoid circular import costs
            from src.infrastructure.repositories.mongo_repository import (
                get_mongo_repository,
            )

            self._sync_repo = get_mongo_repository()
            logger.info(
                "AsyncMongoAdapter: using sync MongoRepository wrapped with to_thread"
            )

    async def get_cached_response(
        self, endpoint: str, params: dict | None = None
    ) -> Optional[dict]:
        key = f"{endpoint}:{str(params)}"
        if self._use_motor:
            doc = await self.api_cache.find_one({"key": key})
            if doc and is_future_time(doc.get("expires_at")):
                return cast(Optional[dict], doc.get("data"))
            return None
        else:
            if not self._sync_repo:
                return None
            return await asyncio.to_thread(
                self._sync_repo.get_cached_response, endpoint, params
            )

    async def save_cached_response(
        self,
        endpoint: str,
        data: dict,
        params: dict | None = None,
        ttl_seconds: int = 3600,
    ) -> None:
        key = f"{endpoint}:{str(params)}"
        expires_at = get_current_time() + timedelta(seconds=ttl_seconds)
        if self._use_motor:
            await self.api_cache.update_one(
                {"key": key},
                {"$set": {"data": data, "expires_at": expires_at}},
                upsert=True,
            )
        else:
            if self._sync_repo:
                await asyncio.to_thread(
                    self._sync_repo.save_cached_response,
                    endpoint,
                    data,
                    params,
                    ttl_seconds,
                )

    async def get_match_prediction(self, match_id: str) -> Optional[dict]:
        if self._use_motor:
            doc = await self.match_predictions.find_one({"match_id": match_id})
            if doc and is_future_time(doc.get("expires_at")):
                return cast(Optional[dict], doc.get("data"))
            return None
        else:
            if not self._sync_repo:
                return None
            return await asyncio.to_thread(
                self._sync_repo.get_match_prediction, match_id
            )

    async def get_match_prediction_document(self, match_id: str) -> Optional[dict]:
        """Return the full match_predictions document (including league_id)."""
        if self._use_motor:
            doc = await self.match_predictions.find_one({"match_id": match_id})
            return cast(Optional[dict], doc)
        else:
            if not self._sync_repo:
                return None

            # Fallback: call sync repo in thread and return the raw document
            def _get_doc() -> Optional[dict]:
                assert self._sync_repo is not None
                return cast(
                    Optional[dict],
                    self._sync_repo.match_predictions.find_one({"match_id": match_id}),
                )

            return await asyncio.to_thread(_get_doc)

    async def get_match_predictions_bulk(self, match_ids: List[str]) -> Dict[str, dict]:
        if not match_ids:
            return {}

        if self._use_motor:
            docs = await self.match_predictions.find(
                {
                    "match_id": {"$in": match_ids},
                    "expires_at": {"$gt": get_current_time()},
                }
            ).to_list(length=None)
            result: Dict[str, dict] = {}
            for doc in docs:
                mid = doc.get("match_id")
                if mid:
                    result[mid] = doc.get("data")
            return result
        else:
            if not self._sync_repo:
                return {}
            return await asyncio.to_thread(
                self._sync_repo.get_match_predictions_bulk, match_ids
            )

    async def save_match_prediction(
        self, match_id: str, league_id: str, data: dict, ttl_seconds: int = 86400
    ) -> None:
        expires_at = get_current_time() + timedelta(seconds=ttl_seconds)
        if self._use_motor:
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
        else:
            if self._sync_repo:
                await asyncio.to_thread(
                    self._sync_repo.save_match_prediction,
                    match_id,
                    league_id,
                    data,
                    ttl_seconds,
                )

    async def bulk_save_predictions(self, predictions_data: List[dict]) -> None:
        if not predictions_data:
            return
        if self._use_motor:
            # Perform bulk updates sequentially to avoid complex bulk API differences
            for p in predictions_data:
                data_payload = p.get("data") or {}
                expires_at = get_current_time() + timedelta(
                    seconds=p.get("ttl_seconds", 86400)
                )
                await self.match_predictions.update_one(
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
        else:
            if self._sync_repo:
                await asyncio.to_thread(
                    self._sync_repo.bulk_save_predictions, predictions_data
                )

    async def get_all_active_predictions(
        self,
        skip: int = 0,
        limit: int = 100,
        league_id: str | None = None,
    ) -> List[dict]:
        if self._use_motor:
            query: Dict[str, Any] = {"expires_at": {"$gt": get_current_time()}}
            if league_id is not None:
                query["league_id"] = league_id
            docs = (
                await self.match_predictions.find(query)
                .skip(skip)
                .limit(limit)
                .to_list(length=None)
            )
            return [
                {
                    "match_id": doc["match_id"],
                    "league_id": doc.get("league_id"),
                    "prediction": doc.get("data"),
                    "last_updated": doc.get("last_updated"),
                }
                for doc in docs
            ]

        if not self._sync_repo:
            return []

        return await asyncio.to_thread(
            self._sync_repo.get_all_active_predictions, skip, limit, league_id
        )

    async def get_league_predictions(
        self, league_id: str, skip: int = 0, limit: int = 100
    ) -> List[dict]:
        if self._use_motor:
            docs = (
                await self.match_predictions.find(
                    {
                        "league_id": league_id,
                        "expires_at": {"$gt": get_current_time()},
                    }
                )
                .skip(skip)
                .limit(limit)
                .to_list(length=None)
            )
            return [
                {
                    "match_id": doc["match_id"],
                    "league_id": doc.get("league_id"),
                    "prediction": doc.get("data"),
                    "last_updated": doc.get("last_updated"),
                }
                for doc in docs
            ]

        if not self._sync_repo:
            return []

        return await asyncio.to_thread(
            self._sync_repo.get_league_predictions, league_id, skip, limit
        )

    async def get_training_result_with_timestamp(
        self, key: str
    ) -> Tuple[Optional[dict], Optional[Any]]:
        if self._use_motor:
            doc = await self.training_results.find_one({"key": key})
            if doc:
                return doc.get("data"), doc.get("last_updated")
            return None, None
        else:
            if not self._sync_repo:
                return None, None
            return await asyncio.to_thread(
                self._sync_repo.get_training_result_with_timestamp, key
            )

    async def save_training_result(self, key: str, data: dict) -> None:
        """Save training result document with timestamp."""
        if self._use_motor:
            await self.training_results.update_one(
                {"key": key},
                {"$set": {"data": data, "last_updated": get_current_time()}},
                upsert=True,
            )
        else:
            if self._sync_repo:
                await asyncio.to_thread(self._sync_repo.save_training_result, key, data)


# Singleton factory
_async_mongo_repo: Optional[Any] = None

# Environment-based override for explicit async mode control
_MONGO_ASYNC_MODE: Optional[bool] = None


def _load_async_mode_flag() -> Optional[bool]:
    """Load MONGO_ASYNC_MODE env flag with proper type coercion."""
    global _MONGO_ASYNC_MODE
    if _MONGO_ASYNC_MODE is not None:
        return _MONGO_ASYNC_MODE

    raw = os.getenv("MONGO_ASYNC_MODE", "")
    if raw.lower() in ("1", "true", "yes", "on"):
        _MONGO_ASYNC_MODE = True
    elif raw.lower() in ("0", "false", "no", "off"):
        _MONGO_ASYNC_MODE = False
    else:
        # Default: None means auto-detect based on motor availability
        _MONGO_ASYNC_MODE = None
    return _MONGO_ASYNC_MODE


def _load_required_async_mongo_settings() -> Tuple[str, str]:
    """Load explicit Mongo settings for rollout-controlled async modes.

    When `MONGO_ASYNC_MODE` is explicitly set, do not silently fall back to the
    local default URI. Deployment environments must provide a real Mongo target.
    """
    mongo_uri = os.getenv("MONGO_URI", "").strip()
    db_name = os.getenv("MONGO_DB_NAME", "").strip() or "bjj_betsports"

    if not mongo_uri:
        raise RuntimeError(
            "MONGO_ASYNC_MODE explicit requires MONGO_URI to be set explicitly."
        )

    return mongo_uri, db_name


def reset_async_mongo_repository() -> None:
    """Reset the singleton (useful for testing or reconfiguration)."""
    global _async_mongo_repo
    _async_mongo_repo = None


def get_async_mongo_repository() -> Any:
    """Factory that returns a Motor-native async repository when possible.

    Falls back to `AsyncMongoAdapter` (which may wrap the sync repo) when
    Motor is not available or initialization fails.

    Environment variables:
        MONGO_ASYNC_MODE: Force async mode on/off.
            - "1", "true", "yes", "on": Force Motor-native (raises if unavailable)
            - "0", "false", "no", "off": Force sync fallback (AsyncMongoAdapter)
            - empty/unset: Auto-detect based on motor availability
    """
    global _async_mongo_repo
    if _async_mongo_repo is None:
        async_flag = _load_async_mode_flag()

        if async_flag is False:
            # Explicitly disabled: use sync fallback
            mongo_uri, db_name = _load_required_async_mongo_settings()
            _async_mongo_repo = AsyncMongoAdapter(
                mongo_uri=mongo_uri,
                db_name=db_name,
            )
            logger.info(
                (
                    "get_async_mongo_repository: MONGO_ASYNC_MODE=off, using "
                    "AsyncMongoAdapter (sync)"
                )
            )
        elif async_flag is True:
            # Explicitly enabled: require Motor
            try:
                mongo_uri, db_name = _load_required_async_mongo_settings()
                from src.infrastructure.repositories.async_mongo_repository import (
                    AsyncMongoRepository,
                )

                _async_mongo_repo = AsyncMongoRepository(
                    mongo_uri=mongo_uri,
                    db_name=db_name,
                )
                logger.info(
                    (
                        "get_async_mongo_repository: MONGO_ASYNC_MODE=on, using "
                        "AsyncMongoRepository (Motor)"
                    )
                )
            except Exception as e:
                logger.error(
                    "MONGO_ASYNC_MODE=on but AsyncMongoRepository failed: %s. "
                    "Set MONGO_ASYNC_MODE=off to use sync fallback.",
                    e,
                )
                raise RuntimeError(f"MONGO_ASYNC_MODE=on but motor不可用: {e}") from e
        else:
            # Auto-detect: use Motor if available, fallback otherwise
            if HAS_MOTOR:
                try:
                    from src.infrastructure.repositories.async_mongo_repository import (
                        AsyncMongoRepository,
                    )

                    _async_mongo_repo = AsyncMongoRepository()
                    logger.info(
                        (
                            "get_async_mongo_repository: auto-detect, using "
                            "AsyncMongoRepository (Motor)"
                        )
                    )
                except Exception as e:
                    logger.warning(
                        (
                            "AsyncMongoRepository initialization failed (%s). "
                            "Falling back to AsyncMongoAdapter."
                        ),
                        e,
                    )
                    _async_mongo_repo = AsyncMongoAdapter()
            else:
                _async_mongo_repo = AsyncMongoAdapter()
                logger.info(
                    (
                        "get_async_mongo_repository: auto-detect, motor not "
                        "available, using AsyncMongoAdapter (sync)"
                    )
                )
    return _async_mongo_repo
