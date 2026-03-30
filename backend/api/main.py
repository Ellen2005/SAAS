from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from contextlib import asynccontextmanager
from sqlalchemy import create_engine

from .core.supabase_client import get_supabase
from .services.email_service import send_automated_briefing
from .services.narrative_service import generate_mock_narrative
from .core.scheduler import start_scheduler, shutdown_scheduler
from .services.etl_service import run_user_etl_pipeline

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
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
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

@app.get("/")
def read_root():
    return {"message": "Welcome to SAAS-PWA Backend"}

@app.get("/api/summary", response_model=DashboardSummary)
def get_dashboard_summary(user_id: str = "user_123_uuid"):
    """
    Returns the daily dashboard summary for a specific user.
    Reads real data from Supabase.
    """
    supabase = get_supabase()
    
    # 1. Fetch KPIs
    kpi_resp = supabase.table('kpi_results').select("*").eq("user_id", user_id).order("recorded_at", desc=True).limit(5).execute()
    kpis = []
    if hasattr(kpi_resp, 'data') and kpi_resp.data:
        for item in kpi_resp.data:
            kpis.append(KPIResult(
                id=item['id'],
                kpi_name=item['kpi_name'],
                value=item['value'],
                dod_pct=item.get('dod_pct'),
                wow_pct=item.get('wow_pct'),
                avg_7d=item.get('avg_7d'),
                status=item['status'],
                recorded_at=str(item['recorded_at'])
            ))
            
    # 2. Fetch Anomalies
    anomaly_resp = supabase.table('anomaly_records').select("*").eq("user_id", user_id).order("detected_at", desc=True).limit(10).execute()
    anomalies = []
    if hasattr(anomaly_resp, 'data') and anomaly_resp.data:
        for item in anomaly_resp.data:
            anomalies.append(AnomalyRecord(
                id=item['id'],
                kpi_name=item['kpi_name'],
                severity=item['severity'],
                deviation=item['deviation'],
                context=item['context'],
                detected_at=item['detected_at']
            ))
            
    # 3. Fetch Latest Narrative
    report_resp = supabase.table('daily_reports').select("*").eq("user_id", user_id).order("report_date", desc=True).limit(1).execute()
    narrative = "No analytics report generated yet. Please trigger a manual sync in Settings."
    last_refreshed = "Never"
    
    if hasattr(report_resp, 'data') and report_resp.data:
        narrative = report_resp.data[0]['narrative']
        last_refreshed = report_resp.data[0]['report_date']
    
    return DashboardSummary(
        kpis=kpis,
        anomalies=anomalies,
        narrative=narrative,
        last_refreshed=last_refreshed
    )



@app.post("/api/etl/trigger")
def trigger_etl(background_tasks: BackgroundTasks, user_id: str = "user_123_uuid"):
    """
    Manually triggers the ETL pipeline logic for the specified user 
    so we can test it from the dashboard or via API testing.
    """
    background_tasks.add_task(run_user_etl_pipeline, user_id)
    return {"status": "Manual ETL trigger started in the background", "user_id": user_id}

@app.post("/api/test-connection")
def test_db_connection(connection_data: dict):
    """
    Attempts to connect to a database using the provided credentials.
    Returns success or error message.
    """
    db_url = connection_data.get("credentials")
    if not db_url:
        raise HTTPException(status_code=400, detail="Missing connection string (credentials)")
    
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            # Simple query to test the connection
            conn.execute("SELECT 1")
        return {"status": "success", "message": "Connection verified!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
