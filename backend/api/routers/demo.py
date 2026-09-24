"""
Demo API endpoints — lets new users explore the platform with CNPS simulation data.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = __import__("logging").getLogger(__name__)
router = APIRouter(prefix="/api/demo", tags=["demo"])


class DemoAnalysisRequest(BaseModel):
    preset_slug: str = "contributions-monitoring"


@router.get("/status")
def demo_status():
    """Check if demo mode is available."""
    return {
        "available": True,
        "message": "Demo mode available — explore the platform with CNPS simulation data",
        "presets": [
            {"slug": "contributions-monitoring", "title": "Contributions Monitoring", "description": "Track monthly contribution collection and compliance"},
            {"slug": "pension-analytics", "title": "Pension Analytics", "description": "Pension disbursement trends and beneficiary growth"},
            {"slug": "workplace-accidents", "title": "Workplace Accidents", "description": "AT/MP claim frequency and processing indicators"},
            {"slug": "employer-compliance", "title": "Employer Compliance", "description": "Delinquent employers and overdue contributions"},
            {"slug": "regional-performance", "title": "Regional Performance", "description": "Comparative performance across regional offices"},
        ],
    }


@router.get("/kpis")
def demo_kpis():
    """Return demo KPIs for dashboard display."""
    from ..services.demo_service import DEMO_KPIS
    return {"kpis": DEMO_KPIS, "is_demo": True}


@router.get("/anomalies")
def demo_anomalies():
    """Return demo anomalies."""
    from ..services.demo_service import DEMO_ANOMALIES
    return {"anomalies": DEMO_ANOMALIES, "is_demo": True}


@router.get("/time-series")
def demo_time_series(days: int = 30):
    """Return demo time series data."""
    from ..services.demo_service import generate_demo_time_series
    return {"series": generate_demo_time_series(days), "is_demo": True}


@router.post("/analysis")
def demo_analysis(body: DemoAnalysisRequest):
    """Run a demo analysis with full statistical outputs."""
    from ..services.demo_service import get_demo_analysis_result
    result = get_demo_analysis_result(body.preset_slug)
    return result


@router.get("/report")
def demo_report():
    """Generate a demo professional report PDF."""
    from fastapi.responses import FileResponse
    import tempfile, os
    from ..services.professional_report_service import ProfessionalReportGenerator
    from ..services.demo_service import DEMO_KPIS, DEMO_ANOMALIES, generate_demo_time_series

    report_data = {
        'title': 'CNPS Institutional Analytics — Demo Report',
        'report_id': 'demo-report-001',
        'prepared_for': 'CNPS Cameroon (Demo)',
        'prepared_by': 'Smart Analytics Platform',
        'date': __import__("datetime").datetime.now().strftime('%B %d, %Y'),
        'version': '1.0',
        'report_type': 'Demonstration Report',
        'executive_summary': (
            'This demonstration report showcases the analytical capabilities of the Smart Analytics Platform. '
            'It analyzes contribution collection patterns, pension processing metrics, employer compliance rates, '
            'and regional performance using simulated institutional data.'
        ),
        'background': 'Prepared as a demonstration of the platform\'s automated report generation capabilities.',
        'objectives': [
            'Demonstrate automated data collection and analysis pipeline',
            'Showcase professional report generation with charts and statistical analysis',
            'Illustrate AI-powered insights and recommendations',
        ],
        'data_sources': [{'name': 'CNPS Demo Database', 'description': 'Simulated institutional data (51 tables, 10 CNPS core tables)'}],
        'methodology': 'Automated ETL pipeline with statistical analysis (regression, correlation, outlier detection) and AI-powered insight generation.',
        'data_quality': 'Data quality validated with 96.8% completeness score. Automated outlier detection and imputation applied.',
        'quality_metrics': [
            {'metric': 'Records Analyzed', 'value': str(len(DEMO_KPIS) * 30), 'status': '✓'},
            {'metric': 'Anomalies Detected', 'value': str(len(DEMO_ANOMALIES)), 'status': '✓'},
            {'metric': 'Data Points in Time Series', 'value': str(len(generate_demo_time_series(30))), 'status': '✓'},
            {'metric': 'Statistical Tests Run', 'value': '12', 'status': '✓'},
        ],
        'kpis': DEMO_KPIS,
        'anomalies': DEMO_ANOMALIES,
        'time_series': generate_demo_time_series(30),
        'forecasts': [],
        'interpretation': (
            'The analysis reveals a generally healthy institutional performance with collection rates trending upward '
            'at 87.3%. However, two areas require attention: the 12.5% spike in delinquent employers and the 3.2% '
            'increase in pension processing time. Regional performance variance suggests opportunities for best-practice '
            'sharing between high-performing and underperforming offices.'
        ),
        'risks': [],
        'recommendations': [
            'Implement targeted employer compliance outreach for the 34 delinquent organizations',
            'Review pension processing workflow to identify and resolve the 3.2% bottleneck',
            'Deploy regional performance dashboards for real-time monitoring',
            'Schedule monthly data quality reviews to maintain >95% completeness',
        ],
        'limitations': 'This is a demonstration using simulated data. Connect your own database for real analysis.',
        'appendices': [],
    }

    out_dir = os.path.join(tempfile.gettempdir(), "demo_reports")
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, "CNPS_Demo_Report.pdf")
    generator = ProfessionalReportGenerator("CNPS")
    generator.generate_report(report_data, pdf_path, format="pdf")
    if os.path.isfile(pdf_path) and os.path.getsize(pdf_path) > 100:
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename="CNPS_Smart_Analytics_Demo_Report.pdf",
        )
    raise HTTPException(status_code=500, detail="Failed to generate demo report")
