import os
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, TypeVar, Generic
import threading
import logging
from src.infrastructure.cache.redis_client import get_redis_client
import diskcache

logger = logging.getLogger(__name__)

T = TypeVar('T')

class CacheService:
    """
    Cache service with Redis backend and in-memory secondary layer.
    
    Provides different TTL presets:
    - LIVE_MATCHES: 30 seconds
    - PREDICTIONS: 24 hours
    - HISTORICAL: 1 hour
    - LEAGUES: 24 hours
    - FORECASTS: 24 hours (for scheduled batch results)
    """
    
    # TTL Presets (in seconds)
    TTL_LIVE_MATCHES = 30
    TTL_PREDICTIONS = 86400  # 24 hours - same as forecasts for consistency
    TTL_HISTORICAL = 3600
    TTL_LEAGUES = 86400
    TTL_FORECASTS = 86400  # 24 hours for scheduled data
    
    def __init__(self):
        """Initialize the cache service."""
        self._memory_cache: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self.redis = get_redis_client()
        self._hits = 0
        self._misses = 0
        
        # Low Memory optimization for Render Free Tier (512MB)
        self.low_memory_mode = os.getenv("LOW_MEMORY_MODE", "false").lower() == "true"
        
        # Initialize DiskCache as a fallback for when Redis is missing
        # This keeps large objects out of RAM but provides persistence
        cache_dir = os.path.join(os.getcwd(), ".cache_data")
        self._disk_cache = diskcache.Cache(cache_dir)
        
        if self.low_memory_mode:
            logger.info("CORE: Low Memory Mode enabled. Local memory cache will be used with disk fallback for large objects.")
        
    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache (Redis -> Disk -> Memory)."""
        # 1. Try Redis first
        if self.redis.is_connected:
            value = self.redis.get(key)
            if value:
                self._hits += 1
                return value
        
        # 2. Try Disk Cache (Fallback for when Redis is missing)
        try:
            value = self._disk_cache.get(key)
            if value:
                self._hits += 1
                return value
        except Exception:
            pass

        # Skip local memory if in Low Memory Mode and it's a large object
        if self.low_memory_mode and (key.startswith("forecasts:") or key.startswith("predictions:")):
            return None

        # 3. Fallback to memory
        with self._lock:
            value = self._memory_cache.get(key)
            if value:
                self._hits += 1
                return value
            
        self._misses += 1
        return None
    
    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Set a value in Redis, Disk, and Memory."""
        # 1. Set in Redis
        if self.redis.is_connected:
            self.redis.set(key, value, ttl_seconds)
            
        # 2. Set in Disk Cache (Always as fallback)
        try:
            self._disk_cache.set(key, value, expire=ttl_seconds)
        except Exception:
            pass

        # Skip local memory if in Low Memory Mode and it's a large object
        if self.low_memory_mode and (key.startswith("forecasts:") or key.startswith("predictions:")):
            return

        # 3. Set in Memory
        with self._lock:
            self._memory_cache[key] = value
    
    def invalidate(self, key: str) -> bool:
        """Invalidate a specific cache entry."""
        redis_ok = False
        if self.redis.is_connected:
            redis_ok = self.redis.delete(key)
            
        with self._lock:
            in_mem = key in self._memory_cache
            if in_mem:
                del self._memory_cache[key]
            return redis_ok or in_mem
    
    def clear(self) -> None:
        """Clear all cache entries."""
        if self.redis.is_connected:
            keys = self.redis.keys("*")
            for k in keys:
                self.redis.delete(k)
        
        with self._lock:
            self._memory_cache.clear()
            logger.info("Cache cleared")
    
    # --- Helper methods for specific cache types ---
    
    def get_live_matches(self, key: str) -> Optional[Any]:
        """Get live matches from cache."""
        return self.get(f"live_matches:{key}")
    
    def set_live_matches(self, data: Any, key: str) -> None:
        """Set live matches in cache with short TTL."""
        self.set(f"live_matches:{key}", data, self.TTL_LIVE_MATCHES)
    
    def get_predictions(self, match_id: str) -> Optional[Any]:
        """Get predictions for a match from cache."""
        return self.get(f"predictions:{match_id}")
    
    def set_predictions(self, match_id: str, data: Any) -> None:
        """Set predictions for a match in cache."""
        self.set(f"predictions:{match_id}", data, self.TTL_PREDICTIONS)
    
    def get_historical(self, league_code: str, seasons_key: str) -> Optional[Any]:
        """Get historical data from cache."""
        return self.get(f"historical:{league_code}:{seasons_key}")
    
    def set_historical(self, league_code: str, seasons_key: str, data: Any) -> None:
        """Set historical data in cache."""
        self.set(f"historical:{league_code}:{seasons_key}", data, self.TTL_HISTORICAL)


    
    def get_league_averages(self, league_id: str) -> Optional[Any]:
        """Get league averages from cache."""
        return self.get(f"league_averages:{league_id}")
    
    def set_league_averages(self, league_id: str, data: Any) -> None:
        """Set league averages in cache."""
        self.set(f"league_averages:{league_id}", data, self.TTL_HISTORICAL) # 1 hour TTL seems appropriate or LEAGUES TTL

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
                logger.info("CacheService initialized with Redis support")
    return _cache_instance
