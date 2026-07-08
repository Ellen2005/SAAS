"""CNPS institutional report section templates."""

# Full CNPS standard report structure (matches the institutional template)
CNPS_STANDARD_SECTIONS = [
    {
        "id": "executive_summary",
        "title": "Executive Summary",
        "description": "A concise summary (~10% of report length) stating the report purpose, data sources, key findings, conclusions and recommendations. Written last but placed first. Self-contained.",
        "content_type": "narrative",
    },
    {
        "id": "introduction",
        "title": "Introduction and Background",
        "description": "Context and motivation for the analysis. CNPS mandate, relevant programs, problem statement, scope, objectives, and time period covered.",
        "content_type": "narrative",
    },
    {
        "id": "data_sources",
        "title": "Data Sources",
        "description": "All data sources used: database name, what it measures, time frame, origin department, variables extracted, unit of analysis, and any preprocessing applied.",
        "content_type": "narrative",
    },
    {
        "id": "methodology",
        "title": "Methodology",
        "description": "Statistical and computational methods, tools used, key assumptions, data cleaning and transformation steps.",
        "content_type": "narrative",
    },
    {
        "id": "data_quality",
        "title": "Data Quality and Cleaning",
        "description": "Completeness, accuracy, timeliness and consistency checks. Missing records, outliers, cross-validation results. Summary of validation pass rate.",
        "content_type": "narrative",
    },
    {
        "id": "analysis_results",
        "title": "Analysis and Results",
        "description": "Core findings with KPI tables and anomaly data. Each result explained in plain language with interpretation. Figures and tables numbered with captions.",
        "content_type": "table_and_narrative",
    },
    {
        "id": "interpretation",
        "title": "Interpretation and Key Findings",
        "description": "What the numbers mean in context of CNPS goals. Trends explained, comparisons noted, implications linked to objectives. Key findings distilled.",
        "content_type": "narrative",
    },
    {
        "id": "conclusions",
        "title": "Conclusions and Recommendations",
        "description": "Conclusions answering the analysis objectives (numbered list). Recommendations as concrete next steps tied to evidence, with responsible parties noted.",
        "content_type": "narrative",
    },
    {
        "id": "limitations",
        "title": "Limitations",
        "description": "Limitations of the analysis: data gaps, assumptions, unanswered questions. Transparent acknowledgement builds credibility.",
        "content_type": "narrative",
    },
    {
        "id": "reproducibility",
        "title": "Reproducibility and Data Access",
        "description": "Where analysis code and data are archived. How authorized users can access or reproduce results. Version control and README references.",
        "content_type": "narrative",
    },
]

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
