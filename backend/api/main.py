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
from .services.etl_service import run_user_etl_pipeline, _get_free_local_port, _replace_db_url_host_port, _start_ssh_tunnel, update_sync_status
from .services.connection_utils import (
    detect_db_type,
    enrich_connection_payload,
    normalize_credentials,
    sqlalchemy_engine_kwargs,
)
from .services.audit_service import log_config_change

from .routers import departments, users, semantic, validation, admin, heartbeat, templates, introspect, analyst, assistant  # noqa: F401
from .services.nlq_service import run_nlq
from .services.custom_report_service import generate_custom_report

LEGACY_DEMO_KPI_NAMES = frozenset({
    "net_revenue", "inventory_value", "support_tickets",
    "Total Revenue", "Inventory Value", "Support Tickets",
})


def _is_legacy_demo_kpi(row: dict) -> bool:
    """Hide leftover seed/demo KPI rows completely."""
    name = row.get("kpi_name")
    return name in LEGACY_DEMO_KPI_NAMES or (name and name.replace("_", " ").title() in LEGACY_DEMO_KPI_NAMES)


def _is_legacy_demo_report(row: dict) -> bool:
    narrative = row.get("narrative") or ""
    # Only filter reports that contain all three legacy demo markers together
    demo_markers = ("Net Revenue is 190,000", "Inventory Value is", "Support Tickets is 150")
    return all(marker in narrative for marker in demo_markers)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="SAAS-PWA Analytics System API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5000",
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
app.include_router(introspect.router)
app.include_router(analyst.router)
app.include_router(assistant.router)


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
        kpi_resp = supabase.table("kpi_results").select("*").eq("user_id", user_id).order("recorded_at", desc=True).limit(25).execute()
        anomaly_resp = supabase.table("anomaly_records").select("*").eq("user_id", user_id).order("detected_at", desc=True).limit(25).execute()
        report_resp = supabase.table("daily_reports").select("*").eq("user_id", user_id).order("report_date", desc=True).limit(10).execute()
        validation_resp = supabase.table("validation_logs").select("check_type, status, message, details").eq("user_id", user_id).order("created_at", desc=True).limit(20).execute()

        kpis = []
        if hasattr(kpi_resp, "data") and kpi_resp.data:
            seen_kpis = set()
            for item in kpi_resp.data:
                kpi_name = str(item.get("kpi_name", "unknown"))
                if _is_legacy_demo_kpi(item) or kpi_name in seen_kpis:
                    continue
                seen_kpis.add(kpi_name)
                try:
                    kpis.append(KPIResult(
                        id=str(item.get("id", "")),
                        kpi_name=kpi_name,
                        value=float(item.get("value") or 0),
                        dod_pct=float(item["dod_pct"]) if item.get("dod_pct") is not None else None,
                        wow_pct=float(item["wow_pct"]) if item.get("wow_pct") is not None else None,
                        avg_7d=float(item["avg_7d"]) if item.get("avg_7d") is not None else None,
                        status=str(item.get("status") or "NORMAL"),
                        recorded_at=str(item.get("recorded_at", "")),
                    ))
                except Exception as parse_err:
                    print(f"KPI parse error: {parse_err} — row: {item}")

        anomalies = []
        if hasattr(anomaly_resp, "data") and anomaly_resp.data:
            for item in [row for row in anomaly_resp.data if not _is_legacy_demo_kpi(row)]:
                try:
                    anomalies.append(AnomalyRecord(
                        id=str(item.get("id", "")),
                        kpi_name=str(item.get("kpi_name", "unknown")),
                        severity=str(item.get("severity") or "WARNING"),
                        deviation=float(item.get("deviation") or 0),
                        context=item.get("context") or {},
                        detected_at=str(item.get("detected_at", "")),
                    ))
                except Exception as parse_err:
                    print(f"Anomaly parse error: {parse_err} — row: {item}")

        narrative = "No analytics report generated yet. Go to Dashboard and click Sync Now to generate your first report."
        last_refreshed = "Never"
        if hasattr(report_resp, "data") and report_resp.data:
            reports = [row for row in report_resp.data if not _is_legacy_demo_report(row)]
            if reports:
                narrative = reports[0]["narrative"]
                last_refreshed = str(reports[0]["report_date"])

        summary = DashboardSummary(kpis=kpis, anomalies=anomalies, narrative=narrative, last_refreshed=last_refreshed)
        summary_dict = summary.model_dump()
        validation_rows = validation_resp.data if hasattr(validation_resp, "data") and validation_resp.data else []
        filtered_validation_rows = []
        for row in validation_rows:
            msg = row.get("message") or ""
            if any(legacy.lower() in msg.lower() or legacy.replace("_", " ").lower() in msg.lower() for legacy in LEGACY_DEMO_KPI_NAMES):
                continue
            filtered_validation_rows.append(row)

        latest_by_type = {}
        for row in filtered_validation_rows:
            latest_by_type.setdefault(row.get("check_type"), row)
        summary_dict["validation"] = list(latest_by_type.values())
        try:
            from .services.kpi_config import resolve_kpi_mode
            from .services.chart_service import build_kpi_snapshot_chart
            summary_dict["kpi_mode"] = resolve_kpi_mode(supabase, user_id)
            summary_dict["snapshot_chart"] = build_kpi_snapshot_chart(kpis)
        except Exception:
            summary_dict["kpi_mode"] = {"mode": "auto"}
            summary_dict["snapshot_chart"] = None
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
        reports = rows.data if hasattr(rows, "data") and rows.data else []
        return {"reports": [row for row in reports if not _is_legacy_demo_report(row)]}
    except Exception as e:
        return {"reports": [], "error": str(e)}


# ── Report download (printable HTML — universal, no extra deps needed) ────────

@app.get("/api/reports/{report_id}/download")
def download_report(report_id: str, user_id: str = Depends(resolve_user_id)):
    """Return the report as a standalone, printable HTML document.

    Browsers can save the response as .html or use *Print → Save as PDF* to
    produce a hard copy. This avoids requiring system-level PDF dependencies
    (wkhtmltopdf / weasyprint / chromium) on free-tier hosts.
    """
    from fastapi.responses import Response
    from .services.email_service import generate_professional_html_email
    supabase = get_supabase()

    rows = (
        supabase.table("daily_reports").select("*")
        .eq("id", report_id).eq("user_id", user_id).limit(1).execute()
    )
    if not rows.data:
        raise HTTPException(status_code=404, detail="Report not found.")
    report = rows.data[0]

    kpi_rows = (
        supabase.table("kpi_results").select("*")
        .eq("user_id", user_id)
        .eq("recorded_at", str(report["report_date"]))
        .execute()
    )
    kpis = kpi_rows.data if hasattr(kpi_rows, "data") and kpi_rows.data else []
    if not kpis:
        # Fall back to most recent KPI batch when none exist for that exact date
        recent = (
            supabase.table("kpi_results").select("*")
            .eq("user_id", user_id).order("recorded_at", desc=True).limit(20).execute()
        )
        kpis = recent.data if hasattr(recent, "data") and recent.data else []

    anomaly_rows = (
        supabase.table("anomaly_records").select("*")
        .eq("user_id", user_id).order("detected_at", desc=True).limit(10).execute()
    )
    anomalies = anomaly_rows.data if hasattr(anomaly_rows, "data") and anomaly_rows.data else []

    html = generate_professional_html_email(
        kpis=kpis,
        narrative_text=report.get("narrative", ""),
        chart_url="",
        anomalies=anomalies,
        department_name=None,
        recipient_email="",
        report_type="Saved",
        report_period=str(report["report_date"]),
    )
    # Inject a print-friendly button + page metadata
    print_helper = (
        "<script>window.addEventListener('load',()=>{setTimeout(()=>window.print(),300)});</script>"
        "<style>@media print{.no-print{display:none!important}}</style>"
    )
    html = html.replace("</head>", f"{print_helper}</head>", 1)

    filename = f"report-{report['report_date']}.html"
    return Response(
        content=html,
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
    update_sync_status(context["user_id"], "FETCHING_DATA")
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
        rows = (
            supabase.table("kpi_forecasts")
            .select("*")
            .eq("user_id", user_id)
            .order("forecast_date")
            .execute()
        )
        raw = rows.data if hasattr(rows, "data") and rows.data else []
        filtered = [
            r
            for r in raw
            if r.get("kpi_name") not in LEGACY_DEMO_KPI_NAMES
            and r.get("kpi_name", "").replace("_", " ").title() not in LEGACY_DEMO_KPI_NAMES
        ]

        # Ensure the shape matches what the frontend expects.
        # Frontend Dashboard.jsx expects: kpi_name, forecast_date, predicted_value, lower_bound, upper_bound.
        forecasts = []
        for f in filtered:
            forecasts.append(
                {
                    **f,
                    "kpi_name": f.get("kpi_name"),
                    "forecast_date": f.get("forecast_date"),
                    "predicted_value": f.get("predicted_value"),
                    "lower_bound": f.get("lower_bound"),
                    "upper_bound": f.get("upper_bound"),
                }
            )

        return {"forecasts": forecasts}
    except Exception as e:
        return {"forecasts": [], "error": str(e)}


# ── Preferences ───────────────────────────────────────────────────────────────

@app.get("/api/settings/preferences")
def get_user_preferences(user_id: str = Depends(resolve_user_id)):
    supabase = get_supabase()
    defaults = {"ai_tone": "insight-driven", "sync_time": "02:00", "last_sync_status": "IDLE"}
    try:
        response = supabase.table("user_preferences").select("*").eq("user_id", user_id).execute()
        if hasattr(response, "data") and response.data:
            return response.data[0]
        return defaults
    except Exception as e:
        err = str(e).lower()
        if any(k in err for k in ("getaddrinfo", "connect", "network", "timeout", "disconnected", "eof")):
            return {**defaults, "warning": "Cannot reach Supabase — using defaults."}
        return {**defaults, "warning": f"Preferences unavailable: {str(e)[:120]}"}


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
    enriched = enrich_connection_payload(connection_data)
    db_url = enriched.get("credentials")
    connection_method = enriched.get("connection_method") or "direct"
    connection_options = enriched.get("connection_options") or connection_data.get("connection_options") or {}
    db_type = enriched.get("db_type") or detect_db_type(db_url or "", connection_data.get("db_type"))
    if not db_url:
        raise HTTPException(status_code=400, detail="Missing connection string (credentials)")

    # MongoDB test
    if db_type == "mongodb":
        try:
            import pymongo
            client = pymongo.MongoClient(db_url, serverSelectionTimeoutMS=8000)
            client.admin.command("ping")
            return {"status": "success", "message": "MongoDB connection verified!"}
        except ImportError:
            return {"status": "error", "message": "pymongo not installed. Run: pip install pymongo"}
        except Exception as e:
            return {"status": "error", "message": f"MongoDB Error: {str(e)}"}

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

        engine = create_engine(
            normalize_credentials(db_url_for_test, db_type),
            **sqlalchemy_engine_kwargs(db_url_for_test, db_type),
        )
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

    enriched = enrich_connection_payload(conn_data)
    if not enriched.get("credentials"):
        raise HTTPException(status_code=400, detail="Missing connection string (credentials)")

    from .services.connection_crypto import encrypt_credentials
    stored_credentials = encrypt_credentials(enriched.get("credentials"))

    supabase = get_supabase()
    data = {
        "user_id": user_id,
        "db_type": enriched.get("db_type", "postgresql"),
        "host": enriched.get("host") or "direct",
        "port": enriched.get("port") if enriched.get("port") is not None else 0,
        "db_name": enriched.get("db_name") or "default",
        "credentials": stored_credentials,
        "read_only": True,
        "connection_method": enriched.get("connection_method", "direct"),
        "connection_options": enriched.get("connection_options"),
    }
    try:
        existing = supabase.table("database_connections").select("id").eq("user_id", user_id).limit(1).execute()
        has_existing = bool(getattr(existing, "data", None))
        if has_existing:
            supabase.table("database_connections").update(data).eq("user_id", user_id).execute()
        else:
            supabase.table("database_connections").insert(data).execute()
    except Exception as e:
        err = str(e)
        if "connection_method" in err or "connection_options" in err:
            legacy = {k: v for k, v in data.items() if k not in {"connection_method", "connection_options"}}
            existing = supabase.table("database_connections").select("id").eq("user_id", user_id).limit(1).execute()
            if bool(getattr(existing, "data", None)):
                supabase.table("database_connections").update(legacy).eq("user_id", user_id).execute()
            else:
                supabase.table("database_connections").insert(legacy).execute()
        elif "value too long" in err.lower() or "character varying" in err.lower():
            raise HTTPException(
                status_code=500,
                detail=(
                    "Connection string is too long for the current database schema. "
                    "Run backend/migrations/006_fix_database_connections.sql in Supabase SQL Editor, then retry."
                ),
            ) from e
        else:
            raise HTTPException(status_code=500, detail=f"Failed to save connection: {err}") from e

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


# ── Natural Language Query ───────────────────────────────────────────────────

class NLQRequest(BaseModel):
    question: str


class CustomChartRequest(BaseModel):
    instruction: str
    chart_type: str = "bar"
    sql: Optional[str] = None
    x_column: Optional[str] = None
    y_column: Optional[str] = None


@app.post("/api/charts/custom")
def build_custom_chart(
    body: CustomChartRequest,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Build a chart from NLQ results or a provided read-only SQL query."""
    from .services.chart_service import build_custom_chart_spec
    from sqlalchemy import text as sql_text

    supabase = get_supabase()
    rows: list = []
    columns: list = []
    sql_used = body.sql

    if body.sql and body.sql.strip():
        conn_resp = supabase.table("database_connections").select("*").eq("user_id", context["user_id"]).limit(1).execute()
        if not conn_resp.data:
            raise HTTPException(status_code=400, detail="No database connection configured.")
        from .services.connection_crypto import maybe_decrypt_connection_row
        conn_info = maybe_decrypt_connection_row(conn_resp.data[0])
        db_type = (conn_info.get("db_type") or "postgresql").lower()
        credentials = conn_info.get("credentials") or ""
        sql_upper = body.sql.strip().upper()
        if not sql_upper.startswith(("SELECT", "WITH", "PRAGMA")):
            raise HTTPException(status_code=400, detail="Only read-only SELECT/PRAGMA queries allowed.")
        from .services.connection_utils import normalize_credentials, sqlalchemy_engine_kwargs
        engine = create_engine(
            normalize_credentials(credentials, db_type),
            **sqlalchemy_engine_kwargs(credentials, db_type),
        )
        try:
            with engine.connect() as conn:
                result = conn.execute(sql_text(body.sql))
                columns = list(result.keys())
                rows = [dict(zip(columns, r)) for r in result.fetchmany(200)]
        finally:
            engine.dispose()
    else:
        nlq_result = run_nlq(context["user_id"], body.instruction.strip(), supabase)
        if nlq_result.get("error"):
            raise HTTPException(status_code=400, detail=nlq_result["error"])
        rows = nlq_result.get("rows") or []
        columns = nlq_result.get("columns") or []
        sql_used = nlq_result.get("sql")

    spec = build_custom_chart_spec(
        rows,
        chart_type=body.chart_type,
        x_column=body.x_column,
        y_column=body.y_column,
        title=body.instruction[:80],
    )
    if not spec:
        raise HTTPException(status_code=400, detail="Could not build chart from query results.")
    return {"chart": spec, "sql": sql_used, "row_count": len(rows), "columns": columns}


@app.post("/api/nlq")
def natural_language_query(
    body: NLQRequest,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Execute a natural language question against the user's connected database."""
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    supabase = get_supabase()
    result = run_nlq(context["user_id"], body.question.strip(), supabase)
    return result


# ── Custom Report Generation ──────────────────────────────────────────────────

class CustomReportRequest(BaseModel):
    instruction: str
    report_scope: str = "my_department"  # my_department | all_departments | specific_departments
    format_type: str = "narrative"       # narrative | table | bullet_points | executive_brief | detailed
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    department_ids: Optional[List[str]] = None
    kpi_names: Optional[List[str]] = None


@app.post("/api/reports/custom")
def create_custom_report(
    body: CustomReportRequest,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Generate a custom report based on user-specified parameters."""
    if not body.instruction.strip():
        raise HTTPException(status_code=400, detail="Instruction cannot be empty.")
    supabase = get_supabase()
    result = generate_custom_report(
        user_id=context["user_id"],
        instruction=body.instruction.strip(),
        report_scope=body.report_scope,
        format_type=body.format_type,
        date_from=body.date_from,
        date_to=body.date_to,
        department_ids=body.department_ids,
        kpi_names=body.kpi_names,
        supabase=supabase,
        role=context.get("role", "manager"),
    )
    return result


@app.post("/api/reports/custom/save")
def save_custom_report(
    body: dict,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Save a custom-generated report to daily_reports history."""
    narrative = body.get("narrative", "").strip()
    instruction = body.get("instruction", "Custom report")
    if not narrative:
        raise HTTPException(status_code=400, detail="Narrative cannot be empty.")
    supabase = get_supabase()
    try:
        supabase.table("daily_reports").insert({
            "user_id": context["user_id"],
            "narrative": f"[Custom: {instruction[:80]}]\n\n{narrative}",
            "report_date": datetime.now().date().isoformat(),
        }).execute()
        return {"status": "saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Audit Log ─────────────────────────────────────────────────────────────────

@app.post("/api/admin/test-email")
def send_test_email(
    body: dict,
    context: dict = Depends(require_role(["admin", "manager"])),
):
    """Send a one-off test email to verify Brevo wiring.

    Body: { "email": "someone@example.com" }
    """
    to_email = (body or {}).get("email", "").strip()
    if not to_email or "@" not in to_email:
        raise HTTPException(status_code=400, detail="A valid email address is required.")
    api_key = os.getenv("BREVO_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="BREVO_API_KEY not configured.")
    try:
        import sib_api_v3_sdk
        from sib_api_v3_sdk.rest import ApiException
        cfg = sib_api_v3_sdk.Configuration()
        cfg.api_key["api-key"] = api_key
        client = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(cfg))
        sender_email = os.getenv("EMAIL_SENDER_ADDRESS", "noreply@saas-analytics.com")
        sender_name = os.getenv("EMAIL_SENDER_NAME", "SAAS Analytics")
        html = (
            "<h2>SaaS Analytics — Test Email</h2>"
            f"<p>Hello! This is a test email confirming Brevo is configured correctly "
            f"for user <b>{context['user_id']}</b>.</p>"
            "<p>If you received this, your nightly briefings will deliver successfully.</p>"
        )
        resp = client.send_transac_email(sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to_email}],
            sender={"name": sender_name, "email": sender_email},
            subject="SaaS Analytics — test email",
            html_content=html,
        ))
        return {"status": "sent", "message_id": resp.message_id, "to": to_email}
    except ApiException as e:
        raise HTTPException(status_code=502, detail=f"Brevo error: {getattr(e, 'body', str(e))}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/audit-log")
def get_audit_log(limit: int = 50, context: dict = Depends(require_role(["manager", "admin"]))):
    supabase = get_supabase()
    try:
        rows = supabase.table("audit_logs").select("*").eq("user_id", context["user_id"]).order("created_at", desc=True).limit(limit).execute()
        return {"logs": rows.data if hasattr(rows, "data") and rows.data else []}
    except Exception as e:
        return {"logs": [], "error": str(e)}
