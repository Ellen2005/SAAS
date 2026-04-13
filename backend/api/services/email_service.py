import os
import hmac
import hashlib
from datetime import datetime
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from .chart_service import generate_trend_chart_url

UNSUBSCRIBE_SECRET = os.getenv("UNSUBSCRIBE_SECRET", "saas-unsubscribe-secret")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


def _make_unsubscribe_token(email: str) -> str:
    """HMAC-SHA256 token so unsubscribe links can't be forged."""
    return hmac.new(UNSUBSCRIBE_SECRET.encode(), email.encode(), hashlib.sha256).hexdigest()


def _unsubscribe_url(email: str) -> str:
    token = _make_unsubscribe_token(email)
    return f"{FRONTEND_URL}/unsubscribe?email={email}&token={token}"


def verify_unsubscribe_token(email: str, token: str) -> bool:
    expected = _make_unsubscribe_token(email)
    return hmac.compare_digest(expected, token)


def get_brevo_client():
    api_key = os.getenv("BREVO_API_KEY")
    if not api_key:
        return None
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = api_key
    return sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))


def _opt_out_footer(email: str) -> str:
    url = _unsubscribe_url(email)
    return f"""
    <p style="font-size:11px;color:#9ca3af;margin-top:24px;text-align:center;border-top:1px solid #e5e7eb;padding-top:12px;">
      You are receiving this because you are a notification recipient for a SAAS department.<br/>
      <a href="{url}" style="color:#6b7280;">Unsubscribe from these emails</a>
    </p>
    """


def generate_html_email(kpis, narrative_text, chart_url, anomalies=None, department_name=None, recipient_email="") -> str:
    kpi_html = ""
    for k in kpis:
        trend_color = "green" if k["dod_pct"] > 0 else "red" if k["dod_pct"] < 0 else "gray"
        kpi_html += f"""
        <div style="border:1px solid #e5e7eb;padding:15px;border-radius:8px;margin-bottom:10px;background:#f9fafb;">
            <h3 style="margin:0;color:#374151;">{k["kpi_name"]}</h3>
            <p style="font-size:24px;font-weight:bold;margin:5px 0;color:#111827;">{k["value"]:,.2f}</p>
            <p style="margin:0;color:{trend_color};font-weight:bold;">{k["dod_pct"]:+.1f}% vs yesterday</p>
        </div>"""

    anomaly_html = ""
    if anomalies:
        items = ""
        for a in anomalies:
            sc = "#ef4444" if a.get("severity") == "CRITICAL" else "#f59e0b"
            bg = "rgba(239,68,68,0.05)" if a.get("severity") == "CRITICAL" else "rgba(245,158,11,0.05)"
            items += f"""
            <div style="border-left:4px solid {sc};padding:10px 15px;margin-bottom:8px;background:{bg};">
                <strong style="color:{sc};">{a.get("severity","WARNING")}</strong>: {a.get("kpi_name","Unknown")}
                <br/><span style="color:#6b7280;font-size:14px;">{a.get("context",{}).get("reason","Deviation detected")} (Deviation: {a.get("deviation",0):.1f}%)</span>
            </div>"""
        anomaly_html = f"<h2>Anomalies Detected ({len(anomalies)})</h2>{items}"

    dept_label = f" — {department_name}" if department_name else ""
    footer = _opt_out_footer(recipient_email) if recipient_email else ""

    return f"""
    <div style="font-family:Helvetica,Arial,sans-serif;max-width:600px;margin:0 auto;color:#333;">
        <h1 style="color:#4f46e5;border-bottom:2px solid #e5e7eb;padding-bottom:10px;">Daily Analytics Briefing{dept_label}</h1>
        <h2>Executive Summary</h2>
        <p style="font-size:16px;line-height:1.5;color:#4b5563;">{narrative_text}</p>
        {anomaly_html}
        <h2>Performance Trend</h2>
        <img src="{chart_url}" alt="KPI Trend Chart" style="width:100%;height:auto;border:1px solid #e5e7eb;border-radius:8px;"/>
        <h2>Current Metrics</h2>
        {kpi_html}
        {footer}
    </div>"""


def send_automated_briefing(user_id: str, kpis: list, anomalies: list, narrative_text: str, historical_df):
    from ..core.supabase_client import get_supabase
    supabase = get_supabase()

    response = supabase.table("notification_recipients").select("email").eq("user_id", user_id).execute()
    recipients = [row["email"] for row in response.data] if hasattr(response, "data") and response.data else []

    if not recipients:
        print(f"[{datetime.now().isoformat()}] WARNING: No recipients for user {user_id}. Briefing skipped.")
        return {"status": "skipped", "reason": "no_recipients"}

    department_name = None
    try:
        dept_resp = supabase.table("user_roles").select("departments(name)").eq("user_id", user_id).limit(1).execute()
        if hasattr(dept_resp, "data") and dept_resp.data and dept_resp.data[0].get("departments"):
            department_name = dept_resp.data[0]["departments"].get("name")
    except Exception:
        pass

    critical_anomalies = [a for a in anomalies if a.get("severity") == "CRITICAL" and a.get("deviation", 0) > 3.0]
    chart_url = generate_trend_chart_url(historical_df)
    client = get_brevo_client()
    dept_subject = f" — {department_name}" if department_name else ""
    subject = f"Daily Analytics Briefing{dept_subject}"

    if not client:
        print(f"[{datetime.now().isoformat()}] INFO: Brevo missing. Simulation mode for {len(recipients)} recipients.")
        return {"status": "success", "mock": True, "recipients": recipients, "critical_alerts": len(critical_anomalies)}

    results = []
    for email in recipients:
        html_content = generate_html_email(kpis, narrative_text, chart_url, anomalies, department_name, recipient_email=email)
        try:
            api_response = client.send_transac_email(sib_api_v3_sdk.SendSmtpEmail(
                to=[{"email": email}],
                sender={"name": "SAAS-PWA System", "email": "reports@saas-pwa.local"},
                subject=subject, html_content=html_content,
            ))
            results.append({"email": email, "type": "digest", "message_id": api_response.message_id})
        except ApiException as e:
            results.append({"email": email, "type": "digest", "status": "failed", "error": str(e)})

    for anomaly in critical_anomalies:
        for email in recipients:
            alert_html = f"""
            <div style="font-family:Helvetica,Arial,sans-serif;max-width:600px;margin:0 auto;">
                <h2 style="color:#ef4444;">CRITICAL Anomaly Alert{dept_subject}</h2>
                <p><strong>{anomaly.get("kpi_name","Unknown KPI")}</strong> has triggered a critical anomaly.</p>
                <p>Deviation: {anomaly.get("deviation",0):.1f}%</p>
                <p>{anomaly.get("context",{}).get("reason","Requires immediate investigation.")}</p>
                {_opt_out_footer(email)}
            </div>"""
            try:
                api_response = client.send_transac_email(sib_api_v3_sdk.SendSmtpEmail(
                    to=[{"email": email}],
                    sender={"name": "SAAS-PWA Alert", "email": "alerts@saas-pwa.local"},
                    subject=f"CRITICAL ALERT: {anomaly.get('kpi_name','Unknown')}{dept_subject}",
                    html_content=alert_html,
                ))
                results.append({"email": email, "type": "critical_alert", "message_id": api_response.message_id})
            except ApiException as e:
                results.append({"email": email, "type": "critical_alert", "status": "failed", "error": str(e)})

    return {"status": "broadcast_complete", "results": results, "digest_sent": True, "critical_alerts_sent": len(critical_anomalies)}


def send_anomaly_alert(to_email: str, anomaly_data: dict):
    pass


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
        print(f"[{datetime.now().isoformat()}] ERROR: Unable to fetch admin user_ids: {e}")
        return {"status": "error", "reason": "admin_role_query_failed"}

    if not admin_user_ids:
        return {"status": "skipped", "reason": "no_admins_found"}

    try:
        auth_users = supabase.auth.admin.list_users()
        users = getattr(auth_users, "users", []) or []
        email_by_id = {str(u.id): getattr(u, "email", None) for u in users}
        recipients = [e for e in [email_by_id.get(str(uid)) for uid in admin_user_ids] if e]
        new_user_email = email_by_id.get(str(new_user_id))
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] ERROR: Unable to map user emails: {e}")
        return {"status": "skipped", "reason": "email_mapping_failed"}

    if not recipients:
        return {"status": "skipped", "reason": "no_admin_emails_resolved"}

    html_content = f"""
    <div style="font-family:Helvetica,Arial,sans-serif;max-width:640px;margin:0 auto;color:#111827;">
      <h2 style="color:#4f46e5;">SAAS onboarding notification</h2>
      <p>A new user was assigned to the default department after their first sign-in.</p>
      <ul>
        <li><strong>User ID:</strong> {new_user_id}</li>
        <li><strong>Email:</strong> {new_user_email or '(not found)'}</li>
      </ul>
      <p style="color:#6b7280;font-size:12px;">Generated by the SAAS-PWA backend.</p>
    </div>"""

    results = []
    for email in recipients:
        try:
            api_response = client.send_transac_email(sib_api_v3_sdk.SendSmtpEmail(
                to=[{"email": email}],
                sender={"name": "SAAS-PWA System", "email": "reports@saas-pwa.local"},
                subject="SAAS: New user onboarded", html_content=html_content,
            ))
            results.append({"email": email, "message_id": api_response.message_id})
        except ApiException as e:
            results.append({"email": email, "status": "failed", "error": str(e)})

    return {"status": "sent", "recipients": len(results), "results": results}
