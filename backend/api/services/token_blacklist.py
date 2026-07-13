import os
import time
import logging
import threading
from typing import Dict

logger = logging.getLogger(__name__)

_redis_client = None
_use_redis = False
_in_memory_blacklist: Dict[str, float] = {}
_in_memory_user_revocations: Dict[str, float] = {}
_lock = threading.Lock()

# Cache size limits to prevent unbounded memory growth
_MAX_BLACKLIST_SIZE = 50000
_MAX_REVOCATION_SIZE = 10000


def _try_connect_redis():
    """Attempt to connect to Redis using REDIS_URL env var (sync, called once)."""
    global _redis_client, _use_redis

    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        _use_redis = False
        return

    try:
        import redis
        _redis_client = redis.Redis(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
            retry_on_timeout=False,
        )
        _redis_client.ping()
        _use_redis = True
        logger.info("Connected to Redis for token blacklist")
    except Exception as e:
        logger.warning(f"Redis unavailable, falling back to in-memory blacklist: {e}")
        _use_redis = False
        _redis_client = None


def blacklist_token(token: str, expires_at: float) -> None:
    """Add a token to the blacklist. Synchronous — safe to call from sync endpoints."""
    global _redis_client, _use_redis

    # Lazy-init Redis connection on first use
    if not _use_redis and _redis_client is None:
        _try_connect_redis()

    ttl = max(int(expires_at - time.time()), 0)

    if _use_redis and _redis_client is not None:
        try:
            _redis_client.setex(f"bl:{token}", ttl, "1")
            return
        except Exception as e:
            logger.warning(f"Redis blacklist set failed, falling back to in-memory: {e}")
            _use_redis = False
            _redis_client = None

    with _lock:
        # Evict oldest entries if at capacity
        if len(_in_memory_blacklist) >= _MAX_BLACKLIST_SIZE:
            now = time.time()
            expired = [tok for tok, exp in _in_memory_blacklist.items() if now > exp]
            for tok in expired:
                del _in_memory_blacklist[tok]
            # If still over limit, remove oldest 10%
            if len(_in_memory_blacklist) >= _MAX_BLACKLIST_SIZE:
                sorted_entries = sorted(_in_memory_blacklist.items(), key=lambda x: x[1])
                for tok, _ in sorted_entries[:len(sorted_entries) // 10]:
                    del _in_memory_blacklist[tok]
        _in_memory_blacklist[token] = expires_at


async def is_blacklisted(token: str) -> bool:
    """Check if a token is currently blacklisted."""
    if _use_redis and _redis_client is not None:
        try:
            return _redis_client.exists(f"bl:{token}") == 1
        except Exception as e:
            logger.warning(f"Redis blacklist check failed, falling back to in-memory: {e}")

    with _lock:
        expires_at = _in_memory_blacklist.get(token)
    if expires_at is None:
        return False
    if time.time() > expires_at:
        with _lock:
            _in_memory_blacklist.pop(token, None)
        return False
    return True


async def cleanup() -> None:
    """Remove expired entries from the in-memory blacklist and user revocations."""
    now = time.time()
    with _lock:
        expired = [tok for tok, exp in _in_memory_blacklist.items() if now > exp]
        for tok in expired:
            del _in_memory_blacklist[tok]
        expired_users = [uid for uid, exp in _in_memory_user_revocations.items() if now > exp]
        for uid in expired_users:
            del _in_memory_user_revocations[uid]


def blacklist_user_tokens(user_id: str, ttl: int = 86400 * 7) -> None:
    """Blacklist all future tokens for a user by storing a revocation timestamp.

    This is called on role change or account deletion. The auth module should
    check this timestamp when validating tokens.
    """
    global _redis_client, _use_redis

    # Lazy-init Redis connection on first use
    if not _use_redis and _redis_client is None:
        _try_connect_redis()

    expires_at = time.time() + ttl

    if _use_redis and _redis_client is not None:
        try:
            _redis_client.setex(f"revoked_user:{user_id}", ttl, str(expires_at))
            return
        except Exception as e:
            logger.warning(f"Redis user revocation failed, falling back to in-memory: {e}")
            _use_redis = False
            _redis_client = None

    with _lock:
        if len(_in_memory_user_revocations) >= _MAX_REVOCATION_SIZE:
            sorted_entries = sorted(_in_memory_user_revocations.items(), key=lambda x: x[1])
            for uid, _ in sorted_entries[:len(sorted_entries) // 10]:
                del _in_memory_user_revocations[uid]
        _in_memory_user_revocations[user_id] = expires_at


async def is_user_revoked(user_id: str) -> bool:
    """Check if all tokens for a user have been revoked."""
    if _use_redis and _redis_client is not None:
        try:
            val = _redis_client.get(f"revoked_user:{user_id}")
            if val is None:
                return False
            return time.time() < float(val)
        except Exception as e:
            logger.warning(f"Redis user revocation check failed: {e}")

    with _lock:
        expires_at = _in_memory_user_revocations.get(user_id)
    if expires_at is None:
        return False
    if time.time() > expires_at:
        with _lock:
            _in_memory_user_revocations.pop(user_id, None)
        return False
    return True
