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
        # Get all user roles first - group by user_id to get latest role
        role_rows = _safe_data(
            supabase.table("user_roles")
            .select("id, user_id, role, department_id, departments(name), created_at")
            .order("user_id")
            .order("created_at", desc=True)
            .execute()
        )

        # Remove duplicates - keep latest role per user
        latest_roles = {}
        for row in role_rows:
            user_id = row["user_id"]
            if user_id not in latest_roles:
                latest_roles[user_id] = row
        
        role_rows = list(latest_roles.values())

        # Get emails from user_profiles and notification_recipients
        email_by_user = {}
        
        try:
            profiles_resp = supabase.table('user_profiles').select('id, email, display_name').execute()
            if hasattr(profiles_resp, 'data') and profiles_resp.data:
                for profile in profiles_resp.data:
                    user_id = str(profile.get('id', ''))
                    email = profile.get('email')
                    display_name = profile.get('display_name')
                    if user_id:
                        email_by_user[user_id] = email or display_name
        except Exception:
            pass
            
        try:
            recipients_resp = supabase.table('notification_recipients').select('user_id, email').execute()
            if hasattr(recipients_resp, 'data') and recipients_resp.data:
                for recipient in recipients_resp.data:
                    user_id = str(recipient.get('user_id', ''))
                    email = recipient.get('email')
                    if user_id and email and user_id not in email_by_user:
                        email_by_user[user_id] = email
        except Exception:
            pass

        # Get ALL users from Supabase Auth
        # supabase-py v2: admin.list_users() returns a list directly
        auth_error = None
        try:
            auth_response = supabase.auth.admin.list_users()
            # Handle both v1 (object with .users) and v2 (direct list)
            if isinstance(auth_response, list):
                auth_users = auth_response
            elif hasattr(auth_response, 'users') and auth_response.users:
                auth_users = auth_response.users
            elif hasattr(auth_response, 'data') and auth_response.data:
                auth_users = auth_response.data
            else:
                auth_users = []

            for auth_user in auth_users:
                uid = str(getattr(auth_user, 'id', '') or auth_user.get('id', '') if isinstance(auth_user, dict) else auth_user.id)
                email = (auth_user.get('email') if isinstance(auth_user, dict) else getattr(auth_user, 'email', None))
                if uid and email and uid not in email_by_user:
                    email_by_user[uid] = email
        except Exception as e:
            auth_error = str(e)

        # Collect all unique user IDs
        all_user_ids = set(row["user_id"] for row in role_rows)
        
        # Add users who don't have roles yet
        for user_id, email in email_by_user.items():
            if user_id not in all_user_ids:
                role_rows.append({
                    "id": None,
                    "user_id": user_id,
                    "role": None,
                    "department_id": None,
                    "departments": None
                })

        # Build final user list
        users = []
        seen_user_ids = set()  # Prevent duplicates
        
        for role_row in role_rows:
            user_id = role_row["user_id"]
            
            # Skip duplicates
            if user_id in seen_user_ids:
                continue
            seen_user_ids.add(user_id)
            
            department_name = None
            if role_row.get("departments"):
                department_name = role_row["departments"].get("name")

            user_email = email_by_user.get(user_id)
            display_name = user_email or f"User {user_id[:8]}..."
            
            users.append({
                "role_id": role_row.get("id"),
                "user_id": user_id,
                "email": user_email,
                "display_name": display_name,
                "role": role_row.get("role"),
                "department_id": role_row.get("department_id"),
                "department_name": department_name,
            })

        return {"users": users, "requested_by": context["user_id"], "auth_error": auth_error}
    except Exception as error:
        return {"users": [], "error": str(error), "auth_error": auth_error if 'auth_error' in dir() else None}


@router.post("/admin/users/{target_user_id}/role")
def set_user_role(
    target_user_id: str,
    request: UserRoleUpdate,
    context: dict = Depends(require_role(["admin"])),
):
    if request.role not in {"admin", "manager", "viewer"}:
        raise HTTPException(status_code=400, detail="Invalid role")

    supabase = get_supabase()
    
    try:
        supabase.table("user_roles").delete().eq("user_id", target_user_id).execute()
    except Exception:
        pass
    
    payload = {
        "user_id": target_user_id,
        "role": request.role,
        "department_id": request.department_id,
    }
    try:
        supabase.table("user_roles").insert(payload).execute()
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
        supabase.auth.admin.delete_user(user_id)
        return {"status": "deleted", "user_id": user_id}
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Failed to delete account: {str(error)}")


@router.get("/admin/debug/auth")
def debug_auth_users(context: dict = Depends(require_role(["admin"]))):
    supabase = get_supabase()
    try:
        # Get users from Supabase Auth
        auth_response = supabase.auth.admin.list_users()
        auth_users = []
        
        if isinstance(auth_response, list):
            raw_list = auth_response
        elif hasattr(auth_response, 'users') and auth_response.users:
            raw_list = auth_response.users
        elif hasattr(auth_response, 'data') and auth_response.data:
            raw_list = auth_response.data
        else:
            raw_list = []

        for user in raw_list:
            is_dict = isinstance(user, dict)
            auth_users.append({
                'id': str(user.get('id', 'No ID') if is_dict else getattr(user, 'id', 'No ID')),
                'email': user.get('email', 'No email') if is_dict else getattr(user, 'email', 'No email'),
                'created_at': str(user.get('created_at', 'Unknown') if is_dict else getattr(user, 'created_at', 'Unknown')),
                'email_confirmed_at': str(user.get('email_confirmed_at', 'Not confirmed') if is_dict else getattr(user, 'email_confirmed_at', 'Not confirmed')),
            })
        
        # Get role assignments
        role_assignments = _safe_data(
            supabase.table("user_roles")
            .select("user_id, role, department_id")
            .execute()
        )
        
        return {
            "total_auth_users": len(auth_users),
            "auth_users": auth_users,
            "role_assignments": role_assignments,
            "raw_response_type": str(type(auth_response))
        }
    except Exception as e:
        return {"error": str(e), "error_type": str(type(e))}


@router.post("/users/me/profile")
def update_my_profile(
    profile_data: dict,
    user_id: str = Depends(resolve_user_id)
):
    supabase = get_supabase()
    
    try:
        profile_update = {
            "id": user_id,
            "email": profile_data.get("email"),
            "display_name": profile_data.get("display_name") or profile_data.get("email")
        }
        
        # Try user_profiles table first, fallback to user_roles
        try:
            supabase.table("user_profiles").upsert(profile_update, on_conflict="id").execute()
        except Exception:
            # If user_profiles table doesn't exist, update user_roles instead
            supabase.table("user_roles").update({
                "department_id": profile_update.get("department_id")
            }).eq("user_id", user_id).execute()
        
        return {"status": "success", "profile": profile_update}
    except Exception as error:
        # Return success anyway to not block login flow
        return {"status": "success", "profile": {"id": user_id}}
