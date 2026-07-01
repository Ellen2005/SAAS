import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from ..core.auth import require_role, resolve_user_id
from ..core.supabase_client import get_supabase
from ..core.utils import safe_data

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["validation"])


@router.get("/validation/logs")
def get_validation_logs(
    limit: int = 50,
    user_id: str = Depends(resolve_user_id),
):
    supabase = get_supabase()
    try:
        rows = safe_data(
            supabase.table("validation_logs")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return {"logs": rows, "requested_by": user_id}
    except Exception:
        logger.error("Get validation logs failed", exc_info=True)
        return {"logs": [], "error": "Failed to fetch validation logs."}


@router.get("/admin/validation/scorecard")
def get_validation_scorecard(context: dict = Depends(require_role(["admin"]))):
    supabase = get_supabase()
    try:
        departments = safe_data(supabase.table("departments").select("id, name").execute())
        scorecard = []

        for department in departments:
            logs = safe_data(
                supabase.table("validation_logs")
                .select("check_type, status, message, created_at")
                .eq("department_id", department["id"])
                .order("created_at", desc=True)
                .limit(20)
                .execute()
            )

            latest_by_type = {}
            for log in logs:
                latest_by_type.setdefault(log["check_type"], log)

            if latest_by_type:
                scores = []
                checks = {}
                for check_type, log in latest_by_type.items():
                    score = 100 if log["status"] == "pass" else (70 if log["status"] == "warning" else 0)
                    scores.append(score)
                    checks[check_type] = log["status"]
                average = round(sum(scores) / len(scores))
            else:
                average = -1
                checks = {}

            scorecard.append(
                {
                    "department_id": department["id"],
                    "department_name": department["name"],
                    "score": average,
                    "checks": checks,
                    "last_validation": logs[0]["created_at"] if logs else None,
                }
            )

        return {"scorecard": scorecard, "requested_by": context["user_id"]}
    except Exception:
        logger.error("Get validation scorecard failed", exc_info=True)
        return {"scorecard": [], "error": "Failed to generate scorecard."}


@router.get("/admin/validation/logs")
def get_all_validation_logs(
    limit: int = 100,
    department_id: Optional[str] = None,
    context: dict = Depends(require_role(["admin"])),
):
    supabase = get_supabase()
    try:
        query = (
            supabase.table("validation_logs")
            .select("*, departments(name)")
            .order("created_at", desc=True)
            .limit(limit)
        )
        if department_id:
            query = query.eq("department_id", department_id)

        rows = safe_data(query.execute())
        logs = []
        for row in rows:
            department_name = None
            if row.get("departments"):
                department_name = row["departments"].get("name")
            logs.append({**row, "department_name": department_name})

        return {"logs": logs, "requested_by": context["user_id"]}
    except Exception:
        logger.error("Get all validation logs failed", exc_info=True)
        return {"logs": [], "error": "Failed to fetch validation logs."}
