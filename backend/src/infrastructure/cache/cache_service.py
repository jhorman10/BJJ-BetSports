from datetime import datetime, timedelta
from typing import Any, Optional, Dict, TypeVar, Generic
import threading
import logging
from src.infrastructure.cache.redis_client import get_redis_client

logger = logging.getLogger(__name__)

T = TypeVar('T')

class CacheService:
    """
    Cache service with Redis backend and in-memory secondary layer.
    
    Provides different TTL presets:
    - LIVE_MATCHES: 30 seconds
    - PREDICTIONS: 5 minutes
    - HISTORICAL: 1 hour
    - LEAGUES: 24 hours
    - FORECASTS: 24 hours (for scheduled batch results)
    """
    
    # TTL Presets (in seconds)
    TTL_LIVE_MATCHES = 30
    TTL_PREDICTIONS = 300
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
        
    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache (Redis first, then memory)."""
        # Try Redis first
        if self.redis.is_connected:
            value = self.redis.get(key)
            if value:
                self._hits += 1
                return value
        
        # Fallback to memory (mostly for transient data or if Redis is down)
        with self._lock:
            value = self._memory_cache.get(key)
            if value:
                self._hits += 1
                return value
            
        self._misses += 1
        return None
    
    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Set a value in both Redis and Memory."""
        if self.redis.is_connected:
            self.redis.set(key, value, ttl_seconds)
            
        with self._lock:
            self._memory_cache[key] = value
            # In memory we don't strictly enforce TTL for simplicity 
            # as Redis is the primary source for fresh data.
            # But we could add it if memory usage becomes an issue.
    
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
