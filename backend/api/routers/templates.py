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
        rows = _safe_data(supabase.table("instance_templates").select("*").order("created_at").execute())
        return {"templates": rows, "requested_by": context["user_id"]}
    except Exception as error:
        return {"templates": [], "error": str(error)}


@router.post("/instances")
def create_instance_template(template: InstanceTemplateCreate, context: dict = Depends(require_role(["admin"]))):
    supabase = get_supabase()
    payload = {"name": template.name, "config": template.config, "created_by": context["user_id"]}
    try:
        rows = _safe_data(supabase.table("instance_templates").insert(payload).execute())
        return {"status": "success", "template": rows[0] if rows else payload}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.put("/instances/{template_id}")
def update_instance_template(template_id: str, template: InstanceTemplateUpdate, context: dict = Depends(require_role(["admin"]))):
    supabase = get_supabase()
    payload = {k: v for k, v in template.model_dump().items() if v is not None}
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")
    try:
        supabase.table("instance_templates").update(payload).eq("id", template_id).execute()
        return {"status": "success", "updated": payload, "updated_by": context["user_id"]}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.delete("/instances/{template_id}")
def delete_instance_template(template_id: str, context: dict = Depends(require_role(["admin"]))):
    supabase = get_supabase()
    try:
        supabase.table("instance_templates").delete().eq("id", template_id).execute()
        return {"status": "success", "deleted": template_id, "deleted_by": context["user_id"]}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.post("/deploy")
def deploy_instance_template(request: DeployTemplateRequest, context: dict = Depends(require_role(["admin"]))):
    supabase = get_supabase()
    errors = []

    try:
        template_rows = _safe_data(
            supabase.table("instance_templates").select("*").eq("id", request.template_id).limit(1).execute()
        )
        if not template_rows:
            raise HTTPException(status_code=404, detail="Instance template not found")

        config = template_rows[0].get("config") or {}
        sync_default = config.get("sync_default") or {}

        # Update department with template reference and schedule
        dept_update = {"instance_template_id": request.template_id}
        if config.get("semantic_template_id"):
            dept_update["template_id"] = config["semantic_template_id"]
        if sync_default.get("frequency"):
            dept_update["heartbeat_schedule"] = sync_default["frequency"]
        if sync_default.get("time"):
            dept_update["heartbeat_time"] = sync_default["time"]

        supabase.table("departments").update(dept_update).eq("id", request.department_id).execute()

        # Get all users in this department
        dept_users = _safe_data(
            supabase.table("user_roles").select("user_id").eq("department_id", request.department_id).execute()
        )

        ai_tone = config.get("ai_tone")
        email_recipients = [e for e in (config.get("email_recipients") or []) if e and "@" in e]

        for user_role in dept_users:
            uid = user_role["user_id"]

            # Update user preferences — try with all fields, fall back to core fields
            if ai_tone or sync_default:
                pref_payload = {
                    "user_id": uid,
                    "ai_tone": ai_tone or "insight-driven",
                    "sync_frequency": sync_default.get("frequency", "daily"),
                    "sync_time": sync_default.get("time", "06:00"),
                }
                try:
                    supabase.table("user_preferences").upsert(pref_payload, on_conflict="user_id").execute()
                except Exception as e:
                    # Fallback: some schemas may not have sync_frequency column yet
                    if "sync_frequency" in str(e):
                        core_pref = {"user_id": uid, "ai_tone": ai_tone or "insight-driven"}
                        try:
                            supabase.table("user_preferences").upsert(core_pref, on_conflict="user_id").execute()
                        except Exception as e2:
                            errors.append(f"Preferences for {uid}: {e2}")
                    else:
                        errors.append(f"Preferences for {uid}: {e}")

            # Insert email recipients — only if list is non-empty
            if email_recipients:
                inserts = [{"user_id": uid, "email": email} for email in email_recipients]
                try:
                    supabase.table("notification_recipients").insert(inserts).execute()
                except Exception as e:
                    errors.append(f"Recipients for {uid}: {e}")

        return {
            "status": "success",
            "department_id": request.department_id,
            "template_id": request.template_id,
            "users_updated": len(dept_users),
            "applied_config": config,
            "deployed_by": context["user_id"],
            "warnings": errors if errors else None,
        }
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))
