"""
AI Monitoring Service
=====================
Collects and reports AI system metrics.
Provides data for the admin monitoring dashboard.
"""
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)
UTC = timezone.utc


class AIMonitor:
    """Collects and reports AI system metrics."""

    def __init__(self, db):
        self.db = db

    async def record_metric(self, event_type: str, **kwargs) -> None:
        """Record a metric event. Non-critical — failures are silently ignored."""
        metric = {
            "event_type": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": kwargs,
        }
        try:
            self.db.table("ai_metrics").insert(metric).execute()
        except Exception:
            pass

    async def get_dashboard_metrics(self, days: int = 7) -> dict:
        """Get metrics for the monitoring dashboard."""
        since = (datetime.now(UTC) - timedelta(days=days)).isoformat()

        # Primary source: governance log (more complete)
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
            return self._empty_metrics(days)

        # Latency
        latencies = sorted([l.get("latency_ms", 0) or 0 for l in logs])
        p95_idx = int(len(latencies) * 0.95)
        p99_idx = int(len(latencies) * 0.99)

        # Daily breakdown
        daily = {}
        for l in logs:
            day = l.get("created_at", "")[:10]
            if day not in daily:
                daily[day] = {"requests": 0, "errors": 0, "tokens": 0}
            daily[day]["requests"] += 1
            if l.get("status") == "error":
                daily[day]["errors"] += 1
            daily[day]["tokens"] += l.get("tokens_total", 0) or 0

        # Error distribution
        error_dist = {}
        for l in logs:
            if l.get("status") == "error":
                err = (l.get("error_message", "unknown") or "unknown")[:80]
                error_dist[err] = error_dist.get(err, 0) + 1

        # Cost estimation ($0.59/1M tokens for llama-3.3-70b)
        total_tokens = sum(l.get("tokens_total", 0) or 0 for l in logs)
        estimated_cost = total_tokens * 0.59 / 1_000_000

        # Confidence
        confidences = [l.get("confidence_score", 0) or 0 for l in logs]

        return {
            "period_days": days,
            "total_requests": total,
            "avg_latency_ms": round(sum(latencies) / len(latencies)) if latencies else 0,
            "p95_latency_ms": latencies[p95_idx] if latencies else 0,
            "p99_latency_ms": latencies[p99_idx] if latencies else 0,
            "success_rate": round(
                sum(1 for l in logs if l.get("status") == "success") / total * 100, 1
            ),
            "error_rate": round(
                sum(1 for l in logs if l.get("status") == "error") / total * 100, 1
            ),
            "retry_count": sum(1 for l in logs if l.get("status") == "retry"),
            "timeout_count": sum(1 for l in logs if l.get("status") == "timeout"),
            "total_tokens": total_tokens,
            "estimated_cost_usd": round(estimated_cost, 4),
            "daily": daily,
            "error_distribution": error_dist,
            "avg_confidence": round(
                sum(confidences) / len(confidences), 3
            ) if confidences else 0,
        }

    def _empty_metrics(self, days: int) -> dict:
        return {
            "period_days": days,
            "total_requests": 0,
            "avg_latency_ms": 0,
            "p95_latency_ms": 0,
            "p99_latency_ms": 0,
            "success_rate": 100.0,
            "error_rate": 0.0,
            "retry_count": 0,
            "timeout_count": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0,
            "daily": {},
            "error_distribution": {},
            "avg_confidence": 0,
        }
