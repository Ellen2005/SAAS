from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..core.auth import require_role, resolve_user_id
from ..core.supabase_client import get_supabase

router = APIRouter(prefix="/api", tags=["semantic"])


class TemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class FieldCreate(BaseModel):
    global_field_name: str
    data_type: str
    required: bool = False
    description: Optional[str] = None


class FieldUpdate(BaseModel):
    global_field_name: Optional[str] = None
    data_type: Optional[str] = None
    required: Optional[bool] = None
    description: Optional[str] = None


class MappingCreate(BaseModel):
    template_field_id: str
    local_column_name: str
    transformation_rule: Optional[dict] = None


class MappingUpdate(BaseModel):
    local_column_name: Optional[str] = None
    transformation_rule: Optional[dict] = None


def _safe_data(response) -> list:
    return response.data if hasattr(response, "data") and response.data else []


@router.get("/admin/semantic/templates")
def list_templates(context: dict = Depends(require_role(["admin"]))):
    supabase = get_supabase()
    try:
        template_rows = _safe_data(
            supabase.table("semantic_templates")
            .select("*")
            .order("created_at")
            .execute()
        )

        templates = []
        for template in template_rows:
            fields_resp = (
                supabase.table("semantic_fields")
                .select("id", count="exact")
                .eq("template_id", template["id"])
                .execute()
            )
            departments_resp = (
                supabase.table("departments")
                .select("id", count="exact")
                .eq("template_id", template["id"])
                .execute()
            )
            templates.append(
                {
                    **template,
                    "field_count": getattr(fields_resp, "count", 0),
                    "department_count": getattr(departments_resp, "count", 0),
                }
            )

        return {"templates": templates, "requested_by": context["user_id"]}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.post("/admin/semantic/templates")
def create_template(
    template: TemplateCreate,
    context: dict = Depends(require_role(["admin"])),
):
    supabase = get_supabase()
    payload = {
        "name": template.name,
        "description": template.description,
        "created_by": context["user_id"],
    }
    try:
        rows = _safe_data(supabase.table("semantic_templates").insert(payload).execute())
        return {"status": "success", "template": rows[0] if rows else payload}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.put("/admin/semantic/templates/{template_id}")
def update_template(
    template_id: str,
    template: TemplateUpdate,
    context: dict = Depends(require_role(["admin"])),
):
    supabase = get_supabase()
    payload = {key: value for key, value in template.model_dump().items() if value is not None}
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        supabase.table("semantic_templates").update(payload).eq("id", template_id).execute()
        return {"status": "success", "updated": payload, "updated_by": context["user_id"]}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.delete("/admin/semantic/templates/{template_id}")
def delete_template(
    template_id: str,
    context: dict = Depends(require_role(["admin"])),
):
    supabase = get_supabase()
    try:
        supabase.table("semantic_templates").delete().eq("id", template_id).execute()
        return {"status": "success", "deleted": template_id, "deleted_by": context["user_id"]}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.get("/admin/semantic/templates/{template_id}/fields")
def list_fields(
    template_id: str,
    context: dict = Depends(require_role(["admin"])),
):
    supabase = get_supabase()
    try:
        rows = _safe_data(
            supabase.table("semantic_fields")
            .select("*")
            .eq("template_id", template_id)
            .order("global_field_name")
            .execute()
        )
        return {"fields": rows, "requested_by": context["user_id"]}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.post("/admin/semantic/templates/{template_id}/fields")
def create_field(
    template_id: str,
    field: FieldCreate,
    context: dict = Depends(require_role(["admin"])),
):
    supabase = get_supabase()
    payload = {
        "template_id": template_id,
        "global_field_name": field.global_field_name,
        "data_type": field.data_type,
        "required": field.required,
        "description": field.description,
    }
    try:
        rows = _safe_data(supabase.table("semantic_fields").insert(payload).execute())
        return {"status": "success", "field": rows[0] if rows else payload}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.put("/admin/semantic/fields/{field_id}")
def update_field(
    field_id: str,
    field: FieldUpdate,
    context: dict = Depends(require_role(["admin"])),
):
    supabase = get_supabase()
    payload = {key: value for key, value in field.model_dump().items() if value is not None}
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        supabase.table("semantic_fields").update(payload).eq("id", field_id).execute()
        return {"status": "success", "updated": payload, "updated_by": context["user_id"]}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.delete("/admin/semantic/fields/{field_id}")
def delete_field(
    field_id: str,
    context: dict = Depends(require_role(["admin"])),
):
    supabase = get_supabase()
    try:
        supabase.table("semantic_fields").delete().eq("id", field_id).execute()
        return {"status": "success", "deleted": field_id, "deleted_by": context["user_id"]}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.get("/semantic/my-template")
def get_my_template(user_id: str = Depends(resolve_user_id)):
    supabase = get_supabase()
    try:
        user_roles = _safe_data(
            supabase.table("user_roles").select("department_id").eq("user_id", user_id).execute()
        )
    except Exception:
        return {"department": None, "template": None, "fields": [], "mappings": []}

    department_id = next(
        (row.get("department_id") for row in user_roles if row.get("department_id")),
        None,
    )

    try:
        if not department_id:
            general_rows = _safe_data(
                supabase.table("departments")
                .select("id, name, template_id")
                .eq("name", "General")
                .limit(1)
                .execute()
            )
            if not general_rows:
                return {"department": None, "template": None, "fields": [], "mappings": []}
            department = general_rows[0]
        else:
            department_rows = _safe_data(
                supabase.table("departments")
                .select("id, name, template_id")
                .eq("id", department_id)
                .limit(1)
                .execute()
            )
            department = department_rows[0] if department_rows else None
    except Exception:
        return {"department": None, "template": None, "fields": [], "mappings": []}

    if not department or not department.get("template_id"):
        return {"department": department, "template": None, "fields": [], "mappings": []}

    try:
        template_rows = _safe_data(
            supabase.table("semantic_templates")
            .select("*")
            .eq("id", department["template_id"])
            .limit(1)
            .execute()
        )
        fields = _safe_data(
            supabase.table("semantic_fields")
            .select("*")
            .eq("template_id", department["template_id"])
            .order("global_field_name")
            .execute()
        )
        mappings = _safe_data(
            supabase.table("field_mappings").select("*").eq("user_id", user_id).execute()
        )
    except Exception:
        return {"department": department, "template": None, "fields": [], "mappings": []}

    return {
        "department": department,
        "template": template_rows[0] if template_rows else None,
        "fields": fields,
        "mappings": mappings,
    }


@router.get("/semantic/mappings")
def list_my_mappings(user_id: str = Depends(resolve_user_id)):
    supabase = get_supabase()
    rows = _safe_data(
        supabase.table("field_mappings")
        .select("*, semantic_fields(global_field_name, data_type, required)")
        .eq("user_id", user_id)
        .execute()
    )
    return {"mappings": rows}


@router.post("/semantic/mappings")
def create_mapping(
    mapping: MappingCreate,
    user_id: str = Depends(resolve_user_id),
):
    supabase = get_supabase()
    payload = {
        "user_id": user_id,
        "template_field_id": mapping.template_field_id,
        "local_column_name": mapping.local_column_name,
        "transformation_rule": mapping.transformation_rule,
    }
    try:
        supabase.table("field_mappings").upsert(
            payload, on_conflict="user_id,template_field_id"
        ).execute()
        return {"status": "success", "mapping": payload}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.put("/semantic/mappings/{mapping_id}")
def update_mapping(
    mapping_id: str,
    mapping: MappingUpdate,
    user_id: str = Depends(resolve_user_id),
):
    supabase = get_supabase()
    payload = {key: value for key, value in mapping.model_dump().items() if value is not None}
    if not payload:
        raise HTTPException(status_code=400, detail="No mapping changes submitted")

    try:
        supabase.table("field_mappings").update(payload).eq("id", mapping_id).eq(
            "user_id", user_id
        ).execute()
        return {"status": "success", "updated": payload}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.delete("/semantic/mappings/{mapping_id}")
def delete_mapping(
    mapping_id: str,
    user_id: str = Depends(resolve_user_id),
):
    supabase = get_supabase()
    try:
        supabase.table("field_mappings").delete().eq("id", mapping_id).eq(
            "user_id", user_id
        ).execute()
        return {"status": "success", "deleted": mapping_id}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.get("/semantic/mappings/validate")
def validate_mappings(user_id: str = Depends(resolve_user_id)):
    template_data = get_my_template(user_id)
    fields = template_data.get("fields", [])
    mappings = template_data.get("mappings", [])

    mapped_field_ids = {mapping["template_field_id"] for mapping in mappings}
    required_fields = [field for field in fields if field.get("required")]
    optional_fields = [field for field in fields if not field.get("required")]

    missing_required = [field for field in required_fields if field["id"] not in mapped_field_ids]
    missing_optional = [field for field in optional_fields if field["id"] not in mapped_field_ids]

    return {
        "valid": len(missing_required) == 0,
        "total_fields": len(fields),
        "mapped_fields": len(mappings),
        "missing_required": [
            {"id": field["id"], "name": field["global_field_name"]} for field in missing_required
        ],
        "missing_optional": [
            {"id": field["id"], "name": field["global_field_name"]} for field in missing_optional
        ],
    }
