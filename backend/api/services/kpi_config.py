"""Admin-defined KPIs vs auto-discovery mode helpers."""
from __future__ import annotations


def get_department_template_id(supabase, user_id: str) -> str | None:
    try:
        roles = (
            supabase.table("user_roles")
            .select("department_id")
            .eq("user_id", user_id)
            .execute()
        )
        dept_id = None
        if hasattr(roles, "data") and roles.data:
            for row in roles.data:
                if row.get("department_id"):
                    dept_id = row["department_id"]
                    break
        if not dept_id:
            general = (
                supabase.table("departments")
                .select("id")
                .eq("name", "General")
                .limit(1)
                .execute()
            )
            if hasattr(general, "data") and general.data:
                dept_id = general.data[0]["id"]
        if not dept_id:
            return None
        dept = (
            supabase.table("departments")
            .select("template_id")
            .eq("id", dept_id)
            .limit(1)
            .execute()
        )
        if hasattr(dept, "data") and dept.data:
            return dept.data[0].get("template_id")
    except Exception:
        pass
    return None


def get_admin_kpi_fields(supabase, user_id: str) -> list[dict]:
    template_id = get_department_template_id(supabase, user_id)
    if not template_id:
        return []
    try:
        resp = (
            supabase.table("semantic_fields")
            .select("id, global_field_name, data_type, required, description")
            .eq("template_id", template_id)
            .execute()
        )
        return resp.data if hasattr(resp, "data") and resp.data else []
    except Exception:
        return []


def get_user_field_mappings(supabase, user_id: str) -> list[dict]:
    try:
        resp = (
            supabase.table("field_mappings")
            .select("id, template_field_id, local_column_name")
            .eq("user_id", user_id)
            .execute()
        )
        return resp.data if hasattr(resp, "data") and resp.data else []
    except Exception:
        return []


def resolve_kpi_mode(supabase, user_id: str) -> dict:
    """
    Returns:
      mode: configured | auto | overview_pending
      admin_field_count, mapped_count
    """
    fields = get_admin_kpi_fields(supabase, user_id)
    mappings = get_user_field_mappings(supabase, user_id)
    mapped_field_ids = {m["template_field_id"] for m in mappings if m.get("template_field_id")}
    required_fields = [f for f in fields if f.get("required")]
    mapped_required = [f for f in required_fields if f["id"] in mapped_field_ids]

    if fields and mapped_field_ids:
        return {
            "mode": "configured",
            "admin_field_count": len(fields),
            "mapped_count": len(mapped_field_ids),
            "required_count": len(required_fields),
            "mapped_required_count": len(mapped_required),
        }
    if fields:
        return {
            "mode": "configured",
            "admin_field_count": len(fields),
            "mapped_count": 0,
            "required_count": len(required_fields),
            "mapped_required_count": 0,
            "note": "Admin KPIs exist but no column mappings yet; sync uses auto-discovery until mappings are saved.",
        }
    return {
        "mode": "auto",
        "admin_field_count": 0,
        "mapped_count": 0,
        "required_count": 0,
        "mapped_required_count": 0,
    }
