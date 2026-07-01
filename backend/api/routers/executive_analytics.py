"""
Executive Analytics Router
==========================
Provides executive-level overview, insights, and risk indicators.
"""
import logging
from datetime import datetime, timezone
UTC = timezone.utc
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from ..core.auth import resolve_user_id, require_role
from ..core.supabase_client import get_supabase

router = APIRouter(prefix="/api/executive", tags=["executive-analytics"])
logger = logging.getLogger(__name__)


@router.get("/overview")
def get_executive_overview(user_id: str = Depends(resolve_user_id)):
    """Return executive-level KPIs and risk indicators."""
    supabase = get_supabase()
    try:
        kpi_rows = (
            supabase.table("kpi_results")
            .select("*")
            .eq("user_id", user_id)
            .order("recorded_at", desc=True)
            .limit(50)
            .execute()
        )
        raw = kpi_rows.data if hasattr(kpi_rows, "data") and kpi_rows.data else []

        # Aggregate by KPI name
        kpi_summary = {}
        for row in raw:
            name = row.get("kpi_name", "unknown")
            if name not in kpi_summary:
                kpi_summary[name] = {
                    "kpi_name": name,
                    "latest_value": row.get("value"),
                    "latest_status": row.get("status", "NORMAL"),
                    "recorded_at": row.get("recorded_at"),
                    "dod_pct": row.get("dod_pct"),
                    "wow_pct": row.get("wow_pct"),
                }

        # Count by status
        status_counts = {"NORMAL": 0, "WARNING": 0, "CRITICAL": 0}
        for kpi in kpi_summary.values():
            status = kpi.get("latest_status", "NORMAL")
            if status in status_counts:
                status_counts[status] += 1

        # Get anomalies
        anomaly_rows = (
            supabase.table("anomaly_records")
            .select("*")
            .eq("user_id", user_id)
            .order("detected_at", desc=True)
            .limit(20)
            .execute()
        )
        anomalies = anomaly_rows.data if hasattr(anomaly_rows, "data") and anomaly_rows.data else []

        # Get recent reports
        report_rows = (
            supabase.table("daily_reports")
            .select("report_date, narrative")
            .eq("user_id", user_id)
            .order("report_date", desc=True)
            .limit(5)
            .execute()
        )
        reports = report_rows.data if hasattr(report_rows, "data") and report_rows.data else []

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "kpi_count": len(kpi_summary),
            "status_summary": status_counts,
            "health_score": _compute_health_score(status_counts, len(kpi_summary)),
            "kpis": list(kpi_summary.values())[:10],
            "anomalies": anomalies[:5],
            "recent_reports": reports,
            "risk_indicators": _compute_risk_indicators(kpi_summary, anomalies),
        }
    except Exception as e:
        logger.error("Executive overview error", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.get("/insights")
def get_executive_insights(user_id: str = Depends(resolve_user_id)):
    """Generate automated executive insights."""
    supabase = get_supabase()
    try:
        overview = get_executive_overview(user_id)
        insights = []

        # Risk insights
        if overview["health_score"] < 70:
            insights.append({
                "type": "risk",
                "priority": "HIGH",
                "title": "System Health Below Threshold",
                "description": f"Overall health score is {overview['health_score']}/100. Immediate attention required.",
                "metric": "Health Score",
                "value": f"{overview['health_score']}/100",
            })

        # Anomaly insights
        critical_anomalies = [a for a in overview["anomalies"] if a.get("severity") == "CRITICAL"]
        if critical_anomalies:
            insights.append({
                "type": "warning",
                "priority": "HIGH",
                "title": "Critical Anomalies Detected",
                "description": f"{len(critical_anomalies)} critical anomaly(ies) require investigation.",
                "metric": "Critical Anomalies",
                "value": str(len(critical_anomalies)),
            })

        # Performance insights
        improving = [k for k in overview["kpis"] if k.get("wow_pct") and k["wow_pct"] > 5]
        declining = [k for k in overview["kpis"] if k.get("wow_pct") and k["wow_pct"] < -5]
        if improving:
            insights.append({
                "type": "positive",
                "priority": "MEDIUM",
                "title": "Strong Performance Detected",
                "description": f"{len(improving)} KPI(s) showing strong week-over-week improvement.",
                "metric": "Improving KPIs",
                "value": str(len(improving)),
            })
        if declining:
            insights.append({
                "type": "negative",
                "priority": "HIGH",
                "title": "Performance Decline Alert",
                "description": f"{len(declining)} KPI(s) declining week-over-week.",
                "metric": "Declining KPIs",
                "value": str(len(declining)),
            })

        # Opportunity insights
        if overview["status_summary"]["NORMAL"] > 0:
            insights.append({
                "type": "info",
                "priority": "LOW",
                "title": "Stable Operations",
                "description": f"{overview['status_summary']['NORMAL']} KPIs operating normally.",
                "metric": "Healthy KPIs",
                "value": str(overview["status_summary"]["NORMAL"]),
            })

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "insight_count": len(insights),
            "insights": insights,
        }
    except Exception as e:
        logger.error("Executive insights error", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.get("/briefing")
def get_executive_briefing(user_id: str = Depends(resolve_user_id)):
    """Generate a complete executive briefing document."""
    try:
        overview = get_executive_overview(user_id)
        insights = get_executive_insights(user_id)

        briefing = {
            "title": "Executive Analytics Briefing",
            "generated_at": datetime.now(UTC).isoformat(),
            "summary": {
                "health_score": overview["health_score"],
                "total_kpis": overview["kpi_count"],
                "status_breakdown": overview["status_summary"],
                "critical_anomalies": len([a for a in overview["anomalies"] if a.get("severity") == "CRITICAL"]),
            },
            "key_insights": insights["insights"],
            "top_kpis": overview["kpis"][:5],
            "risk_indicators": overview["risk_indicators"],
            "recommendations": _generate_recommendations(overview, insights),
        }

        return briefing
    except Exception as e:
        logger.error("Executive briefing error", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


def _compute_health_score(status_counts: dict, total_kpis: int) -> int:
    """Compute overall health score 0-100."""
    if total_kpis == 0:
        return 0
    normal = status_counts.get("NORMAL", 0)
    warning = status_counts.get("WARNING", 0)
    critical = status_counts.get("CRITICAL", 0)
    score = (normal * 100 + warning * 50 + critical * 0) / total_kpis
    return round(max(0, min(100, score)))


def _compute_risk_indicators(kpi_summary: dict, anomalies: list) -> list[dict]:
    """Compute risk indicators from KPIs and anomalies."""
    risks = []
    critical_kpis = [k for k in kpi_summary.values() if k.get("latest_status") == "CRITICAL"]
    if critical_kpis:
        risks.append({
            "level": "HIGH",
            "category": "KPI Performance",
            "indicator": f"{len(critical_kpis)} critical KPI(s)",
            "action": "Review critical KPIs immediately",
        })
    critical_anomalies = [a for a in anomalies if a.get("severity") == "CRITICAL"]
    if critical_anomalies:
        risks.append({
            "level": "HIGH",
            "category": "Anomalies",
            "indicator": f"{len(critical_anomalies)} critical anomaly(ies)",
            "action": "Investigate anomalies",
        })
    return risks


def _generate_recommendations(overview: dict, insights: dict) -> list[dict]:
    """Generate actionable recommendations."""
    recs = []
    if overview["health_score"] < 70:
        recs.append({
            "priority": "HIGH",
            "area": "System Health",
            "action": "Schedule immediate review of critical and warning KPIs",
        })
    if overview["risk_indicators"]:
        recs.append({
            "priority": "HIGH",
            "area": "Risk Management",
            "action": "Address all high-level risk indicators",
        })
    recs.append({
        "priority": "MEDIUM",
        "area": "Analytics",
        "action": "Enable automated daily briefings for continuous monitoring",
    })
    return recs