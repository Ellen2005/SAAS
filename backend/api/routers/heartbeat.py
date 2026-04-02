from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel

from ..core.auth import require_role, resolve_user_id
from ..core.supabase_client import get_supabase
from ..services.etl_service import run_user_etl_pipeline

router = APIRouter(prefix="/api", tags=["heartbeat"])


class IngestPayload(BaseModel):
    department: str
    report_date: str | None = None
    kpis: list = []
    anomalies: list = []
    validation: dict | None = None
    narrative: str | None = None
    department_breakdown: dict | None = None


def _safe_data(response) -> list:
    return response.data if hasattr(response, "data") and response.data else []


@router.get("/heartbeat/status")
def heartbeat_status(user_id: str = Depends(resolve_user_id)):
    """
    Lightweight department-instance status for the admin pull scheduler.
    """
    supabase = get_supabase()

    try:
        user_roles = _safe_data(
            supabase.table("user_roles")
            .select("department_id, role")
            .eq("user_id", user_id)
            .execute()
        )
        department_id = next(
            (row.get("department_id") for row in user_roles if row.get("department_id")),
            None,
        )
        department_name = None
        if department_id:
            dept_rows = _safe_data(
                supabase.table("departments")
                .select("name")
                .eq("id", department_id)
                .limit(1)
                .execute()
            )
            if dept_rows:
                department_name = dept_rows[0].get("name")

        kpi_rows = _safe_data(
            supabase.table("kpi_results")
            .select("recorded_at")
            .eq("user_id", user_id)
            .order("recorded_at", desc=True)
            .limit(1)
            .execute()
        )
        pref_rows = _safe_data(
            supabase.table("user_preferences")
            .select("last_sync_status")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        count_resp = (
            supabase.table("kpi_results")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        validation_rows = _safe_data(
            supabase.table("validation_logs")
            .select("status")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )

        passes = len([row for row in validation_rows if row.get("status") == "pass"])
        validation_score = round((passes / len(validation_rows)) * 100, 1) if validation_rows else None

        return {
            "user_id": user_id,
            "department_id": department_id,
            "department_name": department_name,
            "last_sync": kpi_rows[0].get("recorded_at") if kpi_rows else None,
            "status": pref_rows[0].get("last_sync_status", "IDLE") if pref_rows else "IDLE",
            "data_available": getattr(count_resp, "count", 0) > 0,
            "kpi_count": getattr(count_resp, "count", 0),
            "validation_score": validation_score,
        }
    except Exception as error:
        return {
            "user_id": user_id,
            "department_id": None,
            "department_name": None,
            "last_sync": None,
            "status": "ERROR",
            "data_available": False,
            "kpi_count": 0,
            "error": str(error),
        }


@router.post("/heartbeat/pull")
def heartbeat_pull(
    background_tasks: BackgroundTasks,
    user_id: str = Depends(resolve_user_id),
):
    background_tasks.add_task(run_user_etl_pipeline, user_id)
    return {
        "status": "pull_accepted",
        "user_id": user_id,
        "triggered_at": datetime.now().isoformat(),
    }


@router.post("/ingest")
def ingest_department_summary(
    payload: IngestPayload,
    context: dict = Depends(require_role(["admin", "manager"])),
):
    """
    Allows a department instance to post a summarized payload back to the admin layer.
    In the current monolith deployment this stores a combined report snapshot for observability.
    """
    supabase = get_supabase()
    report_date = payload.report_date or datetime.now().date().isoformat()

    try:
        combined_payload = {
            "report_date": report_date,
            "department_breakdown": payload.department_breakdown
            or {payload.department: {"kpis": payload.kpis, "validation": payload.validation}},
            "combined_kpis": {item.get("kpi_name"): item.get("value") for item in payload.kpis},
            "narrative": payload.narrative
            or f"Ingested summary for {payload.department} on {report_date}.",
        }
        supabase.table("combined_reports").insert(combined_payload).execute()
        return {"status": "ingested", "report_date": report_date, "ingested_by": context["user_id"]}
    except Exception as error:
        return {"status": "error", "message": str(error)}
