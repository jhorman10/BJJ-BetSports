"""
Redis Client Module

Provides a wrapper for Redis operations with JSON serialization support.
"""

import json
import logging
import os
from typing import Any, Optional, Union
import redis
from datetime import timedelta

logger = logging.getLogger(__name__)

class RedisClient:
    """Wrapper for Redis operations with JSON support."""
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: int = 0,
        password: Optional[str] = None,
        decode_responses: bool = True
    ):
        self.host = host or os.getenv("REDIS_HOST", "localhost")
        self.port = port or int(os.getenv("REDIS_PORT", 6379))
        self.password = password or os.getenv("REDIS_PASSWORD", None)
        self.db = db
        
        try:
            self._redis = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=decode_responses,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # Test connection
            self._redis.ping()
            logger.info(f"Connected to Redis at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._redis = None

    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        if self._redis is None:
            return False
        try:
            return self._redis.ping()
        except Exception:
            return False

    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis and deserialize JSON."""
        if not self.is_connected:
            return None
            
        try:
            value = self._redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error getting key {key} from Redis: {e}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[Union[int, timedelta]] = None
    ) -> bool:
        """Serialize value to JSON and set in Redis with optional TTL."""
        if not self.is_connected:
            return False
            
        try:
            serialized_value = json.dumps(value, default=str)
            return self._redis.set(key, serialized_value, ex=ttl_seconds)
        except Exception as e:
            logger.error(f"Error setting key {key} in Redis: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        if not self.is_connected:
            return False
        try:
            return bool(self._redis.delete(key))
        except Exception as e:
            logger.error(f"Error deleting key {key} from Redis: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        if not self.is_connected:
            return False
        try:
            return bool(self._redis.exists(key))
        except Exception as e:
            logger.error(f"Error checking existence for key {key} in Redis: {e}")
            return False

    def keys(self, pattern: str = "*") -> list:
        """List keys matching pattern."""
        if not self.is_connected:
            return []
        try:
            return self._redis.keys(pattern)
        except Exception as e:
            logger.error(f"Error listing keys for pattern {pattern} in Redis: {e}")
            return []

# Singleton instance
_redis_instance = None

def get_redis_client() -> RedisClient:
    """Get global Redis client instance."""
    global _redis_instance
    if _redis_instance is None:
        _redis_instance = RedisClient()
    return _redis_instance
