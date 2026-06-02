"""Goal-driven analysis API for CNPS SAAS."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from ..core.auth import require_role, resolve_user_id, get_user_info
from ..core.supabase_client import get_supabase
from ..services.analysis_engine import run_analysis, list_presets, list_runs, validate_formula
from ..services.export_service import export_analysis_runs_csv

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


class AnalysisRunRequest(BaseModel):
    goal_text: str
    goal_type: str = "natural_language"
    preset_slug: Optional[str] = None
    formula: Optional[str] = None


class FormulaValidateRequest(BaseModel):
    expression: str


class PresetCreateRequest(BaseModel):
    slug: str
    title_en: str
    title_fr: str
    category: str
    default_goal_text: str
    required_domains: Optional[List[str]] = None
    suggested_formula: Optional[str] = None


@router.get("/presets")
def get_presets(lang: str = "en", user_id: str = Depends(resolve_user_id)):
    supabase = get_supabase()
    return {"presets": list_presets(supabase, lang=lang)}


@router.get("/runs")
def get_runs(user_id: str = Depends(resolve_user_id)):
    supabase = get_supabase()
    return {"runs": list_runs(user_id, supabase)}


@router.post("/run")
def post_run(
    body: AnalysisRunRequest,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    if not body.goal_text and not body.preset_slug:
        raise HTTPException(status_code=400, detail="goal_text or preset_slug is required.")
    supabase = get_supabase()
    info = get_user_info(context["user_id"])
    result = run_analysis(
        user_id=context["user_id"],
        goal_text=body.goal_text or "",
        goal_type=body.goal_type,
        preset_slug=body.preset_slug,
        formula=body.formula,
        department_id=info.get("department_id"),
        supabase=supabase,
    )
    if result.get("status") == "failed":
        raise HTTPException(status_code=422, detail=result.get("error", "Analysis failed"))
    return result


@router.post("/validate-formula")
def post_validate_formula(
    body: FormulaValidateRequest,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    return validate_formula(body.expression)


@router.post("/admin/presets")
def create_preset(
    body: PresetCreateRequest,
    context: dict = Depends(require_role(["admin"])),
):
    """Admin: add a new CNPS analysis preset (appears on Analysis page for all users)."""
    supabase = get_supabase()
    slug = body.slug.strip().lower().replace(" ", "-")
    if not slug or not body.default_goal_text.strip():
        raise HTTPException(status_code=400, detail="slug and default_goal_text are required.")
    payload = {
        "slug": slug,
        "title_en": body.title_en,
        "title_fr": body.title_fr,
        "category": body.category,
        "default_goal_text": body.default_goal_text,
        "required_domains": body.required_domains or [],
        "suggested_formula": body.suggested_formula,
    }
    try:
        resp = supabase.table("cnps_analysis_presets").insert(payload).execute()
        row = resp.data[0] if hasattr(resp, "data") and resp.data else payload
        return {"status": "created", "preset": row}
    except Exception as e:
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"Preset slug '{slug}' already exists.")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/admin/presets/{slug}")
def delete_preset(slug: str, context: dict = Depends(require_role(["admin"]))):
    supabase = get_supabase()
    supabase.table("cnps_analysis_presets").delete().eq("slug", slug).execute()
    return {"status": "deleted", "slug": slug}


@router.get("/runs/export")
def export_runs(context: dict = Depends(require_role(["manager", "admin"]))):
    supabase = get_supabase()
    csv_bytes = export_analysis_runs_csv(context["user_id"], supabase)
    from fastapi.responses import Response
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cnps_analysis_runs.csv"},
    )
