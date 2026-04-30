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


def _summarize_for_kpi(result: dict) -> tuple[float, str] | None:
    """Reduce an analysis result down to a single (value, status) for the KPI feed."""
    kind = result.get("kind")
    if kind == "time_series_sum":
        rows = result.get("rows") or []
        if not rows:
            return None
        latest = rows[-1].get("total") or 0
        return float(latest), "NORMAL"
    if kind == "count_over_time":
        rows = result.get("rows") or []
        if not rows:
            return None
        latest = rows[-1].get("total") or 0
        return float(latest), "NORMAL"
    if kind == "anomaly_zscore":
        out = (result.get("stats") or {}).get("outlier_count", 0)
        status = "WARNING" if out >= 5 else ("WATCH" if out > 0 else "NORMAL")
        return float(out), status
    if kind == "missing_recent":
        rows = result.get("rows") or []
        if not rows:
            return None
        from datetime import date as _d
        try:
            last_seen = rows[0].get("last_seen") or ""
            d = _d.fromisoformat(str(last_seen)[:10])
            days = (_d.today() - d).days
        except Exception:
            return None
        status = "CRITICAL" if days > 30 else ("WARNING" if days > 7 else "NORMAL")
        return float(days), status
    if kind == "demographic":
        groups = result.get("groups") or []
        total = sum((r.get("total") or 0) for g in groups for r in (g.get("rows") or []))
        return float(total), "NORMAL"
    if kind == "liability_forecast":
        forecast = result.get("forecast") or []
        if not forecast:
            return None
        projected = sum((r.get("total") or 0) for r in forecast)
        return float(projected), "NORMAL"
    if kind == "overview":
        rows = result.get("rows") or []
        return float(len(rows)), "NORMAL"
    return None


def run_introspect_sync(user_id: str, supabase, refresh: bool = False) -> dict:
    """Discover the user's schema, run every suggested analysis, and persist
    each as a KPI row. Callable from both the HTTP route and the scheduler.

    Returns a dict with `synced`, `failed`, `skipped`, `kpis`, `errors`,
    `recorded_at` (and possibly `warning` / `error` for soft failures).
    """
    schema = _SCHEMA_CACHE.get(user_id)
    if not schema or refresh:
        try:
            schema = schema_introspector.introspect_user_database(user_id, supabase)
        except ValueError as exc:
            return {"synced": 0, "warning": str(exc)}
        except Exception as exc:
            return {"synced": 0, "error": str(exc)}
        _SCHEMA_CACHE[user_id] = schema

    analyses = schema_introspector.suggest_analyses(schema)
    if not analyses:
        return {"synced": 0, "warning": "No analyses could be suggested for this schema."}

    written: list[dict] = []
    failures: list[dict] = []
    from datetime import date as _date
    today = _date.today().isoformat()

    for spec in analyses:
        try:
            result = schema_introspector.run_analysis(user_id, supabase, spec)
            if "error" in result:
                failures.append({"title": spec.get("title"), "error": result["error"]})
                continue
            summary = _summarize_for_kpi(result)
            if summary is None:
                continue
            value, status = summary
            kpi_name = (spec.get("title") or spec.get("kind") or "analysis")[:100]
            row = {
                "user_id": user_id,
                "kpi_name": kpi_name,
                "value": round(value, 2),
                "status": status,
                "recorded_at": today,
            }
            try:
                supabase.table("kpi_results").insert(row).execute()
                written.append({"kpi_name": kpi_name, "value": row["value"], "status": status})
            except Exception as exc:
                failures.append({"title": kpi_name, "error": f"insert failed: {exc}"})
        except Exception as exc:
            failures.append({"title": spec.get("title"), "error": str(exc)})

    return {
        "synced": len(written),
        "skipped": len(analyses) - len(written) - len(failures),
        "failed": len(failures),
        "kpis": written,
        "errors": failures,
        "recorded_at": today,
    }


@router.post("/sync-to-kpis")
def sync_to_kpis(
    payload: dict | None = None,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Run every suggested analysis and persist its summary value as a KPI row.

    The resulting kpi_results rows feed the dashboard, the daily briefing email
    and the validation history — exactly the same surface the legacy
    hard-coded ETL writes to.
    """
    user_id = context["user_id"]
    supabase = get_supabase()
    result = run_introspect_sync(user_id, supabase, refresh=bool((payload or {}).get("refresh")))
    if result.get("error") and result.get("synced", 0) == 0:
        # Surface as 502 so the UI can render a real error
        raise HTTPException(status_code=502, detail=result["error"])
    return result
