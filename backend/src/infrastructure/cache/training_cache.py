"""
Training Cache Module

Stores training results in memory and persists to disk for daily access
without recomputation. Results are cached after the 7 AM daily training
and served until the next training run.
"""

import json
import os
import logging
from datetime import datetime, date
from typing import Optional, Dict, Any
from pathlib import Path
import threading

logger = logging.getLogger(__name__)

# Default cache directory
CACHE_DIR = Path(os.getenv("TRAINING_CACHE_DIR", "/tmp/bjj-betsports-cache"))


class TrainingCache:
    """
    Thread-safe cache for training results.
    
    Stores results in memory for fast access and persists to disk
    for recovery after server restarts.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._cache: Dict[str, Any] = {}
        self._last_update: Optional[datetime] = None
        self._cache_date: Optional[date] = None
        
        # Ensure cache directory exists
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Try to load existing cache from disk
        self._load_from_disk()
        
        self._initialized = True
        logger.info(f"TrainingCache initialized. Cache dir: {CACHE_DIR}")
    
    def _get_cache_file(self) -> Path:
        """Get the cache file path for today."""
        today = date.today()
        return CACHE_DIR / f"training_{today.strftime('%Y%m%d')}.json"
    
    def _load_from_disk(self):
        """Load cache from disk if available for today."""
        cache_file = self._get_cache_file()
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    self._cache = data.get('results', {})
                    self._last_update = datetime.fromisoformat(data.get('last_update', ''))
                    self._cache_date = date.today()
                    logger.info(f"Loaded training cache from {cache_file}")
            except Exception as e:
                logger.warning(f"Failed to load cache from disk: {e}")
                self._cache = {}
    
    def _save_to_disk(self):
        """Persist cache to disk."""
        cache_file = self._get_cache_file()
        
        try:
            data = {
                'last_update': self._last_update.isoformat() if self._last_update else None,
                'cache_date': self._cache_date.isoformat() if self._cache_date else None,
                'results': self._cache
            }
            
            with open(cache_file, 'w') as f:
                json.dump(data, f, default=str)
                
            logger.info(f"Saved training cache to {cache_file}")
            
            # Clean up old cache files (keep only last 7 days)
            self._cleanup_old_caches()
            
        except Exception as e:
            logger.error(f"Failed to save cache to disk: {e}")
    
    def _cleanup_old_caches(self):
        """Remove cache files older than 7 days."""
        try:
            from datetime import timedelta
            cutoff = date.today() - timedelta(days=7)
            
            for cache_file in CACHE_DIR.glob("training_*.json"):
                try:
                    # Extract date from filename
                    date_str = cache_file.stem.replace("training_", "")
                    file_date = datetime.strptime(date_str, "%Y%m%d").date()
                    
                    if file_date < cutoff:
                        cache_file.unlink()
                        logger.info(f"Deleted old cache file: {cache_file}")
                except Exception:
                    pass  # Skip files with unexpected names
                    
        except Exception as e:
            logger.debug(f"Error cleaning up old caches: {e}")
    
    def set(self, key: str, value: Any):
        """Store a value in cache."""
        with self._lock:
            self._cache[key] = value
            self._last_update = datetime.now()
            self._cache_date = date.today()
            self._save_to_disk()
    
    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from cache."""
        # Check if cache is stale (older than 24 hours)
        if self._last_update:
            from datetime import timedelta
            if datetime.now() - self._last_update > timedelta(hours=24):
                logger.info("Cache is older than 24 hours, returning None")
                return None
            
        return self._cache.get(key)
    
    def get_training_results(self) -> Optional[Dict[str, Any]]:
        """Get the cached training results."""
        return self.get('training_results')
    
    def set_training_results(self, results: Dict[str, Any]):
        """Cache training results."""
        self.set('training_results', results)
        logger.info(f"Cached training results: {results.get('matches_processed', 0)} matches")
    
    def get_last_update(self) -> Optional[datetime]:
        """Get the last cache update time."""
        return self._last_update
    
    def is_valid(self) -> bool:
        """Check if cache is valid (updated within 24 hours)."""
        if not self._last_update or 'training_results' not in self._cache:
            return False
            
        from datetime import timedelta
        return (datetime.now() - self._last_update) < timedelta(hours=24)
    
    def invalidate(self):
        """Invalidate the cache."""
        with self._lock:
            self._cache = {}
            self._last_update = None
            self._cache_date = None
            logger.info("Training cache invalidated")


# Global instance
def get_training_cache() -> TrainingCache:
    """Get the singleton training cache instance."""
    return TrainingCache()
