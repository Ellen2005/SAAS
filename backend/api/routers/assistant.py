"""
Floating AI Assistant endpoint.
Answers questions about how to use the app, explains features,
and can reference the user's current data context.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from ..core.auth import resolve_user_id
from ..core.supabase_client import get_supabase
from ..services.groq_utils import execute_groq_completion, get_groq_model

router = APIRouter(prefix="/api/assistant", tags=["assistant"])

SYSTEM_PROMPT = """You are the SAAS Analytics Assistant — a helpful, concise in-app guide built into the Smart Automated Analytics System.

Your job:
1. Explain how to use features of this app (Dashboard, Schema Explorer, AI Analyst, Ask Your Data, Settings, Reports, etc.)
2. Help users understand their KPI data, anomalies, and reports when they ask
3. Guide users through connecting a database, setting up KPI mappings, running syncs, etc.
4. Answer general analytics questions in plain language

App features you know about:
- Dashboard: shows KPIs, anomalies, AI narrative, forecast chart. Click "Generate Report" to sync and analyze.
- Schema Explorer: connect your database, browse tables, run suggested analyses, sync results to dashboard.
- Ask Your Data (NLQ): chat with your connected database using plain English. Shows SQL + results + charts.
- AI Analyst: autonomous insights, governance score, explainable AI, team collaboration snapshots.
- Settings: connect your database (PostgreSQL, MySQL, MongoDB, SQLite), set AI tone, sync schedule.
- Reports: view history of generated reports, download as HTML/PDF, edit and resend.
- Admin panel (admin only): manage departments, semantic templates, KPI field definitions, users.
- Custom Reports: generate a report with specific instructions, date ranges, and formats.

Rules:
- Be concise — 2-4 sentences max unless the user asks for detail.
- Never make up data values. If you reference user data, only use what is provided in context.
- If you don't know something, say so and suggest where to look.
- Do not generate SQL unless the user explicitly asks for it.
"""


class AssistantMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class AssistantRequest(BaseModel):
    message: str
    history: Optional[list[AssistantMessage]] = None
    include_data_context: bool = False


def _build_data_context(supabase, user_id: str) -> str:
    """Fetch a brief snapshot of the user's current data to give the assistant context."""
    try:
        kpi_resp = supabase.table("kpi_results").select("kpi_name, value, status, recorded_at") \
            .eq("user_id", user_id).order("recorded_at", desc=True).limit(5).execute()
        kpis = kpi_resp.data if hasattr(kpi_resp, "data") and kpi_resp.data else []

        anomaly_resp = supabase.table("anomaly_records").select("kpi_name, severity") \
            .eq("user_id", user_id).order("detected_at", desc=True).limit(3).execute()
        anomalies = anomaly_resp.data if hasattr(anomaly_resp, "data") and anomaly_resp.data else []

        conn_resp = supabase.table("database_connections").select("db_type, host") \
            .eq("user_id", user_id).limit(1).execute()
        conn = conn_resp.data[0] if hasattr(conn_resp, "data") and conn_resp.data else None

        lines = []
        if conn:
            lines.append(f"Connected database: {conn.get('db_type', 'unknown')} at {conn.get('host', 'unknown')}")
        if kpis:
            kpi_summary = ", ".join(f"{k['kpi_name']} = {k['value']} ({k['status']})" for k in kpis[:3])
            lines.append(f"Recent KPIs: {kpi_summary}")
        if anomalies:
            anom_summary = ", ".join(f"{a['kpi_name']} [{a['severity']}]" for a in anomalies)
            lines.append(f"Active anomalies: {anom_summary}")

        return "\n".join(lines) if lines else ""
    except Exception:
        return ""


@router.post("/chat")
def assistant_chat(
    body: AssistantRequest,
    user_id: str = Depends(resolve_user_id),
):
    supabase = get_supabase()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Optionally inject user's data context
    if body.include_data_context:
        ctx = _build_data_context(supabase, user_id)
        if ctx:
            messages.append({
                "role": "system",
                "content": f"Current user data context:\n{ctx}"
            })

    # Add conversation history (last 6 turns max to stay within token limits)
    for msg in (body.history or [])[-6:]:
        messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": body.message})

    try:
        completion = execute_groq_completion(
            messages=messages,
            temperature=0.4,
            max_tokens=400,
            model=get_groq_model(),
        )
        reply = completion.choices[0].message.content
    except Exception as e:
        reply = (
            "I'm having trouble connecting to the AI right now. "
            "You can still explore the app — check the Dashboard to generate a report, "
            "or go to Settings to connect your database."
        )

    return {"reply": reply}
