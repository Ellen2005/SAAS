from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..core.auth import require_role
from ..core.supabase_client import get_supabase

router = APIRouter(prefix="/api/admin/departments", tags=["departments"])


class DepartmentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    instance_url: Optional[str] = None
    heartbeat_schedule: str = "daily"
    heartbeat_time: str = "06:00"
    template_id: Optional[str] = None
    instance_template_id: Optional[str] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    instance_url: Optional[str] = None
    heartbeat_schedule: Optional[str] = None
    heartbeat_time: Optional[str] = None
    template_id: Optional[str] = None
    instance_template_id: Optional[str] = None


class AssignUserRequest(BaseModel):
    user_id: str
    role: str = "manager"


def _safe_data(response) -> list:
    return response.data if hasattr(response, "data") and response.data else []


@router.get("")
def list_departments(context: dict = Depends(require_role(["admin"]))):
    supabase = get_supabase()
    try:
        department_rows = _safe_data(
            supabase.table("departments")
            .select("*")
            .order("created_at")
            .execute()
        )

        departments = []
        for department in department_rows:
            users_resp = (
                supabase.table("user_roles")
                .select("id", count="exact")
                .eq("department_id", department["id"])
                .execute()
            )
            last_sync_rows = _safe_data(
                supabase.table("daily_reports")
                .select("report_date")
                .eq("department_id", department["id"])
                .order("report_date", desc=True)
                .limit(1)
                .execute()
            )
            template_name = None
            if department.get("template_id"):
                template_rows = _safe_data(
                    supabase.table("semantic_templates")
                    .select("name")
                    .eq("id", department["template_id"])
                    .limit(1)
                    .execute()
                )
                if template_rows:
                    template_name = template_rows[0].get("name")

            instance_template_name = None
            if department.get("instance_template_id"):
                instance_template_rows = _safe_data(
                    supabase.table("instance_templates")
                    .select("name")
                    .eq("id", department["instance_template_id"])
                    .limit(1)
                    .execute()
                )
                if instance_template_rows:
                    instance_template_name = instance_template_rows[0].get("name")

            departments.append(
                {
                    **department,
                    "user_count": getattr(users_resp, "count", 0),
                    "last_sync": last_sync_rows[0]["report_date"] if last_sync_rows else None,
                    "template_name": template_name,
                    "instance_template_name": instance_template_name,
                }
            )

        return {"departments": departments, "requested_by": context["user_id"]}
    except Exception as error:
        return {"departments": [], "error": str(error)}


@router.post("")
def create_department(
    department: DepartmentCreate,
    context: dict = Depends(require_role(["admin"])),
):
    supabase = get_supabase()
    payload = {
        "name": department.name,
        "description": department.description,
        "instance_url": department.instance_url,
        "heartbeat_schedule": department.heartbeat_schedule,
        "heartbeat_time": department.heartbeat_time,
        "template_id": department.template_id,
        "instance_template_id": department.instance_template_id,
    }
    try:
        rows = _safe_data(supabase.table("departments").insert(payload).execute())
        return {
            "status": "success",
            "department": rows[0] if rows else payload,
            "created_by": context["user_id"],
        }
    except Exception as error:
        return {"status": "error", "message": str(error)}


@router.put("/{dept_id}")
def update_department(
    dept_id: str,
    department: DepartmentUpdate,
    context: dict = Depends(require_role(["admin"])),
):
    supabase = get_supabase()
    payload = {
        key: value for key, value in department.model_dump().items() if value is not None
    }
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        supabase.table("departments").update(payload).eq("id", dept_id).execute()
        return {
            "status": "success",
            "department_id": dept_id,
            "updated": payload,
            "updated_by": context["user_id"],
        }
    except Exception as error:
        return {"status": "error", "message": str(error)}


@router.delete("/{dept_id}")
def delete_department(
    dept_id: str,
    context: dict = Depends(require_role(["admin"])),
):
    supabase = get_supabase()
    try:
        supabase.table("user_roles").delete().eq("department_id", dept_id).neq(
            "role", "admin"
        ).execute()
        supabase.table("departments").delete().eq("id", dept_id).execute()
        return {
            "status": "success",
            "deleted": dept_id,
            "deleted_by": context["user_id"],
        }
    except Exception as error:
        return {"status": "error", "message": str(error)}


@router.post("/{dept_id}/assign-user")
def assign_user_to_department(
    dept_id: str,
    request: AssignUserRequest,
    context: dict = Depends(require_role(["admin"])),
):
    if request.role not in {"admin", "manager", "viewer"}:
        raise HTTPException(status_code=400, detail="Invalid role")

    supabase = get_supabase()
    payload = {
        "user_id": request.user_id,
        "department_id": dept_id,
        "role": request.role,
    }
    try:
        supabase.table("user_roles").upsert(
            payload, on_conflict="user_id,department_id"
        ).execute()
        return {"status": "success", "assignment": payload, "assigned_by": context["user_id"]}
    except Exception as error:
        return {"status": "error", "message": str(error)}
