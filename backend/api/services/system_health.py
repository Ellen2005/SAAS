"""
System Health Monitoring Service
================================
Periodic health checks for all platform subsystems:
  - Database connectivity
  - AI/LLM availability
  - ETL pipeline status
  - Cache availability
  - Memory/disk usage
Stores checkpoints and provides a unified health dashboard.

Tables involved:
  system_health_checkpoints  — Periodic health check results
"""
import logging
import time
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)
UTC = timezone.utc


class SystemHealth:
    """Monitors health of all platform subsystems."""

    def __init__(self, db):
        self.db = db

    async def run_health_checks(self) -> dict:
        """Run all health checks and return results."""
        checks = {}

        # 1. Database (Supabase)
        checks["database"] = await self._check_database()

        # 2. AI/LLM (Groq)
        checks["ai_llm"] = await self._check_ai_llm()

        # 3. Cache (Redis/In-memory)
        checks["cache"] = await self._check_cache()

        # 4. ETL Pipeline
        checks["etl"] = await self._check_etl_status()

        # 5. Disk usage
        checks["disk"] = await self._check_disk()

        # 6. Memory
        checks["memory"] = await self._check_memory()

        # Compute overall status
        statuses = [c.get("status", "unknown") for c in checks.values()]
        if "down" in statuses:
            overall = "degraded"
        elif "warning" in statuses:
            overall = "warning"
        else:
            overall = "healthy"

        result = {
            "overall": overall,
            "checks": checks,
            "checked_at": datetime.now(UTC).isoformat(),
        }

        # Store checkpoint
        await self._store_checkpoint(result)

        return result

    async def get_health_dashboard(self, hours: int = 24) -> dict:
        """Get health dashboard with recent checkpoints."""
        since = (datetime.now(UTC) - timedelta(hours=hours)).isoformat()
        try:
            result = (
                self.db.table("system_health_checkpoints")
                .select("*")
                .gte("checked_at", since)
                .order("checked_at", desc=True)
                .limit(100)
                .execute()
            )
            checkpoints = result.data if hasattr(result, "data") else []
        except Exception:
            checkpoints = []

        # Compute uptime per subsystem
        subsystem_uptime = {}
        for cp in checkpoints:
            for name, check in (cp.get("checks") or {}).items():
                if name not in subsystem_uptime:
                    subsystem_uptime[name] = {"total": 0, "healthy": 0, "degraded": 0, "down": 0}
                subsystem_uptime[name]["total"] += 1
                status = check.get("status", "unknown")
                if status in subsystem_uptime[name]:
                    subsystem_uptime[name][status] += 1

        uptime_pct = {}
        for name, stats in subsystem_uptime.items():
            total = stats["total"]
            uptime_pct[name] = round(stats["healthy"] / total * 100, 1) if total > 0 else 0

        # Latest check
        latest = checkpoints[0] if checkpoints else None

        return {
            "latest": latest,
            "uptime_pct": uptime_pct,
            "checkpoint_count": len(checkpoints),
            "period_hours": hours,
        }

    async def _check_database(self) -> dict:
        """Check Supabase database connectivity."""
        try:
            start = time.time()
            result = self.db.table("kpi_results").select("id").limit(1).execute()
            latency_ms = int((time.time() - start) * 1000)
            has_data = bool(result.data if hasattr(result, "data") else [])
            return {
                "status": "healthy" if latency_ms < 2000 else "warning",
                "latency_ms": latency_ms,
                "message": "Database responsive" if has_data else "Database connected but no data",
            }
        except Exception as e:
            return {"status": "down", "message": f"Database error: {str(e)[:120]}"}

    async def _check_ai_llm(self) -> dict:
        """Check Groq LLM API availability."""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return {"status": "warning", "message": "GROQ_API_KEY not configured"}
        try:
            from .groq_utils import execute_groq_completion
            start = time.time()
            result = execute_groq_completion(
                messages=[{"role": "user", "content": "Reply with: ok"}],
                temperature=0.1,
                max_tokens=5,
            )
            latency_ms = int((time.time() - start) * 1000)
            content = result.choices[0].message.content if result else ""
            return {
                "status": "healthy" if latency_ms < 5000 else "warning",
                "latency_ms": latency_ms,
                "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                "message": f"LLM responding ({latency_ms}ms)",
            }
        except Exception as e:
            return {"status": "down", "message": f"LLM error: {str(e)[:120]}"}

    async def _check_cache(self) -> dict:
        """Check cache availability."""
        try:
            from .cache_service import get_cached, set_cached
            test_key = "_health_check_test"
            set_cached(test_key, {"ts": time.time()}, ttl=10)
            val = get_cached(test_key)
            if val:
                return {"status": "healthy", "message": "Cache operational (in-memory)"}
            return {"status": "warning", "message": "Cache test failed, using fallback"}
        except Exception as e:
            return {"status": "warning", "message": f"Cache check failed: {str(e)[:80]}"}

    async def _check_etl_status(self) -> dict:
        """Check ETL pipeline status."""
        try:
            result = (
                self.db.table("user_preferences")
                .select("last_sync_status")
                .order("updated_at", desc=True)
                .limit(10)
                .execute()
            )
            rows = result.data if hasattr(result, "data") else []
            statuses = [r.get("last_sync_status", "IDLE") for r in rows]
            running = sum(1 for s in statuses if s in ("FETCHING_DATA", "RUNNING_ETL"))
            failed = sum(1 for s in statuses if s and "ERROR" in s.upper())
            if running > 0:
                return {"status": "healthy", "message": f"{running} ETL job(s) running", "running": running}
            elif failed > 0:
                return {"status": "warning", "message": f"{failed} recent ETL failure(s)", "failed": failed}
            return {"status": "healthy", "message": "ETL pipeline idle"}
        except Exception as e:
            return {"status": "warning", "message": f"ETL check failed: {str(e)[:80]}"}

    async def _check_disk(self) -> dict:
        """Check disk usage."""
        try:
            stat = os.statvfs("/") if hasattr(os, "statvfs") else None
            if stat:
                total = stat.f_blocks * stat.f_frsize
                free = stat.f_bavail * stat.f_frsize
                used_pct = round((1 - free / total) * 100, 1) if total > 0 else 0
                status = "healthy" if used_pct < 85 else "warning" if used_pct < 95 else "down"
                return {"status": status, "used_pct": used_pct, "message": f"Disk {used_pct}% used"}
            return {"status": "healthy", "message": "Disk check not available on this platform"}
        except Exception:
            return {"status": "healthy", "message": "Disk check skipped"}

    async def _check_memory(self) -> dict:
        """Check memory usage."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            used_pct = mem.percent
            status = "healthy" if used_pct < 80 else "warning" if used_pct < 95 else "down"
            return {"status": status, "used_pct": used_pct, "message": f"Memory {used_pct}% used"}
        except ImportError:
            return {"status": "healthy", "message": "Memory check not available (psutil not installed)"}
        except Exception:
            return {"status": "healthy", "message": "Memory check skipped"}

    async def _store_checkpoint(self, result: dict) -> None:
        """Store health checkpoint (non-critical)."""
        try:
            self.db.table("system_health_checkpoints").insert({
                "overall": result["overall"],
                "checks": result["checks"],
                "checked_at": result["checked_at"],
            }).execute()
        except Exception as e:
            logger.warning(f"Health checkpoint storage failed: {e}")
