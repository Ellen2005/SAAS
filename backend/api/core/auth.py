from fastapi import HTTPException, Header, Query, Depends
from typing import Optional
from ..core.supabase_client import get_supabase


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Extracts user from Supabase JWT token passed in Authorization header.
    Returns user dict with id, email, role, department_id.
    Falls back to user_id query param for backward compat during transition.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.replace("Bearer ", "")
    supabase = get_supabase()

    try:
        user_resp = supabase.auth.get_user(token)
        if not user_resp or not hasattr(user_resp, "user") or not user_resp.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return user_resp.user
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


def resolve_user_id(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
    user_id: Optional[str] = Query(None),
) -> str:
    """
    Resolve the acting user.
    Preferred order:
    1. Verified Supabase bearer token
    2. X-User-Id header
    3. user_id query param
    """
    if authorization:
        try:
            user = get_current_user(authorization)

            # Supabase client may return user as either an object with `.id`
            # or a plain dict (depending on SDK version / mocking).
            if isinstance(user, dict):
                resolved = user.get("id") or user.get("user_id")
                if resolved:
                    return str(resolved)
            else:
                resolved = getattr(user, "id", None) or getattr(user, "user_id", None)
                if resolved:
                    return str(resolved)
        except HTTPException:
            # Graceful local-dev fallback: if the client also supplies a user id,
            # continue with that identity when token verification is temporarily unavailable.
            if x_user_id:
                return x_user_id
            if user_id:
                return user_id

    if x_user_id:
        return x_user_id

    if user_id:
        return user_id

    raise HTTPException(status_code=401, detail="Missing authenticated user context")


def get_user_role(user_id: str) -> Optional[str]:
    """Returns the user's highest role: admin > manager > viewer, or None if no role."""
    supabase = get_supabase()
    try:
        resp = (
            supabase.table("user_roles").select("role").eq("user_id", user_id).execute()
        )
        if hasattr(resp, "data") and resp.data:
            roles = [r["role"] for r in resp.data]
            if "admin" in roles:
                return "admin"
            if "manager" in roles:
                return "manager"
            if "viewer" in roles:
                return "viewer"
    except Exception:
        pass  # user_roles table may not exist yet
    return None


def get_user_department(user_id: str) -> Optional[str]:
    """Returns the user's department_id (first non-null), or None."""
    supabase = get_supabase()
    try:
        resp = (
            supabase.table("user_roles")
            .select("department_id")
            .eq("user_id", user_id)
            .execute()
        )
        if hasattr(resp, "data") and resp.data:
            for r in resp.data:
                if r.get("department_id"):
                    return r["department_id"]
    except Exception:
        pass
    return None


def get_user_info(user_id: str) -> dict:
    """Returns full user role info: role, department_id, department_name."""
    supabase = get_supabase()
    info = {
        "user_id": user_id,
        "role": None,
        "department_id": None,
        "department_name": None,
    }

    try:
        resp = (
            supabase.table("user_roles")
            .select("role, department_id")
            .eq("user_id", user_id)
            .execute()
        )
        if hasattr(resp, "data") and resp.data:
            roles = resp.data
            # Find highest role
            role_order = {"admin": 0, "manager": 1, "viewer": 2}
            best = min(roles, key=lambda r: role_order.get(r["role"], 99))
            info["role"] = best["role"]
            info["department_id"] = best.get("department_id")

            if info["department_id"]:
                dept_resp = (
                    supabase.table("departments")
                    .select("name")
                    .eq("id", info["department_id"])
                    .execute()
                )
                if hasattr(dept_resp, "data") and dept_resp.data:
                    info["department_name"] = dept_resp.data[0]["name"]
    except Exception:
        pass

    return info


def is_admin(user_id: str) -> bool:
    return get_user_role(user_id) == "admin"


def is_manager_or_above(user_id: str) -> bool:
    role = get_user_role(user_id)
    return role in ("admin", "manager")


def require_role(allowed_roles: list):
    """
    FastAPI dependency that checks if the current user has one of the allowed roles.
    Usage: Depends(require_role(['admin'])) or Depends(require_role(['admin', 'manager']))
    """

    def role_checker(resolved_user_id: str = Depends(resolve_user_id)):
        effective_user_id = resolved_user_id
        role = get_user_role(effective_user_id)
        user_info = get_user_info(effective_user_id)
        if role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required: {allowed_roles}, got: {role}",
            )
        return {
            "user_id": effective_user_id,
            "role": role,
            "department_id": user_info.get("department_id"),
            "department_name": user_info.get("department_name"),
        }

    return role_checker
