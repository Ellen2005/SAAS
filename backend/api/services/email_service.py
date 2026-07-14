import os
import hmac
import hashlib
import logging
import re
from html import escape
from datetime import datetime, date
try:
    import sib_api_v3_sdk
    from sib_api_v3_sdk.rest import ApiException
    BREVO_AVAILABLE = True
except ImportError:
    sib_api_v3_sdk = None
    ApiException = Exception
    BREVO_AVAILABLE = False
from .chart_service import generate_trend_chart_url

logger = logging.getLogger(__name__)

UNSUBSCRIBE_SECRET = os.getenv("UNSUBSCRIBE_SECRET")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
# Use a real verified sender — set these in your .env
INSTITUTION = os.getenv("INSTITUTION_NAME", "Smart Analytics")
SENDER_NAME = os.getenv("EMAIL_SENDER_NAME", f"{INSTITUTION} System")
SENDER_EMAIL = os.getenv("EMAIL_SENDER_ADDRESS", "analytics@company.com")
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_recipient_email(email: str | None) -> str | None:
    if not email:
        return None
    normalized = str(email).strip().lower()
    if not normalized or len(normalized) > 254 or not EMAIL_REGEX.fullmatch(normalized):
        return None
    return normalized


def _make_unsubscribe_token(email: str) -> str:
    normalized_email = normalize_recipient_email(email) or ""
    if not UNSUBSCRIBE_SECRET:
        return hashlib.sha256(f"no-secret:{normalized_email}".encode()).hexdigest()
    return hmac.new(
        UNSUBSCRIBE_SECRET.encode(),
        normalized_email.encode(),
        hashlib.sha256,
    ).hexdigest()


def _unsubscribe_url(email: str) -> str:
    normalized_email = normalize_recipient_email(email)
    if not normalized_email:
        return f"{FRONTEND_URL}/unsubscribe"
    token = _make_unsubscribe_token(normalized_email)
    from urllib.parse import quote
    return f"{FRONTEND_URL}/unsubscribe?email={quote(normalized_email)}&token={quote(token)}"


def verify_unsubscribe_token(email: str, token: str) -> bool:
    if not email or not token:
        return False
    return hmac.compare_digest(_make_unsubscribe_token(email), token)


def get_brevo_client():
    api_key = os.getenv("BREVO_API_KEY")
    if not api_key:
        return None
    cfg = sib_api_v3_sdk.Configuration()
    cfg.api_key["api-key"] = api_key
    return sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(cfg))


def _rag_badge(kpis: list) -> tuple:
    statuses = [k.get("status", "NORMAL") for k in kpis]
    if any(s == "CRITICAL" for s in statuses):
        return "#ef4444", "RED — Immediate Attention Required"
    if any(s == "WARNING" for s in statuses):
        return "#f59e0b", "AMBER — Monitor Closely"
    return "#10b981", "GREEN — Performing Well"


def _kpi_summary_stats(kpis: list) -> dict:
    """Compute quick summary stats from KPI list for the report header."""
    total = len(kpis)
    warnings = sum(1 for k in kpis if k.get("status") == "WARNING")
    criticals = sum(1 for k in kpis if k.get("status") == "CRITICAL")
    normals = total - warnings - criticals
    avg_dod = 0
    dod_vals = [k.get("dod_pct", 0) for k in kpis if k.get("dod_pct") is not None]
    if dod_vals:
        avg_dod = sum(dod_vals) / len(dod_vals)
    return {"total": total, "normals": normals, "warnings": warnings, "criticals": criticals, "avg_dod": avg_dod}


def generate_professional_html_email(
    kpis: list,
    narrative_text: str,
    chart_url: str,
    anomalies: list = None,
    department_name: str = None,
    recipient_email: str = "",
    report_type: str = "Daily",
    report_period: str = None,
) -> str:
    if not report_period:
        report_period = date.today().strftime("%B %d, %Y")

    today = date.today().strftime("%B %d, %Y")
    safe_department_name = escape(str(department_name or ""))
    safe_report_type = escape(str(report_type or "Daily"))
    safe_report_period = escape(str(report_period or today))
    dept_label = f" — {safe_department_name}" if safe_department_name else ""
    rag_color, rag_label = _rag_badge(kpis)
    dashboard_url = f"{FRONTEND_URL}/reports"
    unsubscribe = _unsubscribe_url(recipient_email) if recipient_email else "#"
    rag_emoji = "🔴" if "RED" in rag_label else "🟡" if "AMBER" in rag_label else "🟢"
    stats = _kpi_summary_stats(kpis)

    # ── KPI table rows ──
    kpi_rows = ""
    for k in kpis:
        name = escape(str(k.get("kpi_name", "")).replace("_", " ").title())
        val = f"{k.get('value', 0):,.2f}"
        dod = k.get("dod_pct") or 0
        wow = k.get("wow_pct") or 0
        status = escape(str(k.get("status", "NORMAL")))
        dod_color = "#10b981" if dod >= 0 else "#ef4444"
        wow_color = "#10b981" if wow >= 0 else "#ef4444"
        status_color = "#10b981" if status == "NORMAL" else "#f59e0b" if status == "WARNING" else "#ef4444"
        trend_arrow = "&#9650;" if dod > 0 else "&#9660;" if dod < 0 else "&#8212;"
        trend_color = "#10b981" if dod > 0 else "#ef4444" if dod < 0 else "#6b7280"
        kpi_rows += f"""
        <tr style="border-bottom:1px solid #f0f0f0;">
          <td style="padding:12px 14px;font-weight:600;color:#1a1a2e;font-size:0.9rem;">{name}</td>
          <td style="padding:12px 14px;font-size:1.05rem;font-weight:700;color:#1a1a2e;text-align:right;">{val}</td>
          <td style="padding:12px 14px;color:{dod_color};font-weight:600;text-align:right;">{dod:+.1f}% <span style="font-size:0.7rem;">{trend_arrow}</span></td>
          <td style="padding:12px 14px;color:{wow_color};font-weight:600;text-align:right;">{wow:+.1f}%</td>
          <td style="padding:12px 14px;text-align:center;">
            <span style="background:{status_color}18;color:{status_color};padding:4px 12px;border-radius:999px;font-size:0.72rem;font-weight:700;letter-spacing:0.03em;">{status}</span>
          </td>
        </tr>"""

    # ── Anomaly rows ──
    anomaly_rows = ""
    anomaly_count = 0
    if anomalies:
        anomaly_count = len(anomalies)
        for a in anomalies:
            name = escape(str(a.get("kpi_name", "")).replace("_", " ").title())
            sev = escape(str(a.get("severity", "WARNING")))
            reason = escape(str(a.get("context", {}).get("reason", "Deviation detected")))
            dev = a.get("deviation", 0)
            sc = "#ef4444" if sev == "CRITICAL" else "#f59e0b"
            anomaly_rows += f"""
            <tr style="border-bottom:1px solid #f0f0f0;">
              <td style="padding:10px 12px;">
                <span style="background:{sc}18;color:{sc};padding:4px 12px;border-radius:999px;font-size:0.72rem;font-weight:700;">{sev}</span>
              </td>
              <td style="padding:10px 12px;font-weight:600;color:#1a1a2e;">{name}</td>
              <td style="padding:10px 12px;color:#555;font-size:0.88rem;">{reason}</td>
              <td style="padding:10px 12px;color:#1a1a2e;font-weight:600;text-align:right;">{dev:.1f}&#963;</td>
            </tr>"""
    else:
        anomaly_rows = '<tr><td colspan="4" style="padding:20px;color:#6b7280;text-align:center;font-style:italic;">No anomalies detected this period. All metrics within expected ranges.</td></tr>'

    # ── Narrative paragraphs ──
    narrative_html = ""
    for p in (narrative_text or "").split("\n"):
        p = p.strip()
        if not p:
            continue
        safe_p = escape(p)
        # Make lines starting with ** bold
        if p.startswith("**") and p.endswith("**"):
            narrative_html += f'<p style="margin:0 0 8px 0;line-height:1.7;color:#1a1a2e;font-weight:600;">{escape(p[2:-2])}</p>'
        else:
            narrative_html += f'<p style="margin:0 0 12px 0;line-height:1.7;color:#374151;">{safe_p}</p>'

    # ── Chart section ──
    chart_section = ""
    if chart_url:
        chart_section = f"""
    <div style="margin-bottom:36px;">
      <h2 style="margin:0 0 16px 0;font-size:0.85rem;text-transform:uppercase;letter-spacing:0.1em;color:#6b7280;border-bottom:2px solid #f0f0f0;padding-bottom:8px;">Trend Analysis</h2>
      <div style="background:#fafafa;border-radius:10px;padding:16px;border:1px solid #e5e7eb;">
        <img src="{chart_url}" alt="KPI Trend Chart" style="width:100%;height:auto;border-radius:6px;"/>
      </div>
    </div>"""

    # ── Forecast summary (extract from narrative if present) ──
    forecast_section = ""
    if narrative_text and ("forecast" in narrative_text.lower() or "projection" in narrative_text.lower() or "trend" in narrative_text.lower()):
        forecast_section = f"""
    <div style="margin-bottom:36px;">
      <h2 style="margin:0 0 16px 0;font-size:0.85rem;text-transform:uppercase;letter-spacing:0.1em;color:#6b7280;border-bottom:2px solid #f0f0f0;padding-bottom:8px;">Forward-Looking Indicators</h2>
      <div style="background:linear-gradient(135deg,#eff6ff,#f0fdf4);border-radius:10px;padding:20px;border:1px solid #dbeafe;">
        <p style="margin:0;color:#1e40af;font-size:0.88rem;line-height:1.6;">
          Based on historical trend analysis, projections are embedded within the AI narrative above.
          Review the dashboard for interactive forecast charts with confidence intervals.
        </p>
      </div>
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>{safe_report_type} Statistical Report — {INSTITUTION}</title></head>
<body style="margin:0;padding:0;background:#eef2f7;font-family:Georgia,'Times New Roman',serif;">
<div style="max-width:700px;margin:0 auto;background:#ffffff;box-shadow:0 2px 20px rgba(0,0,0,0.06);">

  <!-- Header Band -->
  <div style="background:linear-gradient(135deg,#1e3a5f 0%,#2563eb 50%,#1e40af 100%);padding:36px 44px 28px;">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;">
      <div>
        <div style="color:rgba(255,255,255,0.6);font-size:0.7rem;text-transform:uppercase;letter-spacing:0.15em;margin-bottom:6px;font-family:Helvetica,Arial,sans-serif;">{INSTITUTION}</div>
        <h1 style="margin:0;color:#ffffff;font-size:1.6rem;font-weight:700;font-family:Georgia,serif;line-height:1.3;">Statistical {safe_report_type} Report{dept_label}</h1>
        <div style="margin-top:10px;color:rgba(255,255,255,0.75);font-size:0.82rem;font-family:Helvetica,Arial,sans-serif;">
          Reporting Period: <strong>{safe_report_period}</strong>
        </div>
      </div>
      <div style="text-align:right;">
        <div style="background:{rag_color};color:#fff;padding:6px 16px;border-radius:6px;font-size:0.75rem;font-weight:700;font-family:Helvetica,Arial,sans-serif;letter-spacing:0.05em;">{rag_emoji} {rag_label}</div>
        <div style="color:rgba(255,255,255,0.5);font-size:0.7rem;margin-top:8px;font-family:Helvetica,Arial,sans-serif;">Generated: {today}</div>
      </div>
    </div>
  </div>

  <!-- Summary Stats Bar -->
  <div style="background:#f8fafc;border-bottom:1px solid #e2e8f0;padding:16px 44px;display:flex;gap:24px;font-family:Helvetica,Arial,sans-serif;">
    <div style="flex:1;text-align:center;">
      <div style="font-size:1.4rem;font-weight:700;color:#1e3a5f;">{stats['total']}</div>
      <div style="font-size:0.7rem;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em;">KPIs Tracked</div>
    </div>
    <div style="flex:1;text-align:center;border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0;">
      <div style="font-size:1.4rem;font-weight:700;color:#10b981;">{stats['normals']}</div>
      <div style="font-size:0.7rem;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em;">On Track</div>
    </div>
    <div style="flex:1;text-align:center;border-right:1px solid #e2e8f0;">
      <div style="font-size:1.4rem;font-weight:700;color:#f59e0b;">{stats['warnings']}</div>
      <div style="font-size:0.7rem;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em;">Warnings</div>
    </div>
    <div style="flex:1;text-align:center;">
      <div style="font-size:1.4rem;font-weight:700;color:#ef4444;">{stats['criticals']}</div>
      <div style="font-size:0.7rem;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em;">Critical</div>
    </div>
    <div style="flex:1;text-align:center;border-left:1px solid #e2e8f0;">
      <div style="font-size:1.4rem;font-weight:700;color:{'#10b981' if stats['avg_dod'] >= 0 else '#ef4444'};">{stats['avg_dod']:+.1f}%</div>
      <div style="font-size:0.7rem;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em;">Avg DoD</div>
    </div>
  </div>

  <div style="padding:36px 44px;">

    <!-- 1. Executive Summary -->
    <div style="margin-bottom:36px;">
      <h2 style="margin:0 0 16px 0;font-size:0.85rem;text-transform:uppercase;letter-spacing:0.1em;color:#6b7280;border-bottom:2px solid #f0f0f0;padding-bottom:8px;font-family:Helvetica,Arial,sans-serif;">1. Executive Summary</h2>
      {narrative_html}
    </div>

    <!-- 2. Key Performance Indicators -->
    <div style="margin-bottom:36px;">
      <h2 style="margin:0 0 16px 0;font-size:0.85rem;text-transform:uppercase;letter-spacing:0.1em;color:#6b7280;border-bottom:2px solid #f0f0f0;padding-bottom:8px;font-family:Helvetica,Arial,sans-serif;">2. Key Performance Indicators</h2>
      <table style="width:100%;border-collapse:collapse;font-size:0.88rem;font-family:Helvetica,Arial,sans-serif;">
        <thead>
          <tr style="background:#f1f5f9;">
            <th style="padding:10px 14px;text-align:left;color:#475569;font-weight:700;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;">Indicator</th>
            <th style="padding:10px 14px;text-align:right;color:#475569;font-weight:700;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;">Value</th>
            <th style="padding:10px 14px;text-align:right;color:#475569;font-weight:700;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;">DoD</th>
            <th style="padding:10px 14px;text-align:right;color:#475569;font-weight:700;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;">WoW</th>
            <th style="padding:10px 14px;text-align:center;color:#475569;font-weight:700;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;">Status</th>
          </tr>
        </thead>
        <tbody>{kpi_rows}</tbody>
      </table>
    </div>

    {chart_section}

    <!-- 3. Anomaly Analysis -->
    <div style="margin-bottom:36px;">
      <h2 style="margin:0 0 16px 0;font-size:0.85rem;text-transform:uppercase;letter-spacing:0.1em;color:#6b7280;border-bottom:2px solid #f0f0f0;padding-bottom:8px;font-family:Helvetica,Arial,sans-serif;">3. Anomaly Analysis {f'({anomaly_count} detected)' if anomaly_count else ''}</h2>
      <table style="width:100%;border-collapse:collapse;font-size:0.88rem;font-family:Helvetica,Arial,sans-serif;">
        <thead>
          <tr style="background:#f1f5f9;">
            <th style="padding:10px 14px;text-align:left;color:#475569;font-weight:700;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;">Severity</th>
            <th style="padding:10px 14px;text-align:left;color:#475569;font-weight:700;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;">Indicator</th>
            <th style="padding:10px 14px;text-align:left;color:#475569;font-weight:700;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;">Finding</th>
            <th style="padding:10px 14px;text-align:right;color:#475569;font-weight:700;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;">Deviation</th>
          </tr>
        </thead>
        <tbody>{anomaly_rows}</tbody>
      </table>
    </div>

    {forecast_section}

    <!-- 4. Data Quality Notes -->
    <div style="margin-bottom:36px;">
      <h2 style="margin:0 0 16px 0;font-size:0.85rem;text-transform:uppercase;letter-spacing:0.1em;color:#6b7280;border-bottom:2px solid #f0f0f0;padding-bottom:8px;font-family:Helvetica,Arial,sans-serif;">4. Methodology &amp; Data Quality</h2>
      <div style="background:#f8fafc;border-radius:10px;padding:20px;border:1px solid #e2e8f0;font-family:Helvetica,Arial,sans-serif;">
        <p style="margin:0 0 10px 0;color:#475569;font-size:0.85rem;line-height:1.6;">
          This report is generated from automated data extraction, transformation, and analysis (ETL) of your connected institutional database.
          All KPIs are computed from raw source data using validated statistical methods.
        </p>
        <p style="margin:0 0 10px 0;color:#475569;font-size:0.85rem;line-height:1.6;">
          Anomalies are detected using standard deviation thresholds (configurable).
          Day-over-day (DoD) and week-over-week (WoW) comparisons use the most recent available data points.
        </p>
        <p style="margin:0;color:#475569;font-size:0.85rem;line-height:1.6;">
          AI-generated narrative insights are produced using large language models and should be interpreted alongside the quantitative data.
        </p>
      </div>
    </div>

    <!-- Dashboard CTA -->
    <div style="background:linear-gradient(135deg,#eff6ff,#f0f9ff);border-radius:10px;padding:24px;margin-bottom:24px;text-align:center;border:1px solid #dbeafe;">
      <p style="margin:0 0 14px 0;color:#1e40af;font-size:0.9rem;font-weight:600;">Access Interactive Dashboard</p>
      <p style="margin:0 0 16px 0;color:#475569;font-size:0.85rem;">View historical trends, drill down into regional performance, and explore forecast projections.</p>
      <a href="{dashboard_url}" style="display:inline-block;background:linear-gradient(135deg,#2563eb,#1d4ed8);color:#ffffff;padding:12px 32px;border-radius:8px;text-decoration:none;font-weight:600;font-size:0.88rem;font-family:Helvetica,Arial,sans-serif;box-shadow:0 2px 8px rgba(37,99,235,0.3);">Open Dashboard &#8594;</a>
    </div>

  </div>

  <!-- Footer -->
  <div style="background:#f1f5f9;padding:20px 44px;border-top:1px solid #e2e8f0;font-family:Helvetica,Arial,sans-serif;">
    <table style="width:100%;border-collapse:collapse;">
      <tr>
        <td style="padding:0;font-size:0.72rem;color:#94a3b8;line-height:1.6;">
          <strong style="color:#64748b;">{INSTITUTION}</strong> &mdash; Automated Statistical Reporting<br/>
          Report Type: {safe_report_type} &nbsp;|&nbsp; Period: {safe_report_period} &nbsp;|&nbsp; Generated: {today}<br/>
          <a href="{unsubscribe}" style="color:#94a3b8;text-decoration:underline;">Unsubscribe from automated reports</a>
        </td>
        <td style="padding:0;text-align:right;vertical-align:bottom;">
          <div style="font-size:0.65rem;color:#cbd5e1;">Powered by Smart Analytics Platform</div>
        </td>
      </tr>
    </table>
  </div>

</div>
</body>
</html>"""


def send_automated_briefing(
    user_id: str,
    kpis: list,
    anomalies: list,
    narrative_text: str,
    historical_df,
    report_type: str = "Daily",
    report_period: str = None,
):
    from ..core.supabase_client import get_supabase
    supabase = get_supabase()

    response = supabase.table("notification_recipients").select("email").eq("user_id", user_id).execute()
    recipients = []
    if hasattr(response, "data") and response.data:
        for row in response.data:
            normalized_email = normalize_recipient_email(row.get("email"))
            if normalized_email:
                recipients.append(normalized_email)

    if not recipients:
        print(f"[{datetime.now().isoformat()}] WARNING: No email recipients configured for user {user_id}. Go to Settings > Email Recipients to add at least one.")
        return {"status": "skipped", "reason": "no_recipients"}

    department_name = None
    try:
        dept_resp = supabase.table("user_roles").select("departments(name)").eq("user_id", user_id).limit(1).execute()
        if hasattr(dept_resp, "data") and dept_resp.data and dept_resp.data[0].get("departments"):
            department_name = dept_resp.data[0]["departments"].get("name")
    except Exception as e:
        logger.warning(f"Failed to fetch department name for email: {e}")

    if not report_period:
        report_period = date.today().strftime("%B %d, %Y")

    critical_anomalies = [a for a in (anomalies or []) if a.get("severity") == "CRITICAL" and a.get("deviation", 0) > 3.0]
    chart_url = generate_trend_chart_url(historical_df)
    client = get_brevo_client()
    dept_subject = f" — {department_name}" if department_name else ""
    subject = f"{report_type} Analytics Report{dept_subject} | {report_period}"

    if not client:
        print(f"[{datetime.now().isoformat()}] INFO: BREVO_API_KEY not set. Email simulation for {len(recipients)} recipient(s).")
        print(f"[{datetime.now().isoformat()}] Would send to: {recipients}")
        return {"status": "simulated", "recipients": recipients, "critical_alerts": len(critical_anomalies)}

    results = []
    for email in recipients:
        html_content = generate_professional_html_email(
            kpis=kpis, narrative_text=narrative_text, chart_url=chart_url,
            anomalies=anomalies, department_name=department_name,
            recipient_email=email, report_type=report_type, report_period=report_period,
        )
        try:
            api_response = client.send_transac_email(sib_api_v3_sdk.SendSmtpEmail(
                to=[{"email": email}],
                sender={"name": SENDER_NAME, "email": SENDER_EMAIL},
                subject=subject,
                html_content=html_content,
            ))
            results.append({"email": email, "type": "digest", "message_id": api_response.message_id})
            print(f"[{datetime.now().isoformat()}] Email sent to {email}: {api_response.message_id}")
        except ApiException as e:
            print(f"[{datetime.now().isoformat()}] Email failed for {email}: {e}")
            results.append({"email": email, "type": "digest", "status": "failed", "error": str(e)})

    from html import escape as _html_escape
    for anomaly in critical_anomalies:
        for email in recipients:
            sc = "#ef4444"
            kpi_name = _html_escape(anomaly.get('kpi_name', '').replace('_', ' ').title())
            reason = _html_escape(anomaly.get('context', {}).get('reason', 'Requires immediate investigation.'))
            deviation = anomaly.get('deviation', 0)
            alert_html = f"""<!DOCTYPE html><html><body style="font-family:Helvetica,Arial,sans-serif;background:#f3f4f6;padding:20px;">
            <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;">
              <div style="background:{sc};padding:24px 32px;">
                <h1 style="margin:0;color:#fff;font-size:1.2rem;">&#128680; CRITICAL Anomaly Alert{dept_subject}</h1>
              </div>
              <div style="padding:24px 32px;">
                <p><strong>{kpi_name}</strong> has triggered a critical anomaly.</p>
                <p style="color:#6b7280;">{reason}</p>
                <p>Deviation: <strong>{deviation:.1f}&#963;</strong></p>
                <a href="{FRONTEND_URL}/dashboard" style="display:inline-block;background:{sc};color:#fff;padding:10px 24px;border-radius:8px;text-decoration:none;font-weight:600;margin-top:12px;">View Dashboard &#8594;</a>
              </div>
              <div style="padding:16px 32px;background:#f9fafb;text-align:center;font-size:0.75rem;color:#9ca3af;">
                <a href="{_unsubscribe_url(email)}" style="color:#9ca3af;">Unsubscribe</a>
              </div>
            </div></body></html>"""
            try:
                api_response = client.send_transac_email(sib_api_v3_sdk.SendSmtpEmail(
                    to=[{"email": email}],
                    sender={"name": SENDER_NAME, "email": SENDER_EMAIL},
                    subject=f"CRITICAL ALERT: {anomaly.get('kpi_name','').replace('_',' ').title()}{dept_subject}",
                    html_content=alert_html,
                ))
                results.append({"email": email, "type": "critical_alert", "message_id": api_response.message_id})
            except ApiException as e:
                results.append({"email": email, "type": "critical_alert", "status": "failed", "error": str(e)})

    return {"status": "broadcast_complete", "results": results, "digest_sent": True, "critical_alerts_sent": len(critical_anomalies)}


def send_anomaly_alert(to_email: str, anomaly_data: dict):
    normalized_email = normalize_recipient_email(to_email)
    if not normalized_email:
        return {"status": "skipped", "reason": "invalid_recipient"}

    client = get_brevo_client()
    kpi_name = escape(str((anomaly_data or {}).get("kpi_name", "Unknown KPI")).replace("_", " ").title())
    severity = escape(str((anomaly_data or {}).get("severity", "WARNING")))
    deviation = (anomaly_data or {}).get("deviation", 0)
    reason = escape(str((anomaly_data or {}).get("context", {}).get("reason", "Anomaly detected.")))

    if not client:
        print(f"[{datetime.now().isoformat()}] INFO: BREVO_API_KEY not set. Would send anomaly alert to {normalized_email}.")
        return {"status": "simulated", "recipient": normalized_email, "severity": severity}

    color = "#ef4444" if severity == "CRITICAL" else "#f59e0b"
    html_content = f"""<div style="font-family:Helvetica,Arial,sans-serif;max-width:560px;margin:0 auto;color:#111827;padding:24px;">
      <h2 style="color:{color};">Analytics Alert: {kpi_name}</h2>
      <p><strong>Severity:</strong> {severity}</p>
      <p><strong>Deviation:</strong> {float(deviation or 0):.1f}&#963;</p>
      <p style="color:#374151;line-height:1.6;">{reason}</p>
      <p><a href="{FRONTEND_URL}/dashboard" style="color:#2563eb;">Open dashboard</a></p>
    </div>"""
    try:
        response = client.send_transac_email(sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": normalized_email}],
            sender={"name": SENDER_NAME, "email": SENDER_EMAIL},
            subject=f"{severity}: {kpi_name} anomaly",
            html_content=html_content,
        ))
        return {"status": "sent", "recipient": normalized_email, "message_id": response.message_id}
    except ApiException as e:
        print(f"[{datetime.now().isoformat()}] Anomaly alert failed for {normalized_email}: {e}")
        return {"status": "failed", "recipient": normalized_email, "error": str(e)}


def send_admin_onboarding_notification(new_user_id: str):
    from ..core.supabase_client import get_supabase
    supabase = get_supabase()
    client = get_brevo_client()

    if not client:
        print(f"[{datetime.now().isoformat()}] INFO: Brevo missing. Simulation mode for onboarding notification.")
        return {"status": "mock", "brevo_configured": False}

    try:
        admin_resp = supabase.table("user_roles").select("user_id").eq("role", "admin").execute()
        admin_user_ids = [row["user_id"] for row in getattr(admin_resp, "data", []) if row.get("user_id")]
    except Exception as e:
        return {"status": "error", "reason": str(e)}

    if not admin_user_ids:
        return {"status": "skipped", "reason": "no_admins_found"}

    try:
        auth_users = supabase.auth.admin.list_users()
        users = getattr(auth_users, "users", []) or []
        email_by_id = {str(u.id): getattr(u, "email", None) for u in users}
        recipients = [e for e in [email_by_id.get(str(uid)) for uid in admin_user_ids] if e]
        new_user_email = email_by_id.get(str(new_user_id))
    except Exception:
        return {"status": "skipped", "reason": "email_mapping_failed"}

    if not recipients:
        return {"status": "skipped", "reason": "no_admin_emails_resolved"}

    html_content = f"""<div style="font-family:Helvetica,Arial,sans-serif;max-width:560px;margin:0 auto;color:#111827;padding:24px;">
      <h2 style="color:#4f46e5;">SAAS: New User Onboarded</h2>
      <p>A new user was provisioned into the default department after their first sign-in.</p>
      <ul><li><strong>User ID:</strong> {new_user_id}</li><li><strong>Email:</strong> {new_user_email or '(not found)'}</li></ul>
      <p style="color:#6b7280;font-size:12px;">Generated by the SAAS-PWA backend.</p>
    </div>"""

    results = []
    for email in recipients:
        try:
            api_response = client.send_transac_email(sib_api_v3_sdk.SendSmtpEmail(
                to=[{"email": email}],
                sender={"name": SENDER_NAME, "email": SENDER_EMAIL},
                subject="SAAS: New user onboarded",
                html_content=html_content,
            ))
            results.append({"email": email, "message_id": api_response.message_id})
        except ApiException as e:
            results.append({"email": email, "status": "failed", "error": str(e)})

    return {"status": "sent", "recipients": len(results), "results": results}
