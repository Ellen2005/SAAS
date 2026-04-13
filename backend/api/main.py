from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
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
from .services.email_service import send_automated_briefing, verify_unsubscribe_token
from .core.scheduler import start_scheduler, shutdown_scheduler
from .services.etl_service import run_user_etl_pipeline, _get_free_local_port, _replace_db_url_host_port, _start_ssh_tunnel
from .services.audit_service import log_config_change

from .routers import departments, users, semantic, validation, admin, heartbeat, templates


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="SAAS-PWA Analytics System API", lifespan=lifespan)

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

app.include_router(departments.router)
app.include_router(users.router)
app.include_router(semantic.router)
app.include_router(validation.router)
app.include_router(admin.router)
app.include_router(heartbeat.router)
app.include_router(templates.router)


# ── Models ────────────────────────────────────────────────────────────────────

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


# ── Keepalive ping (prevents cold-start on free-tier hosts) ───────────────────

@app.get("/api/ping", include_in_schema=False)
def ping():
    return {"ok": True}


# ── Favicon (suppresses 404 log noise) ────────────────────────────────────────

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    from fastapi.responses import Response
    return Response(status_code=204)


# ── Root ──────────────────────────────────────────────────────────────────────

@app.get("/")
def read_root():
    return {"message": "Welcome to SAAS-PWA Backend"}


# ── Dashboard Summary ─────────────────────────────────────────────────────────

@app.get("/api/summary", response_model=DashboardSummary)
def get_dashboard_summary(user_id: str = Depends(resolve_user_id)):
    supabase = get_supabase()
    try:
        kpi_resp = supabase.table("kpi_results").select("*").eq("user_id", user_id).order("recorded_at", desc=True).limit(5).execute()
        anomaly_resp = supabase.table("anomaly_records").select("*").eq("user_id", user_id).order("detected_at", desc=True).limit(10).execute()
        report_resp = supabase.table("daily_reports").select("*").eq("user_id", user_id).order("report_date", desc=True).limit(1).execute()
        validation_resp = supabase.table("validation_logs").select("check_type, status, message").eq("user_id", user_id).order("created_at", desc=True).limit(5).execute()

        kpis = []
        if hasattr(kpi_resp, "data") and kpi_resp.data:
            for item in kpi_resp.data:
                kpis.append(KPIResult(
                    id=item["id"], kpi_name=item["kpi_name"], value=float(item["value"]),
                    dod_pct=item.get("dod_pct"), wow_pct=item.get("wow_pct"), avg_7d=item.get("avg_7d"),
                    status=item["status"], recorded_at=str(item["recorded_at"]),
                ))

        anomalies = []
        if hasattr(anomaly_resp, "data") and anomaly_resp.data:
            for item in anomaly_resp.data:
                anomalies.append(AnomalyRecord(
                    id=item["id"], kpi_name=item["kpi_name"], severity=item["severity"],
                    deviation=float(item["deviation"]), context=item["context"], detected_at=item["detected_at"],
                ))

        narrative = "No analytics report generated yet. Go to Dashboard and click Sync Now to generate your first report."
        last_refreshed = "Never"
        if hasattr(report_resp, "data") and report_resp.data:
            narrative = report_resp.data[0]["narrative"]
            last_refreshed = str(report_resp.data[0]["report_date"])

        summary = DashboardSummary(kpis=kpis, anomalies=anomalies, narrative=narrative, last_refreshed=last_refreshed)
        summary_dict = summary.model_dump()
        summary_dict["validation"] = validation_resp.data if hasattr(validation_resp, "data") and validation_resp.data else []
        return summary_dict
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] Summary Fetch Error: {e}")
        fallback = DashboardSummary(kpis=[], anomalies=[], narrative=f"System Error: {str(e)}.", last_refreshed="ERROR")
        fallback_dict = fallback.model_dump()
        fallback_dict["validation"] = []
        return fallback_dict


# ── Report History ────────────────────────────────────────────────────────────

@app.get("/api/reports/history")
def get_reports_history(limit: int = 50, user_id: str = Depends(resolve_user_id)):
    """Returns all past daily reports for the user, newest first."""
    supabase = get_supabase()
    try:
        rows = (
            supabase.table("daily_reports")
            .select("id, report_date, narrative, department_id")
            .eq("user_id", user_id)
            .order("report_date", desc=True)
            .limit(limit)
            .execute()
        )
        return {"reports": rows.data if hasattr(rows, "data") and rows.data else []}
    except Exception as e:
        return {"reports": [], "error": str(e)}


# ── Report Edit & Resend ─────────────────────────────────────────────────────

@app.patch("/api/reports/{report_id}")
def edit_report_narrative(
    report_id: str,
    body: dict,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Save an edited narrative back to the daily_reports record."""
    narrative = body.get("narrative", "").strip()
    if not narrative:
        raise HTTPException(status_code=400, detail="Narrative cannot be empty.")
    supabase = get_supabase()
    try:
        supabase.table("daily_reports").update({"narrative": narrative}).eq("id", report_id).eq("user_id", context["user_id"]).execute()
        log_config_change(supabase, context["user_id"], "update", "report_narrative", {"report_id": report_id})
        return {"status": "updated", "report_id": report_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reports/{report_id}/send")
def resend_report(
    report_id: str,
    background_tasks: BackgroundTasks,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Resend a stored report (with any edits) to all notification recipients."""
    supabase = get_supabase()
    try:
        rows = supabase.table("daily_reports").select("*").eq("id", report_id).eq("user_id", context["user_id"]).limit(1).execute()
        if not rows.data:
            raise HTTPException(status_code=404, detail="Report not found.")
        report = rows.data[0]

        kpi_rows = supabase.table("kpi_results").select("*").eq("user_id", context["user_id"]).order("recorded_at", desc=True).limit(5).execute()
        anomaly_rows = supabase.table("anomaly_records").select("*").eq("user_id", context["user_id"]).order("detected_at", desc=True).limit(10).execute()
        kpis = kpi_rows.data if hasattr(kpi_rows, "data") and kpi_rows.data else []
        anomalies = anomaly_rows.data if hasattr(anomaly_rows, "data") and anomaly_rows.data else []

        import pandas as pd
        from .services.email_service import send_automated_briefing
        background_tasks.add_task(
            send_automated_briefing,
            context["user_id"], kpis, anomalies,
            report["narrative"],
            pd.DataFrame(),
            "Daily",
            str(report["report_date"]),
        )
        return {"status": "queued", "report_id": report_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── ETL ───────────────────────────────────────────────────────────────────────

@app.post("/api/etl/trigger")
def trigger_etl(background_tasks: BackgroundTasks, context: dict = Depends(require_role(["manager", "admin"]))):
    background_tasks.add_task(run_user_etl_pipeline, context["user_id"])
    return {"status": "Manual ETL trigger started in the background", "user_id": context["user_id"]}


@app.get("/api/etl/status")
def get_etl_status(user_id: str = Depends(resolve_user_id)):
    supabase = get_supabase()
    response = supabase.table("user_preferences").select("last_sync_status").eq("user_id", user_id).execute()
    if hasattr(response, "data") and response.data:
        return {"status": response.data[0].get("last_sync_status", "IDLE")}
    return {"status": "IDLE"}


# ── Forecasts ─────────────────────────────────────────────────────────────────

@app.get("/api/forecasts")
def get_forecasts(user_id: str = Depends(resolve_user_id)):
    supabase = get_supabase()
    try:
        rows = supabase.table("kpi_forecasts").select("*").eq("user_id", user_id).order("forecast_date").execute()
        return {"forecasts": rows.data if hasattr(rows, "data") and rows.data else []}
    except Exception as e:
        return {"forecasts": [], "error": str(e)}


# ── Preferences ───────────────────────────────────────────────────────────────

@app.get("/api/settings/preferences")
def get_user_preferences(user_id: str = Depends(resolve_user_id)):
    supabase = get_supabase()
    response = supabase.table("user_preferences").select("*").eq("user_id", user_id).execute()
    if hasattr(response, "data") and response.data:
        return response.data[0]
    return {"ai_tone": "insight-driven", "sync_time": "02:00", "last_sync_status": "IDLE"}


@app.post("/api/settings/preferences")
def update_user_preferences(prefs: dict, context: dict = Depends(require_role(["manager", "admin"]))):
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
        supabase.table("user_preferences").upsert(data, on_conflict="user_id").execute()
    except Exception as e:
        if any(k in str(e) for k in ("sync_frequency", "yearly_date", "analysis_instruction")):
            legacy = {k: v for k, v in data.items() if k not in {"sync_frequency", "yearly_date", "analysis_instruction"}}
            supabase.table("user_preferences").upsert(legacy, on_conflict="user_id").execute()
        else:
            raise

    log_config_change(supabase, user_id, "update", "preferences", {k: v for k, v in data.items() if k != "user_id"})
    return {"status": "success", "preferences": data}


# ── Connection ────────────────────────────────────────────────────────────────

@app.post("/api/test-connection")
def test_db_connection(connection_data: dict):
    db_url = connection_data.get("credentials")
    connection_method = connection_data.get("connection_method") or "direct"
    connection_options = connection_data.get("connection_options") or {}
    if not db_url:
        raise HTTPException(status_code=400, detail="Missing connection string (credentials)")

    engine = None
    tunnel_proc = None
    try:
        db_url_for_test = db_url
        if connection_method == "ssh_tunnel":
            ssh_host = connection_options.get("ssh_host") or connection_data.get("host")
            ssh_user = connection_options.get("ssh_user")
            remote_host = connection_options.get("remote_db_host") or connection_data.get("host")
            remote_port = connection_data.get("port")
            if not all([ssh_host, ssh_user, remote_host, remote_port]):
                raise HTTPException(status_code=400, detail="SSH tunnel test requires SSH host, user, remote DB host, and port.")
            local_port = _get_free_local_port()
            tunnel_proc = _start_ssh_tunnel(ssh_host=str(ssh_host), ssh_user=str(ssh_user), remote_host=str(remote_host), remote_port=int(remote_port), local_port=int(local_port))
            db_url_for_test = _replace_db_url_host_port(db_url, "127.0.0.1", int(local_port))

        engine = create_engine(db_url_for_test, connect_args={"connect_timeout": 10}, pool_pre_ping=True)
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("SELECT 1"))
        return {"status": "success", "message": "Connection verified!"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": f"Database Error: {str(e)}"}
    finally:
        if engine is not None:
            try:
                engine.dispose()
            except Exception:
                pass
        if tunnel_proc is not None:
            try:
                tunnel_proc.terminate()
                tunnel_proc.wait(timeout=5)
            except Exception:
                try:
                    tunnel_proc.kill()
                except Exception:
                    pass


@app.post("/api/settings/connection")
def save_db_connection(conn_data: dict, context: dict = Depends(require_role(["manager", "admin"]))):
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
        existing = supabase.table("database_connections").select("id").eq("user_id", user_id).limit(1).execute()
        has_existing = bool(getattr(existing, "data", None))
        if has_existing:
            supabase.table("database_connections").update(data).eq("user_id", user_id).execute()
        else:
            supabase.table("database_connections").insert(data).execute()
    except Exception as e:
        if "connection_method" in str(e) or "connection_options" in str(e):
            legacy = {k: v for k, v in data.items() if k not in {"connection_method", "connection_options"}}
            existing = supabase.table("database_connections").select("id").eq("user_id", user_id).limit(1).execute()
            if bool(getattr(existing, "data", None)):
                supabase.table("database_connections").update(legacy).eq("user_id", user_id).execute()
            else:
                supabase.table("database_connections").insert(legacy).execute()
        else:
            raise

    log_config_change(supabase, user_id, "update", "connection", {"db_type": data["db_type"], "host": data["host"], "connection_method": data["connection_method"]})
    return {"status": "success", "message": "Connection details saved successfully."}


# ── Unsubscribe ───────────────────────────────────────────────────────────────

@app.get("/api/unsubscribe")
def unsubscribe(email: str, token: str):
    if not verify_unsubscribe_token(email, token):
        raise HTTPException(status_code=400, detail="Invalid or expired unsubscribe link.")
    supabase = get_supabase()
    try:
        supabase.table("notification_recipients").delete().eq("email", email).execute()
        return {"status": "unsubscribed", "email": email}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unsubscribe: {str(e)}")


# ── Audit Log ─────────────────────────────────────────────────────────────────

@app.get("/api/audit-log")
def get_audit_log(limit: int = 50, context: dict = Depends(require_role(["manager", "admin"]))):
    supabase = get_supabase()
    try:
        rows = supabase.table("audit_logs").select("*").eq("user_id", context["user_id"]).order("created_at", desc=True).limit(limit).execute()
        return {"logs": rows.data if hasattr(rows, "data") and rows.data else []}
    except Exception as e:
        return {"logs": [], "error": str(e)}
