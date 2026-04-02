from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..core.auth import require_role
from ..core.supabase_client import get_supabase

router = APIRouter(prefix="/api/templates", tags=["instance-templates"])


class InstanceTemplateCreate(BaseModel):
    name: str
    config: dict


class InstanceTemplateUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[dict] = None


class DeployTemplateRequest(BaseModel):
    template_id: str
    department_id: str


def _safe_data(response) -> list:
    return response.data if hasattr(response, "data") and response.data else []


@router.get("/instances")
def list_instance_templates(context: dict = Depends(require_role(["admin"]))):
    supabase = get_supabase()
    try:
        rows = _safe_data(
            supabase.table("instance_templates")
            .select("*")
            .order("created_at")
            .execute()
        )
        return {"templates": rows, "requested_by": context["user_id"]}
    except Exception as error:
        return {"templates": [], "error": str(error)}


@router.post("/instances")
def create_instance_template(
    template: InstanceTemplateCreate,
    context: dict = Depends(require_role(["admin"])),
):
    supabase = get_supabase()
    payload = {
        "name": template.name,
        "config": template.config,
        "created_by": context["user_id"],
    }
    try:
        rows = _safe_data(supabase.table("instance_templates").insert(payload).execute())
        return {"status": "success", "template": rows[0] if rows else payload}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.put("/instances/{template_id}")
def update_instance_template(
    template_id: str,
    template: InstanceTemplateUpdate,
    context: dict = Depends(require_role(["admin"])),
):
    supabase = get_supabase()
    payload = {
        key: value for key, value in template.model_dump().items() if value is not None
    }
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        supabase.table("instance_templates").update(payload).eq("id", template_id).execute()
        return {"status": "success", "updated": payload, "updated_by": context["user_id"]}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.delete("/instances/{template_id}")
def delete_instance_template(
    template_id: str,
    context: dict = Depends(require_role(["admin"])),
):
    supabase = get_supabase()
    try:
        supabase.table("instance_templates").delete().eq("id", template_id).execute()
        return {"status": "success", "deleted": template_id, "deleted_by": context["user_id"]}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.post("/deploy")
def deploy_instance_template(
    request: DeployTemplateRequest,
    context: dict = Depends(require_role(["admin"])),
):
    supabase = get_supabase()
    try:
        template_rows = _safe_data(
            supabase.table("instance_templates")
            .select("*")
            .eq("id", request.template_id)
            .limit(1)
            .execute()
        )
        if not template_rows:
            raise HTTPException(status_code=404, detail="Instance template not found")

        template = template_rows[0]
        config = template.get("config") or {}
        sync_default = config.get("sync_default") or {}

        department_update = {"instance_template_id": request.template_id}
        if config.get("semantic_template_id"):
            department_update["template_id"] = config["semantic_template_id"]
        if sync_default.get("frequency"):
            department_update["heartbeat_schedule"] = sync_default["frequency"]
        if sync_default.get("time"):
            department_update["heartbeat_time"] = sync_default["time"]

        supabase.table("departments").update(department_update).eq(
            "id", request.department_id
        ).execute()

        department_users = _safe_data(
            supabase.table("user_roles")
            .select("user_id")
            .eq("department_id", request.department_id)
            .execute()
        )

        email_recipients = config.get("email_recipients") or []
        ai_tone = config.get("ai_tone")
        for user_role in department_users:
            if ai_tone or sync_default:
                preference_payload = {
                    "user_id": user_role["user_id"],
                    "ai_tone": ai_tone or "insight-driven",
                    "sync_frequency": sync_default.get("frequency", "daily"),
                    "sync_time": sync_default.get("time", "06:00"),
                }
                supabase.table("user_preferences").upsert(
                    preference_payload, on_conflict="user_id"
                ).execute()

            if email_recipients:
                inserts = [
                    {"user_id": user_role["user_id"], "email": email}
                    for email in email_recipients
                ]
                supabase.table("notification_recipients").insert(inserts).execute()

        return {
            "status": "success",
            "department_id": request.department_id,
            "template_id": request.template_id,
            "applied_config": config,
            "deployed_by": context["user_id"],
        }
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))
