"""
Caching Service
===============
Redis-based caching for dashboard data, KPI series, and query results.
Falls back to in-memory cache if Redis is not available.
"""
import json
import logging
import time
from typing import Any, Optional
from datetime import datetime, timezone
UTC = timezone.utc

logger = logging.getLogger(__name__)

# In-memory fallback cache
_memory_cache: dict[str, dict] = {}
_cache_ttl = 300  # 5 minutes default

# Try to import Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory cache")


class CacheService:
    """Unified caching service with Redis + in-memory fallback."""
    
    def __init__(self):
        self.redis_client = None
        if REDIS_AVAILABLE:
            try:
                import os
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
                logger.info("Redis cache connected")
            except Exception as e:
                logger.warning(f"Redis connection failed, using in-memory cache: {e}")
                self.redis_client = None
    
    def _make_key(self, prefix: str, user_id: str, *args) -> str:
        """Generate cache key."""
        parts = [prefix, user_id] + [str(a) for a in args]
        return ":".join(parts)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            if self.redis_client:
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)
            else:
                entry = _memory_cache.get(key)
                if entry and entry["expires"] > time.time():
                    return entry["value"]
                elif entry:
                    del _memory_cache[key]
        except Exception as e:
            logger.debug(f"Cache get error: {e}")
        return None
    
    def set(self, key: str, value: Any, ttl: int = _cache_ttl):
        """Set value in cache."""
        try:
            if self.redis_client:
                self.redis_client.setex(key, ttl, json.dumps(value, default=str))
            else:
                _memory_cache[key] = {
                    "value": value,
                    "expires": time.time() + ttl,
                }
        except Exception as e:
            logger.debug(f"Cache set error: {e}")
    
    def delete(self, key: str):
        """Delete value from cache."""
        try:
            if self.redis_client:
                self.redis_client.delete(key)
            else:
                _memory_cache.pop(key, None)
        except Exception as e:
            logger.debug(f"Cache delete error: {e}")
    
    def invalidate_user(self, user_id: str, prefix: str):
        """Invalidate all cache entries for a user."""
        try:
            if self.redis_client:
                pattern = f"{prefix}:{user_id}:*"
                cursor = 0
                while True:
                    cursor, keys = self.redis_client.scan(cursor=cursor, match=pattern, count=500)
                    if keys:
                        self.redis_client.delete(*keys)
                    if cursor == 0:
                        break
            else:
                keys_to_delete = [k for k in _memory_cache if k.startswith(f"{prefix}:{user_id}:")]
                for k in keys_to_delete:
                    del _memory_cache[k]
        except Exception as e:
            logger.debug(f"Cache invalidate error: {e}")


# Global cache instance
cache = CacheService()


def cache_key(prefix: str, user_id: str, *args) -> str:
    """Generate cache key."""
    return cache._make_key(prefix, user_id, *args)


def get_cached(key: str) -> Optional[Any]:
    """Get from cache."""
    return cache.get(key)


def set_cached(key: str, value: Any, ttl: int = _cache_ttl):
    """Set in cache."""
    cache.set(key, value, ttl)


def invalidate_user_cache(user_id: str, prefix: str = "v1"):
    """Invalidate all cache entries for a user across all prefixes."""
    for p in ("v1:summary", "v1:kpi_series"):
        cache.invalidate_user(user_id, p)
    # Also invalidate by the generic prefix if caller passes one
    if prefix not in ("v1", "v1:summary", "v1:kpi_series"):
        cache.invalidate_user(user_id, prefix)