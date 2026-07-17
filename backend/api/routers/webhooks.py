"""
Webhooks Router
===============
Provides webhook functionality for event notifications.

Features:
- Create/manage webhooks
- Event types: etl_complete, anomaly_detected, report_generated, validation_failed
- Retry logic with exponential backoff
- Webhook logs and monitoring
"""

import logging
import hmac
import hashlib
import json
from typing import List, Optional
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

from ..core.auth import require_role, resolve_user_id
from ..core.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


# ── Models ───────────────────────────────────────────────────────────────────

class EventType(str, Enum):
    ETL_COMPLETE = "etl_complete"
    ANOMALY_DETECTED = "anomaly_detected"
    REPORT_GENERATED = "report_generated"
    VALIDATION_FAILED = "validation_failed"
    KPI_THRESHOLD_BREACH = "kpi_threshold_breach"
    SYSTEM_ALERT = "system_alert"

class WebhookCreate(BaseModel):
    name: str
    url: str
    events: List[EventType]
    secret: Optional[str] = None
    headers: dict = {}
    is_active: bool = True
    retry_count: int = 3
    timeout_seconds: int = 30

class WebhookUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    events: Optional[List[EventType]] = None
    secret: Optional[str] = None
    headers: Optional[dict] = None
    is_active: Optional[bool] = None
    retry_count: Optional[int] = None
    timeout_seconds: Optional[int] = None

class Webhook(BaseModel):
    id: str
    user_id: str
    name: str
    url: str
    events: List[str]
    secret: Optional[str]
    headers: dict
    is_active: bool
    retry_count: int
    timeout_seconds: int
    last_triggered: Optional[str]
    success_count: int
    failure_count: int
    created_at: str
    updated_at: str

class WebhookLog(BaseModel):
    id: str
    webhook_id: str
    event_type: str
    payload: dict
    response_status: Optional[int]
    response_body: Optional[str]
    error: Optional[str]
    attempts: int
    created_at: str


# ── CRUD Operations ──────────────────────────────────────────────────────────

@router.get("/")
def get_webhooks(user_id: str = Depends(resolve_user_id)):
    """Get all webhooks for the user."""
    supabase = get_supabase()
    
    response = supabase.table("webhooks")\
        .select("*")\
        .eq("user_id", user_id)\
        .order("created_at", desc=True)\
        .execute()
    
    webhooks = response.data if hasattr(response, "data") and response.data else []
    return {"webhooks": webhooks}


@router.get("/{webhook_id}")
def get_webhook(webhook_id: str, user_id: str = Depends(resolve_user_id)):
    """Get a specific webhook."""
    supabase = get_supabase()
    
    response = supabase.table("webhooks")\
        .select("*")\
        .eq("id", webhook_id)\
        .eq("user_id", user_id)\
        .execute()
    
    if not hasattr(response, "data") or not response.data:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return response.data[0]


@router.post("/")
def create_webhook(
    webhook: WebhookCreate,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Create a new webhook."""
    supabase = get_supabase()
    user_id = context["user_id"]
    
    try:
        response = supabase.table("webhooks").insert({
            "user_id": user_id,
            "name": webhook.name,
            "url": webhook.url,
            "events": [e.value for e in webhook.events],
            "secret": webhook.secret,
            "headers": webhook.headers,
            "is_active": webhook.is_active,
            "retry_count": webhook.retry_count,
            "timeout_seconds": webhook.timeout_seconds,
            "last_triggered": None,
            "success_count": 0,
            "failure_count": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }).execute()
        
        if hasattr(response, "data") and response.data:
            return response.data[0]
        raise HTTPException(status_code=500, detail="Failed to create webhook")
    except Exception as e:
        logger.error("Failed to create webhook", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.patch("/{webhook_id}")
def update_webhook(
    webhook_id: str,
    updates: WebhookUpdate,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Update a webhook."""
    supabase = get_supabase()
    user_id = context["user_id"]
    
    # Verify ownership
    existing = supabase.table("webhooks")\
        .select("user_id")\
        .eq("id", webhook_id)\
        .eq("user_id", user_id)\
        .execute()
    
    if not hasattr(existing, "data") or not existing.data:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    # Build update dict
    update_data = {"updated_at": datetime.now().isoformat()}
    if updates.name is not None:
        update_data["name"] = updates.name
    if updates.url is not None:
        update_data["url"] = updates.url
    if updates.events is not None:
        update_data["events"] = [e.value for e in updates.events]
    if updates.secret is not None:
        update_data["secret"] = updates.secret
    if updates.headers is not None:
        update_data["headers"] = updates.headers
    if updates.is_active is not None:
        update_data["is_active"] = updates.is_active
    if updates.retry_count is not None:
        update_data["retry_count"] = updates.retry_count
    if updates.timeout_seconds is not None:
        update_data["timeout_seconds"] = updates.timeout_seconds
    
    try:
        response = supabase.table("webhooks")\
            .update(update_data)\
            .eq("id", webhook_id)\
            .execute()
        
        if hasattr(response, "data") and response.data:
            return response.data[0]
        raise HTTPException(status_code=500, detail="Failed to update webhook")
    except Exception as e:
        logger.error("Failed to update webhook", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.delete("/{webhook_id}")
def delete_webhook(
    webhook_id: str,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Delete a webhook."""
    supabase = get_supabase()
    user_id = context["user_id"]
    
    # Verify ownership
    existing = supabase.table("webhooks")\
        .select("user_id")\
        .eq("id", webhook_id)\
        .eq("user_id", user_id)\
        .execute()
    
    if not hasattr(existing, "data") or not existing.data:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    try:
        supabase.table("webhooks")\
            .delete()\
            .eq("id", webhook_id)\
            .execute()
        
        return {"status": "deleted", "webhook_id": webhook_id}
    except Exception as e:
        logger.error("Failed to delete webhook", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.get("/{webhook_id}/logs")
def get_webhook_logs(
    webhook_id: str,
    limit: int = Query(50, description="Number of logs to return"),
    user_id: str = Depends(resolve_user_id),
):
    """Get webhook execution logs."""
    supabase = get_supabase()
    
    # Verify access
    webhook = supabase.table("webhooks")\
        .select("user_id")\
        .eq("id", webhook_id)\
        .execute()
    
    if not hasattr(webhook, "data") or not webhook.data:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    if webhook.data[0]["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    response = supabase.table("webhook_logs")\
        .select("*")\
        .eq("webhook_id", webhook_id)\
        .order("created_at", desc=True)\
        .limit(limit)\
        .execute()
    
    logs = response.data if hasattr(response, "data") and response.data else []
    return {"logs": logs}


@router.post("/{webhook_id}/test")
def test_webhook(
    webhook_id: str,
    background_tasks: BackgroundTasks,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    """Send a test event to the webhook."""
    supabase = get_supabase()
    user_id = context["user_id"]
    
    # Get webhook
    response = supabase.table("webhooks")\
        .select("*")\
        .eq("id", webhook_id)\
        .eq("user_id", user_id)\
        .execute()
    
    if not hasattr(response, "data") or not response.data:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    webhook = response.data[0]
    
    # Send test event
    test_payload = {
        "event": "test",
        "timestamp": datetime.now().isoformat(),
        "message": "This is a test webhook event",
        "webhook_id": webhook_id,
    }
    
    background_tasks.add_task(
        _send_webhook,
        webhook,
        EventType.SYSTEM_ALERT,
        test_payload
    )
    
    return {"status": "test_sent", "webhook_id": webhook_id}


# ── Helper Functions ─────────────────────────────────────────────────────────

def _is_private_ip(hostname: str) -> tuple[bool, str | None]:
    """Check if hostname resolves to a private/reserved IP (SSRF protection).
    Returns (is_private, resolved_ip) to prevent DNS rebinding attacks."""
    import ipaddress
    try:
        ip = ipaddress.ip_address(hostname)
        return (ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local), hostname
    except ValueError:
        import socket
        try:
            resolved = socket.getaddrinfo(hostname, None)
            for _, _, _, _, sockaddr in resolved:
                ip = ipaddress.ip_address(sockaddr[0])
                if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
                    return True, None
            # Return the first resolved IP for direct connection (prevents DNS rebinding)
            if resolved:
                first_ip = resolved[0][4][0]
                return False, first_ip
        except (socket.gaierror, OSError):
            pass
    return False, None


def _send_webhook(webhook: dict, event_type: EventType, payload: dict):
    """Send webhook with retry logic and SSRF protection."""
    import requests
    from urllib.parse import urlparse

    url = webhook["url"]
    # SSRF protection: block private/internal IPs, resolve DNS once to prevent rebinding
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        is_private, resolved_ip = _is_private_ip(hostname)
        if is_private:
            logger.warning("Webhook blocked: URL targets private/internal IP: %s", url)
            return None
        if parsed.scheme not in ("http", "https"):
            logger.warning("Webhook blocked: invalid scheme %s", parsed.scheme)
            return None
        # Use resolved IP directly to prevent DNS rebinding
        if resolved_ip and resolved_ip != hostname:
            url = url.replace(f"://{hostname}", f"://{resolved_ip}", 1)
    except Exception:
        logger.warning("Webhook URL parse failed: %s", url)
        return None

    headers = webhook.get("headers", {})
    headers["Content-Type"] = "application/json"
    
    # Add signature if secret is provided
    secret = webhook.get("secret")
    if secret:
        payload_bytes = json.dumps(payload).encode()
        signature = hmac.new(
            secret.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        headers["X-Webhook-Signature"] = signature
    
    # Send with retries
    max_attempts = webhook.get("retry_count", 3)
    timeout = webhook.get("timeout_seconds", 30)
    
    for attempt in range(max_attempts):
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=timeout
            )
            
            # Log success
            _log_webhook(webhook, event_type, payload, response.status_code, None, attempt + 1)
            
            # Update success count
            _update_webhook_stats(webhook["id"], success=True)
            
            return response
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Webhook attempt {attempt + 1} failed: {error_msg}")
            
            if attempt == max_attempts - 1:
                # Final attempt failed
                _log_webhook(webhook, event_type, payload, None, error_msg, attempt + 1)
                _update_webhook_stats(webhook["id"], success=False)


def _log_webhook(webhook: dict, event_type: EventType, payload: dict, 
                 response_status: Optional[int], error: Optional[str], attempts: int):
    """Log webhook execution."""
    supabase = get_supabase()
    
    try:
        supabase.table("webhook_logs").insert({
            "webhook_id": webhook["id"],
            "event_type": event_type.value,
            "payload": payload,
            "response_status": response_status,
            "response_body": None,
            "error": error,
            "attempts": attempts,
            "created_at": datetime.now().isoformat(),
        }).execute()
    except Exception as e:
        logger.error(f"Failed to log webhook: {e}")


def _update_webhook_stats(webhook_id: str, success: bool):
    """Update webhook success/failure counts."""
    supabase = get_supabase()
    
    try:
        current = supabase.table("webhooks").select("success_count, failure_count").eq("id", webhook_id).limit(1).execute()
        row = current.data[0] if hasattr(current, "data") and current.data else {}
        sc = int(row.get("success_count") or 0)
        fc = int(row.get("failure_count") or 0)
        if success:
            sc += 1
        else:
            fc += 1
        supabase.table("webhooks").update({
            "success_count": sc,
            "failure_count": fc,
            "last_triggered": datetime.now().isoformat(),
        }).eq("id", webhook_id).execute()
    except Exception as e:
        logger.error(f"Failed to update webhook stats: {e}")


def trigger_webhook(user_id: str, event_type: EventType, payload: dict):
    """
    Trigger all active webhooks for a user that listen to this event.
    
    This function should be called from other parts of the system.
    """
    supabase = get_supabase()
    
    try:
        # Get all active webhooks for this user
        response = supabase.table("webhooks")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("is_active", True)\
            .execute()
        
        webhooks = response.data if hasattr(response, "data") and response.data else []
        
        # Filter webhooks that listen to this event
        matching_webhooks = [
            w for w in webhooks 
            if event_type.value in w.get("events", [])
        ]
        
        # Trigger each webhook
        for webhook in matching_webhooks:
            _send_webhook(webhook, event_type, payload)
            
    except Exception as e:
        logger.error(f"Failed to trigger webhooks: {e}")