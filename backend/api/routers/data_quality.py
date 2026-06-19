"""
Data Quality Center Router
==========================
Provides data quality validation, scoring, and reporting.
"""
import logging
from datetime import datetime, timezone
UTC = timezone.utc
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from ..core.auth import resolve_user_id, require_role
from ..core.supabase_client import get_supabase

router = APIRouter(prefix="/api/data-quality", tags=["data-quality"])
logger = logging.getLogger(__name__)


@router.get("/score")
def get_data_quality_score(user_id: str = Depends(resolve_user_id)):
    """Compute overall data quality score for the user's data."""
    supabase = get_supabase()
    try:
        kpi_rows = (
            supabase.table("kpi_results")
            .select("*")
            .eq("user_id", user_id)
            .limit(500)
            .execute()
        )
        raw = kpi_rows.data if hasattr(kpi_rows, "data") and kpi_rows.data else []

        if not raw:
            return {"score": 0, "grade": "N/A", "checks": [], "recommendations": []}

        checks = []
        total_score = 0
        max_score = 0

        # 1. Completeness check (no missing values)
        max_score += 25
        total_fields = len(raw) * len(raw[0]) if raw else 0
        missing_fields = sum(1 for row in raw for v in row.values() if v is None or v == "")
        completeness = ((total_fields - missing_fields) / total_fields * 100) if total_fields > 0 else 0
        checks.append({
            "check": "Completeness",
            "score": round(completeness, 1),
            "max_score": 25,
            "status": "pass" if completeness >= 90 else "warning" if completeness >= 70 else "fail",
            "message": f"{missing_fields} missing values out of {total_fields} fields",
        })
        total_score += (completeness / 100) * 25

        # 2. Freshness check (data recency)
        max_score += 25
        dates = [r.get("recorded_at") for r in raw if r.get("recorded_at")]
        if dates:
            latest = max(dates)
            try:
                latest_dt = datetime.fromisoformat(latest.replace("Z", "+00:00"))
                days_old = (datetime.now(UTC) - latest_dt).days
                freshness = max(0, 100 - days_old * 5)  # Loses 5% per day
                freshness = min(100, freshness)
            except Exception:
                freshness = 50
        else:
            freshness = 0
        checks.append({
            "check": "Freshness",
            "score": round(freshness, 1),
            "max_score": 25,
            "status": "pass" if freshness >= 80 else "warning" if freshness >= 50 else "fail",
            "message": f"Latest data is {days_old if dates else 'N/A'} days old",
        })
        total_score += (freshness / 100) * 25

        # 3. Validity check (data types and ranges)
        max_score += 25
        invalid_values = 0
        for row in raw:
            val = row.get("value")
            if val is not None:
                try:
                    float(val)
                except (TypeError, ValueError):
                    invalid_values += 1
        validity = ((len(raw) - invalid_values) / len(raw) * 100) if raw else 0
        checks.append({
            "check": "Validity",
            "score": round(validity, 1),
            "max_score": 25,
            "status": "pass" if validity >= 95 else "warning" if validity >= 80 else "fail",
            "message": f"{invalid_values} invalid numeric values found",
        })
        total_score += (validity / 100) * 25

        # 4. Consistency check (duplicate KPI names)
        max_score += 25
        kpi_names = [r.get("kpi_name") for r in raw if r.get("kpi_name")]
        unique_names = set(kpi_names)
        consistency = (len(unique_names) / len(kpi_names) * 100) if kpi_names else 0
        checks.append({
            "check": "Consistency",
            "score": round(consistency, 1),
            "max_score": 25,
            "status": "pass" if consistency >= 95 else "warning" if consistency >= 80 else "fail",
            "message": f"{len(kpi_names) - len(unique_names)} duplicate KPI entries",
        })
        total_score += (consistency / 100) * 25

        # Compute final score and grade
        final_score = round((total_score / max_score) * 100) if max_score > 0 else 0
        grade = "A" if final_score >= 90 else "B" if final_score >= 80 else "C" if final_score >= 70 else "D" if final_score >= 60 else "F"

        # Generate recommendations
        recommendations = []
        for check in checks:
            if check["status"] == "fail":
                recommendations.append({
                    "priority": "HIGH",
                    "area": check["check"],
                    "action": f"Address {check['check'].lower()} issues: {check['message']}",
                })
            elif check["status"] == "warning":
                recommendations.append({
                    "priority": "MEDIUM",
                    "area": check["check"],
                    "action": f"Improve {check['check'].lower()}: {check['message']}",
                })

        return {
            "score": final_score,
            "grade": grade,
            "checks": checks,
            "recommendations": recommendations,
            "generated_at": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f"Data quality score error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/issues")
def get_data_quality_issues(user_id: str = Depends(resolve_user_id)):
    """Return detailed data quality issues."""
    supabase = get_supabase()
    try:
        kpi_rows = (
            supabase.table("kpi_results")
            .select("*")
            .eq("user_id", user_id)
            .limit(500)
            .execute()
        )
        raw = kpi_rows.data if hasattr(kpi_rows, "data") and kpi_rows.data else []

        issues = []

        # Check for missing values
        for row in raw:
            for key, value in row.items():
                if value is None or value == "":
                    issues.append({
                        "type": "missing_value",
                        "field": key,
                        "record_id": row.get("id"),
                        "severity": "medium",
                        "message": f"Missing value in field '{key}'",
                    })

        # Check for duplicates
        seen = {}
        for row in raw:
            kpi_name = row.get("kpi_name")
            recorded_at = row.get("recorded_at")
            key = f"{kpi_name}_{recorded_at}"
            if key in seen:
                issues.append({
                    "type": "duplicate",
                    "field": "kpi_name + recorded_at",
                    "record_id": row.get("id"),
                    "severity": "low",
                    "message": f"Duplicate entry for {kpi_name} at {recorded_at}",
                })
            seen[key] = row.get("id")

        # Check for outliers (simple z-score)
        values = [float(r["value"]) for r in raw if r.get("value") is not None]
        if len(values) >= 3:
            mean = sum(values) / len(values)
            std = (sum((x - mean) ** 2 for x in values) / len(values)) ** 0.5
            if std > 0:
                for row in raw:
                    val = row.get("value")
                    if val is not None:
                        try:
                            z = abs(float(val) - mean) / std
                            if z > 3:
                                issues.append({
                                    "type": "outlier",
                                    "field": "value",
                                    "record_id": row.get("id"),
                                    "severity": "high",
                                    "message": f"Outlier detected: {val} (z-score: {z:.2f})",
                                })
                        except (TypeError, ValueError):
                            pass

        return {
            "issue_count": len(issues),
            "issues": issues[:100],  # Limit to 100 issues
            "generated_at": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f"Data quality issues error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report")
def get_data_quality_report(user_id: str = Depends(resolve_user_id)):
    """Generate comprehensive data quality report."""
    try:
        score = get_data_quality_score(user_id)
        issues = get_data_quality_issues(user_id)

        return {
            "title": "Data Quality Report",
            "generated_at": datetime.now(UTC).isoformat(),
            "overall_score": score["score"],
            "grade": score["grade"],
            "summary": {
                "total_checks": len(score["checks"]),
                "passed": len([c for c in score["checks"] if c["status"] == "pass"]),
                "warnings": len([c for c in score["checks"] if c["status"] == "warning"]),
                "failed": len([c for c in score["checks"] if c["status"] == "fail"]),
            },
            "checks": score["checks"],
            "issues": issues["issues"],
            "recommendations": score["recommendations"],
        }
    except Exception as e:
        logger.error(f"Data quality report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))