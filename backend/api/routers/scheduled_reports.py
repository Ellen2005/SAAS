"""Scheduled report generation endpoints."""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import logging
from datetime import datetime, timezone

from ..core.auth import require_role, resolve_user_id
from ..core.supabase_client import get_supabase
from ..services.etl_service import run_user_etl_pipeline
from ..services.narrative_service import generate_live_narrative
from ..services.email_service import send_automated_briefing
from ..services.cache_service import invalidate_user_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/scheduled-reports", tags=["scheduled-reports"])


class ScheduleConfig(BaseModel):
    frequency: str = "daily"  # daily, weekly, monthly
    time: str = "06:00"  # HH:MM format
    enabled: bool = True
    recipients: List[str] = []
    report_type: str = "daily"  # daily, weekly, monthly


@router.post("/configure")
def configure_scheduled_reports(
    config: ScheduleConfig,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Configure scheduled report generation."""
    supabase = get_supabase()
    user_id = context["user_id"]
    
    try:
        # Save configuration to user_preferences
        prefs_data = {
            "user_id": user_id,
            "report_schedule_frequency": config.frequency,
            "report_schedule_time": config.time,
            "report_schedule_enabled": config.enabled,
            "report_recipients": config.recipients,
            "report_type": config.report_type,
        }
        
        supabase.table("user_preferences").upsert(prefs_data, on_conflict="user_id").execute()
        
        return {
            "status": "configured",
            "message": f"Scheduled {config.frequency} reports at {config.time}",
            "config": config.dict(),
        }
    except Exception as e:
        logger.error(f"Schedule configuration error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to configure schedule: {str(e)}")


@router.get("/config")
def get_schedule_config(user_id: str = Depends(resolve_user_id)):
    """Get current scheduled report configuration."""
    supabase = get_supabase()
    try:
        response = supabase.table("user_preferences").select("*").eq("user_id", user_id).limit(1).execute()
        if not response.data:
            return {
                "frequency": "daily",
                "time": "06:00",
                "enabled": False,
                "recipients": [],
                "report_type": "daily",
            }
        
        prefs = response.data[0]
        return {
            "frequency": prefs.get("report_schedule_frequency", "daily"),
            "time": prefs.get("report_schedule_time", "06:00"),
            "enabled": prefs.get("report_schedule_enabled", False),
            "recipients": prefs.get("report_recipients", []),
            "report_type": prefs.get("report_type", "daily"),
        }
    except Exception as e:
        logger.error(f"Get schedule config error: {e}")
        return {
            "frequency": "daily",
            "time": "06:00",
            "enabled": False,
            "recipients": [],
            "report_type": "daily",
        }


@router.post("/run-now")
def run_scheduled_report_now(
    background_tasks: BackgroundTasks,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Manually trigger a scheduled report generation."""
    user_id = context["user_id"]
    supabase = get_supabase()
    
    try:
        # Run ETL to get fresh data
        run_user_etl_pipeline(user_id)
        
        # Fetch KPIs and anomalies
        kpi_rows = (
            supabase.table("kpi_results")
            .select("*")
            .eq("user_id", user_id)
            .order("recorded_at", desc=True)
            .limit(20)
            .execute()
        )
        kpis = kpi_rows.data if hasattr(kpi_rows, "data") and kpi_rows.data else []
        
        anomaly_rows = (
            supabase.table("anomaly_records")
            .select("*")
            .eq("user_id", user_id)
            .order("detected_at", desc=True)
            .limit(10)
            .execute()
        )
        anomalies = anomaly_rows.data if hasattr(anomaly_rows, "data") and anomaly_rows.data else []
        
        # Generate narrative
        report_date = datetime.now().date().isoformat()
        narrative = generate_live_narrative(
            kpi_data=kpis,
            anomaly_data=anomalies,
            tone="insight-driven",
            company_name="CNPS",
            report_period=report_date,
            report_type="Daily",
        )
        
        # Save report
        supabase.table("daily_reports").insert({
            "user_id": user_id,
            "narrative": narrative,
            "report_date": report_date,
        }).execute()
        
        # Send email if recipients configured
        prefs_resp = supabase.table("user_preferences").select("report_recipients").eq("user_id", user_id).limit(1).execute()
        if prefs_resp.data:
            recipients = prefs_resp.data[0].get("report_recipients", [])
            if recipients:
                import pandas as pd
                background_tasks.add_task(
                    send_automated_briefing,
                    user_id, kpis, anomalies, narrative, pd.DataFrame(), "Daily", report_date
                )
        
        # Invalidate cache
        invalidate_user_cache(user_id)
        
        return {
            "status": "generated",
            "report_date": report_date,
            "message": "Report generated and queued for email delivery",
        }
    except Exception as e:
        logger.error(f"Manual report generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@router.get("/history")
def get_scheduled_report_history(
    limit: int = 20,
    user_id: str = Depends(resolve_user_id),
):
    """Get history of scheduled reports."""
    supabase = get_supabase()
    try:
        rows = (
            supabase.table("daily_reports")
            .select("id, report_date, created_at")
            .eq("user_id", user_id)
            .order("report_date", desc=True)
            .limit(limit)
            .execute()
        )
        reports = rows.data if hasattr(rows, "data") and rows.data else []
        return {"reports": reports, "count": len(reports)}
    except Exception as e:
        logger.error(f"Get report history error: {e}")
        return {"reports": [], "count": 0}