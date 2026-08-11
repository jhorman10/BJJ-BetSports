import asyncio
import logging
import os
import threading
from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Any, Optional, TypeVar

import diskcache

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheProvider(ABC):
    """Abstract base class for cache providers."""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int) -> bool:
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    def clear(self) -> bool:
        pass

    def close(self) -> None:
        """Optional close method for cleanup."""
        pass


class DiskCacheProvider(CacheProvider):
    """DiskCache implementation."""

    def __init__(self, cache_dir: str) -> None:
        self.cache = diskcache.Cache(cache_dir)
        logger.info(f"DiskCache initialized at {cache_dir}")

    def get(self, key: str) -> Optional[Any]:
        try:
            return self.cache.get(key)
        except Exception as e:
            logger.debug(f"DiskCache get failed for {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int) -> bool:
        try:
            return bool(self.cache.set(key, value, expire=ttl))
        except Exception as e:
            logger.error(f"DiskCache set failed for {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        try:
            return bool(self.cache.delete(key))
        except Exception as e:
            logger.debug(f"DiskCache delete failed for {key}: {e}")
            return False

    def clear(self) -> bool:
        try:
            return bool(self.cache.clear())
        except Exception as e:
            logger.debug(f"DiskCache clear failed: {e}")
            return False

    def close(self) -> None:
        try:
            self.cache.close()
            logger.info("DiskCache closed")
        except Exception as e:
            logger.debug(f"DiskCache close failed: {e}")


class CacheService:
    """
    Multi-level Cache Service.
    Priority: Memory -> DiskCache
    """

    # TTL Presets (in seconds)
    TTL_LIVE_MATCHES = 30
    TTL_PREDICTIONS = 86400  # 24 hours
    TTL_TRAINING = 86400  # 24 hours
    TTL_HISTORICAL = 3600
    TTL_LEAGUES = 86400
    TTL_FORECASTS = 86400
    MAX_MEMORY_ITEMS = 200  # Cap to prevent OOM on 512MB RAM

    def __init__(self) -> None:
        """Initialize the cache service with providers."""
        self._memory_cache: OrderedDict[str, Any] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

        # Initialize Providers
        self.providers: list[CacheProvider] = []

        # 1. DiskCache (Local Persistent Fallback)
        cache_dir = os.path.join(os.getcwd(), ".cache_data")
        self.disk_provider = DiskCacheProvider(cache_dir)
        self.providers.append(self.disk_provider)

    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache (Memory -> Disk)."""
        # 1. Memory (LRU style move-to-end)
        with self._lock:
            if key in self._memory_cache:
                self._hits += 1
                self._memory_cache.move_to_end(key)
                return self._memory_cache[key]

        # 2. Providers
        for provider in self.providers:
            value = provider.get(key)
            if value is not None:
                self._hits += 1
                # Populate memory cache for faster subsequent access
                with self._lock:
                    self._memory_cache[key] = value
                    self._memory_cache.move_to_end(key)
                    # Enforce size limit
                    if len(self._memory_cache) > self.MAX_MEMORY_ITEMS:
                        self._memory_cache.popitem(last=False)
                return value

        self._misses += 1
        return None

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Set a value in all cache layers."""
        # 1. Memory
        with self._lock:
            self._memory_cache[key] = value
            self._memory_cache.move_to_end(key)
            # Enforce size limit
            if len(self._memory_cache) > self.MAX_MEMORY_ITEMS:
                self._memory_cache.popitem(last=False)

        # 2. Providers
        # We write to ALL active providers to keep them in sync/warm
        for provider in self.providers:
            provider.set(key, value, ttl_seconds)

    def invalidate(self, key: str) -> bool:
        """Invalidate a specific cache entry across all layers."""
        with self._lock:
            if key in self._memory_cache:
                del self._memory_cache[key]

        results = [p.delete(key) for p in self.providers]
        return any(results)

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._memory_cache.clear()

        for provider in self.providers:
            provider.clear()

        logger.info("Cache cleared across all layers")

    def close(self) -> None:
        """Close all cache providers."""
        with self._lock:
            for provider in self.providers:
                provider.close()
        logger.info("CacheService closed")

    # --- Helper methods ---

    def get_live_matches(self, key: str) -> Optional[Any]:
        return self.get(f"live_matches:{key}")

    def set_live_matches(self, data: Any, key: str) -> None:
        self.set(f"live_matches:{key}", data, self.TTL_LIVE_MATCHES)

    def get_predictions(self, match_id: str) -> Optional[Any]:
        return self.get(f"predictions:{match_id}")

    def set_predictions(self, match_id: str, data: Any) -> None:
        self.set(f"predictions:{match_id}", data, self.TTL_PREDICTIONS)

    def get_historical(self, league_code: str, seasons_key: str) -> Optional[Any]:
        return self.get(f"historical:{league_code}:{seasons_key}")

    def set_historical(self, league_code: str, seasons_key: str, data: Any) -> None:
        self.set(f"historical:{league_code}:{seasons_key}", data, self.TTL_HISTORICAL)

    def get_league_averages(self, league_id: str) -> Optional[Any]:
        return self.get(f"league_averages:{league_id}")

    def set_league_averages(self, league_id: str, data: Any) -> None:
        self.set(f"league_averages:{league_id}", data, self.TTL_HISTORICAL)

    # --- Async wrappers ---
    async def aget(self, key: str) -> Optional[Any]:
        """Async wrapper for `get` to be used in async contexts.

        Runs the synchronous `get` in a thread to avoid blocking the event loop.
        """
        return await asyncio.to_thread(self.get, key)

    async def aset(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Async wrapper for `set` to be used in async contexts."""
        await asyncio.to_thread(self.set, key, value, ttl_seconds)

    async def aget_live_matches(self, key: str) -> Optional[Any]:
        return await self.aget(f"live_matches:{key}")

    async def aset_live_matches(self, data: Any, key: str) -> None:
        await self.aset(f"live_matches:{key}", data, self.TTL_LIVE_MATCHES)

    async def aget_predictions(self, match_id: str) -> Optional[Any]:
        return await self.aget(f"predictions:{match_id}")

    async def aset_predictions(self, match_id: str, data: Any) -> None:
        await self.aset(f"predictions:{match_id}", data, self.TTL_PREDICTIONS)

    def get_accuracy_history(self, league_id: str) -> Optional[Any]:
        return self.get(f"accuracy_history:{league_id}")

    def set_accuracy_history(self, league_id: str, data: Any) -> None:
        self.set(f"accuracy_history:{league_id}", data, 3600)

    def invalidate_accuracy_history(self, league_id: str) -> bool:
        return self.invalidate(f"accuracy_history:{league_id}")

    async def aget_accuracy_history(self, league_id: str) -> Optional[Any]:
        return await self.aget(f"accuracy_history:{league_id}")

    async def aset_accuracy_history(self, league_id: str, data: Any) -> None:
        await self.aset(f"accuracy_history:{league_id}", data, 3600)

    async def ainvalidate_accuracy_history(self, league_id: str) -> bool:
        return await asyncio.to_thread(self.invalidate_accuracy_history, league_id)

    # Key pattern reference:
    #   accuracy_history:{league_id} -> dict with total_predictions,
    #   exact_score_hits, accuracy_percentage
    #   TTL: 3600 seconds (1 hour). Use aget/aset directly.


# Singleton instance
_cache_instance: Optional[CacheService] = None
_instance_lock = threading.Lock()


def get_cache_service() -> CacheService:
    """Get the singleton cache service instance."""
    global _cache_instance
    if _cache_instance is None:
        with _instance_lock:
            if _cache_instance is None:
                _cache_instance = CacheService()
                logger.info("CacheService initialized (Multi-Level)")
    return _cache_instance
