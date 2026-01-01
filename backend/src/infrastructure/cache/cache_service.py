import os
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, TypeVar, Generic
import threading
import logging
import diskcache

logger = logging.getLogger(__name__)

T = TypeVar('T')

class CacheService:
    """
    Cache service using DiskCache as primary backend and in-memory secondary layer.
    Redis has been removed to simplify the architecture.
    
    Provides different TTL presets:
    - LIVE_MATCHES: 30 seconds
    - PREDICTIONS: 24 hours
    - HISTORICAL: 1 hour
    - LEAGUES: 24 hours
    - FORECASTS: 24 hours (for scheduled batch results)
    """
    
    # TTL Presets (in seconds)
    TTL_LIVE_MATCHES = 30
    TTL_PREDICTIONS = 86400  # 24 hours
    TTL_HISTORICAL = 3600
    TTL_LEAGUES = 86400
    TTL_FORECASTS = 86400
    
    def __init__(self):
        """Initialize the cache service."""
        self._memory_cache: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        
        # Low Memory optimization
        self.low_memory_mode = os.getenv("LOW_MEMORY_MODE", "false").lower() == "true"
        
        # Initialize DiskCache
        cache_dir = os.path.join(os.getcwd(), ".cache_data")
        self._disk_cache = diskcache.Cache(cache_dir)
        logger.info(f"DiskCache initialized at {cache_dir}")
        
    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache (Disk -> Memory)."""
        # 1. Try Disk Cache First (Persistence)
        try:
            value = self._disk_cache.get(key)
            if value:
                self._hits += 1
                return value
        except Exception as e:
            logger.warning(f"DiskCache get error: {e}")
        
        # 2. Try Memory (Fallback/Speed if we were using it for small items)
        # Note: In previous design, memory was layer 3. Here we can check it.
        # But usually DiskCache is fast enough. Let's keep memory for non-persistent or extremely hot items if needed.
        with self._lock:
            value = self._memory_cache.get(key)
            if value:
                self._hits += 1
                return value
            
        self._misses += 1
        return None
    
    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Set a value in Disk Cache and Memory."""
        # 1. Set in Disk Cache
        try:
            self._disk_cache.set(key, value, expire=ttl_seconds)
        except Exception as e:
            logger.warning(f"DiskCache set error: {e}")

        # Skip local memory if in Low Memory Mode and it's a large object
        if self.low_memory_mode and (key.startswith("forecasts:") or key.startswith("predictions:")):
            return

        # 2. Set in Memory (Optional optimization)
        with self._lock:
            self._memory_cache[key] = value
    
    def invalidate(self, key: str) -> bool:
        """Invalidate a specific cache entry."""
        disk_ok = False
        try:
            disk_ok = self._disk_cache.delete(key)
        except Exception:
            pass
            
        with self._lock:
            in_mem = key in self._memory_cache
            if in_mem:
                del self._memory_cache[key]
            return disk_ok or in_mem
    
    def clear(self) -> None:
        """Clear all cache entries."""
        try:
            self._disk_cache.clear()
        except Exception:
            pass
        
        with self._lock:
            self._memory_cache.clear()
            logger.info("Cache cleared")
    
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
                logger.info("CacheService initialized (DiskCache-only)")
    return _cache_instance
