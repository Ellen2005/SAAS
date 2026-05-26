import os
import hmac
import hashlib
from datetime import datetime, date
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from .chart_service import generate_trend_chart_url

UNSUBSCRIBE_SECRET = os.getenv("UNSUBSCRIBE_SECRET", "saas-unsubscribe-secret")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
# Use a real verified sender — set these in your .env
SENDER_NAME = os.getenv("EMAIL_SENDER_NAME", "SAAS Analytics")
SENDER_EMAIL = os.getenv("EMAIL_SENDER_ADDRESS", "noreply@saas-analytics.com")


def _make_unsubscribe_token(email: str) -> str:
    return hmac.new(
        UNSUBSCRIBE_SECRET.encode(),
        email.encode(),
        hashlib.sha256,
    ).hexdigest()


def _unsubscribe_url(email: str) -> str:
    token = _make_unsubscribe_token(email)
    return f"{FRONTEND_URL}/unsubscribe?email={email}&token={token}"


def verify_unsubscribe_token(email: str, token: str) -> bool:
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
    dept_label = f" — {department_name}" if department_name else ""
    rag_color, rag_label = _rag_badge(kpis)
    dashboard_url = f"{FRONTEND_URL}/reports"
    unsubscribe = _unsubscribe_url(recipient_email) if recipient_email else "#"
    rag_emoji = "🔴" if "RED" in rag_label else "🟡" if "AMBER" in rag_label else "🟢"

    kpi_rows = ""
    for k in kpis:
        name = k.get("kpi_name", "").replace("_", " ").title()
        val = f"{k.get('value', 0):,.2f}"
        dod = k.get("dod_pct") or 0
        wow = k.get("wow_pct") or 0
        status = k.get("status", "NORMAL")
        dod_color = "#10b981" if dod >= 0 else "#ef4444"
        wow_color = "#10b981" if wow >= 0 else "#ef4444"
        status_color = "#10b981" if status == "NORMAL" else "#f59e0b" if status == "WARNING" else "#ef4444"
        kpi_rows += f"""
        <tr style="border-bottom:1px solid #f3f4f6;">
          <td style="padding:10px 12px;font-weight:600;color:#111827;">{name}</td>
          <td style="padding:10px 12px;font-size:1.05rem;font-weight:700;color:#111827;">{val}</td>
          <td style="padding:10px 12px;color:{dod_color};font-weight:600;">{dod:+.1f}%</td>
          <td style="padding:10px 12px;color:{wow_color};font-weight:600;">{wow:+.1f}%</td>
          <td style="padding:10px 12px;">
            <span style="background:{status_color}22;color:{status_color};padding:3px 10px;border-radius:999px;font-size:0.75rem;font-weight:700;">{status}</span>
          </td>
        </tr>"""

    anomaly_rows = ""
    if anomalies:
        for a in anomalies:
            name = a.get("kpi_name", "").replace("_", " ").title()
            sev = a.get("severity", "WARNING")
            reason = a.get("context", {}).get("reason", "Deviation detected")
            dev = a.get("deviation", 0)
            sc = "#ef4444" if sev == "CRITICAL" else "#f59e0b"
            anomaly_rows += f"""
            <tr style="border-bottom:1px solid #f3f4f6;">
              <td style="padding:10px 12px;">
                <span style="background:{sc}22;color:{sc};padding:3px 10px;border-radius:999px;font-size:0.75rem;font-weight:700;">{sev}</span>
              </td>
              <td style="padding:10px 12px;font-weight:600;color:#111827;">{name}</td>
              <td style="padding:10px 12px;color:#6b7280;font-size:0.9rem;">{reason}</td>
              <td style="padding:10px 12px;color:#374151;font-weight:600;">{dev:.1f}&#963;</td>
            </tr>"""
    else:
        anomaly_rows = '<tr><td colspan="4" style="padding:16px;color:#6b7280;text-align:center;">No anomalies detected in this period.</td></tr>'

    narrative_html = "".join(
        f'<p style="margin:0 0 12px 0;line-height:1.7;color:#374151;">{p.strip()}</p>'
        for p in (narrative_text or "").split("\n") if p.strip()
    )

    chart_section = ""
    if chart_url:
        chart_section = f"""
    <div style="margin-bottom:32px;">
      <h2 style="margin:0 0 16px 0;font-size:1rem;text-transform:uppercase;letter-spacing:0.08em;color:#6b7280;border-bottom:2px solid #f3f4f6;padding-bottom:8px;">Performance Trend</h2>
      <img src="{chart_url}" alt="KPI Trend Chart" style="width:100%;height:auto;border-radius:8px;border:1px solid #e5e7eb;"/>
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>{report_type} Report</title></head>
<body style="margin:0;padding:20px 0;background:#f3f4f6;font-family:Helvetica,Arial,sans-serif;">
<div style="max-width:680px;margin:0 auto;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

  <div style="background:linear-gradient(135deg,#4f46e5,#3b82f6);padding:32px 40px;">
    <div style="color:rgba(255,255,255,0.7);font-size:0.75rem;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;">Smart Automated Analytics System</div>
    <h1 style="margin:0;color:#ffffff;font-size:1.5rem;font-weight:700;">{report_type} Performance Report{dept_label}</h1>
    <div style="margin-top:12px;color:rgba(255,255,255,0.85);font-size:0.85rem;">
      &#128197; Period: {report_period} &nbsp;&nbsp; &#128228; Submitted: {today}
    </div>
  </div>

  <div style="padding:32px 40px;">

    <div style="margin-bottom:32px;">
      <h2 style="margin:0 0 16px 0;font-size:1rem;text-transform:uppercase;letter-spacing:0.08em;color:#6b7280;border-bottom:2px solid #f3f4f6;padding-bottom:8px;">Executive Summary</h2>
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;padding:12px 16px;border-radius:8px;background:{rag_color}18;border-left:4px solid {rag_color};">
        <span style="font-size:1.1rem;">{rag_emoji}</span>
        <span style="font-weight:700;color:{rag_color};">Overall Status: {rag_label}</span>
      </div>
      {narrative_html}
    </div>

    <div style="margin-bottom:32px;">
      <h2 style="margin:0 0 16px 0;font-size:1rem;text-transform:uppercase;letter-spacing:0.08em;color:#6b7280;border-bottom:2px solid #f3f4f6;padding-bottom:8px;">Key Performance Indicators</h2>
      <table style="width:100%;border-collapse:collapse;font-size:0.9rem;">
        <thead>
          <tr style="background:#f9fafb;">
            <th style="padding:10px 12px;text-align:left;color:#6b7280;font-weight:600;font-size:0.8rem;">Metric</th>
            <th style="padding:10px 12px;text-align:left;color:#6b7280;font-weight:600;font-size:0.8rem;">Value</th>
            <th style="padding:10px 12px;text-align:left;color:#6b7280;font-weight:600;font-size:0.8rem;">DoD %</th>
            <th style="padding:10px 12px;text-align:left;color:#6b7280;font-weight:600;font-size:0.8rem;">WoW %</th>
            <th style="padding:10px 12px;text-align:left;color:#6b7280;font-weight:600;font-size:0.8rem;">Status</th>
          </tr>
        </thead>
        <tbody>{kpi_rows}</tbody>
      </table>
    </div>

    {chart_section}

    <div style="margin-bottom:32px;">
      <h2 style="margin:0 0 16px 0;font-size:1rem;text-transform:uppercase;letter-spacing:0.08em;color:#6b7280;border-bottom:2px solid #f3f4f6;padding-bottom:8px;">Anomalies &amp; Alerts</h2>
      <table style="width:100%;border-collapse:collapse;font-size:0.9rem;">
        <thead>
          <tr style="background:#f9fafb;">
            <th style="padding:10px 12px;text-align:left;color:#6b7280;font-weight:600;font-size:0.8rem;">Severity</th>
            <th style="padding:10px 12px;text-align:left;color:#6b7280;font-weight:600;font-size:0.8rem;">Metric</th>
            <th style="padding:10px 12px;text-align:left;color:#6b7280;font-weight:600;font-size:0.8rem;">Finding</th>
            <th style="padding:10px 12px;text-align:left;color:#6b7280;font-weight:600;font-size:0.8rem;">Deviation</th>
          </tr>
        </thead>
        <tbody>{anomaly_rows}</tbody>
      </table>
    </div>

    <div style="background:#f9fafb;border-radius:8px;padding:20px;margin-bottom:24px;text-align:center;">
      <p style="margin:0 0 12px 0;color:#6b7280;font-size:0.9rem;">Full data, historical trends, and interactive charts are available in your dashboard.</p>
      <a href="{dashboard_url}" style="display:inline-block;background:linear-gradient(135deg,#4f46e5,#3b82f6);color:#ffffff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;font-size:0.9rem;">View Full Report in Dashboard &#8594;</a>
    </div>

  </div>

  <div style="background:#f9fafb;padding:20px 40px;border-top:1px solid #e5e7eb;text-align:center;">
    <p style="margin:0 0 6px 0;font-size:0.75rem;color:#9ca3af;">This report was automatically generated by the SAAS Analytics System.</p>
    <p style="margin:0;font-size:0.75rem;color:#9ca3af;">
      <a href="{unsubscribe}" style="color:#9ca3af;text-decoration:underline;">Unsubscribe from these reports</a>
    </p>
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
    recipients = [row["email"] for row in response.data] if hasattr(response, "data") and response.data else []

    if not recipients:
        print(f"[{datetime.now().isoformat()}] WARNING: No recipients for user {user_id}. Add email recipients in Settings.")
        return {"status": "skipped", "reason": "no_recipients"}

    department_name = None
    try:
        dept_resp = supabase.table("user_roles").select("departments(name)").eq("user_id", user_id).limit(1).execute()
        if hasattr(dept_resp, "data") and dept_resp.data and dept_resp.data[0].get("departments"):
            department_name = dept_resp.data[0]["departments"].get("name")
    except Exception:
        pass

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

    for anomaly in critical_anomalies:
        for email in recipients:
            sc = "#ef4444"
            alert_html = f"""<!DOCTYPE html><html><body style="font-family:Helvetica,Arial,sans-serif;background:#f3f4f6;padding:20px;">
            <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;">
              <div style="background:{sc};padding:24px 32px;">
                <h1 style="margin:0;color:#fff;font-size:1.2rem;">&#128680; CRITICAL Anomaly Alert{dept_subject}</h1>
              </div>
              <div style="padding:24px 32px;">
                <p><strong>{anomaly.get('kpi_name','').replace('_',' ').title()}</strong> has triggered a critical anomaly.</p>
                <p style="color:#6b7280;">{anomaly.get('context',{}).get('reason','Requires immediate investigation.')}</p>
                <p>Deviation: <strong>{anomaly.get('deviation',0):.1f}&#963;</strong></p>
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
    if not to_email or "@" not in to_email:
        return {"status": "skipped", "reason": "invalid_recipient"}

    client = get_brevo_client()
    kpi_name = (anomaly_data or {}).get("kpi_name", "Unknown KPI").replace("_", " ").title()
    severity = (anomaly_data or {}).get("severity", "WARNING")
    deviation = (anomaly_data or {}).get("deviation", 0)
    reason = (anomaly_data or {}).get("context", {}).get("reason", "Anomaly detected.")

    if not client:
        print(f"[{datetime.now().isoformat()}] INFO: BREVO_API_KEY not set. Would send anomaly alert to {to_email}.")
        return {"status": "simulated", "recipient": to_email, "severity": severity}

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
            to=[{"email": to_email}],
            sender={"name": SENDER_NAME, "email": SENDER_EMAIL},
            subject=f"{severity}: {kpi_name} anomaly",
            html_content=html_content,
        ))
        return {"status": "sent", "recipient": to_email, "message_id": response.message_id}
    except ApiException as e:
        print(f"[{datetime.now().isoformat()}] Anomaly alert failed for {to_email}: {e}")
        return {"status": "failed", "recipient": to_email, "error": str(e)}


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
