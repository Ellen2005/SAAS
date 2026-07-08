"""
Executive Reports Router
========================
Enterprise-grade reports for CNPS leadership:
  - DG Monthly Report (Rapport au Directeur Général)
  - Board Report (Rapport du Conseil d'Administration)
  - Regional Performance Report (Rapport de Performance Régionale)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from ..core.auth import require_role, resolve_user_id
from ..core.supabase_client import get_supabase
from ..core.utils import safe_data
from ..services.executive_report_service import (
    generate_dg_report,
    generate_board_report,
    generate_regional_performance_report,
    generate_pdf_report,
    render_html_to_pdf,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/executive", tags=["executive-reports"])


# ─── Data builders ────────────────────────────────────────────────────────────

def _build_kpi_data(user_id: str, supabase, limit: int = 20) -> list:
    rows = safe_data(
        supabase.table("kpi_results")
        .select("*")
        .eq("user_id", user_id)
        .order("recorded_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [
        {
            "name": r.get("kpi_name", "KPI"),
            "value": float(r.get("value", 0)),
            "change_pct": float(r.get("dod_pct", 0)) if r.get("dod_pct") else None,
            "status": r.get("status", "NORMAL"),
        }
        for r in rows
    ]


def _build_anomaly_data(user_id: str, supabase, limit: int = 20) -> list:
    rows = safe_data(
        supabase.table("anomaly_records")
        .select("*")
        .eq("user_id", user_id)
        .order("detected_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [
        {
            "kpi_name": r.get("kpi_name", "N/A"),
            "severity": r.get("severity", "WARNING"),
            "deviation": float(r.get("deviation", 0)),
            "context": r.get("context", {}),
        }
        for r in rows
    ]


def _build_regional_data(supabase) -> list:
    """Build regional performance data using real validation pass rates."""
    depts = safe_data(
        supabase.table("departments").select("*").order("created_at").execute()
    )
    regions = []
    for dept in depts:
        dept_id = dept["id"]

        kpis = safe_data(
            supabase.table("kpi_results")
            .select("kpi_name, value")
            .eq("department_id", dept_id)
            .order("recorded_at", desc=True)
            .limit(20)
            .execute()
        )

        contributions = 0.0
        pensions = 0.0
        claims = 0
        for k in kpis:
            name = str(k.get("kpi_name", "")).lower()
            val = float(k.get("value", 0))
            if "contribution" in name or "cotisation" in name:
                contributions += val
            elif "pension" in name or "prestation" in name:
                pensions += val
            elif "claim" in name or "accident" in name or "at/mp" in name or "sinistre" in name:
                claims += int(val)

        # Collection rate = validation pass rate for this department (real data)
        val_logs = safe_data(
            supabase.table("validation_logs")
            .select("status")
            .eq("department_id", dept_id)
            .order("created_at", desc=True)
            .limit(30)
            .execute()
        )
        total_checks = len(val_logs)
        passed_checks = sum(1 for v in val_logs if v.get("status") == "pass")
        collection_rate = round(passed_checks / total_checks * 100, 1) if total_checks > 0 else 0.0
        compliance_rate = collection_rate

        status = "green"
        if collection_rate < 50:
            status = "red"
        elif collection_rate < 75:
            status = "amber"

        regions.append({
            "name": dept.get("name", "Unknown"),
            "contributions": contributions,
            "pensions": pensions,
            "claims": claims,
            "collection_rate": collection_rate,
            "compliance_rate": compliance_rate,
            "status": status,
        })
    return regions


def _build_department_performance(supabase) -> list:
    """KPI score = % of KPIs with NORMAL status. Validation rate = pass rate from logs."""
    depts = safe_data(
        supabase.table("departments").select("*").order("created_at").execute()
    )
    performance = []
    for dept in depts:
        dept_id = dept["id"]

        val_logs = safe_data(
            supabase.table("validation_logs")
            .select("status")
            .eq("department_id", dept_id)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        total_val = len(val_logs)
        passes = sum(1 for v in val_logs if v.get("status") == "pass")
        validation_rate = round(passes / total_val * 100, 1) if total_val > 0 else 0.0

        kpis = safe_data(
            supabase.table("kpi_results")
            .select("status, recorded_at")
            .eq("department_id", dept_id)
            .order("recorded_at", desc=True)
            .limit(20)
            .execute()
        )
        total_kpis = len(kpis)
        normal_kpis = sum(1 for k in kpis if k.get("status") == "NORMAL")
        kpi_score = round(normal_kpis / total_kpis * 100, 1) if total_kpis > 0 else 0.0

        last_sync = str(kpis[0].get("recorded_at", ""))[:10] if kpis else None

        performance.append({
            "name": dept.get("name", "Unknown"),
            "score": kpi_score,
            "validation_rate": validation_rate,
            "last_sync": last_sync or "Never",
            "status": "Active" if kpis else "Pending",
        })
    return performance


def _build_recommendations(kpis: list, anomalies: list) -> list:
    """Generate data-driven recommendations from actual KPI and anomaly results."""
    recs = []
    critical = [a for a in anomalies if a.get("severity") == "CRITICAL"]
    warnings = [a for a in anomalies if a.get("severity") == "WARNING"]

    for a in critical[:2]:
        name = a.get("kpi_name", "").replace("_", " ").title()
        recs.append({
            "title": f"Investigate critical anomaly: {name}",
            "body": a.get("context", {}).get("reason", f"{name} has exceeded the critical z-score threshold. Immediate investigation required."),
        })
    for a in warnings[:2]:
        name = a.get("kpi_name", "").replace("_", " ").title()
        recs.append({
            "title": f"Monitor warning: {name}",
            "body": a.get("context", {}).get("reason", f"{name} shows a notable deviation. Monitor closely over the next reporting period."),
        })

    declining = [k for k in kpis if (k.get("change_pct") or 0) < -5]
    for k in declining[:2]:
        name = k.get("name", "").replace("_", " ").title()
        pct = abs(k.get("change_pct") or 0)
        recs.append({
            "title": f"Address decline in {name}",
            "body": f"{name} has decreased by {pct:.1f}% compared to the previous period. Review contributing factors and initiate corrective action.",
        })

    if not recs:
        recs.append({
            "title": "Continue monitoring all KPIs",
            "body": "No critical issues detected this period. Maintain current operational cadence and ensure data connections remain active for continuous monitoring.",
        })
    return recs[:4]


def _build_risks(anomalies: list) -> list:
    """Build risk flags from actual detected anomalies only."""
    risks = []
    for a in anomalies:
        if a.get("severity") in ("CRITICAL", "WARNING"):
            name = a.get("kpi_name", "").replace("_", " ").title()
            dev = a.get("deviation", 0)
            reason = a.get("context", {}).get("reason", "Significant deviation detected.")
            risks.append({
                "title": f"{a.get('severity')} — {name}",
                "body": f"{reason} (z-score deviation: {dev:.1f})",
            })
    return risks[:3]


def _build_strategic_objectives(kpis: list, supabase) -> list:
    """
    Build strategic objectives using DoD% trend as progress indicator.
    A KPI trending up vs its 7-day average is considered on-track.
    """
    objectives = []
    for kpi in kpis[:6]:
        value = kpi.get("value", 0)
        change = kpi.get("change_pct") or 0
        # Progress: map change_pct to a 0-100 scale centred at 85 (stable = 85%)
        # Positive trend pushes toward 100, negative toward 60
        progress = min(100.0, max(0.0, 85.0 + change))
        objectives.append({
            "name": kpi.get("name", "KPI").replace("_", " ").title(),
            "target": f"{value * 1.10:,.0f}",   # 10% stretch target
            "progress": round(progress, 1),
            "current": f"{value:,.0f}",
        })
    return objectives


def _generate_executive_summary(user_id: str, supabase, kpis: list, anomalies: list) -> str:
    try:
        from ..services.ai_orchestrator import AIOrchestrator
        kpi_text = "; ".join(f"{k['name']}: {k['value']:,.2f}" for k in kpis[:5])
        anomaly_text = "; ".join(f"{a['kpi_name']} ({a['severity']})" for a in anomalies[:3]) if anomalies else "Aucune anomalie"
        prompt = (
            "You are a CNPS (Cameroon Social Security) executive assistant. "
            "Write a concise executive summary in French (100-150 words) for the Director General's monthly report.\n\n"
            f"Current KPIs: {kpi_text}\nActive alerts: {anomaly_text}\n\n"
            "Format: Professional, formal French. Start with \"Au cours de cette période,\".\n"
            "Include: overall performance assessment, key achievements, areas needing attention, and outlook."
        )
        orchestrator = AIOrchestrator()
        result = orchestrator.execute_sync(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300,
        )
        if result and hasattr(result, "choices") and result.choices:
            return result.choices[0].message.content
    except Exception as e1:
        logger.warning(f"Orchestrator executive summary failed: {e1}")
        try:
            from ..services.groq_utils import execute_groq_completion
            completion = execute_groq_completion(prompt=prompt, temperature=0.3, max_tokens=300)
            if completion and hasattr(completion, "choices") and completion.choices:
                return completion.choices[0].message.content
        except Exception as e:
            logger.warning(f"LLM executive summary failed: {e}")

    anomaly_count = len(anomalies)
    kpi_count = len(kpis)
    if anomaly_count > 0:
        return (
            f"Au cours de cette période, {kpi_count} indicateurs clés ont été analysés avec "
            f"{anomaly_count} anomalie(s) détectée(s). Les performances globales nécessitent "
            "une attention particulière sur les points identifiés dans le rapport détaillé ci-dessous."
        )
    return (
        f"Au cours de cette période, {kpi_count} indicateurs clés ont été suivis. "
        "La situation générale est stable avec des performances conformes aux objectifs fixés."
    )


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/report/dg")
def get_dg_report(
    period: Optional[str] = Query(None, description="Report period (e.g. 'June 2026')"),
    format: str = Query("html", pattern="^(html|pdf)$"),
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Generate the Director General Monthly Report (Rapport Mensuel DG)."""
    supabase = get_supabase()
    user_id = context["user_id"]

    kpis = _build_kpi_data(user_id, supabase)
    anomalies = _build_anomaly_data(user_id, supabase)
    regional_data = _build_regional_data(supabase)
    dept_performance = _build_department_performance(supabase)
    recommendations = _build_recommendations(kpis, anomalies)
    risks = _build_risks(anomalies)
    executive_summary = _generate_executive_summary(user_id, supabase, kpis, anomalies)

    from ..services.etl_service import get_department_id
    dept_id = get_department_id(user_id, supabase)
    company_name = "CNPS"
    if dept_id:
        dept_resp = supabase.table("departments").select("name").eq("id", dept_id).limit(1).execute()
        if dept_resp.data:
            company_name = dept_resp.data[0].get("name", "CNPS")

    report_period = period or datetime.now().strftime("%B %Y")

    kwargs = dict(
        company_name=company_name,
        report_period=report_period,
        kpis=kpis,
        anomalies=anomalies,
        regional_data=regional_data,
        department_performance=dept_performance,
        recommendations=recommendations,
        risks=risks,
        executive_summary=executive_summary,
    )

    if format == "pdf":
        pdf_bytes, filename, _ = generate_pdf_report("dg", **kwargs)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    html = generate_dg_report(**kwargs)
    return Response(
        content=html,
        media_type="text/html",
        headers={"Content-Disposition": f'inline; filename="Rapport_DG_{report_period.replace(" ", "_")}.html"'},
    )


@router.get("/report/board")
def get_board_report(
    period: Optional[str] = Query(None, description="Report period"),
    format: str = Query("html", pattern="^(html|pdf)$"),
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Generate the Board of Directors Report."""
    supabase = get_supabase()
    user_id = context["user_id"]

    kpis = _build_kpi_data(user_id, supabase)
    anomalies = _build_anomaly_data(user_id, supabase)
    report_period = period or datetime.now().strftime("%B %Y")
    strategic_objectives = _build_strategic_objectives(kpis, supabase)

    # AI-generated financial summary
    try:
        from ..services.ai_orchestrator import AIOrchestrator
        kpi_text = "; ".join(f"{k['name']}: {k['value']:,.2f}" for k in kpis[:5])
        anomaly_text = "; ".join(f"{a['kpi_name']} ({a['severity']})" for a in anomalies[:3]) if anomalies else "Aucune anomalie"
        prompt = (
            f"Write a 2-sentence financial summary in French for the CNPS Board of Directors report for {report_period}. "
            f"KPIs: {kpi_text}. Alerts: {anomaly_text}. Be formal and factual."
        )
        orchestrator = AIOrchestrator()
        result = orchestrator.execute_sync(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=150,
        )
        financial_summary = result.choices[0].message.content if result and result.choices else ""
    except Exception:
        financial_summary = (
            f"Présentation de la situation financière de la CNPS pour la période {report_period}. "
            "Les indicateurs clés montrent une stabilité globale avec des axes d'amélioration identifiés."
        )

    kwargs = dict(
        company_name="CNPS",
        report_period=report_period,
        kpis=kpis,
        strategic_objectives=strategic_objectives,
        financial_summary=financial_summary,
    )

    if format == "pdf":
        pdf_bytes, filename, _ = generate_pdf_report("board", **kwargs)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    html = generate_board_report(**kwargs)
    return Response(
        content=html,
        media_type="text/html",
        headers={"Content-Disposition": f'inline; filename="Rapport_CA_{report_period.replace(" ", "_")}.html"'},
    )


@router.get("/report/regional")
def get_regional_report(
    period: Optional[str] = Query(None, description="Report period"),
    format: str = Query("html", pattern="^(html|pdf)$"),
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Generate Regional Performance Report."""
    supabase = get_supabase()
    regions = _build_regional_data(supabase)
    report_period = period or datetime.now().strftime("%B %Y")

    kwargs = dict(company_name="CNPS", report_period=report_period, regions=regions)

    if format == "pdf":
        pdf_bytes, filename, _ = generate_pdf_report("regional", **kwargs)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    html = generate_regional_performance_report(**kwargs)
    return Response(
        content=html,
        media_type="text/html",
        headers={"Content-Disposition": f'inline; filename="Performance_Regionale_{report_period.replace(" ", "_")}.html"'},
    )


@router.get("/report/fraud")
def get_fraud_detection_report(
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Run fraud detection on current data and return results."""
    supabase = get_supabase()
    user_id = context["user_id"]
    kpi_rows = safe_data(
        supabase.table("kpi_results")
        .select("*")
        .eq("user_id", user_id)
        .order("recorded_at", desc=True)
        .limit(500)
        .execute()
    )
    from ..services.fraud_detection_service import run_full_fraud_detection
    return run_full_fraud_detection(kpi_rows)


@router.get("/report/list")
def list_available_reports(
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """List all available executive report types."""
    return {
        "reports": [
            {
                "id": "dg",
                "name": "Rapport Mensuel du Directeur Général",
                "description": "Rapport complet de performance institutionnelle destiné au Directeur Général.",
                "formats": ["html", "pdf"],
                "frequency": "Mensuel",
                "audience": "Direction Générale",
                "classification": "Confidentiel",
            },
            {
                "id": "board",
                "name": "Rapport du Conseil d'Administration",
                "description": "Rapport stratégique pour le Conseil d'Administration avec objectifs et indicateurs.",
                "formats": ["html", "pdf"],
                "frequency": "Trimestriel",
                "audience": "Conseil d'Administration",
                "classification": "Confidentiel",
            },
            {
                "id": "regional",
                "name": "Rapport de Performance Régionale",
                "description": "Comparaison des performances des directions régionales.",
                "formats": ["html", "pdf"],
                "frequency": "Mensuel",
                "audience": "Directions Régionales",
                "classification": "Interne",
            },
            {
                "id": "fraud",
                "name": "Rapport de Détection des Anomalies et Fraudes",
                "description": "Détection automatisée des schémas suspects, anomalies régionales et doublons.",
                "formats": ["json"],
                "frequency": "Temps réel",
                "audience": "Direction de la Surveillance",
                "classification": "Confidentiel",
            },
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
