import os
import httpx
import logging
from groq import Groq

logger = logging.getLogger(__name__)

# Base definitions for consistent metric interpretation across departments
BASE_DEFINITIONS = """
STANDARD METRIC DEFINITIONS (use these consistently):
- Net Revenue = Gross Revenue minus Returns and Discounts
- Customer Count = Number of unique active accounts in the reporting period
- Gross Margin = (Revenue minus COGS) divided by Revenue, expressed as a percentage
- Inventory Value = Total current valuation of stock on hand
- Support Tickets = Count of customer support requests (open or resolved)
- DoD % = Day-over-Day percentage change
- WoW % = Week-over-Week percentage change
"""


def build_prompt(
    kpis: list,
    anomalies: list,
    tone: str = "insight-driven",
    instruction: str = None,
    base_definitions: str = None,
    prompt_template: str = None,
    company_name: str = "your company",
) -> str:
    """
    Constructs a sophisticated prompt for the LLM with anchored metric definitions.
    """
    data_context = f"KPIs: {kpis}\nAnomalies: {anomalies}"
    focus_clause = f"\n\nCRITICAL STRATEGIC FOCUS: {instruction}" if instruction else ""
    defs = base_definitions or BASE_DEFINITIONS

    if prompt_template:
        base_prompt = prompt_template.format(
            company_name=company_name,
            user_tone=tone,
            user_instruction=instruction or "Provide the most important operational insights.",
            kpis=kpis,
            anomalies=anomalies,
            definitions=defs,
        )
    else:
        base_prompt = f"""You are a business analyst for {company_name}. {defs}

IMPORTANT: Use the metric definitions above precisely when discussing any KPI values. Do not redefine these terms.
{data_context}{focus_clause}
"""
    if tone == "formal":
        return (
            base_prompt
            + "\nProvide a formal, concise executive summary. Focus on accuracy and professional tone. Keep it under 200 words."
        )
    else:
        return (
            base_prompt
            + "\nProvide a punchy, insight-driven narrative. Use bold terms, highlight the most exciting changes. Keep it under 200 words."
        )


def generate_live_narrative(
    kpi_data: list,
    anomaly_data: list,
    tone: str = "insight-driven",
    instruction: str = None,
    base_definitions: str = None,
    prompt_template: str = None,
    company_name: str = "your company",
):
    """
    Connect to Groq (Cloud) or Ollama (Local) to generate a live AI narrative with anchored definitions.
    """
    groq_api_key = os.getenv("GROQ_API_KEY")

    # 1. Attempt Groq (Primary)
    if groq_api_key:
        try:
            client = Groq(api_key=groq_api_key)
            prompt = build_prompt(
                kpi_data,
                anomaly_data,
                tone,
                instruction,
                base_definitions=base_definitions,
                prompt_template=prompt_template,
                company_name=company_name,
            )

            completion = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500,
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq API Error: {str(e)}")

    # 2. Attempt Ollama (Fallback)
    try:
        prompt = build_prompt(
            kpi_data,
            anomaly_data,
            tone,
            instruction,
            base_definitions=base_definitions,
            prompt_template=prompt_template,
            company_name=company_name,
        )
        response = httpx.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3", "prompt": prompt, "stream": False},
            timeout=10.0,
        )
        if response.status_code == 200:
            return response.json().get("response")
    except Exception as e:
        logger.warning(f"Ollama Fallback Failed: {str(e)}")

    # 3. Final Fallback (Template-based)
    return build_dynamic_narrative(kpi_data, anomaly_data)


def build_dynamic_narrative(kpis: list, anomalies: list) -> str:
    """
    Standard template-based narrative if AI services are unavailable.
    """
    narrative_parts = []
    for k in kpis:
        trend = "up" if k.get("dod_pct", 0) > 0 else "down"
        narrative_parts.append(
            f"{k['kpi_name']} is currently at {k['value']:,.2f} ({trend})."
        )
    if anomalies:
        narrative_parts.append(
            f"We detected {len(anomalies)} anomalies requiring investigation."
        )
    return " ".join(narrative_parts)
