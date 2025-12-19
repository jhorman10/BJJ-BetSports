"""
Cache Service Module

In-memory caching with TTL support for reducing API latency
and optimizing data access patterns.
"""

from datetime import datetime, timedelta
from typing import Any, Optional, Dict, TypeVar, Generic
from dataclasses import dataclass, field
import threading
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """A single cache entry with expiration tracking."""
    value: T
    created_at: datetime
    ttl_seconds: int
    
    @property
    def is_expired(self) -> bool:
        """Check if the entry has expired."""
        return datetime.utcnow() > self.created_at + timedelta(seconds=self.ttl_seconds)
    
    @property
    def age_seconds(self) -> float:
        """Get age of cache entry in seconds."""
        return (datetime.utcnow() - self.created_at).total_seconds()


class CacheService:
    """
    Thread-safe in-memory cache service with TTL support.
    
    Provides different TTL presets for different data types:
    - LIVE_MATCHES: 30 seconds (frequently updated)
    - PREDICTIONS: 5 minutes (computationally expensive)
    - HISTORICAL: 1 hour (rarely changes)
    - LEAGUES: 24 hours (static data)
    """
    
    # TTL Presets (in seconds)
    TTL_LIVE_MATCHES = 30
    TTL_PREDICTIONS = 300  # 5 minutes
    TTL_HISTORICAL = 3600  # 1 hour
    TTL_LEAGUES = 86400    # 24 hours
    
    def __init__(self):
        """Initialize the cache service."""
        self._cache: Dict[str, CacheEntry[Any]] = {}
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._misses += 1
                return None
                
            if entry.is_expired:
                # Clean up expired entry
                del self._cache[key]
                self._misses += 1
                logger.debug(f"Cache miss (expired): {key}")
                return None
            
            self._hits += 1
            logger.debug(f"Cache hit: {key} (age: {entry.age_seconds:.1f}s)")
            return entry.value
    
    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time-to-live in seconds
        """
        with self._lock:
            self._cache[key] = CacheEntry(
                value=value,
                created_at=datetime.utcnow(),
                ttl_seconds=ttl_seconds,
            )
            logger.debug(f"Cache set: {key} (TTL: {ttl_seconds}s)")
    
    def invalidate(self, key: str) -> bool:
        """
        Invalidate a specific cache entry.
        
        Args:
            key: Cache key to invalidate
            
        Returns:
            True if entry was found and removed
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache invalidated: {key}")
                return True
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all cache entries matching a pattern.
        
        Args:
            pattern: Key prefix to match
            
        Returns:
            Number of entries invalidated
        """
        with self._lock:
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(pattern)]
            for key in keys_to_remove:
                del self._cache[key]
            if keys_to_remove:
                logger.debug(f"Cache invalidated {len(keys_to_remove)} entries with pattern: {pattern}")
            return len(keys_to_remove)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache cleared: {count} entries removed")
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        with self._lock:
            expired_keys = [
                k for k, v in self._cache.items() if v.is_expired
            ]
            for key in expired_keys:
                del self._cache[key]
            if expired_keys:
                logger.debug(f"Cache cleanup: {len(expired_keys)} expired entries removed")
            return len(expired_keys)
    
    @property
    def stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            return {
                "entries": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{hit_rate:.1f}%",
            }
    
    # Convenience methods for specific cache types
    
    def get_live_matches(self, key_suffix: str = "") -> Optional[Any]:
        """Get cached live matches."""
        return self.get(f"live_matches:{key_suffix}")
    
    def set_live_matches(self, value: Any, key_suffix: str = "") -> None:
        """Cache live matches with appropriate TTL."""
        self.set(f"live_matches:{key_suffix}", value, self.TTL_LIVE_MATCHES)
    
    def get_predictions(self, match_id: str) -> Optional[Any]:
        """Get cached prediction for a match."""
        return self.get(f"prediction:{match_id}")
    
    def set_predictions(self, match_id: str, value: Any) -> None:
        """Cache prediction with appropriate TTL."""
        self.set(f"prediction:{match_id}", value, self.TTL_PREDICTIONS)
    
    def get_historical(self, league_id: str, seasons: str) -> Optional[Any]:
        """Get cached historical data."""
        return self.get(f"historical:{league_id}:{seasons}")
    
    def set_historical(self, league_id: str, seasons: str, value: Any) -> None:
        """Cache historical data with appropriate TTL."""
        self.set(f"historical:{league_id}:{seasons}", value, self.TTL_HISTORICAL)


# Singleton instance
_cache_instance: Optional[CacheService] = None
_instance_lock = threading.Lock()


def get_cache_service() -> CacheService:
    """
    Get the singleton cache service instance.
    
    Returns:
        CacheService singleton
    """
    global _cache_instance
    if _cache_instance is None:
        with _instance_lock:
            if _cache_instance is None:
                _cache_instance = CacheService()
                logger.info("CacheService initialized")
    return _cache_instance
