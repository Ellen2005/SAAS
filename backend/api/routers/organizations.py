from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..core.auth import require_role, resolve_user_id, get_user_info
from ..core.supabase_client import get_supabase
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/organizations", tags=["organizations"])

class OrgUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    locale: Optional[str] = None
    industry: Optional[str] = None

@router.get("/me")
def get_my_org(user_id: str = Depends(resolve_user_id)):
    supabase = get_supabase()
    info = get_user_info(user_id)
    org_id = info.get("organization_id")
    if not org_id:
        import os
        return {"organization": {"id": None, "name": info.get("organization_name") or os.getenv("INSTITUTION_NAME","CNPS"), "is_default": True}}
    try:
        resp = supabase.table("organizations").select("*").eq("id", org_id).limit(1).execute()
        if hasattr(resp, "data") and resp.data:
            return {"organization": resp.data[0]}
    except Exception as e:
        logger.warning(f"org fetch failed: {e}")
    import os
    return {"organization": {"id": org_id, "name": info.get("organization_name") or os.getenv("INSTITUTION_NAME","CNPS")}}

@router.get("")
def list_orgs(context: dict = Depends(require_role(["admin"]))):
    supabase = get_supabase()
    resp = supabase.table("organizations").select("*").order("created_at").execute()
    return {"organizations": resp.data if hasattr(resp, "data") else []}

@router.patch("/{org_id}")
def update_org(org_id: str, body: OrgUpdate, context: dict = Depends(require_role(["admin"]))):
    supabase = get_supabase()
    payload = {k: v for k, v in body.model_dump().items() if v is not None}
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")
    payload["updated_at"] = "now()"
    try:
        resp = supabase.table("organizations").update(payload).eq("id", org_id).execute()
        row = resp.data[0] if hasattr(resp, "data") and resp.data else payload
        return {"organization": row}
    except Exception as e:
        logger.error(f"org update failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update organization")

@router.post("")
def create_org(body: OrgUpdate, context: dict = Depends(require_role(["admin"]))):
    supabase = get_supabase()
    if not body.name:
        raise HTTPException(status_code=400, detail="name is required")
    payload = body.model_dump(exclude_none=True)
    import re
    slug = re.sub(r'[^a-z0-9]+','-', body.name.lower()).strip('-')[:80]
    payload["slug"] = slug
    try:
        resp = supabase.table("organizations").insert(payload).execute()
        row = resp.data[0] if hasattr(resp, "data") and resp.data else payload
        return {"organization": row}
    except Exception as e:
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail="Organization slug already exists")
        raise HTTPException(status_code=500, detail="Failed to create organization")
