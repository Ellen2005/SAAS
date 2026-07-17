from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Optional
from datetime import datetime, timezone
UTC = timezone.utc
from ..core.supabase_client import get_supabase
from ..core.auth import require_role, resolve_user_id
from ..core.utils import safe_data
from ..services.cache_service import invalidate_user_cache
from ..services.audit_service import log_config_change
from ..services.custom_report_service import generate_custom_report
from ..services.analysis_engine import run_analysis as run_goal_analysis
from ..services.professional_report_service import generate_goal_analysis_report
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["reports"])


def _find_report(supabase, report_id: str, user_id: str):
    """Find a report by report_id, falling back to id if report_id column doesn't exist."""
    try:
        resp = supabase.table("reports").select("*").eq("report_id", report_id).eq("user_id", user_id).limit(1).execute()
        if hasattr(resp, "data") and resp.data:
            return resp.data[0]
    except Exception as e:
        if "column" in str(e).lower() or "schema" in str(e).lower():
            pass
        else:
            raise
    resp = supabase.table("reports").select("*").eq("id", report_id).eq("user_id", user_id).limit(1).execute()
    if hasattr(resp, "data") and resp.data:
        return resp.data[0]
    return None


def _delete_report_by_id(supabase, report_id: str, user_id: str):
    """Delete a report by report_id, falling back to id."""
    try:
        supabase.table("reports").delete().eq("report_id", report_id).eq("user_id", user_id).execute()
    except Exception as e:
        if "column" in str(e).lower() or "schema" in str(e).lower():
            supabase.table("reports").delete().eq("id", report_id).eq("user_id", user_id).execute()
        else:
            raise


def _update_report_narrative(supabase, report_id: str, user_id: str, narrative: str):
    """Update report narrative by report_id, falling back to id."""
    update_data = {"narrative": narrative}
    try:
        update_data["updated_at"] = datetime.now(UTC).isoformat()
    except Exception:
        pass
    try:
        supabase.table("reports").update(update_data).eq("report_id", report_id).eq("user_id", user_id).execute()
    except Exception as e:
        if "column" in str(e).lower() or "schema" in str(e).lower():
            update_data.pop("updated_at", None)
            supabase.table("reports").update(update_data).eq("id", report_id).eq("user_id", user_id).execute()
        else:
            raise


@router.get("/reports/history")
def get_reports_history(limit: int = 50, user_id: str = Depends(resolve_user_id)):
    supabase = get_supabase()
    try:
        rows = safe_data(
            supabase.table("daily_reports")
            .select("*")
            .eq("user_id", user_id)
            .order("report_date", desc=True)
            .limit(limit)
            .execute()
        )
        return {"reports": rows}
    except Exception:
        logger.error("Reports history error", exc_info=True)
        return {"reports": [], "error": "Failed to fetch reports history."}


@router.get("/reports/{report_id}/download")
def download_report(report_id: str, user_id: str = Depends(resolve_user_id)):
    from fastapi.responses import Response, FileResponse
    import tempfile
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

    try:
        from ..services.professional_report_service import ProfessionalReportGenerator
        user_report_dir = os.path.join(tempfile.gettempdir(), f"reports_{user_id}")
        os.makedirs(user_report_dir, exist_ok=True)

        report_data = {
            'title': f'CNPS Daily Report - {report["report_date"]}',
            'report_id': report_id,
            'prepared_for': os.getenv("INSTITUTION_NAME", "CNPS"),
            'prepared_by': 'CNPS AI Analytics System',
            'date': str(report["report_date"]),
            'version': '1.0',
            'report_type': 'Daily Report',
            'executive_summary': report.get("narrative", "Daily KPI report."),
            'background': 'Automated daily report.',
            'objectives': ['Track daily KPI performance'],
            'data_sources': [{'name': 'CNPS Institutional Database', 'description': 'Main data warehouse'}],
            'methodology': 'Automated KPI tracking and anomaly detection.',
            'data_quality': 'Automated quality checks applied.',
            'quality_metrics': [
                {'metric': 'KPIs Tracked', 'value': str(len(kpis)), 'status': '✓'},
                {'metric': 'Anomalies', 'value': str(len(anomalies)), 'status': '✓'},
            ],
            'kpis': kpis,
            'anomalies': anomalies,
            'time_series': [],
            'forecasts': [],
            'interpretation': report.get("narrative", ""),
            'risks': [],
            'recommendations': [],
            'appendices': [],
        }

        pdf_path = os.path.join(user_report_dir, f"daily_{report_id}.pdf")
        generator = ProfessionalReportGenerator(os.getenv("INSTITUTION_NAME", "CNPS"))
        generator.generate_report(report_data, pdf_path, format="pdf")

        if os.path.isfile(pdf_path) and os.path.getsize(pdf_path) > 100:
            return FileResponse(
                path=pdf_path,
                media_type="application/pdf",
                filename=f"report-{report['report_date']}.pdf",
            )
    except Exception as e:
        logger.warning(f"PDF generation failed, falling back to HTML: {e}")

    from ..services.email_service import generate_professional_html_email
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
    print_helper = (
        "<script>window.addEventListener('load',()=>{setTimeout(()=>window.print(),300)});</script>"
        "<style>@media print{.no-print{display:none!important}}</style>"
    )
    html = html.replace("</head>", f"{print_helper}</head>", 1)
    filename = f"report-{report['report_date']}.html"
    return Response(
        content=html,
        media_type="text/html",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.post("/reports/generate")
def generate_report(background_tasks: BackgroundTasks, context: dict = Depends(require_role(["manager", "admin"]))):
    supabase = get_supabase()
    user_id = context["user_id"]
    try:
        from ..services.etl_service import run_user_etl_pipeline
        from ..services.narrative_service import generate_live_narrative
        from datetime import date
        
        run_user_etl_pipeline(user_id)
        
        kpi_rows = supabase.table("kpi_results").select("*").eq("user_id", user_id).order("recorded_at", desc=True).limit(20).execute()
        kpis = kpi_rows.data if hasattr(kpi_rows, "data") and kpi_rows.data else []
        
        anomaly_rows = supabase.table("anomaly_records").select("*").eq("user_id", user_id).order("detected_at", desc=True).limit(10).execute()
        anomalies = anomaly_rows.data if hasattr(anomaly_rows, "data") and anomaly_rows.data else []
        
        report_date = date.today().isoformat()
        
        narrative = generate_live_narrative(
            kpi_data=kpis,
            anomaly_data=anomalies,
            tone="insight-driven",
            company_name=os.getenv("INSTITUTION_NAME", "CNPS"),
            report_period=report_date,
            report_type="Daily",
        )
        
        supabase.table("daily_reports").insert({
            "user_id": user_id,
            "narrative": narrative,
            "report_date": report_date,
        }).execute()
        
        invalidate_user_cache(user_id)
        
        return {"status": "generated", "report_date": report_date}
    except Exception as e:
        logger.error(f"Report generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Report generation failed. Please try again later.")


@router.patch("/reports/{report_id}")
def edit_report_narrative(
    report_id: str,
    body: dict,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    narrative = body.get("narrative", "").strip()
    if not narrative:
        raise HTTPException(status_code=400, detail="Narrative cannot be empty.")
    supabase = get_supabase()
    try:
        supabase.table("daily_reports").update({"narrative": narrative}).eq("id", report_id).eq("user_id", context["user_id"]).execute()
        log_config_change(supabase, context["user_id"], "update", "report_narrative", {"report_id": report_id})
        return {"status": "updated", "report_id": report_id}
    except Exception as e:
        logger.error(f"Report edit error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update report.")


@router.post("/reports/{report_id}/send")
def resend_report(
    report_id: str,
    background_tasks: BackgroundTasks,
    context: dict = Depends(require_role(["manager", "admin"])),
):
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
        from ..services.email_service import send_automated_briefing
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
        logger.error(f"Report send error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to send report.")


@router.post("/reports/custom")
def create_custom_report(
    body: dict,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    instruction = body.get("instruction", "").strip()
    if not instruction:
        raise HTTPException(status_code=400, detail="Instruction cannot be empty.")
    supabase = get_supabase()
    try:
        run_goal_analysis(
            user_id=context["user_id"],
            goal_text=instruction,
            supabase=supabase,
        )
    except Exception as e:
        logger.warning(f"Goal analysis failed (non-blocking): {e}")
    result = generate_custom_report(
        user_id=context["user_id"],
        instruction=instruction,
        report_scope=body.get("report_scope", "my_department"),
        format_type=body.get("format_type", "narrative"),
        date_from=body.get("date_from"),
        date_to=body.get("date_to"),
        department_ids=body.get("department_ids"),
        kpi_names=body.get("kpi_names"),
        supabase=supabase,
        role=context.get("role", "manager"),
        report_template=body.get("report_template"),
    )
    return result


@router.post("/reports/custom/save")
def save_custom_report(
    body: dict,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    narrative = body.get("narrative", "").strip()
    instruction = body.get("instruction", "Custom report")
    if not narrative:
        raise HTTPException(status_code=400, detail="Narrative cannot be empty.")
    supabase = get_supabase()
    try:
        supabase.table("daily_reports").insert({
            "user_id": context["user_id"],
            "narrative": f"[Custom: {instruction[:80]}]\n\n{narrative}",
            "report_date": datetime.now(UTC).date().isoformat(),
        }).execute()
        return {"status": "saved"}
    except Exception as e:
        logger.error(f"Custom report save error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save report.")


@router.post("/reports/generate-professional")
def generate_professional_report(
    body: dict,
    context: dict = Depends(require_role(["manager", "admin"]))
):
    from fastapi.responses import FileResponse
    import tempfile
    
    supabase = get_supabase()
    user_id = context["user_id"]
    
    try:
        analysis_result = {}
        analysis_id = body.get("analysis_id")
        goal_text = body.get("goal_text")
        
        if analysis_id:
            analysis_resp = supabase.table("analysis_runs").select("*").eq("id", analysis_id).eq("user_id", user_id).limit(1).execute()
            if hasattr(analysis_resp, "data") and analysis_resp.data:
                analysis_result = analysis_resp.data[0]
        
        if goal_text:
            analysis_result["goal_text"] = goal_text
        if not analysis_result.get("goal_text"):
            analysis_result["goal_text"] = "Data Analysis Report"
        
        user_report_dir = os.path.join(tempfile.gettempdir(), f"reports_{user_id}")
        os.makedirs(user_report_dir, exist_ok=True)
        
        result = generate_goal_analysis_report(
            user_id=user_id,
            analysis_result=analysis_result,
            supabase=supabase,
            institution_name=os.getenv("INSTITUTION_NAME", "CNPS"),
            output_dir=user_report_dir
        )
        
        report_record = {
            "user_id": user_id,
            "report_type": "goal_analysis",
            "file_path": result["pdf"],
            "title": analysis_result.get("goal_text", "Goal Analysis Report")[:80],
            "status": "generated"
        }
        try:
            report_record_full = {
                **report_record,
                "excel_path": result.get("excel"),
                "report_id": result["report_id"],
            }
            supabase.table("reports").insert(report_record_full).execute()
        except Exception as insert_err:
            if "column" in str(insert_err).lower() or "schema" in str(insert_err).lower():
                logger.warning(f"reports table missing columns, inserting without optional fields: {insert_err}")
                supabase.table("reports").insert(report_record).execute()
            else:
                raise

        db_report_id = result["report_id"]
        try:
            latest = supabase.table("reports").select("id").eq("user_id", user_id).eq("file_path", result["pdf"]).order("created_at", desc=True).limit(1).execute()
            if hasattr(latest, "data") and latest.data:
                db_report_id = latest.data[0]["id"]
        except Exception as e:
            logger.warning(f"Could not fetch inserted report id: {e}")

        return {
            "status": "success",
            "report_id": db_report_id,
            "pdf_path": result["pdf"],
            "excel_path": result.get("excel"),
            "download_url": f"/api/reports/download/{db_report_id}?format=pdf",
            "excel_url": f"/api/reports/download/{db_report_id}?format=excel"
        }
    
    except Exception as e:
        logger.error(f"Professional report generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Report generation failed. Please try again or contact support.")


@router.get("/reports/download/{report_id}")
def download_professional_report(
    report_id: str,
    format: str = "pdf",
    context: dict = Depends(require_role(["manager", "admin"]))
):
    from fastapi.responses import FileResponse, PlainTextResponse
    import tempfile
    import uuid

    supabase = get_supabase()
    user_id = context["user_id"]

    report = _find_report(supabase, report_id, user_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    file_path = report.get("file_path", "")

    if format == "excel":
        excel_path = report.get("excel_path", "")
        if excel_path and os.path.isfile(excel_path):
            return FileResponse(
                path=excel_path,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename=f"report_{report_id}.xlsx",
            )
        kpis = report.get("kpis") or []
        if not kpis:
            try:
                resp = supabase.table("kpi_results").select("*").eq("user_id", user_id).order("recorded_at", desc=True).limit(20).execute()
                if hasattr(resp, "data") and resp.data:
                    kpis = resp.data
            except Exception:
                pass
        csv_lines = ["KPI,Value,DoD %,WoW %,Status"]
        for k in kpis:
            csv_lines.append(
                f"{k.get('kpi_name', '')},{k.get('value', 0)},{k.get('dod_pct', 0)},{k.get('wow_pct', 0)},{k.get('status', '')}"
            )
        return PlainTextResponse(
            content="\n".join(csv_lines),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="report_{report_id}.csv"'}
        )

    if file_path and os.path.isfile(file_path):
        return FileResponse(
            path=file_path,
            media_type="application/pdf",
            filename=f"report_{report_id}.pdf",
        )

    try:
        kpis = report.get("kpis") or []
        if not kpis:
            try:
                resp = supabase.table("kpi_results").select("*").eq("user_id", user_id).order("recorded_at", desc=True).limit(20).execute()
                if hasattr(resp, "data") and resp.data:
                    kpis = resp.data
            except Exception:
                pass

        anomalies = report.get("anomalies") or []
        if not anomalies:
            try:
                resp = supabase.table("anomaly_records").select("*").eq("user_id", user_id).order("detected_at", desc=True).limit(10).execute()
                if hasattr(resp, "data") and resp.data:
                    anomalies = resp.data
            except Exception:
                pass

        from ..services.professional_report_service import ProfessionalReportGenerator
        user_report_dir = os.path.join(tempfile.gettempdir(), f"reports_{user_id}")
        os.makedirs(user_report_dir, exist_ok=True)

        report_data = {
            'title': report.get("title", "CNPS Analysis Report"),
            'report_id': report_id,
            'prepared_for': os.getenv("INSTITUTION_NAME", "CNPS"),
            'prepared_by': 'CNPS AI Analytics System',
            'date': datetime.now().strftime('%B %d, %Y'),
            'version': '1.0',
            'report_type': report.get("report_type", "Analysis Report"),
            'executive_summary': report.get("narrative", "Report generated by CNPS Smart Analytics."),
            'background': 'Automated analysis report.',
            'objectives': ['Data analysis and insight generation'],
            'data_sources': [{'name': 'CNPS Institutional Database', 'description': 'Main data warehouse'}],
            'methodology': 'AI-Driven Analysis Pipeline with statistical analysis.',
            'data_quality': 'Automated quality checks applied.',
            'quality_metrics': [
                {'metric': 'KPIs Analyzed', 'value': str(len(kpis)), 'status': '✓'},
                {'metric': 'Anomalies Detected', 'value': str(len(anomalies)), 'status': '✓'},
            ],
            'kpis': kpis,
            'anomalies': anomalies,
            'time_series': [],
            'forecasts': [],
            'interpretation': report.get("narrative", ""),
            'risks': [],
            'recommendations': [],
            'appendices': [],
        }

        pdf_path = os.path.join(user_report_dir, f"report_{report_id}.pdf")
        generator = ProfessionalReportGenerator(os.getenv("INSTITUTION_NAME", "CNPS"))
        generator.generate_report(report_data, pdf_path, format="pdf")

        if os.path.isfile(pdf_path) and os.path.getsize(pdf_path) > 100:
            try:
                supabase.table("reports").update({"file_path": pdf_path}).eq("id", report_id).execute()
            except Exception:
                pass
            return FileResponse(
                path=pdf_path,
                media_type="application/pdf",
                filename=f"report_{report_id}.pdf",
            )
    except Exception as e:
        logger.error(f"PDF generation failed for report {report_id}: {e}", exc_info=True)

    from fastapi.responses import HTMLResponse
    from ..services.email_service import generate_professional_html_email
    narrative = report.get("narrative", "")
    try:
        html = generate_professional_html_email(
            kpis=kpis if 'kpis' in dir() else [],
            narrative_text=narrative,
            chart_url="",
            anomalies=anomalies if 'anomalies' in dir() else [],
            department_name=report.get("department_name", ""),
            report_type=report.get("report_type", "Daily"),
            report_period=report.get("report_period", ""),
        )
    except Exception as e:
        logger.error(f"HTML fallback also failed for report {report_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate report")

    print_helper = (
        "<script>window.addEventListener('load',()=>{setTimeout(()=>window.print(),300)});</script>"
        "<style>@media print{.no-print{display:none!important}}</style>"
    )
    html = html.replace("</head>", f"{print_helper}</head>", 1)
    return HTMLResponse(
        content=html,
        headers={"Content-Disposition": f'inline; filename="report_{report_id}.html"'}
    )


@router.get("/reports/professional/list")
def list_professional_reports(
    limit: int = 50,
    context: dict = Depends(require_role(["manager", "admin"]))
):
    supabase = get_supabase()
    user_id = context["user_id"]
    
    try:
        rows = supabase.table("reports").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
        reports = rows.data if hasattr(rows, "data") and rows.data else []
    except Exception as e:
        if "column" in str(e).lower() or "schema" in str(e).lower():
            logger.warning(f"reports table schema issue, listing without optional columns: {e}")
            try:
                rows = supabase.table("reports").select("id, user_id, report_type, file_path, title, status, created_at").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
                reports = rows.data if hasattr(rows, "data") and rows.data else []
            except Exception:
                reports = []
        else:
            logger.error(f"List reports error: {e}")
            reports = []
    
    return {"reports": reports}


@router.delete("/reports/professional/{report_id}")
def delete_professional_report(
    report_id: str,
    context: dict = Depends(require_role(["manager", "admin"]))
):
    supabase = get_supabase()
    user_id = context["user_id"]
    
    report = _find_report(supabase, report_id, user_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    for path_key in ["file_path", "excel_path"]:
        file_path = report.get(path_key)
        if file_path:
            try:
                file_path = os.path.normpath(file_path)
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    os.remove(file_path)
                    logger.info(f"Deleted report file: {file_path}")
            except Exception as e:
                logger.warning(f"Could not delete file {file_path}: {e}")
    
    _delete_report_by_id(supabase, report_id, user_id)
    
    return {"status": "deleted", "report_id": report_id}


@router.patch("/reports/professional/{report_id}/narrative")
def update_report_narrative(
    report_id: str,
    body: dict,
    context: dict = Depends(require_role(["manager", "admin"]))
):
    supabase = get_supabase()
    user_id = context["user_id"]
    
    narrative = body.get("narrative", "").strip()
    if not narrative:
        raise HTTPException(status_code=400, detail="Narrative cannot be empty")
    
    if len(narrative) > 100000:
        raise HTTPException(status_code=400, detail="Narrative too long (max 100KB)")
    
    _update_report_narrative(supabase, report_id, user_id, narrative)
    
    return {"status": "updated", "report_id": report_id}
