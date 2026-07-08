"""Email testing and debugging endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from ..core.auth import require_role, resolve_user_id
from ..core.supabase_client import get_supabase
from ..services.email_service import send_automated_briefing, get_brevo_client, normalize_recipient_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/email", tags=["email"])


class EmailTestRequest(BaseModel):
    recipient_email: str
    test_type: str = "digest"  # digest, alert, onboarding


@router.get("/config")
def get_email_config(user_id: str = Depends(resolve_user_id)):
    """Get current email configuration status."""
    from ..services.email_service import SENDER_EMAIL, SENDER_NAME
    import os
    
    brevo_key = os.getenv("BREVO_API_KEY")
    client = get_brevo_client()
    
    supabase = get_supabase()
    recipients = []
    try:
        response = supabase.table("notification_recipients").select("email").eq("user_id", user_id).execute()
        recipients = [row["email"] for row in (response.data or [])]
    except Exception as e:
        logger.error(f"Failed to fetch recipients: {e}")
    
    return {
        "brevo_configured": bool(brevo_key),
        "brevo_client_ready": client is not None,
        "sender_email": SENDER_EMAIL,
        "sender_name": SENDER_NAME,
        "recipients": recipients,
        "recipient_count": len(recipients),
        "status": "ready" if (brevo_key and client and recipients) else "incomplete",
        "missing": [
            *([] if brevo_key else ["BREVO_API_KEY"]),
            *([] if client else ["Brevo client initialization failed"]),
            *([] if recipients else ["No email recipients configured"]),
        ],
    }


@router.post("/test")
def test_email(
    request: EmailTestRequest,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Send a test email to verify configuration."""
    import pandas as pd
    from datetime import date
    
    user_id = context["user_id"]
    supabase = get_supabase()
    
    normalized_email = normalize_recipient_email(request.recipient_email)
    if not normalized_email:
        raise HTTPException(status_code=400, detail="Valid recipient email required")
    
    # Check Brevo configuration
    client = get_brevo_client()
    if not client:
        raise HTTPException(
            status_code=503,
            detail="Email service not configured. Please set BREVO_API_KEY in backend/.env"
        )
    
    # Save recipient if not exists
    try:
        existing = supabase.table("notification_recipients").select("*").eq("user_id", user_id).eq("email", request.recipient_email).limit(1).execute()
        if not existing.data:
            supabase.table("notification_recipients").insert({
                "user_id": user_id,
                "email": normalized_email,
            }).execute()
    except Exception as e:
        logger.error(f"Failed to save recipient: {e}")
    
    # Send test email
    try:
        if request.test_type == "digest":
            result = send_automated_briefing(
                user_id=user_id,
                kpis=[],
                anomalies=[],
                narrative_text="This is a test email to verify your email configuration is working correctly. If you receive this, your Brevo integration is ready!",
                historical_df=pd.DataFrame(),
                report_type="Test",
                report_period=date.today().strftime("%B %d, %Y"),
            )
        else:
            result = {"status": "test_sent", "recipient": request.recipient_email}
        
        return {
            "status": "success",
            "message": f"Test email sent to {request.recipient_email}",
            "result": result,
        }
    except Exception as e:
        logger.error("Test email failed", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.post("/add-recipient")
def add_email_recipient(
    email: str,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Add an email recipient for reports."""
    user_id = context["user_id"]
    supabase = get_supabase()
    
    normalized_email = normalize_recipient_email(email)
    if not normalized_email:
        raise HTTPException(status_code=400, detail="Valid email address required")
    
    try:
        supabase.table("notification_recipients").upsert({
            "user_id": user_id,
            "email": normalized_email,
        }, on_conflict="user_id,email").execute()
        
        return {"status": "added", "email": normalized_email}
    except Exception as e:
        logger.error("Add email recipient failed", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.delete("/remove-recipient")
def remove_email_recipient(
    email: str,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Remove an email recipient."""
    user_id = context["user_id"]
    supabase = get_supabase()
    normalized_email = normalize_recipient_email(email)
    
    try:
        supabase.table("notification_recipients").delete().eq("user_id", user_id).eq("email", normalized_email).execute()
        return {"status": "removed", "email": normalized_email}
    except Exception as e:
        logger.error("Remove email recipient failed", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")