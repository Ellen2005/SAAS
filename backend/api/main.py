from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os
from contextlib import asynccontextmanager
from sqlalchemy import create_engine
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from .core.supabase_client import get_supabase
from .core.auth import require_role, resolve_user_id
from .services.email_service import send_automated_briefing
from .core.scheduler import start_scheduler, shutdown_scheduler
from .services.etl_service import run_user_etl_pipeline

from .routers import departments, users, semantic, validation, admin, heartbeat, templates


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_scheduler()
    yield
    # Shutdown
    shutdown_scheduler()


app = FastAPI(title="SAAS-PWA Analytics System API", lifespan=lifespan)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include governed mesh routers
app.include_router(departments.router)
app.include_router(users.router)
app.include_router(semantic.router)
app.include_router(validation.router)
app.include_router(admin.router)
app.include_router(heartbeat.router)
app.include_router(templates.router)


# Models for the API
class KPIResult(BaseModel):
    id: str
    kpi_name: str
    value: float
    dod_pct: Optional[float] = None
    wow_pct: Optional[float] = None
    avg_7d: Optional[float] = None
    status: str
    recorded_at: str


class AnomalyRecord(BaseModel):
    id: str
    kpi_name: str
    severity: str
    deviation: float
    context: dict
    detected_at: str


class DashboardSummary(BaseModel):
    kpis: List[KPIResult]
    anomalies: List[AnomalyRecord]
    narrative: str
    last_refreshed: str
    validation: List[dict] = []


@app.get("/")
def read_root():
    return {"message": "Welcome to SAAS-PWA Backend"}


@app.get("/api/summary", response_model=DashboardSummary)
def get_dashboard_summary(user_id: str = Depends(resolve_user_id)):
    """
    Returns the daily dashboard summary for a specific user.
    Reads real data from Supabase.
    """
    supabase = get_supabase()

    try:
        # 1. Fetch KPIs
        kpi_resp = (
            supabase.table("kpi_results")
            .select("*")
            .eq("user_id", user_id)
            .order("recorded_at", desc=True)
            .limit(5)
            .execute()
        )
        kpis = []
        if hasattr(kpi_resp, "data") and kpi_resp.data:
            for item in kpi_resp.data:
                kpis.append(
                    KPIResult(
                        id=item["id"],
                        kpi_name=item["kpi_name"],
                        value=float(item["value"]),
                        dod_pct=item.get("dod_pct"),
                        wow_pct=item.get("wow_pct"),
                        avg_7d=item.get("avg_7d"),
                        status=item["status"],
                        recorded_at=str(item["recorded_at"]),
                    )
                )

        # 2. Fetch Anomalies
        anomaly_resp = (
            supabase.table("anomaly_records")
            .select("*")
            .eq("user_id", user_id)
            .order("detected_at", desc=True)
            .limit(10)
            .execute()
        )
        anomalies = []
        if hasattr(anomaly_resp, "data") and anomaly_resp.data:
            for item in anomaly_resp.data:
                anomalies.append(
                    AnomalyRecord(
                        id=item["id"],
                        kpi_name=item["kpi_name"],
                        severity=item["severity"],
                        deviation=float(item["deviation"]),
                        context=item["context"],
                        detected_at=item["detected_at"],
                    )
                )

        # 3. Fetch Latest Narrative
        report_resp = (
            supabase.table("daily_reports")
            .select("*")
            .eq("user_id", user_id)
            .order("report_date", desc=True)
            .limit(1)
            .execute()
        )
        validation_resp = (
            supabase.table("validation_logs")
            .select("check_type, status, message")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        narrative = "No analytics report generated yet. Please trigger a manual sync in Settings."
        last_refreshed = "Never"

        if hasattr(report_resp, "data") and report_resp.data:
            narrative = report_resp.data[0]["narrative"]
            last_refreshed = str(report_resp.data[0]["report_date"])

        summary = DashboardSummary(
            kpis=kpis,
            anomalies=anomalies,
            narrative=narrative,
            last_refreshed=last_refreshed,
        )
        summary_dict = summary.model_dump()
        summary_dict["validation"] = (
            validation_resp.data
            if hasattr(validation_resp, "data") and validation_resp.data
            else []
        )
        return summary_dict
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] Summary Fetch Error: {e}")
        # Fallback to empty if tables are missing or id mismatches
        fallback = DashboardSummary(
            kpis=[],
            anomalies=[],
            narrative=f"System Error: {str(e)}. Please ensure Supabase tables are initialized.",
            last_refreshed="ERROR",
        )
        fallback_dict = fallback.model_dump()
        fallback_dict["validation"] = []
        return fallback_dict


@app.post("/api/etl/trigger")
def trigger_etl(
    background_tasks: BackgroundTasks,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """
    Manually triggers the ETL pipeline logic for the specified user
    so we can test it from the dashboard or via API testing.
    """
    background_tasks.add_task(run_user_etl_pipeline, context["user_id"])
    return {
        "status": "Manual ETL trigger started in the background",
        "user_id": context["user_id"],
    }


@app.get("/api/settings/preferences")
def get_user_preferences(user_id: str = Depends(resolve_user_id)):
    """
    Fetch the user's AI tone and sync time preferences.
    """
    supabase = get_supabase()
    response = (
        supabase.table("user_preferences").select("*").eq("user_id", user_id).execute()
    )

    if hasattr(response, "data") and response.data:
        return response.data[0]
    else:
        # Default fallback
        return {
            "ai_tone": "insight-driven",
            "sync_time": "02:00",
            "last_sync_status": "IDLE",
        }


@app.get("/api/etl/status")
def get_etl_status(user_id: str = Depends(resolve_user_id)):
    """
    Returns the current sync status for a user.
    """
    supabase = get_supabase()
    response = (
        supabase.table("user_preferences")
        .select("last_sync_status")
        .eq("user_id", user_id)
        .execute()
    )

    if hasattr(response, "data") and response.data:
        return {"status": response.data[0].get("last_sync_status", "IDLE")}
    return {"status": "IDLE"}


@app.post("/api/settings/preferences")
def update_user_preferences(
    prefs: dict,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """
    Update the user's AI tone, scheduling, and instructions.
    """
    user_id = prefs.get("user_id") or context["user_id"]
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user_id")

    supabase = get_supabase()
    data = {
        "user_id": user_id,
        "ai_tone": prefs.get("ai_tone", "insight-driven"),
        "sync_time": prefs.get("sync_time", "02:00"),
        "sync_frequency": prefs.get("sync_frequency", "daily"),
        "yearly_date": prefs.get("yearly_date", "01-01"),
        "analysis_instruction": prefs.get("analysis_instruction"),
    }

    try:
        response = (
            supabase.table("user_preferences")
            .upsert(data, on_conflict="user_id")
            .execute()
        )
    except Exception as e:
        if (
            "sync_frequency" in str(e)
            or "yearly_date" in str(e)
            or "analysis_instruction" in str(e)
        ):
            legacy_data = {
                key: value
                for key, value in data.items()
                if key
                not in {"sync_frequency", "yearly_date", "analysis_instruction"}
            }
            response = (
                supabase.table("user_preferences")
                .upsert(legacy_data, on_conflict="user_id")
                .execute()
            )
        else:
            raise
    return {"status": "success", "preferences": data}


@app.post("/api/test-connection")
def test_db_connection(connection_data: dict):
    """
    Attempts to connect to a database using the provided credentials.
    Returns success or error message.
    """
    db_url = connection_data.get("credentials")
    if not db_url:
        raise HTTPException(
            status_code=400, detail="Missing connection string (credentials)"
        )

    try:
        # Added 15s timeout to prevent 'forever' hangs on unreachable hosts
        engine = create_engine(db_url, connect_args={"connect_timeout": 15})
        with engine.connect() as conn:
            # Simple query to test the connection
            from sqlalchemy import text

            conn.execute(text("SELECT 1"))
        return {"status": "success", "message": "Connection verified!"}
    except Exception as e:
        import traceback

        error_msg = f"Database Error: {str(e)}"
        print(f"[{datetime.now().isoformat()}] {error_msg}")
        traceback.print_exc()
        return {"status": "error", "message": error_msg}


@app.post("/api/settings/connection")
def save_db_connection(
    conn_data: dict,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """
    Saves the user's database connection details to Supabase.
    """
    user_id = conn_data.get("user_id") or context["user_id"]
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user_id")

    supabase = get_supabase()
    data = {
        "user_id": user_id,
        "db_type": conn_data.get("db_type", "postgresql"),
        "host": conn_data.get("host"),
        "port": conn_data.get("port"),
        "db_name": conn_data.get("db_name"),
        "credentials": conn_data.get("credentials"),
        "read_only": True,
        "connection_method": conn_data.get("connection_method", "direct"),
        "connection_options": conn_data.get("connection_options"),
    }

    try:
        # database_connections.user_id is not guaranteed to have a UNIQUE constraint,
        # so `upsert(..., on_conflict="user_id")` can fail. Implement update-or-insert
        # based on whether a row already exists for this user.
        existing = (
            supabase.table("database_connections")
            .select("id")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        has_existing = bool(getattr(existing, "data", None))

        if has_existing:
            supabase.table("database_connections").update(data).eq("user_id", user_id).execute()
        else:
            supabase.table("database_connections").insert(data).execute()
    except Exception as e:
        # Graceful fallback for pre-migration schemas missing newer optional columns.
        if "connection_method" in str(e) or "connection_options" in str(e):
            legacy_data = {
                key: value
                for key, value in data.items()
                if key not in {"connection_method", "connection_options"}
            }
            existing = (
                supabase.table("database_connections")
                .select("id")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            has_existing = bool(getattr(existing, "data", None))

            if has_existing:
                supabase.table("database_connections").update(legacy_data).eq("user_id", user_id).execute()
            else:
                supabase.table("database_connections").insert(legacy_data).execute()
        else:
            raise
    return {"status": "success", "message": "Connection details saved successfully."}
