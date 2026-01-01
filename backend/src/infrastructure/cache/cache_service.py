import os
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, TypeVar, Generic
import threading
import logging
import diskcache
import redis
import json
import pickle

logger = logging.getLogger(__name__)

T = TypeVar('T')


from abc import ABC, abstractmethod

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

class RedisCacheProvider(CacheProvider):
    """Redis cache implementation."""
    
    def __init__(self, host='localhost', port=6379, db=0, password=None):
        try:
            # Flexible connection: Priorities REDIS_URL (Render/Upstash style)
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                self.client = redis.Redis.from_url(redis_url, decode_responses=False)
                host = "URL" # For logging
            else:
                self.client = redis.Redis(
                    host=host, 
                    port=port, 
                    db=db, 
                    password=password,
                    decode_responses=False # Keep bytes for pickling
                )
            self.client.ping()
            logger.info(f"Redis connected at {host}:{port}/{db}")
            self._is_connected = True
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self._is_connected = False
            
    def get(self, key: str) -> Optional[Any]:
        if not self._is_connected: return None
        try:
            data = self.client.get(key)
            if data:
                return pickle.loads(data)
        except Exception as e:
            logger.warning(f"Redis get error for {key}: {e}")
        return None
        
    def set(self, key: str, value: Any, ttl: int) -> bool:
        if not self._is_connected: return False
        try:
            data = pickle.dumps(value)
            return self.client.setex(key, ttl, data)
        except Exception as e:
            logger.warning(f"Redis set error for {key}: {e}")
            return False
            
    def delete(self, key: str) -> bool:
        if not self._is_connected: return False
        try:
            return self.client.delete(key) > 0
        except Exception:
            return False

    def clear(self) -> bool:
        if not self._is_connected: return False
        try:
            return self.client.flushdb()
        except Exception:
            return False

class DiskCacheProvider(CacheProvider):
    """DiskCache implementation."""
    
    def __init__(self, cache_dir: str):
        self.cache = diskcache.Cache(cache_dir)
        logger.info(f"DiskCache initialized at {cache_dir}")
        
    def get(self, key: str) -> Optional[Any]:
        try:
            return self.cache.get(key)
        except Exception:
            return None
            
    def set(self, key: str, value: Any, ttl: int) -> bool:
        try:
            return self.cache.set(key, value, expire=ttl)
        except Exception as e:
            logger.error(f"DiskCache set failed for {key}: {e}")
            return False
            
    def delete(self, key: str) -> bool:
        try:
            return self.cache.delete(key)
        except Exception:
            return False

    def clear(self) -> bool:
        try:
            return self.cache.clear()
        except Exception:
            return False

class CacheService:
    """
    Multi-level Cache Service.
    Priority: Memory -> Redis -> DiskCache
    """
    
    # TTL Presets (in seconds)
    TTL_LIVE_MATCHES = 30
    TTL_PREDICTIONS = 86400  # 24 hours
    TTL_HISTORICAL = 3600
    TTL_LEAGUES = 86400
    TTL_FORECASTS = 86400
    
    def __init__(self):
        """Initialize the cache service with providers."""
        self._memory_cache: Dict[str, Any] = {}
        self._lock = threading.RLock()
        
        # Initialize Providers
        self.providers: list[CacheProvider] = []
        
        # 1. Redis (Primary Distributed)
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        self.redis_provider = RedisCacheProvider(host=redis_host, port=redis_port)
        if self.redis_provider._is_connected:
            self.providers.append(self.redis_provider)
        
        # 2. DiskCache (Local Persistent Fallback)
        cache_dir = os.path.join(os.getcwd(), ".cache_data")
        self.disk_provider = DiskCacheProvider(cache_dir)
        self.providers.append(self.disk_provider)
        
    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache (Memory -> Redis -> Disk)."""
        # 1. Memory
        with self._lock:
            if key in self._memory_cache:
                return self._memory_cache[key]
        
        # 2. Providers
        for provider in self.providers:
            value = provider.get(key)
            if value is not None:
                # Populate memory cache for faster subsequent access (short TTL logic could be added here)
                with self._lock:
                    self._memory_cache[key] = value
                return value
        
        return None
    
    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Set a value in all cache layers."""
        # 1. Memory
        with self._lock:
            self._memory_cache[key] = value
            
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
                logger.info("CacheService initialized (Multi-Level)")
    return _cache_instance
