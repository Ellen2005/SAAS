"""
Custom Report Service
Generates on-demand reports based on user-specified parameters, scope, and format.
"""
import os
import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)


def generate_custom_report(
    user_id: str,
    instruction: str,
    report_scope: str,  # "my_department" | "all_departments" | "specific_kpi" | "anomalies_only"
    format_type: str,   # "narrative" | "table" | "bullet_points" | "executive_brief" | "detailed"
    date_from: str = None,
    date_to: str = None,
    department_ids: list = None,
    kpi_names: list = None,
    supabase=None,
    role: str = "manager",
) -> dict:
    """
    Generate a custom report based on user instructions.
    Returns the report text and metadata.
    """
    groq_api_key = os.getenv("GROQ_API_KEY")

    # --- Fetch data based on scope ---
    kpis = []
    anomalies = []
    departments_data = []

    try:
        if report_scope == "all_departments" and role == "admin":
            kpi_q = supabase.table("kpi_results").select("*, departments(name)").order("recorded_at", desc=True).limit(200)
            anomaly_q = supabase.table("anomaly_records").select("*, departments(name)").order("detected_at", desc=True).limit(100)
            dept_q = supabase.table("departments").select("id, name").execute()
            departments_data = dept_q.data if hasattr(dept_q, "data") and dept_q.data else []
        elif report_scope == "specific_departments" and department_ids:
            kpi_q = supabase.table("kpi_results").select("*, departments(name)").in_("department_id", department_ids).order("recorded_at", desc=True).limit(200)
            anomaly_q = supabase.table("anomaly_records").select("*").in_("department_id", department_ids).order("detected_at", desc=True).limit(100)
        else:
            kpi_q = supabase.table("kpi_results").select("*").eq("user_id", user_id).order("recorded_at", desc=True).limit(100)
            anomaly_q = supabase.table("anomaly_records").select("*").eq("user_id", user_id).order("detected_at", desc=True).limit(50)

        if date_from:
            kpi_q = kpi_q.gte("recorded_at", date_from)
            anomaly_q = anomaly_q.gte("detected_at", date_from)
        if date_to:
            kpi_q = kpi_q.lte("recorded_at", date_to)
            anomaly_q = anomaly_q.lte("detected_at", date_to)

        kpi_resp = kpi_q.execute()
        anomaly_resp = anomaly_q.execute()
        kpis = kpi_resp.data if hasattr(kpi_resp, "data") and kpi_resp.data else []
        anomalies = anomaly_resp.data if hasattr(anomaly_resp, "data") and anomaly_resp.data else []

        # Filter by KPI names if specified
        if kpi_names:
            kpis = [k for k in kpis if k.get("kpi_name") in kpi_names]
            anomalies = [a for a in anomalies if a.get("kpi_name") in kpi_names]

    except Exception as e:
        logger.error(f"Data fetch error for custom report: {e}")

    if not kpis and not anomalies:
        return {
            "report": "No data found for the specified parameters. Please run a sync first or adjust your filters.",
            "kpi_count": 0,
            "anomaly_count": 0,
        }

    # --- Build prompt ---
    kpi_text = _format_kpis_for_prompt(kpis)
    anomaly_text = _format_anomalies_for_prompt(anomalies)
    dept_text = ", ".join([d.get("name", "") for d in departments_data]) if departments_data else "your department"

    format_instructions = {
        "narrative": "Write a flowing narrative report with paragraphs. Be analytical and insightful.",
        "table": "Present data in a structured tabular text format with clear columns and rows.",
        "bullet_points": "Use bullet points and short sentences. Be concise and scannable.",
        "executive_brief": "Write a very short executive brief (max 150 words). Focus only on the most critical findings.",
        "detailed": "Write a comprehensive detailed report with all sections: summary, KPI analysis, anomalies, trends, recommendations.",
    }

    format_instruction = format_instructions.get(format_type, format_instructions["narrative"])
    today = date.today().strftime("%B %d, %Y")
    period_text = f"from {date_from} to {date_to}" if date_from and date_to else f"as of {today}"

    prompt = f"""You are a senior business analyst. Generate a custom report based on the following request.

USER REQUEST: {instruction}

REPORT FORMAT: {format_instruction}

DATA SCOPE: {dept_text} — {period_text}

KPI DATA:
{kpi_text}

ANOMALIES:
{anomaly_text}

IMPORTANT:
- Use actual numbers from the data above
- Do not use placeholders
- Respond in the same language as the user's request (French or English)
- Keep it under 800 words unless format is "detailed"

REPORT:"""

    # --- Generate with Groq ---
    if groq_api_key:
        try:
            from .groq_utils import execute_groq_completion, get_groq_model
            completion = execute_groq_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=1200,
                model=get_groq_model(),
            )
            report_text = completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq error in custom report: {e}")
            report_text = _fallback_report(kpis, anomalies, instruction, today)
    else:
        report_text = _fallback_report(kpis, anomalies, instruction, today)

    return {
        "report": report_text,
        "kpi_count": len(kpis),
        "anomaly_count": len(anomalies),
        "generated_at": datetime.utcnow().isoformat(),
        "scope": report_scope,
        "format": format_type,
    }


def _format_kpis_for_prompt(kpis: list) -> str:
    if not kpis:
        return "  No KPI data available."
    lines = []
    for k in kpis[:30]:
        dept = ""
        if k.get("departments"):
            dept = f" [{k['departments'].get('name', '')}]"
        lines.append(
            f"  - {k.get('kpi_name', '').replace('_', ' ').title()}{dept}: "
            f"{float(k.get('value', 0)):,.2f} | DoD: {k.get('dod_pct') or 0:+.1f}% | "
            f"Status: {k.get('status', 'NORMAL')} | Date: {k.get('recorded_at', '')}"
        )
    return "\n".join(lines)


def _format_anomalies_for_prompt(anomalies: list) -> str:
    if not anomalies:
        return "  No anomalies detected."
    lines = []
    for a in anomalies[:20]:
        lines.append(
            f"  [{a.get('severity', 'WARNING')}] {a.get('kpi_name', '').replace('_', ' ').title()}: "
            f"{a.get('context', {}).get('reason', 'Deviation detected')} "
            f"(z={a.get('deviation', 0):.1f})"
        )
    return "\n".join(lines)


def _fallback_report(kpis, anomalies, instruction, today) -> str:
    lines = [f"Custom Report — {today}", f"Request: {instruction}", ""]
    for k in kpis[:10]:
        lines.append(f"- {k.get('kpi_name', '').replace('_', ' ').title()}: {float(k.get('value', 0)):,.2f} ({k.get('status', 'NORMAL')})")
    if anomalies:
        lines.append(f"\n{len(anomalies)} anomaly/anomalies detected.")
    return "\n".join(lines)
