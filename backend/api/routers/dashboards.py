"""
Custom Dashboards Router
========================
Allows users to create, save, and share custom dashboard layouts.

Features:
- Save dashboard configurations
- Share dashboards with other users
- Template dashboards
- Widget positioning
- Custom filters
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..core.auth import require_role, resolve_user_id
from ..core.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboards", tags=["dashboards"])


# ── Models ───────────────────────────────────────────────────────────────────

class DashboardWidget(BaseModel):
    id: str
    type: str  # kpi_card, chart, table, metric
    title: str
    x: int
    y: int
    width: int
    height: int
    config: dict = {}
    data_source: Optional[str] = None
    refresh_interval: Optional[int] = 60  # seconds

class DashboardFilter(BaseModel):
    id: str
    name: str
    type: str  # date, select, multiselect, text
    column: str
    default_value: Optional[str] = None
    options: List[str] = []

class DashboardCreate(BaseModel):
    name: str
    description: Optional[str] = None
    layout: List[DashboardWidget]
    filters: List[DashboardFilter] = []
    is_public: bool = False
    is_template: bool = False
    tags: List[str] = []

class DashboardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    layout: Optional[List[DashboardWidget]] = None
    filters: Optional[List[DashboardFilter]] = None
    is_public: Optional[bool] = None
    is_template: Optional[bool] = None
    tags: Optional[List[str]] = None

class Dashboard(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str]
    layout: List[dict]
    filters: List[dict]
    is_public: bool
    is_template: bool
    tags: List[str]
    created_at: str
    updated_at: str
    shared_with: List[str] = []


# ── CRUD Operations ──────────────────────────────────────────────────────────

@router.get("/")
def get_dashboards(
    include_public: bool = Query(True, description="Include public dashboards"),
    include_templates: bool = Query(True, description="Include templates"),
    user_id: str = Depends(resolve_user_id),
):
    """Get all dashboards accessible to the user."""
    supabase = get_supabase()
    
    # Get user's own dashboards
    response = supabase.table("dashboards")\
        .select("*")\
        .eq("user_id", user_id)\
        .order("updated_at", desc=True)\
        .execute()
    
    dashboards = response.data if hasattr(response, "data") and response.data else []
    
    # Add public dashboards if requested
    if include_public:
        public_response = supabase.table("dashboards")\
            .select("*")\
            .eq("is_public", True)\
            .neq("user_id", user_id)\
            .order("updated_at", desc=True)\
            .execute()
        
        public_dashboards = public_response.data if hasattr(public_response, "data") and public_response.data else []
        dashboards.extend(public_dashboards)
    
    # Add templates if requested
    if include_templates:
        template_response = supabase.table("dashboards")\
            .select("*")\
            .eq("is_template", True)\
            .order("created_at", desc=True)\
            .execute()
        
        templates = template_response.data if hasattr(template_response, "data") and template_response.data else []
        dashboards.extend(templates)
    
    return {"dashboards": dashboards}


@router.get("/{dashboard_id}")
def get_dashboard(
    dashboard_id: str,
    user_id: str = Depends(resolve_user_id),
):
    """Get a specific dashboard by ID."""
    supabase = get_supabase()
    
    response = supabase.table("dashboards")\
        .select("*")\
        .eq("id", dashboard_id)\
        .execute()
    
    if not hasattr(response, "data") or not response.data:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    dashboard = response.data[0]
    
    # Check access: owner, public, or shared
    if dashboard["user_id"] != user_id and not dashboard.get("is_public"):
        shared_with = dashboard.get("shared_with", [])
        if user_id not in shared_with:
            raise HTTPException(status_code=403, detail="Access denied")
    
    return dashboard


@router.post("/")
def create_dashboard(
    dashboard: DashboardCreate,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Create a new custom dashboard."""
    supabase = get_supabase()
    user_id = context["user_id"]
    
    try:
        response = supabase.table("dashboards").insert({
            "user_id": user_id,
            "name": dashboard.name,
            "description": dashboard.description,
            "layout": [w.dict() for w in dashboard.layout],
            "filters": [f.dict() for f in dashboard.filters],
            "is_public": dashboard.is_public,
            "is_template": dashboard.is_template,
            "tags": dashboard.tags,
            "shared_with": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }).execute()
        
        if hasattr(response, "data") and response.data:
            return response.data[0]
        raise HTTPException(status_code=500, detail="Failed to create dashboard")
    except Exception as e:
        logger.error(f"Failed to create dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{dashboard_id}")
def update_dashboard(
    dashboard_id: str,
    updates: DashboardUpdate,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Update an existing dashboard."""
    supabase = get_supabase()
    user_id = context["user_id"]
    
    # Verify ownership
    existing = supabase.table("dashboards")\
        .select("user_id")\
        .eq("id", dashboard_id)\
        .execute()
    
    if not hasattr(existing, "data") or not existing.data:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    if existing.data[0]["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Only owner can update dashboard")
    
    # Build update dict
    update_data = {"updated_at": datetime.now().isoformat()}
    if updates.name is not None:
        update_data["name"] = updates.name
    if updates.description is not None:
        update_data["description"] = updates.description
    if updates.layout is not None:
        update_data["layout"] = [w.dict() if hasattr(w, 'dict') else w for w in updates.layout]
    if updates.filters is not None:
        update_data["filters"] = [f.dict() if hasattr(f, 'dict') else f for f in updates.filters]
    if updates.is_public is not None:
        update_data["is_public"] = updates.is_public
    if updates.is_template is not None:
        update_data["is_template"] = updates.is_template
    if updates.tags is not None:
        update_data["tags"] = updates.tags
    
    try:
        response = supabase.table("dashboards")\
            .update(update_data)\
            .eq("id", dashboard_id)\
            .execute()
        
        if hasattr(response, "data") and response.data:
            return response.data[0]
        raise HTTPException(status_code=500, detail="Failed to update dashboard")
    except Exception as e:
        logger.error(f"Failed to update dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{dashboard_id}")
def delete_dashboard(
    dashboard_id: str,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Delete a dashboard."""
    supabase = get_supabase()
    user_id = context["user_id"]
    
    # Verify ownership
    existing = supabase.table("dashboards")\
        .select("user_id")\
        .eq("id", dashboard_id)\
        .execute()
    
    if not hasattr(existing, "data") or not existing.data:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    if existing.data[0]["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Only owner can delete dashboard")
    
    try:
        supabase.table("dashboards")\
            .delete()\
            .eq("id", dashboard_id)\
            .execute()
        
        return {"status": "deleted", "dashboard_id": dashboard_id}
    except Exception as e:
        logger.error(f"Failed to delete dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{dashboard_id}/share")
def share_dashboard(
    dashboard_id: str,
    user_ids: List[str],
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Share dashboard with other users."""
    supabase = get_supabase()
    owner_id = context["user_id"]
    
    # Verify ownership
    existing = supabase.table("dashboards")\
        .select("user_id, shared_with")\
        .eq("id", dashboard_id)\
        .execute()
    
    if not hasattr(existing, "data") or not existing.data:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    if existing.data[0]["user_id"] != owner_id:
        raise HTTPException(status_code=403, detail="Only owner can share dashboard")
    
    # Update shared_with list
    current_shared = existing.data[0].get("shared_with", [])
    updated_shared = list(set(current_shared + user_ids))
    
    try:
        supabase.table("dashboards")\
            .update({"shared_with": updated_shared})\
            .eq("id", dashboard_id)\
            .execute()
        
        return {"status": "shared", "dashboard_id": dashboard_id, "shared_with": updated_shared}
    except Exception as e:
        logger.error(f"Failed to share dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{dashboard_id}/unshare")
def unshare_dashboard(
    dashboard_id: str,
    user_ids: List[str],
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Remove users from dashboard sharing."""
    supabase = get_supabase()
    owner_id = context["user_id"]
    
    # Verify ownership
    existing = supabase.table("dashboards")\
        .select("user_id, shared_with")\
        .eq("id", dashboard_id)\
        .execute()
    
    if not hasattr(existing, "data") or not existing.data:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    if existing.data[0]["user_id"] != owner_id:
        raise HTTPException(status_code=403, detail="Only owner can unshare dashboard")
    
    # Remove users from shared_with list
    current_shared = existing.data[0].get("shared_with", [])
    updated_shared = [uid for uid in current_shared if uid not in user_ids]
    
    try:
        supabase.table("dashboards")\
            .update({"shared_with": updated_shared})\
            .eq("id", dashboard_id)\
            .execute()
        
        return {"status": "unshared", "dashboard_id": dashboard_id, "shared_with": updated_shared}
    except Exception as e:
        logger.error(f"Failed to unshare dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/list")
def get_dashboard_templates():
    """Get all public dashboard templates."""
    supabase = get_supabase()
    
    response = supabase.table("dashboards")\
        .select("*")\
        .eq("is_template", True)\
        .eq("is_public", True)\
        .order("created_at", desc=True)\
        .execute()
    
    templates = response.data if hasattr(response, "data") and response.data else []
    return {"templates": templates}


@router.post("/{dashboard_id}/duplicate")
def duplicate_dashboard(
    dashboard_id: str,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Duplicate an existing dashboard."""
    supabase = get_supabase()
    user_id = context["user_id"]
    
    # Get original dashboard
    original = supabase.table("dashboards")\
        .select("*")\
        .eq("id", dashboard_id)\
        .execute()
    
    if not hasattr(original, "data") or not original.data:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    original_data = original.data[0]
    
    # Create duplicate
    try:
        response = supabase.table("dashboards").insert({
            "user_id": user_id,
            "name": f"{original_data['name']} (Copy)",
            "description": original_data.get("description"),
            "layout": original_data.get("layout", []),
            "filters": original_data.get("filters", []),
            "is_public": False,
            "is_template": False,
            "tags": original_data.get("tags", []),
            "shared_with": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }).execute()
        
        if hasattr(response, "data") and response.data:
            return response.data[0]
        raise HTTPException(status_code=500, detail="Failed to duplicate dashboard")
    except Exception as e:
        logger.error(f"Failed to duplicate dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))