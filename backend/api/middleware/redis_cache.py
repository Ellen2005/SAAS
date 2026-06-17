"""
Redis Caching Middleware
========================
Optional Redis caching for frequently accessed data.

Falls back to in-memory cache if Redis is not available.
"""

import json
import logging
import hashlib
from typing import Optional
from functools import wraps

logger = logging.getLogger(__name__)

# Try to import Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not installed. Install with: pip install redis")


class CacheManager:
    """Simple cache manager with Redis backend and in-memory fallback."""
    
    def __init__(self):
        self.redis_client = None
        self.memory_cache = {}
        self._init_redis()
    
    def _init_redis(self):
        if not REDIS_AVAILABLE:
            return
        
        try:
            import os
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            logger.info("Redis cache connected")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Using in-memory cache.")
            self.redis_client = None
    
    def get(self, key: str) -> Optional[str]:
        if self.redis_client:
            try:
                return self.redis_client.get(key)
            except Exception:
                pass
        return self.memory_cache.get(key)
    
    def set(self, key: str, value: str, ttl: int = 300):
        if self.redis_client:
            try:
                self.redis_client.setex(key, ttl, value)
                return
            except Exception:
                pass
        self.memory_cache[key] = value
    
    def delete(self, key: str):
        if self.redis_client:
            try:
                self.redis_client.delete(key)
            except Exception:
                pass
        self.memory_cache.pop(key, None)
    
    def clear(self):
        if self.redis_client:
            try:
                self.redis_client.flushdb()
            except Exception:
                pass
        self.memory_cache.clear()


# Global cache instance
cache = CacheManager()


def cache_response(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator to cache API responses.
    
    Usage:
        @cache_response(ttl=60, key_prefix="dashboard")
        def get_dashboard_data():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_data = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()
            
            # Try to get from cache
            cached = cache.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            try:
                cache.set(cache_key, json.dumps(result), ttl=ttl)
            except Exception:
                pass
            
            return result
        return wrapper
    return decorator


# Helper functions for manual caching
def cache_get(key: str) -> Optional[dict]:
    """Get cached data."""
    cached = cache.get(key)
    return json.loads(cached) if cached else None


def cache_set(key: str, value: dict, ttl: int = 300):
    """Set cached data."""
    try:
        cache.set(key, json.dumps(value), ttl=ttl)
    except Exception:
        pass


def cache_invalidate(pattern: str):
    """Invalidate cache entries matching pattern."""
    if cache.redis_client:
        try:
            keys = cache.redis_client.keys(f"*{pattern}*")
            if keys:
                cache.redis_client.delete(*keys)
        except Exception:
            pass