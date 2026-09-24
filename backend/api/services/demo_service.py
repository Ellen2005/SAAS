"""
Demo Mode Service
Provides pre-loaded CNPS sample data so new users can explore
the platform without connecting their own database.
"""

import logging
import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)

# ── Sample KPIs ──────────────────────────────────────────────────────────────

DEMO_KPIS = [
    {"kpi_name": "Contribution Collection Rate", "value": 87.3, "dod_pct": 2.1, "wow_pct": -0.5, "status": "NORMAL", "source": "demo"},
    {"kpi_name": "Pension Processing Time", "value": 12.4, "dod_pct": -1.8, "wow_pct": 3.2, "status": "WARNING", "source": "demo"},
    {"kpi_name": "Employer Compliance Rate", "value": 94.1, "dod_pct": 0.3, "wow_pct": 1.1, "status": "NORMAL", "source": "demo"},
    {"kpi_name": "Average Claim Duration", "value": 28.6, "dod_pct": 4.5, "wow_pct": -2.1, "status": "WARNING", "source": "demo"},
    {"kpi_name": "Revenue per Employee", "value": 45200, "dod_pct": 1.2, "wow_pct": 0.8, "status": "NORMAL", "source": "demo"},
    {"kpi_name": "Active Beneficiaries", "value": 23456, "dod_pct": 0.1, "wow_pct": 0.3, "status": "NORMAL", "source": "demo"},
    {"kpi_name": "Delinquent Employers", "value": 34, "dod_pct": -8.2, "wow_pct": 12.5, "status": "CRITICAL", "source": "demo"},
    {"kpi_name": "Data Quality Score", "value": 96.8, "dod_pct": 0.5, "wow_pct": 1.2, "status": "NORMAL", "source": "demo"},
]

DEMO_ANOMALIES = [
    {"kpi_name": "Delinquent Employers", "severity": "CRITICAL", "deviation": 12.5, "context": {"reason": "12.5% week-over-week increase in delinquent employers — possible seasonal pattern or enforcement gap"}, "detected_at": datetime.now().isoformat()},
    {"kpi_name": "Pension Processing Time", "severity": "WARNING", "deviation": 3.2, "context": {"reason": "Processing time 3.2% above 7-day average — may indicate staffing constraints"}, "detected_at": datetime.now().isoformat()},
    {"kpi_name": "Average Claim Duration", "severity": "WARNING", "deviation": 4.5, "context": {"reason": "Claim duration trending upward — review AT/MP processing workflow"}, "detected_at": datetime.now().isoformat()},
]


def generate_demo_time_series(days: int = 30) -> List[Dict]:
    """Generate realistic time series data for demo."""
    base_values = {
        "contributions": 1500000,
        "pension_payments": 850000,
        "new_registrations": 120,
        "claims_processed": 45,
    }
    series = []
    for i in range(days):
        date = (datetime.now() - timedelta(days=days - i)).strftime("%Y-%m-%d")
        for kpi, base in base_values.items():
            noise = random.gauss(0, base * 0.05)
            trend = base * 0.001 * i
            series.append({
                "date": date,
                "kpi_name": kpi,
                "value": round(base + trend + noise, 2),
                "source": "demo",
            })
    return series


def get_demo_analysis_result(preset_slug: str = "contributions-monitoring") -> Dict[str, Any]:
    """Generate a demo analysis result with real statistical outputs."""
    import pandas as pd
    from ..services.statistical_engine import (
        comprehensive_stats, compute_correlation_matrix,
        detect_outliers_iqr, forecast_linear_trend,
    )

    time_series = generate_demo_time_series(30)
    df = pd.DataFrame(time_series)

    # Pivot to get columns per KPI
    pivoted = df.pivot_table(index="date", columns="kpi_name", values="value", aggfunc="first")
    pivoted = pivoted.dropna()

    stat_results = {}
    if not pivoted.empty:
        numeric_cols = pivoted.select_dtypes(include=["number"]).columns.tolist()
        for col in numeric_cols:
            vals = pivoted[col].dropna().tolist()
            if len(vals) >= 3:
                stat_results[col] = comprehensive_stats(vals)

        if len(numeric_cols) >= 2:
            corr = compute_correlation_matrix(pivoted[numeric_cols])
            stat_results["correlations"] = corr.get("strong_pairs", [])

        for col in numeric_cols[:3]:
            vals = pivoted[col].dropna().tolist()
            if len(vals) >= 5:
                fc = forecast_linear_trend(vals, periods=6)
                if "error" not in fc:
                    stat_results[f"forecast_{col}"] = fc

    return {
        "id": "demo-analysis-001",
        "status": "completed",
        "goal_text": _preset_goal(preset_slug),
        "overview": _demo_overview(preset_slug),
        "observations": _demo_observations(preset_slug),
        "insights": _demo_insights(preset_slug),
        "kpis": DEMO_KPIS,
        "anomalies": DEMO_ANOMALIES,
        "time_series": time_series,
        "statistical_analysis": stat_results,
        "forecasts": [],
        "risk_analysis": _demo_risks(preset_slug),
        "recommendations": _demo_recommendations(preset_slug),
        "limitations": "This is a demonstration using simulated data. Connect your own database for real analysis.",
        "assumptions": ["Data follows historical patterns", "No structural changes in reporting period"],
        "is_demo": True,
    }


def _preset_goal(slug: str) -> str:
    goals = {
        "contributions-monitoring": "Monthly contribution collection totals and payment compliance rate by regional office",
        "pension-analytics": "Monthly pension disbursement trends and beneficiary growth over the last 12 months",
        "workplace-accidents": "Workplace accident frequency and average claim processing indicators by region",
        "employer-compliance": "Count of delinquent employers and overdue contribution amounts by region",
        "regional-performance": "Regional contribution share and comparative performance across all offices",
    }
    return goals.get(slug, "Analyze institutional KPIs and performance metrics")


def _demo_overview(slug: str) -> str:
    return (
        "This demonstration analysis covers key performance indicators for institutional social security operations. "
        "The analysis examines contribution collection efficiency, pension processing throughput, employer compliance rates, "
        "and regional performance distribution. All metrics are computed from simulated data that mirrors real-world patterns."
    )


def _demo_observations(slug: str) -> List[str]:
    return [
        "Contribution collection rate is at 87.3%, trending upward over the analysis period",
        "Pension processing time has increased 3.2% week-over-week, flagged as a warning",
        "Employer compliance remains strong at 94.1% but delinquent employers increased 12.5%",
        "8 KPIs tracked across 5 regional offices with 23,456 active beneficiaries",
        "Data completeness score is 96.8% with minimal missing values detected",
    ]


def _demo_insights(slug: str) -> List[Dict]:
    return [
        {"title": "Collection Rate Improvement", "severity": "info", "detail": "Contribution collection has improved 2.1% day-over-day, suggesting recent enforcement measures are effective."},
        {"title": "Delinquent Employer Spike", "severity": "critical", "detail": "The 12.5% increase in delinquent employers requires immediate attention — consider targeted outreach to non-compliant organizations."},
        {"title": "Processing Time Trend", "severity": "warning", "detail": "Average pension processing time is above the 7-day average. If this trend continues, it may impact beneficiary satisfaction scores."},
        {"title": "Regional Variance", "severity": "info", "detail": "Performance varies significantly across regional offices. Top performer contributes 31% of total collection while lowest contributes 12%."},
    ]


def _demo_risks(slug: str) -> str:
    return (
        "Key risks identified in this analysis period:\n"
        "1. **Employer Non-Compliance**: The 12.5% spike in delinquent employers could impact future contribution volumes.\n"
        "2. **Processing Bottleneck**: Increasing pension processing time may lead to beneficiary complaints and regulatory scrutiny.\n"
        "3. **Regional Imbalance**: Heavy concentration in 2-3 offices creates operational risk if any single office experiences disruption.\n"
        "4. **Data Quality**: While overall score is 96.8%, specific fields (AT/MP claim duration) show higher null rates."
    )


def _demo_recommendations(slug: str) -> List[str]:
    return [
        "Initiate targeted employer compliance outreach program for the 34 delinquent organizations",
        "Review pension processing workflow to identify and resolve the bottleneck causing 3.2% increase",
        "Implement regional performance dashboards to enable real-time monitoring of office-level metrics",
        "Schedule monthly data quality reviews to maintain completeness above 95% threshold",
        "Consider automated alerts for KPI deviations exceeding 2 standard deviations",
    ]
