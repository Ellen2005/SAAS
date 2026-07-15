"""Goal-driven analysis API for CNPS SAAS."""
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List

from ..core.auth import require_role, resolve_user_id, get_user_info
from ..core.supabase_client import get_supabase
from ..services.analysis_engine import run_analysis, list_presets, list_runs, validate_formula
from ..services.export_service import export_analysis_runs_csv

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analysis", tags=["analysis"])


def _auto_generate_report(user_id: str, analysis_id: str, goal_text: str):
    """Background task: generate a professional report after goal analysis."""
    import os, tempfile, logging
    logger = logging.getLogger(__name__)
    try:
        from ..services.professional_report_service import generate_goal_analysis_report
        supabase = get_supabase()
        # Fetch the full analysis run to get the AI narrative (explanation)
        run_resp = supabase.table("analysis_runs").select("*").eq("id", analysis_id).limit(1).execute()
        run_data = run_resp.data[0] if hasattr(run_resp, "data") and run_resp.data else {}
        analysis_result = {
            "goal_text": goal_text,
            "id": analysis_id,
            "sql": run_data.get("plan_json", {}).get("sql", ""),
            "metrics": run_data.get("metrics_json", {}),
        }
        user_report_dir = os.path.join(tempfile.gettempdir(), f"reports_{user_id}")
        os.makedirs(user_report_dir, exist_ok=True)
        result = generate_goal_analysis_report(
            user_id=user_id,
            analysis_result=analysis_result,
            supabase=supabase,
            institution_name=os.getenv("INSTITUTION_NAME", "CNPS"),
            output_dir=user_report_dir,
        )
        report_record = {
            "user_id": user_id,
            "report_type": "goal_analysis",
            "file_path": result.get("pdf", ""),
            "excel_path": result.get("excel", ""),
            "report_id": result.get("report_id", analysis_id),
            "title": (goal_text or "Goal Analysis Report")[:80],
            "status": "generated",
        }
        try:
            supabase.table("reports").insert(report_record).execute()
        except Exception as insert_err:
            logger.warning(f"Could not save report record to reports table: {insert_err}")
        logger.info(f"Auto-generated report for analysis {analysis_id}")
    except Exception as e:
        logger.warning(f"Auto-report generation failed for analysis {analysis_id}: {e}")


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
    background_tasks: BackgroundTasks,
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
        error_msg = result.get("error", "Analysis failed")
        # Return 400 for expected errors (no DB) instead of 500
        if any(kw in error_msg.lower() for kw in ("no database connection", "could not generate", "could not generate analysis query")):
            raise HTTPException(status_code=400, detail=error_msg)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {error_msg}")
    # Auto-generate report in background after successful analysis
    analysis_id = result.get("id") or result.get("run_id") or ""
    background_tasks.add_task(
        _auto_generate_report,
        user_id=context["user_id"],
        analysis_id=str(analysis_id),
        goal_text=body.goal_text or "",
    )
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
        logger.error("Create preset failed", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


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
