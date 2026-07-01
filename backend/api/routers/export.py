"""Enhanced export endpoints with Excel support."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from typing import Optional
import logging
from datetime import datetime, timezone

from ..core.auth import require_role, resolve_user_id
from ..core.supabase_client import get_supabase
from ..services.export_service import export_kpis_csv, export_kpis_excel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/kpis/csv")
def export_kpis_csv_endpoint(context: dict = Depends(require_role(["manager", "admin"]))):
    """Export KPIs as CSV."""
    supabase = get_supabase()
    try:
        csv_bytes = export_kpis_csv(context["user_id"], supabase)
        filename = f"kpis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            content=csv_bytes,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        logger.error("CSV export error", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.get("/kpis/excel")
def export_kpis_excel_endpoint(context: dict = Depends(require_role(["manager", "admin"]))):
    """Export KPIs as Excel with formatting."""
    supabase = get_supabase()
    try:
        excel_bytes = export_kpis_excel(context["user_id"], supabase)
        filename = f"kpis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        logger.error("Excel export error", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.get("/reports/{report_id}/excel")
def export_report_excel(report_id: str, context: dict = Depends(require_role(["manager", "admin"]))):
    """Export a specific report as Excel."""
    supabase = get_supabase()
    try:
        from ..services.export_service import export_report_as_excel
        
        # Fetch report data
        report_resp = (
            supabase.table("daily_reports")
            .select("*")
            .eq("id", report_id)
            .eq("user_id", context["user_id"])
            .limit(1)
            .execute()
        )
        if not report_resp.data:
            raise HTTPException(status_code=404, detail="Report not found")
        
        report = report_resp.data[0]
        excel_bytes = export_report_as_excel(report, supabase)
        
        filename = f"report_{report.get('report_date', 'export')}.xlsx"
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Report Excel export error", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")