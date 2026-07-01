"""
Global Dashboard Filters Router
================================
Provides filter metadata and filtered data for the dashboard.
All filters apply globally across all visualizations.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..core.auth import resolve_user_id, require_role
from ..core.supabase_client import get_supabase

router = APIRouter(prefix="/api/filters", tags=["dashboard-filters"])
logger = logging.getLogger(__name__)


class FilterState(BaseModel):
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    region: Optional[str] = None
    department: Optional[str] = None
    product: Optional[str] = None
    status: Optional[str] = None
    kpi_names: list[str] = []


@router.get("/options")
def get_filter_options(user_id: str = Depends(resolve_user_id)):
    """Return available filter options for the current user's data."""
    supabase = get_supabase()
    try:
        kpi_rows = (
            supabase.table("kpi_results")
            .select("kpi_name, recorded_at, department_id")
            .eq("user_id", user_id)
            .order("recorded_at", desc=True)
            .limit(1000)
            .execute()
        )
        raw = kpi_rows.data if hasattr(kpi_rows, "data") and kpi_rows.data else []

        kpi_names = sorted({r.get("kpi_name") for r in raw if r.get("kpi_name")})
        dates = [r.get("recorded_at") for r in raw if r.get("recorded_at")]
        date_from = min(dates) if dates else None
        date_to = max(dates) if dates else None
        departments = sorted({r.get("department_id") for r in raw if r.get("department_id")})

        return {
            "kpi_names": kpi_names,
            "date_range": {"from": date_from, "to": date_to},
            "departments": departments,
            "statuses": ["NORMAL", "WARNING", "CRITICAL"],
        }
    except Exception as e:
        logger.error(f"Filter options error: {e}")
        return {"kpi_names": [], "date_range": {}, "departments": [], "statuses": []}


@router.post("/apply")
def apply_filters(
    filters: FilterState,
    user_id: str = Depends(resolve_user_id),
):
    """Apply global filters and return filtered KPI data."""
    supabase = get_supabase()
    try:
        query = (
            supabase.table("kpi_results")
            .select("*")
            .eq("user_id", user_id)
        )

        if filters.date_from:
            query = query.gte("recorded_at", filters.date_from)
        if filters.date_to:
            query = query.lte("recorded_at", filters.date_to)
        if filters.department:
            query = query.eq("department_id", filters.department)
        if filters.kpi_names:
            query = query.in_("kpi_name", filters.kpi_names)

        rows = query.order("recorded_at", desc=True).limit(500).execute()
        data = rows.data if hasattr(rows, "data") and rows.data else []

        return {
            "filters_applied": filters.model_dump(exclude_none=True),
            "row_count": len(data),
            "data": data,
        }
    except Exception as e:
        logger.error("Apply filters error", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.get("/state")
def get_filter_state(user_id: str = Depends(resolve_user_id)):
    """Get saved filter state for the user."""
    supabase = get_supabase()
    try:
        resp = (
            supabase.table("user_preferences")
            .select("filter_state")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if hasattr(resp, "data") and resp.data and resp.data[0].get("filter_state"):
            return resp.data[0]["filter_state"]
        return {}
    except Exception:
        return {}


@router.post("/state")
def save_filter_state(
    state: dict,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Save filter state for the user."""
    supabase = get_supabase()
    try:
        supabase.table("user_preferences").upsert({
            "user_id": context["user_id"],
            "filter_state": state,
        }, on_conflict="user_id").execute()
        return {"status": "saved"}
    except Exception as e:
        logger.error("Save filter state error", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")