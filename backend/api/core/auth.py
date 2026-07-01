from fastapi import HTTPException, Header, Query, Depends
from typing import Optional
import logging
from ..core.supabase_client import get_supabase

logger = logging.getLogger(__name__)


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    token = authorization.replace("Bearer ", "")

    from ..services.token_blacklist import is_blacklisted
    if is_blacklisted(token):
        raise HTTPException(status_code=401, detail="Token has been revoked")

    supabase = get_supabase()
    try:
        user_resp = supabase.auth.get_user(token)
        if not user_resp or not hasattr(user_resp, "user") or not user_resp.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return user_resp.user
    except HTTPException:
        raise
    except Exception as e:
        # Network/DNS failures — try once more before giving up
        import time
        time.sleep(0.3)
        try:
            user_resp = supabase.auth.get_user(token)
            if not user_resp or not hasattr(user_resp, "user") or not user_resp.user:
                raise HTTPException(status_code=401, detail="Invalid or expired token")
            return user_resp.user
        except HTTPException:
            raise
        except Exception as e2:
            raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e2)}")


def resolve_user_id(authorization: Optional[str] = Header(None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    user = get_current_user(authorization)
    if isinstance(user, dict):
        resolved = user.get("id") or user.get("user_id")
    else:
        resolved = getattr(user, "id", None) or getattr(user, "user_id", None)
    if not resolved:
        raise HTTPException(status_code=401, detail="Unable to resolve user from token")
    return str(resolved)


def get_user_role(user_id: str) -> Optional[str]:
    supabase = get_supabase()
    try:
        resp = supabase.table("user_roles").select("role").eq("user_id", user_id).execute()
        if hasattr(resp, "data") and resp.data:
            roles = [r["role"] for r in resp.data]
            if "admin" in roles:
                return "admin"
            if "manager" in roles:
                return "manager"
            if "viewer" in roles:
                return "viewer"
    except Exception:
        logger.warning("role lookup failed for user %s", user_id, exc_info=True)
    return None


def get_user_department(user_id: str) -> Optional[str]:
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
        if role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required: {allowed_roles}, got: {role}",
            )
        return {
            "user_id": resolved_user_id,
            "role": role,
            "department_id": user_info.get("department_id"),
            "department_name": user_info.get("department_name"),
        }
    return role_checker
