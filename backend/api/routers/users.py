from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel

from ..core.auth import get_current_user, get_user_info, require_role, resolve_user_id
from ..core.supabase_client import get_supabase

router = APIRouter(prefix="/api", tags=["users"])


class UserRoleUpdate(BaseModel):
    role: str
    department_id: Optional[str] = None


def _safe_data(response) -> list:
    return response.data if hasattr(response, "data") and response.data else []


@router.get("/users/me")
def get_current_user_info(user_id: str = Depends(resolve_user_id)):
    info = get_user_info(user_id)

    if info["role"] is None:
        try:
            supabase = get_supabase()
            general_rows = _safe_data(
                supabase.table("departments")
                .select("id, name")
                .eq("name", "General")
                .limit(1)
                .execute()
            )
            if general_rows:
                default_department = general_rows[0]
                supabase.table("user_roles").upsert(
                    {
                        "user_id": user_id,
                        "department_id": default_department["id"],
                        "role": "manager",
                    },
                    on_conflict="user_id,department_id",
                ).execute()
                info["role"] = "manager"
                info["department_id"] = default_department["id"]
                info["department_name"] = default_department["name"]

                # Optional onboarding notification: only on first provisioning into
                # the default department + role.
                try:
                    from ..services.email_service import send_admin_onboarding_notification

                    send_admin_onboarding_notification(user_id)
                except Exception:
                    pass
        except Exception:
            pass

    return info


@router.get("/admin/users")
def list_all_users(context: dict = Depends(require_role(["admin"]))):
    supabase = get_supabase()
    try:
        role_rows = _safe_data(
            supabase.table("user_roles")
            .select("id, user_id, role, department_id, departments(name)")
            .order("created_at")
            .execute()
        )

        email_by_user = {}
        try:
            auth_users = supabase.auth.admin.list_users()
            for auth_user in getattr(auth_users, "users", []):
                email_by_user[str(auth_user.id)] = getattr(auth_user, "email", None)
        except Exception:
            pass

        users = []
        for role_row in role_rows:
            department_name = None
            if role_row.get("departments"):
                department_name = role_row["departments"].get("name")

            users.append(
                {
                    "role_id": role_row["id"],
                    "user_id": role_row["user_id"],
                    "email": email_by_user.get(role_row["user_id"]),
                    "role": role_row["role"],
                    "department_id": role_row.get("department_id"),
                    "department_name": department_name,
                }
            )

        return {"users": users, "requested_by": context["user_id"]}
    except Exception as error:
        return {"users": [], "error": str(error)}


@router.post("/admin/users/{target_user_id}/role")
def set_user_role(
    target_user_id: str,
    request: UserRoleUpdate,
    context: dict = Depends(require_role(["admin"])),
):
    if request.role not in {"admin", "manager", "viewer"}:
        raise HTTPException(status_code=400, detail="Invalid role")

    supabase = get_supabase()
    payload = {
        "user_id": target_user_id,
        "role": request.role,
        "department_id": request.department_id,
    }
    try:
        supabase.table("user_roles").upsert(
            payload, on_conflict="user_id,department_id"
        ).execute()
        return {"status": "success", **payload, "updated_by": context["user_id"]}
    except Exception as error:
        return {"status": "error", "message": str(error)}


@router.delete("/admin/users/{target_user_id}/role")
def remove_user_role(
    target_user_id: str,
    context: dict = Depends(require_role(["admin"])),
):
    supabase = get_supabase()
    try:
        supabase.table("user_roles").delete().eq("user_id", target_user_id).execute()
        return {"status": "success", "removed": target_user_id, "removed_by": context["user_id"]}
    except Exception as error:
        return {"status": "error", "message": str(error)}


@router.delete("/account")
def delete_my_account(authorization: Optional[str] = Header(None)):
    """
    Deletes the currently authenticated Supabase user.

    Security note: this endpoint uses the verified JWT from the Authorization header
    (no fallback to X-User-Id / user_id query params).
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    user = get_current_user(authorization)

    if isinstance(user, dict):
        user_id = user.get("id") or user.get("user_id")
    else:
        user_id = getattr(user, "id", None) or getattr(user, "user_id", None)

    if not user_id:
        raise HTTPException(status_code=401, detail="Unable to resolve authenticated user")

    supabase = get_supabase()
    try:
        supabase.auth.admin.deleteUser(user_id)
        return {"status": "deleted", "user_id": user_id}
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Failed to delete account: {str(error)}")
