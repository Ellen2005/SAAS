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
            supabase.table("departments").select("*").order("created_at").execute()
        )
        if not department_rows:
            return {"departments": [], "requested_by": context["user_id"]}

        dept_ids = [d["id"] for d in department_rows]

        # Batch: user counts per department
        user_count_rows = _safe_data(
            supabase.table("user_roles")
            .select("department_id")
            .in_("department_id", dept_ids)
            .execute()
        )
        user_counts = {}
        for row in user_count_rows:
            did = row["department_id"]
            user_counts[did] = user_counts.get(did, 0) + 1

        # Batch: latest report date per department
        report_rows = _safe_data(
            supabase.table("daily_reports")
            .select("department_id, report_date")
            .in_("department_id", dept_ids)
            .order("report_date", desc=True)
            .execute()
        )
        last_sync_by_dept = {}
        for row in report_rows:
            did = row["department_id"]
            if did not in last_sync_by_dept:
                last_sync_by_dept[did] = row["report_date"]

        # Batch: semantic template names
        template_ids = list({d["template_id"] for d in department_rows if d.get("template_id")})
        template_name_map = {}
        if template_ids:
            tpl_rows = _safe_data(
                supabase.table("semantic_templates")
                .select("id, name")
                .in_("id", template_ids)
                .execute()
            )
            template_name_map = {r["id"]: r["name"] for r in tpl_rows}

        # Batch: instance template names
        instance_template_ids = list({d["instance_template_id"] for d in department_rows if d.get("instance_template_id")})
        instance_template_name_map = {}
        if instance_template_ids:
            inst_rows = _safe_data(
                supabase.table("instance_templates")
                .select("id, name")
                .in_("id", instance_template_ids)
                .execute()
            )
            instance_template_name_map = {r["id"]: r["name"] for r in inst_rows}

        departments = []
        for department in department_rows:
            did = department["id"]
            departments.append({
                **department,
                "user_count": user_counts.get(did, 0),
                "last_sync": last_sync_by_dept.get(did),
                "template_name": template_name_map.get(department.get("template_id")),
                "instance_template_name": instance_template_name_map.get(department.get("instance_template_id")),
            })

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
