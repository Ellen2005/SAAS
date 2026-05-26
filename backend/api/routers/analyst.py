"""
AI Analyst Router — exposes autonomous analytics endpoints.

Endpoints:
  POST /api/analyst/prepare        — auto data preparation
  POST /api/analyst/model          — auto modelling
  GET  /api/analyst/insights       — augmented analytics (proactive insights)
  GET  /api/analyst/explain/{id}   — explainable AI for a KPI or anomaly
  GET  /api/analyst/governance     — governance health score
  GET  /api/analyst/snapshots      — collaboration insight snapshots
  POST /api/analyst/snapshots      — save an insight snapshot
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..core.auth import require_role, resolve_user_id
from ..core.supabase_client import get_supabase
from ..services.ai_analyst_service import (
    auto_prepare,
    auto_model,
    generate_augmented_insights,
    explain_anomaly,
    explain_kpi_movement,
    compute_governance_score,
    create_insight_snapshot,
    get_insight_snapshots,
)

router = APIRouter(prefix="/api/analyst", tags=["ai-analyst"])


def _safe(resp) -> list:
    return resp.data if hasattr(resp, "data") and resp.data else []


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


# ─── Auto Data Preparation ────────────────────────────────────────────────────

@router.post("/prepare")
def prepare_data(context: dict = Depends(require_role(["manager", "admin"]))):
    """
    Fetch the user's latest raw KPI data, run auto-preparation,
    and return a summary of actions taken.
    """
    supabase = get_supabase()
    user_id = context["user_id"]

    rows = _safe(
        supabase.table("kpi_results")
        .select("kpi_name, value, dod_pct, wow_pct, avg_7d, recorded_at")
        .eq("user_id", user_id)
        .order("recorded_at", desc=True)
        .limit(200)
        .execute()
    )
    if not rows:
        return {"actions": [], "message": "No data to prepare. Run a sync first."}

    import pandas as pd
    df = pd.DataFrame(rows)
    _, actions = auto_prepare(df)
    return {
        "actions": actions,
        "rows_processed": len(df),
        "columns_processed": len(df.columns),
        "message": f"Auto-preparation complete. {len(actions)} action(s) applied.",
    }


# ─── Auto Modelling ───────────────────────────────────────────────────────────

@router.post("/model")
def model_data(context: dict = Depends(require_role(["manager", "admin"]))):
    """
    Run auto-modelling on the user's ETL data to detect column roles,
    KPI candidates, and suggested aggregations.
    """
    supabase = get_supabase()
    user_id = context["user_id"]

    rows = _safe(
        supabase.table("kpi_results")
        .select("*")
        .eq("user_id", user_id)
        .order("recorded_at", desc=True)
        .limit(500)
        .execute()
    )
    if not rows:
        return {"message": "No data available. Run a sync first.", "model": {}}

    import pandas as pd
    df = pd.DataFrame(rows)
    model = auto_model(df)
    return {"model": model, "rows_analysed": len(df)}


# ─── Augmented Analytics ─────────────────────────────────────────────────────

@router.get("/insights")
def get_augmented_insights(user_id: str = Depends(resolve_user_id)):
    """
    Return proactively generated insights: trend shifts, correlations,
    concentration risk, data freshness warnings.
    """
    supabase = get_supabase()

    kpi_rows = _safe(
        supabase.table("kpi_results")
        .select("*")
        .eq("user_id", user_id)
        .order("recorded_at", desc=True)
        .limit(300)
        .execute()
    )
    anomaly_rows = _safe(
        supabase.table("anomaly_records")
        .select("*")
        .eq("user_id", user_id)
        .order("detected_at", desc=True)
        .limit(50)
        .execute()
    )

    if not kpi_rows:
        return {"insights": [], "message": "No data yet. Run a sync to generate insights."}

    import pandas as pd
    # Build a time-series frame from kpi_results
    df_rows = []
    for r in kpi_rows:
        df_rows.append({
            "date": r.get("recorded_at"),
            "kpi_name": r.get("kpi_name"),
            "value": _to_float(r.get("value")),
            "customer_id": r.get("department_id"),
        })
    df = pd.DataFrame(df_rows)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    insights = generate_augmented_insights(df, kpi_rows, anomaly_rows)

    # Enrich each insight with an XAI explanation
    for ins in insights:
        if ins["type"] in ("trend_shift",):
            ins["xai_explanation"] = ins.get("explanation", "")

    return {
        "insights": insights,
        "insight_count": len(insights),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ─── Explainable AI ───────────────────────────────────────────────────────────

@router.get("/explain/anomaly/{anomaly_id}")
def explain_anomaly_endpoint(anomaly_id: str, user_id: str = Depends(resolve_user_id)):
    """Return a plain-language explanation for a specific anomaly."""
    supabase = get_supabase()
    rows = _safe(
        supabase.table("anomaly_records")
        .select("*")
        .eq("id", anomaly_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Anomaly not found.")

    anomaly = rows[0]
    explanation = explain_anomaly(anomaly)
    return {"anomaly_id": anomaly_id, "explanation": explanation, "anomaly": anomaly}


@router.get("/explain/kpi/{kpi_id}")
def explain_kpi_endpoint(kpi_id: str, user_id: str = Depends(resolve_user_id)):
    """Return a plain-language explanation for a specific KPI result."""
    supabase = get_supabase()
    rows = _safe(
        supabase.table("kpi_results")
        .select("*")
        .eq("id", kpi_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="KPI not found.")

    kpi = rows[0]
    explanation = explain_kpi_movement(kpi)
    return {"kpi_id": kpi_id, "explanation": explanation, "kpi": kpi}


@router.get("/explain/all")
def explain_all(user_id: str = Depends(resolve_user_id)):
    """Return XAI explanations for all current KPIs and anomalies."""
    supabase = get_supabase()

    kpis = _safe(
        supabase.table("kpi_results")
        .select("*")
        .eq("user_id", user_id)
        .order("recorded_at", desc=True)
        .limit(10)
        .execute()
    )
    anomalies = _safe(
        supabase.table("anomaly_records")
        .select("*")
        .eq("user_id", user_id)
        .order("detected_at", desc=True)
        .limit(5)
        .execute()
    )

    return {
        "kpi_explanations": [
            {"id": k["id"], "kpi_name": k["kpi_name"], "explanation": explain_kpi_movement(k)}
            for k in kpis
        ],
        "anomaly_explanations": [
            {"id": a["id"], "kpi_name": a["kpi_name"], "explanation": explain_anomaly(a)}
            for a in anomalies
        ],
    }


# ─── Governance Score ─────────────────────────────────────────────────────────

@router.get("/governance")
def get_governance_score(user_id: str = Depends(resolve_user_id)):
    """Compute and return the governance health score for this user's data."""
    supabase = get_supabase()

    import pandas as pd
    from datetime import date as _date

    kpi_rows = _safe(
        supabase.table("kpi_results")
        .select("*")
        .eq("user_id", user_id)
        .order("recorded_at", desc=True)
        .limit(200)
        .execute()
    )
    validation_rows = _safe(
        supabase.table("validation_logs")
        .select("check_type, status, message")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    mapping_rows = _safe(
        supabase.table("field_mappings")
        .select("id")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    pref_rows = _safe(
        supabase.table("user_preferences")
        .select("last_sync_status")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    df = pd.DataFrame(kpi_rows) if kpi_rows else pd.DataFrame()

    # Compute days since last sync
    days_stale = 999
    if kpi_rows:
        try:
            latest = pd.to_datetime(kpi_rows[0].get("recorded_at")).date()
            days_stale = (_date.today() - latest).days
        except Exception:
            pass

    score = compute_governance_score(
        df=df,
        validation_results=validation_rows,
        days_since_last_sync=days_stale,
        has_semantic_mappings=bool(mapping_rows),
    )
    return score


# ─── Collaboration — Insight Snapshots ───────────────────────────────────────

class SnapshotCreate(BaseModel):
    title: str
    content: str
    insight_type: str = "manual"
    kpi_name: Optional[str] = None
    metadata: Optional[dict] = None


@router.get("/snapshots")
def list_snapshots(limit: int = 20, user_id: str = Depends(resolve_user_id)):
    """List recent insight snapshots for collaboration."""
    supabase = get_supabase()
    snapshots = get_insight_snapshots(supabase, user_id, limit=limit)
    return {"snapshots": snapshots, "count": len(snapshots)}


@router.post("/snapshots")
def save_snapshot(body: SnapshotCreate, context: dict = Depends(require_role(["manager", "admin"]))):
    """Save an insight snapshot for sharing with the team."""
    supabase = get_supabase()
    snapshot = create_insight_snapshot(
        supabase=supabase,
        user_id=context["user_id"],
        title=body.title,
        content=body.content,
        insight_type=body.insight_type,
        kpi_name=body.kpi_name,
        metadata=body.metadata,
    )
    return {"status": "saved", "snapshot": snapshot}


@router.delete("/snapshots/{snapshot_id}")
def delete_snapshot(snapshot_id: str, context: dict = Depends(require_role(["manager", "admin"]))):
    """Delete an insight snapshot."""
    supabase = get_supabase()
    try:
        supabase.table("insight_snapshots").delete().eq("id", snapshot_id).eq("user_id", context["user_id"]).execute()
        return {"status": "deleted", "id": snapshot_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Full Autonomous Analysis Run ────────────────────────────────────────────

@router.post("/run-full")
def run_full_analysis(context: dict = Depends(require_role(["manager", "admin"]))):
    """
    Run the complete autonomous AI analyst pipeline:
    1. Auto-prepare data
    2. Auto-model
    3. Generate augmented insights
    4. Compute governance score
    5. Return everything in one response
    """
    supabase = get_supabase()
    user_id = context["user_id"]

    import pandas as pd

    kpi_rows = _safe(
        supabase.table("kpi_results")
        .select("*")
        .eq("user_id", user_id)
        .order("recorded_at", desc=True)
        .limit(300)
        .execute()
    )
    anomaly_rows = _safe(
        supabase.table("anomaly_records")
        .select("*")
        .eq("user_id", user_id)
        .order("detected_at", desc=True)
        .limit(50)
        .execute()
    )
    validation_rows = _safe(
        supabase.table("validation_logs")
        .select("check_type, status")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    mapping_rows = _safe(
        supabase.table("field_mappings").select("id").eq("user_id", user_id).limit(1).execute()
    )

    if not kpi_rows:
        return {
            "status": "no_data",
            "message": "No data available. Run a sync first.",
            "preparation": {}, "model": {}, "insights": [], "governance": {}, "explanations": [],
        }

    df_rows = [{"date": r.get("recorded_at"), "kpi_name": r.get("kpi_name"),
                "value": _to_float(r.get("value")), "customer_id": r.get("department_id")} for r in kpi_rows]
    df = pd.DataFrame(df_rows)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # 1. Prepare
    _, prep_actions = auto_prepare(df)

    # 2. Model
    model = auto_model(df)

    # 3. Insights
    insights = generate_augmented_insights(df, kpi_rows, anomaly_rows)

    # 4. Governance
    from datetime import date as _date
    days_stale = 999
    try:
        latest = pd.to_datetime(kpi_rows[0].get("recorded_at")).date()
        days_stale = (_date.today() - latest).days
    except Exception:
        pass
    governance = compute_governance_score(df, validation_rows, days_stale, bool(mapping_rows))

    # 5. XAI for top anomalies
    explanations = [
        {"id": a["id"], "kpi_name": a["kpi_name"], "explanation": explain_anomaly(a)}
        for a in anomaly_rows[:3]
    ]

    return {
        "status": "complete",
        "preparation": {"actions": prep_actions, "rows": len(df)},
        "model": model,
        "insights": insights,
        "governance": governance,
        "explanations": explanations,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
