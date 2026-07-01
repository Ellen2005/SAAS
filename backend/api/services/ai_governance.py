"""
AI Governance Service
=====================
Tracks every AI request with full metadata for auditability.
Every LLM call in the system should be logged through this service.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)
UTC = timezone.utc


class AIGovernance:
    """Tracks and governs all AI interactions."""

    def __init__(self, db):
        self.db = db

    async def log_request(
        self,
        *,
        request_id: str,
        user_id: Optional[str] = None,
        category: str,
        intent: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tokens_used: Optional[dict] = None,
        latency_ms: Optional[int] = None,
        confidence: Optional[float] = None,
        safety_status: str = "safe",
        prompt_version: Optional[str] = None,
        status: str = "success",
        error: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """Log an AI request for governance."""
        record = {
            "request_id": request_id,
            "user_id": user_id,
            "category": category,
            "intent": intent,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "tokens_input": tokens_used.get("prompt_tokens") if tokens_used else None,
            "tokens_output": tokens_used.get("completion_tokens") if tokens_used else None,
            "tokens_total": tokens_used.get("total_tokens") if tokens_used else None,
            "latency_ms": latency_ms,
            "confidence_score": confidence,
            "safety_status": safety_status,
            "prompt_version": prompt_version,
            "status": status,
            "error_message": error,
            "ip_address": ip_address,
            "created_at": datetime.now(UTC).isoformat(),
        }
        try:
            self.db.table("ai_governance_log").insert(record).execute()
        except Exception as e:
            logger.warning(f"Governance log write failed (non-critical): {e}")

    async def get_model_config(self, category: str) -> dict:
        """Get governance-approved model configuration per category."""
        defaults = {
            "nlq": {"model": "llama-3.3-70b-versatile", "temperature": 0.1, "max_tokens": 800},
            "narrative": {"model": "llama-3.3-70b-versatile", "temperature": 0.4, "max_tokens": 1000},
            "analyst": {"model": "llama-3.3-70b-versatile", "temperature": 0.3, "max_tokens": 600},
            "report": {"model": "llama-3.3-70b-versatile", "temperature": 0.5, "max_tokens": 1200},
            "forecast": {"model": "llama-3.3-70b-versatile", "temperature": 0.4, "max_tokens": 400},
            "assistant": {"model": "llama-3.1-8b-instant", "temperature": 0.4, "max_tokens": 400},
            "recommendation": {"model": "llama-3.3-70b-versatile", "temperature": 0.3, "max_tokens": 600},
        }
        return defaults.get(category, defaults["narrative"])

    async def get_governance_dashboard(self, days: int = 30) -> dict:
        """Get governance metrics for admin dashboard."""
        since = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        try:
            result = (
                self.db.table("ai_governance_log")
                .select("*")
                .gte("created_at", since)
                .execute()
            )
            logs = result.data if hasattr(result, "data") else []
        except Exception:
            logs = []

        total = len(logs)
        if total == 0:
            return {"total_requests": 0, "period_days": days}

        success = sum(1 for l in logs if l.get("status") == "success")
        errors = sum(1 for l in logs if l.get("status") == "error")
        latencies = [l.get("latency_ms", 0) or 0 for l in logs]
        total_tokens = sum(l.get("tokens_total", 0) or 0 for l in logs)
        confidences = [l.get("confidence_score", 0) or 0 for l in logs]

        by_category = {}
        for l in logs:
            cat = l.get("category", "unknown")
            if cat not in by_category:
                by_category[cat] = {"count": 0, "errors": 0, "total_latency": 0}
            by_category[cat]["count"] += 1
            if l.get("status") == "error":
                by_category[cat]["errors"] += 1
            by_category[cat]["total_latency"] += l.get("latency_ms", 0) or 0

        return {
            "total_requests": total,
            "success_rate": round(success / total * 100, 1),
            "error_rate": round(errors / total * 100, 1),
            "avg_latency_ms": round(sum(latencies) / len(latencies)) if latencies else 0,
            "total_tokens": total_tokens,
            "avg_confidence": round(sum(confidences) / len(confidences), 3) if confidences else 0,
            "by_category": by_category,
            "period_days": days,
        }
