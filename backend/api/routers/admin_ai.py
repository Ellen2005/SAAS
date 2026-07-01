"""
Admin AI Router
===============
Centralized admin endpoints for AI Governance, Monitoring, Prompt Library,
Feedback, and Background Jobs.

All endpoints require admin role.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from ..core.auth import require_role
from ..core.supabase_client import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/ai", tags=["admin-ai"])


# ── Request/Response Models ────────────────────────────────────────────────

class PromptCreate(BaseModel):
    name: str
    category: str
    template: str
    variables: Optional[list] = None
    description: Optional[str] = None


class PromptUpdate(BaseModel):
    template: str
    variables: Optional[list] = None
    changelog: Optional[str] = None


class FeedbackSubmit(BaseModel):
    request_id: str
    rating: int
    category: Optional[str] = None
    prompt_name: Optional[str] = None
    comment: Optional[str] = None
    response_preview: Optional[str] = None


# ── Dependency: get Supabase client ────────────────────────────────────────

def _get_db():
    return get_supabase()


# ══════════════════════════════════════════════════════════════════════════
#  GOVERNANCE
# ══════════════════════════════════════════════════════════════════════════

@router.get("/governance")
async def get_governance_dashboard(
    days: int = Query(30, ge=1, le=365),
    _admin=Depends(require_role(["admin"])),
):
    """AI Governance dashboard — request counts, success rates, safety flags."""
    from ..services.ai_governance import AIGovernance
    db = _get_db()
    gov = AIGovernance(db)
    return await gov.get_governance_dashboard(days=days)


@router.get("/governance/config")
async def get_governance_config(
    _admin=Depends(require_role(["admin"])),
):
    """Get per-category governance model configs."""
    from ..services.ai_governance import AIGovernance
    gov = AIGovernance(_get_db())
    categories = ["nlq", "narrative", "analyst", "report", "forecast", "assistant", "recommendation"]
    configs = {}
    for cat in categories:
        configs[cat] = await gov.get_model_config(cat)
    return {"configs": configs}


# ══════════════════════════════════════════════════════════════════════════
#  MONITORING
# ══════════════════════════════════════════════════════════════════════════

@router.get("/monitoring")
async def get_monitoring_dashboard(
    days: int = Query(7, ge=1, le=90),
    _admin=Depends(require_role(["admin"])),
):
    """AI Monitoring dashboard — latency, tokens, cost, errors."""
    from ..services.ai_monitor import AIMonitor
    db = _get_db()
    monitor = AIMonitor(db)
    return await monitor.get_dashboard_metrics(days=days)


# ══════════════════════════════════════════════════════════════════════════
#  PROMPT LIBRARY
# ══════════════════════════════════════════════════════════════════════════

@router.get("/prompts")
async def list_prompts(
    category: Optional[str] = Query(None),
    _admin=Depends(require_role(["admin"])),
):
    """List all prompt templates, optionally filtered by category."""
    from ..services.prompt_manager import PromptManager
    db = _get_db()
    pm = PromptManager(db)
    prompts = await pm.list_prompts(category=category)
    return {"prompts": prompts, "total": len(prompts)}


@router.get("/prompts/{prompt_id}")
async def get_prompt(
    prompt_id: str,
    _admin=Depends(require_role(["admin"])),
):
    """Get a single prompt template by ID."""
    from ..services.prompt_manager import PromptManager
    db = _get_db()
    pm = PromptManager(db)
    try:
        result = db.table("prompt_templates").select("*").eq("id", prompt_id).limit(1).execute()
        rows = result.data if hasattr(result, "data") else []
        if not rows:
            raise HTTPException(status_code=404, detail="Prompt not found")
        return rows[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get prompt failed", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.post("/prompts")
async def create_prompt(
    body: PromptCreate,
    _admin=Depends(require_role(["admin"])),
):
    """Create a new prompt template."""
    from ..services.prompt_manager import PromptManager
    db = _get_db()
    pm = PromptManager(db)
    prompt = await pm.create_prompt(
        name=body.name,
        category=body.category,
        template=body.template,
        variables=body.variables,
        description=body.description,
    )
    return {"prompt": prompt}


@router.put("/prompts/{prompt_id}")
async def update_prompt(
    prompt_id: str,
    body: PromptUpdate,
    _admin=Depends(require_role(["admin"])),
):
    """Update a prompt template (creates new version)."""
    from ..services.prompt_manager import PromptManager
    db = _get_db()
    pm = PromptManager(db)
    try:
        prompt = await pm.update_prompt(
            prompt_id,
            template=body.template,
            variables=body.variables,
            changelog=body.changelog,
        )
        return {"prompt": prompt}
    except ValueError:
        raise HTTPException(status_code=404, detail="Prompt not found.")


@router.get("/prompts/{prompt_id}/versions")
async def get_prompt_versions(
    prompt_id: str,
    _admin=Depends(require_role(["admin"])),
):
    """Get version history for a prompt."""
    from ..services.prompt_manager import PromptManager
    db = _get_db()
    pm = PromptManager(db)
    versions = await pm.get_versions(prompt_id)
    return {"versions": versions, "total": len(versions)}


@router.post("/prompts/{prompt_id}/rollback")
async def rollback_prompt(
    prompt_id: str,
    version: int,
    _admin=Depends(require_role(["admin"])),
):
    """Rollback a prompt to a specific version."""
    from ..services.prompt_manager import PromptManager
    db = _get_db()
    pm = PromptManager(db)
    try:
        prompt = await pm.rollback(prompt_id, version)
        return {"prompt": prompt}
    except ValueError:
        raise HTTPException(status_code=404, detail="Prompt not found or version invalid.")


# ══════════════════════════════════════════════════════════════════════════
#  FEEDBACK
# ══════════════════════════════════════════════════════════════════════════

@router.post("/feedback")
async def submit_feedback(
    body: FeedbackSubmit,
    request: Request,
):
    """Submit feedback on an AI response (any authenticated user)."""
    from ..services.ai_feedback import AIFeedbackLoop
    from ..core.auth import resolve_user_id
    db = _get_db()
    user_id = resolve_user_id(request)
    fb = AIFeedbackLoop(db)
    result = await fb.submit_feedback(
        request_id=body.request_id,
        user_id=user_id,
        rating=body.rating,
        category=body.category,
        prompt_name=body.prompt_name,
        comment=body.comment,
        response_preview=body.response_preview,
    )
    return {"feedback": result}


@router.get("/feedback")
async def list_feedback(
    category: Optional[str] = Query(None),
    min_rating: Optional[int] = Query(None, ge=1, le=5),
    max_rating: Optional[int] = Query(None, ge=1, le=5),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _admin=Depends(require_role(["admin"])),
):
    """List feedback records (admin only)."""
    from ..services.ai_feedback import AIFeedbackLoop
    db = _get_db()
    fb = AIFeedbackLoop(db)
    records = await fb.get_feedback_list(
        category=category,
        min_rating=min_rating,
        max_rating=max_rating,
        limit=limit,
        offset=offset,
    )
    return {"feedback": records, "total": len(records)}


@router.get("/feedback/summary")
async def get_feedback_summary(
    days: int = Query(30, ge=1, le=365),
    _admin=Depends(require_role(["admin"])),
):
    """Aggregated feedback statistics."""
    from ..services.ai_feedback import AIFeedbackLoop
    db = _get_db()
    fb = AIFeedbackLoop(db)
    return await fb.get_feedback_summary(days=days)


@router.get("/feedback/low-rated")
async def get_low_rated_feedback(
    threshold: int = Query(2, ge=1, le=5),
    limit: int = Query(20, ge=1, le=100),
    _admin=Depends(require_role(["admin"])),
):
    """Get low-rated feedback for prompt improvement."""
    from ..services.ai_feedback import AIFeedbackLoop
    db = _get_db()
    fb = AIFeedbackLoop(db)
    records = await fb.get_low_rated_feedback(threshold=threshold, limit=limit)
    return {"feedback": records, "total": len(records)}


# ══════════════════════════════════════════════════════════════════════════
#  BACKGROUND JOBS
# ══════════════════════════════════════════════════════════════════════════

@router.get("/jobs")
async def list_jobs(
    job_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _admin=Depends(require_role(["admin"])),
):
    """List background jobs."""
    from ..services.background_jobs import BackgroundJobCenter
    db = _get_db()
    jc = BackgroundJobCenter(db)
    jobs = await jc.get_jobs(job_type=job_type, status=status, limit=limit, offset=offset)
    return {"jobs": jobs, "total": len(jobs)}


@router.get("/jobs/dashboard")
async def get_jobs_dashboard(
    days: int = Query(7, ge=1, le=90),
    _admin=Depends(require_role(["admin"])),
):
    """Job center dashboard metrics."""
    from ..services.background_jobs import BackgroundJobCenter
    db = _get_db()
    jc = BackgroundJobCenter(db)
    return await jc.get_dashboard(days=days)


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: str,
    _admin=Depends(require_role(["admin"])),
):
    """Get a single job with its logs."""
    from ..services.background_jobs import BackgroundJobCenter
    db = _get_db()
    jc = BackgroundJobCenter(db)
    job = await jc.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    logs = await jc.get_job_logs(job_id)
    return {"job": job, "logs": logs}


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    _admin=Depends(require_role(["admin"])),
):
    """Cancel a pending or running job."""
    from ..services.background_jobs import BackgroundJobCenter
    db = _get_db()
    jc = BackgroundJobCenter(db)
    success = await jc.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")
    return {"cancelled": True}


# ══════════════════════════════════════════════════════════════════════════
#  SYSTEM HEALTH
# ══════════════════════════════════════════════════════════════════════════

@router.get("/health")
async def run_health_checks(
    _admin=Depends(require_role(["admin"])),
):
    """Run live health checks on all subsystems."""
    from ..services.system_health import SystemHealth
    db = _get_db()
    health = SystemHealth(db)
    return await health.run_health_checks()


@router.get("/health/dashboard")
async def get_health_dashboard(
    hours: int = Query(24, ge=1, le=168),
    _admin=Depends(require_role(["admin"])),
):
    """Get health dashboard with uptime stats."""
    from ..services.system_health import SystemHealth
    db = _get_db()
    health = SystemHealth(db)
    return await health.get_health_dashboard(hours=hours)


# ══════════════════════════════════════════════════════════════════════════
#  DATA QUALITY (Admin view)
# ══════════════════════════════════════════════════════════════════════════

@router.get("/data-quality/overview")
async def get_data_quality_overview(
    _admin=Depends(require_role(["admin"])),
):
    """Aggregate data quality scores across all departments."""
    db = _get_db()
    try:
        result = db.table("departments").select("id, name").execute()
        departments = result.data if hasattr(result, "data") else []
    except Exception:
        departments = []

    dept_scores = []
    for dept in departments:
        try:
            kpi_result = (
                db.table("kpi_results")
                .select("value, recorded_at")
                .eq("department_id", dept["id"])
                .limit(200)
                .execute()
            )
            rows = kpi_result.data if hasattr(kpi_result, "data") else []
            if not rows:
                dept_scores.append({"department_id": dept["id"], "department_name": dept["name"], "score": 0, "grade": "N/A"})
                continue

            # Quick quality score
            total = len(rows)
            missing = sum(1 for r in rows if r.get("value") is None)
            completeness = ((total - missing) / total * 100) if total > 0 else 0

            dates = [r.get("recorded_at") for r in rows if r.get("recorded_at")]
            if dates:
                latest = max(dates)
                try:
                    latest_dt = datetime.fromisoformat(latest.replace("Z", "+00:00"))
                    days_old = (datetime.now(UTC) - latest_dt).days
                    freshness = max(0, 100 - days_old * 5)
                except Exception:
                    freshness = 50
            else:
                freshness = 0

            score = round((completeness * 0.5 + freshness * 0.5))
            grade = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 60 else "F"
            dept_scores.append({
                "department_id": dept["id"],
                "department_name": dept["name"],
                "score": score,
                "grade": grade,
                "completeness": round(completeness, 1),
                "freshness": round(freshness, 1),
            })
        except Exception:
            dept_scores.append({"department_id": dept["id"], "department_name": dept["name"], "score": 0, "grade": "Error"})

    overall = round(sum(d["score"] for d in dept_scores) / len(dept_scores)) if dept_scores else 0
    overall_grade = "A" if overall >= 90 else "B" if overall >= 80 else "C" if overall >= 70 else "D" if overall >= 60 else "F"

    return {
        "overall_score": overall,
        "overall_grade": overall_grade,
        "departments": dept_scores,
        "department_count": len(dept_scores),
    }
