"""
Introspection / Auto-Discovery API.

Exposes endpoints that:
  • Discover the structure of a customer's connected database
  • Suggest field mappings to the active semantic template
  • Suggest analyses based on the discovered schema
  • Run a single suggested analysis on demand
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Optional

from ..core.auth import require_role
from ..core.supabase_client import get_supabase
from ..services import schema_introspector

router = APIRouter(prefix="/api/introspect", tags=["introspect"])


# In-process cache so repeated UI calls don't hammer the customer DB.
# Keyed by user_id; not persistent — refresh on demand.
_SCHEMA_CACHE: dict[str, dict[str, Any]] = {}


class AnalysisSpec(BaseModel):
    id: Optional[str] = None
    kind: str
    table: Optional[str] = None
    title: Optional[str] = None
    amount_column: Optional[str] = None
    date_column: Optional[str] = None


@router.post("/schema")
def discover_schema(
    payload: dict | None = None,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    refresh = bool((payload or {}).get("refresh", False))
    sample_rows = int((payload or {}).get("sample_rows", 5))
    max_tables = int((payload or {}).get("max_tables", 200))
    user_id = context["user_id"]

    cached = _SCHEMA_CACHE.get(user_id)
    if cached and not refresh:
        return {"cached": True, **cached}

    supabase = get_supabase()
    try:
        schema = schema_introspector.introspect_user_database(
            user_id, supabase, sample_rows=sample_rows, max_tables=max_tables,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Introspection failed: {exc}")

    _SCHEMA_CACHE[user_id] = schema
    return {"cached": False, **schema}


@router.post("/auto-map")
def auto_map(
    payload: dict | None = None,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Suggest mappings between the user's semantic template and discovered columns."""
    user_id = context["user_id"]
    supabase = get_supabase()

    schema = _SCHEMA_CACHE.get(user_id)
    if not schema or (payload or {}).get("refresh"):
        try:
            schema = schema_introspector.introspect_user_database(user_id, supabase)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc))
        _SCHEMA_CACHE[user_id] = schema

    # Pull the user's semantic fields (via the existing semantic helper).
    from .semantic import get_my_template
    template = get_my_template(user_id=user_id)
    fields = template.get("fields") or []
    if not fields:
        return {"suggestions": [], "warning": "No semantic template configured."}

    suggestions = schema_introspector.suggest_field_mappings(schema, fields)
    return {"suggestions": suggestions, "field_count": len(fields)}


@router.post("/apply-mappings")
def apply_mappings(
    payload: dict,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Persist a list of suggested mappings as field_mappings rows."""
    user_id = context["user_id"]
    items = payload.get("mappings") or []
    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=400, detail="No mappings supplied.")
    supabase = get_supabase()
    saved = 0
    errors: list[str] = []
    for item in items:
        try:
            field_id = item.get("semantic_field_id") or item.get("template_field_id")
            local_col = item.get("column") or item.get("local_column_name")
            if not field_id or not local_col:
                continue
            supabase.table("field_mappings").upsert(
                {
                    "user_id": user_id,
                    "template_field_id": field_id,
                    "local_column_name": local_col,
                    "transformation_rule": item.get("transformation_rule"),
                },
                on_conflict="user_id,template_field_id",
            ).execute()
            saved += 1
        except Exception as exc:
            errors.append(str(exc))
    return {"saved": saved, "errors": errors}


@router.post("/analyses")
def list_suggested_analyses(
    context: dict = Depends(require_role(["manager", "admin"])),
):
    user_id = context["user_id"]
    schema = _SCHEMA_CACHE.get(user_id)
    if not schema:
        supabase = get_supabase()
        try:
            schema = schema_introspector.introspect_user_database(user_id, supabase)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc))
        _SCHEMA_CACHE[user_id] = schema
    return {"analyses": schema_introspector.suggest_analyses(schema)}


@router.post("/run-analysis")
def run_analysis(
    spec: AnalysisSpec,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    user_id = context["user_id"]
    supabase = get_supabase()
    try:
        result = schema_introspector.run_analysis(user_id, supabase, spec.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return result


@router.delete("/cache")
def clear_cache(context: dict = Depends(require_role(["manager", "admin"]))):
    _SCHEMA_CACHE.pop(context["user_id"], None)
    return {"cleared": True}
