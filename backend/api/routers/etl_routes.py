from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import Optional
from ..core.supabase_client import get_supabase
from ..core.auth import require_role, resolve_user_id
from ..services.etl_service import run_user_etl_pipeline, update_sync_status
from ..services.export_service import export_kpis_csv
from ..services.analysis_engine import run_analysis as run_goal_analysis
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["etl"])


def _run_etl_with_optional_goal(user_id: str, analysis_goal: str | None, preset_slug: str | None):
    run_user_etl_pipeline(user_id)
    if analysis_goal or preset_slug:
        try:
            supabase = get_supabase()
            run_goal_analysis(
                user_id=user_id,
                goal_text=analysis_goal or "",
                preset_slug=preset_slug,
                supabase=supabase,
            )
        except Exception as e:
            logger.error(f"Goal analysis failed for user {user_id}: {e}", exc_info=True)


@router.post("/etl/trigger")
def trigger_etl(
    background_tasks: BackgroundTasks,
    context: dict = Depends(require_role(["manager", "admin"])),
    body: Optional[dict] = None,
):
    update_sync_status(context["user_id"], "FETCHING_DATA")
    goal = body.get("analysis_goal") if body else None
    preset = body.get("preset_slug") if body else None
    background_tasks.add_task(_run_etl_with_optional_goal, context["user_id"], goal, preset)
    return {
        "status": "Data refresh started in the background",
        "user_id": context["user_id"],
        "analysis_goal_queued": bool(goal or preset),
    }


@router.get("/etl/status")
def get_etl_status(user_id: str = Depends(resolve_user_id)):
    try:
        supabase = get_supabase()
        response = supabase.table("user_preferences").select("last_sync_status").eq("user_id", user_id).execute()
        if hasattr(response, "data") and response.data:
            return {"status": response.data[0].get("last_sync_status", "IDLE")}
        return {"status": "IDLE"}
    except Exception as e:
        logger.warning(f"ETL status fetch failed: {e}")
        return {"status": "IDLE"}


@router.get("/kpis/export")
def export_kpis(context: dict = Depends(require_role(["manager", "admin"]))):
    from fastapi.responses import Response
    supabase = get_supabase()
    return Response(
        content=export_kpis_csv(context["user_id"], supabase),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cnps_kpis.csv"},
    )
