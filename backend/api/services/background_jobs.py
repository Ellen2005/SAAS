"""
Background Job Center
=====================
Manages long-running AI and data tasks (ETL, report generation, batch analysis).
Provides job tracking, status updates, and admin visibility.

Tables involved:
  background_jobs  — Job definitions and status
  job_logs         — Per-step execution logs
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)
UTC = timezone.utc


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BackgroundJobCenter:
    """Manages background job execution and tracking."""

    def __init__(self, db):
        self.db = db

    async def create_job(
        self,
        *,
        job_type: str,
        name: str,
        payload: Optional[dict] = None,
        created_by: Optional[str] = None,
        priority: int = 0,
    ) -> dict:
        """Create a new background job."""
        job_id = str(uuid.uuid4())[:12]
        record = {
            "job_id": job_id,
            "job_type": job_type,
            "name": name,
            "status": JobStatus.PENDING,
            "payload": payload or {},
            "created_by": created_by,
            "priority": priority,
            "progress_pct": 0,
            "result": None,
            "error": None,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "started_at": None,
            "completed_at": None,
        }
        try:
            result = self.db.table("background_jobs").insert(record).execute()
            rows = result.data if hasattr(result, "data") else []
            return rows[0] if rows else record
        except Exception as e:
            logger.warning(f"Job create failed: {e}")
            return record

    async def update_job(
        self,
        job_id: str,
        *,
        status: Optional[str] = None,
        progress_pct: Optional[int] = None,
        result: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> dict:
        """Update job status/progress."""
        update = {"updated_at": datetime.now(UTC).isoformat()}
        if status:
            update["status"] = status
            if status == JobStatus.RUNNING:
                update["started_at"] = datetime.now(UTC).isoformat()
            elif status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                update["completed_at"] = datetime.now(UTC).isoformat()
        if progress_pct is not None:
            update["progress_pct"] = min(100, max(0, progress_pct))
        if result is not None:
            update["result"] = result
        if error is not None:
            update["error"] = error[:1000]

        try:
            self.db.table("background_jobs").update(update).eq("job_id", job_id).execute()
        except Exception as e:
            logger.warning(f"Job update failed: {e}")
        return update

    async def log_step(self, job_id: str, step: str, status: str, detail: Optional[str] = None) -> None:
        """Log a job execution step."""
        record = {
            "job_id": job_id,
            "step": step,
            "status": status,
            "detail": (detail or "")[:500],
            "timestamp": datetime.now(UTC).isoformat(),
        }
        try:
            self.db.table("job_logs").insert(record).execute()
        except Exception:
            pass

    async def get_job(self, job_id: str) -> Optional[dict]:
        """Get a single job by ID."""
        try:
            result = (
                self.db.table("background_jobs")
                .select("*")
                .eq("job_id", job_id)
                .limit(1)
                .execute()
            )
            rows = result.data if hasattr(result, "data") else []
            return rows[0] if rows else None
        except Exception:
            return None

    async def get_jobs(
        self,
        *,
        job_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list:
        """List jobs with optional filters."""
        try:
            query = self.db.table("background_jobs").select("*")
            if job_type:
                query = query.eq("job_type", job_type)
            if status:
                query = query.eq("status", status)
            result = (
                query
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            return result.data if hasattr(result, "data") else []
        except Exception as e:
            logger.warning(f"Job list failed: {e}")
            return []

    async def get_job_logs(self, job_id: str) -> list:
        """Get execution logs for a job."""
        try:
            result = (
                self.db.table("job_logs")
                .select("*")
                .eq("job_id", job_id)
                .order("timestamp")
                .execute()
            )
            return result.data if hasattr(result, "data") else []
        except Exception:
            return []

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending or running job."""
        try:
            job = await self.get_job(job_id)
            if not job:
                return False
            if job["status"] in (JobStatus.COMPLETED, JobStatus.CANCELLED):
                return False
            await self.update_job(job_id, status=JobStatus.CANCELLED)
            await self.log_step(job_id, "cancel", "cancelled", "Job cancelled by user")
            return True
        except Exception:
            return False

    async def get_dashboard(self, days: int = 7) -> dict:
        """Get job center dashboard metrics."""
        try:
            from datetime import timedelta
            since = (datetime.now(UTC) - timedelta(days=days)).isoformat()
            result = (
                self.db.table("background_jobs")
                .select("*")
                .gte("created_at", since)
                .execute()
            )
            jobs = result.data if hasattr(result, "data") else []
        except Exception:
            jobs = []

        total = len(jobs)
        by_status = {}
        by_type = {}
        for j in jobs:
            s = j.get("status", "unknown")
            by_status[s] = by_status.get(s, 0) + 1
            t = j.get("job_type", "unknown")
            if t not in by_type:
                by_type[t] = {"count": 0, "completed": 0, "failed": 0}
            by_type[t]["count"] += 1
            if s == JobStatus.COMPLETED:
                by_type[t]["completed"] += 1
            elif s == JobStatus.FAILED:
                by_type[t]["failed"] += 1

        return {
            "total_jobs": total,
            "by_status": by_status,
            "by_type": by_type,
            "period_days": days,
        }
