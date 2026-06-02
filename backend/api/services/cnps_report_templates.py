"""CNPS institutional report section templates."""

CNPS_REPORT_SECTIONS = {
    "executive_brief": [
        "Executive Summary (Cotisations, Prestations, Sinistres)",
        "Key Performance Indicators",
        "Critical Anomalies",
        "Regional Performance Highlights",
        "Recommended Actions",
    ],
    "contributions": [
        "Contribution Collections Overview",
        "Payment Compliance and Arrears",
        "Employer Compliance",
        "Regional Contribution Performance",
    ],
    "pension": [
        "Pension Disbursement Trends",
        "Beneficiary Growth",
        "Reserve and Liability Indicators",
    ],
    "department_performance": [
        "Departmental KPI Summary",
        "Cross-Department Comparison",
        "Operational Priorities",
    ],
    "statistical_summary": [
        "Statistical Overview",
        "Data Quality Notes",
        "Trend Tables",
    ],
}


def sections_for_format(format_type: str) -> list[str]:
    mapping = {
        "executive_brief": "executive_brief",
        "brief": "executive_brief",
        "contributions": "contributions",
        "pension": "pension",
        "detailed": "statistical_summary",
    }
    key = mapping.get(format_type, "executive_brief")
    return CNPS_REPORT_SECTIONS.get(key, CNPS_REPORT_SECTIONS["executive_brief"])
