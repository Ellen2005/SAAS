from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from ..core.auth import require_role, resolve_user_id
from ..core.supabase_client import get_supabase

router = APIRouter(prefix="/api", tags=["validation"])


def _safe_data(response) -> list:
    return response.data if hasattr(response, "data") and response.data else []


@router.get("/validation/logs")
def get_validation_logs(
    limit: int = 50,
    user_id: str = Depends(resolve_user_id),
):
    supabase = get_supabase()
    try:
        rows = _safe_data(
            supabase.table("validation_logs")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return {"logs": rows, "requested_by": user_id}
    except Exception as error:
        return {"logs": [], "error": str(error)}


@router.get("/admin/validation/scorecard")
def get_validation_scorecard(context: dict = Depends(require_role(["admin"]))):
    supabase = get_supabase()
    try:
        departments = _safe_data(supabase.table("departments").select("id, name").execute())
        scorecard = []

        for department in departments:
            logs = _safe_data(
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
    except Exception as error:
        return {"scorecard": [], "error": str(error)}


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

        rows = _safe_data(query.execute())
        logs = []
        for row in rows:
            department_name = None
            if row.get("departments"):
                department_name = row["departments"].get("name")
            logs.append({**row, "department_name": department_name})

        return {"logs": logs, "requested_by": context["user_id"]}
    except Exception as error:
        return {"logs": [], "error": str(error)}
