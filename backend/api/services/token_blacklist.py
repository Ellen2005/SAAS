import os
import time
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_redis_client = None
_use_redis = False
_in_memory_blacklist: Dict[str, float] = {}


def _get_redis():
    """Attempt to connect to Redis using REDIS_URL env var."""
    global _redis_client, _use_redis

    if _redis_client is not None:
        return _redis_client

    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        _use_redis = False
        return None

    try:
        import redis
        _redis_client = redis.from_url(redis_url, decode_responses=True)
        _redis_client.ping()
        _use_redis = True
        logger.info("Connected to Redis for token blacklist")
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis unavailable, falling back to in-memory blacklist: {e}")
        _use_redis = False
        _redis_client = None
        return None


def blacklist_token(token: str, expires_at: float) -> None:
    """Add a token to the blacklist with a TTL based on its expiry timestamp."""
    r = _get_redis()
    ttl = max(int(expires_at - time.time()), 0)

    if r is not None and _use_redis:
        try:
            r.setex(f"bl:{token}", ttl, "1")
            return
        except Exception as e:
            logger.warning(f"Redis blacklist set failed, falling back to in-memory: {e}")

    _in_memory_blacklist[token] = expires_at


def is_blacklisted(token: str) -> bool:
    """Check if a token is currently blacklisted."""
    r = _get_redis()

    if r is not None and _use_redis:
        try:
            return r.exists(f"bl:{token}") == 1
        except Exception as e:
            logger.warning(f"Redis blacklist check failed, falling back to in-memory: {e}")

    expires_at = _in_memory_blacklist.get(token)
    if expires_at is None:
        return False
    if time.time() > expires_at:
        del _in_memory_blacklist[token]
        return False
    return True


def cleanup() -> None:
    """Remove expired entries from the in-memory blacklist."""
    now = time.time()
    expired = [tok for tok, exp in _in_memory_blacklist.items() if now > exp]
    for tok in expired:
        del _in_memory_blacklist[tok]
