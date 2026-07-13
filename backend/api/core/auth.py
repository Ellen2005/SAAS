from fastapi import HTTPException, Header, Query, Depends
from typing import Optional
import logging
import time
from functools import lru_cache
from ..core.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# In-memory JWT cache with TTL and size limit
_jwt_cache: dict[str, tuple[dict, float]] = {}
_JWT_CACHE_TTL = 300  # 5 minutes
_JWT_CACHE_MAX = 5000

# Role cache with TTL and size limit
_role_cache: dict[str, tuple[dict, float]] = {}
_ROLE_CACHE_TTL = 300  # 5 minutes
_ROLE_CACHE_MAX = 5000

# Rate limiting for Supabase auth calls
_last_auth_call: dict[str, float] = {}
_AUTH_CALL_MIN_INTERVAL = 0.1  # 100ms between calls per user
_RATE_LIMIT_MAX = 10000


def _evict_oldest(cache: dict, max_size: int) -> None:
    """Evict oldest 10% of entries when cache exceeds max_size."""
    if len(cache) < max_size:
        return
    sorted_entries = sorted(cache.items(), key=lambda x: x[1][1] if isinstance(x[1], tuple) else x[1])
    evict_count = max(1, len(cache) // 10)
    for key, _ in sorted_entries[:evict_count]:
        del cache[key]


def _get_cached_user(token: str) -> Optional[dict]:
    """Get cached user from JWT token if valid and not expired."""
    if token in _jwt_cache:
        user_data, expires_at = _jwt_cache[token]
        if time.time() < expires_at:
            return user_data
        else:
            del _jwt_cache[token]
    return None


def _cache_user(token: str, user_data: dict, ttl: int = None) -> None:
    """Cache user data with TTL."""
    ttl = ttl or _JWT_CACHE_TTL
    _evict_oldest(_jwt_cache, _JWT_CACHE_MAX)
    _jwt_cache[token] = (user_data, time.time() + ttl)


def _rate_limit_auth(user_id: str) -> bool:
    """Rate limit auth calls per user."""
    now = time.time()
    if user_id in _last_auth_call:
        if now - _last_auth_call[user_id] < _AUTH_CALL_MIN_INTERVAL:
            return False
    # Evict stale entries
    if len(_last_auth_call) > _RATE_LIMIT_MAX:
        cutoff = now - 300  # 5 minutes
        stale = [k for k, v in _last_auth_call.items() if v < cutoff]
        for k in stale[:len(stale) // 2]:
            del _last_auth_call[k]
    _last_auth_call[user_id] = now
    return True


async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    token = authorization.replace("Bearer ", "")

    from ..services.token_blacklist import is_blacklisted, is_user_revoked
    if await is_blacklisted(token):
        raise HTTPException(status_code=401, detail="Token has been revoked")

    # Check cache first
    cached = _get_cached_user(token)
    if cached:
        # Still need to check user revocation even with cached token
        if await is_user_revoked(cached.get("id", "")):
            del _jwt_cache[token]
            raise HTTPException(status_code=401, detail="Token has been revoked")
        return cached

    # Rate limit per-user auth calls
    # Use a hash of token as user identifier for rate limiting
    token_hash = hash(token) % 10000
    if not _rate_limit_auth(f"token_{token_hash}"):
        # If rate limited, try cache first, then raise 429
        cached = _get_cached_user(token)
        if cached:
            return cached
        logger.warning(f"Auth rate limit hit for token hash {token_hash}")
        raise HTTPException(status_code=429, detail="Too many authentication requests. Please try again later.")

    supabase = get_supabase()
    try:
        user_resp = supabase.auth.get_user(token)
        if not user_resp or not hasattr(user_resp, "user") or not user_resp.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        user = user_resp.user
        user_dict = user if isinstance(user, dict) else {"id": getattr(user, "id", None), "email": getattr(user, "email", None)}
        if await is_user_revoked(user_dict.get("id", "")):
            raise HTTPException(status_code=401, detail="Token has been revoked")
        _cache_user(token, user_dict)
        return user_dict
    except HTTPException:
        raise
    except Exception as e2:
        logger.error(f"Auth error: {e2}")
        raise HTTPException(status_code=401, detail="Authentication failed")


async def resolve_user_id(authorization: Optional[str] = Header(None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    user = await get_current_user(authorization)
    if isinstance(user, dict):
        resolved = user.get("id") or user.get("user_id")
    else:
        resolved = getattr(user, "id", None) or getattr(user, "user_id", None)
    if not resolved:
        raise HTTPException(status_code=401, detail="Unable to resolve user from token")
    return str(resolved)


def _get_cached_role(user_id: str) -> Optional[dict]:
    """Get cached role info if valid and not expired."""
    if user_id in _role_cache:
        role_data, expires_at = _role_cache[user_id]
        if time.time() < expires_at:
            return role_data
        else:
            del _role_cache[user_id]
    return None


def _cache_role(user_id: str, role_data: dict, ttl: int = None) -> None:
    """Cache role data with TTL."""
    ttl = ttl or _ROLE_CACHE_TTL
    _evict_oldest(_role_cache, _ROLE_CACHE_MAX)
    _role_cache[user_id] = (role_data, time.time() + ttl)


def evict_role_cache(user_id: str) -> None:
    """Evict cached role data for a user. Call after role changes."""
    _role_cache.pop(user_id, None)


def evict_user_cache(token: str) -> None:
    """Evict cached user data for a token. Call after role changes."""
    _jwt_cache.pop(token, None)


def get_user_role(user_id: str) -> Optional[str]:
    # Check cache first
    cached = _get_cached_role(user_id)
    if cached:
        return cached.get("role")

    supabase = get_supabase()
    try:
        resp = supabase.table("user_roles").select("role").eq("user_id", user_id).execute()
        if hasattr(resp, "data") and resp.data:
            roles = [r["role"] for r in resp.data if r.get("role")]
            if "admin" in roles:
                role = "admin"
            elif "manager" in roles:
                role = "manager"
            elif "viewer" in roles:
                role = "viewer"
            else:
                role = None
            _cache_role(user_id, {"role": role})
            return role
    except Exception:
        logger.warning("role lookup failed for user %s", user_id, exc_info=True)
    _cache_role(user_id, {"role": None})
    return None


def get_user_department(user_id: str) -> Optional[str]:
    cached = _get_cached_role(user_id)
    if cached and cached.get("department_id"):
        return cached["department_id"]

    supabase = get_supabase()
    try:
        resp = supabase.table("user_roles").select("department_id").eq("user_id", user_id).execute()
        if hasattr(resp, "data") and resp.data:
            for r in resp.data:
                if r.get("department_id"):
                    return r["department_id"]
    except Exception:
        logger.warning("department lookup failed for user %s", user_id, exc_info=True)
    return None


def get_user_info(user_id: str) -> dict:
    # Check cache first
    cached = _get_cached_role(user_id)
    if cached:
        return cached

    supabase = get_supabase()
    info = {"user_id": user_id, "role": None, "department_id": None, "department_name": None}
    try:
        resp = supabase.table("user_roles").select("role, department_id, departments(name)").eq("user_id", user_id).execute()
        if hasattr(resp, "data") and resp.data:
            roles = resp.data
            role_order = {"admin": 0, "manager": 1, "viewer": 2}
            best = min(roles, key=lambda r: role_order.get(r["role"], 99))
            info["role"] = best["role"]
            info["department_id"] = best.get("department_id")
            if best.get("departments"):
                info["department_name"] = best["departments"].get("name")
            _cache_role(user_id, info)
    except Exception:
        logger.warning("user info lookup failed for user %s", user_id, exc_info=True)
    return info


def is_admin(user_id: str) -> bool:
    return get_user_role(user_id) == "admin"


def is_manager_or_above(user_id: str) -> bool:
    role = get_user_role(user_id)
    return role in ("admin", "manager")


def require_role(allowed_roles: list):
    def role_checker(resolved_user_id: str = Depends(resolve_user_id)):
        user_info = get_user_info(resolved_user_id)
        role = user_info.get("role")
        if not role or role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions.",
            )
        return {
            "user_id": resolved_user_id,
            "role": role,
            "department_id": user_info.get("department_id"),
            "department_name": user_info.get("department_name"),
        }
    return role_checker