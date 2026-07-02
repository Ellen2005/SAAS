"""
AI Feedback Loop Service
========================
Collects user feedback on AI-generated content (thumbs up/down, comments),
tracks feedback trends, and feeds into prompt optimization and quality scoring.

Tables involved:
  ai_feedback          — Individual feedback records
  ai_feedback_summary  — Aggregated feedback stats per prompt/category
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)
UTC = timezone.utc


class AIFeedbackLoop:
    """Collects and analyzes user feedback on AI outputs."""

    def __init__(self, db):
        self.db = db

    async def submit_feedback(
        self,
        *,
        request_id: str,
        user_id: Optional[str] = None,
        rating: int,
        category: Optional[str] = None,
        prompt_name: Optional[str] = None,
        comment: Optional[str] = None,
        response_preview: Optional[str] = None,
    ) -> dict:
        """
        Submit feedback for an AI response.
        rating: 1 (thumbs down) or 5 (thumbs up) — or any 1-5 scale.
        """
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")

        record = {
            "request_id": request_id,
            "user_id": user_id,
            "rating": rating,
            "category": category,
            "prompt_name": prompt_name,
            "comment": comment,
            "response_preview": (response_preview or "")[:500],
            "created_at": datetime.now(UTC).isoformat(),
        }

        try:
            result = self.db.table("ai_feedback").insert(record).execute()
            rows = result.data if hasattr(result, "data") else []
            await self._refresh_summary(category, prompt_name)
            return rows[0] if rows else record
        except Exception as e:
            logger.warning(f"Feedback write failed: {e}")
            return record

    async def get_feedback_list(
        self,
        *,
        category: Optional[str] = None,
        min_rating: Optional[int] = None,
        max_rating: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list:
        """Get feedback records with optional filters."""
        try:
            query = self.db.table("ai_feedback").select("*")
            if category:
                query = query.eq("category", category)
            if min_rating is not None:
                query = query.gte("rating", min_rating)
            if max_rating is not None:
                query = query.lte("rating", max_rating)
            result = (
                query
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            return result.data if hasattr(result, "data") else []
        except Exception as e:
            logger.warning(f"Feedback list failed: {e}")
            return []

    async def get_feedback_summary(self, days: int = 30) -> dict:
        """Get aggregated feedback statistics."""
        since = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        try:
            result = (
                self.db.table("ai_feedback")
                .select("*")
                .gte("created_at", since)
                .execute()
            )
            logs = result.data if hasattr(result, "data") else []
        except Exception as e:
            logger.debug(f"Failed to fetch feedback logs: {e}")
            logs = []

        total = len(logs)
        if total == 0:
            return {"total_feedback": 0, "period_days": days, "by_category": {}}

        avg_rating = sum(l.get("rating", 3) for l in logs) / total
        thumbs_up = sum(1 for l in logs if l.get("rating", 0) >= 4)
        thumbs_down = sum(1 for l in logs if l.get("rating", 0) <= 2)

        by_category = {}
        for l in logs:
            cat = l.get("category", "unknown")
            if cat not in by_category:
                by_category[cat] = {"count": 0, "total_rating": 0, "thumbs_up": 0, "thumbs_down": 0}
            by_category[cat]["count"] += 1
            by_category[cat]["total_rating"] += l.get("rating", 3)
            if l.get("rating", 0) >= 4:
                by_category[cat]["thumbs_up"] += 1
            elif l.get("rating", 0) <= 2:
                by_category[cat]["thumbs_down"] += 1

        for cat in by_category:
            c = by_category[cat]
            c["avg_rating"] = round(c["total_rating"] / c["count"], 2) if c["count"] else 0
            del c["total_rating"]

        return {
            "total_feedback": total,
            "avg_rating": round(avg_rating, 2),
            "thumbs_up": thumbs_up,
            "thumbs_down": thumbs_down,
            "satisfaction_rate": round(thumbs_up / total * 100, 1) if total else 0,
            "by_category": by_category,
            "recent_comments": [
                {"rating": l.get("rating"), "comment": l.get("comment"), "category": l.get("category")}
                for l in logs if l.get("comment")
            ][:10],
            "period_days": days,
        }

    async def get_low_rated_feedback(self, threshold: int = 2, limit: int = 20) -> list:
        """Get feedback with low ratings for prompt improvement."""
        try:
            result = (
                self.db.table("ai_feedback")
                .select("*")
                .lte("rating", threshold)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data if hasattr(result, "data") else []
        except Exception as e:
            logger.debug(f"Failed to fetch recent feedback logs: {e}")
            return []

    async def _refresh_summary(self, category: Optional[str], prompt_name: Optional[str]) -> None:
        """Refresh the summary materialized view (non-critical)."""
        try:
            since = (datetime.now(UTC) - timedelta(days=30)).isoformat()
            query = self.db.table("ai_feedback").select("rating").gte("created_at", since)
            if category:
                query = query.eq("category", category)
            result = query.execute()
            ratings = [r.get("rating", 3) for r in (result.data if hasattr(result, "data") else [])]
            if ratings:
                summary = {
                    "category": category,
                    "prompt_name": prompt_name,
                    "avg_rating": round(sum(ratings) / len(ratings), 2),
                    "count": len(ratings),
                    "updated_at": datetime.now(UTC).isoformat(),
                }
                self.db.table("ai_feedback_summary").upsert(summary, on_conflict="category,prompt_name").execute()
        except Exception as e:
            logger.warning(f"Failed to update feedback summary: {e}")
