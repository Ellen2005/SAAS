from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from ..core.auth import require_role
from ..core.supabase_client import get_supabase
from ..services.etl_service import run_user_etl_pipeline

router = APIRouter(prefix="/api/admin", tags=["admin"])

def _safe_data(response) -> list:
    return response.data if hasattr(response, "data") and response.data else []


@router.get("/summary")
def get_admin_summary(context: dict = Depends(require_role(["admin"]))):
    """
    Combined KPIs, department previews, and time-series drill-down data.
    """
    supabase = get_supabase()

    try:
        departments = _safe_data(
            supabase.table("departments").select("*").order("created_at").execute()
        )
        kpi_rows = _safe_data(
            supabase.table("kpi_results")
            .select("*, departments(name)")
            .order("recorded_at", desc=True)
            .limit(500)
            .execute()
        )
        anomaly_rows = _safe_data(
            supabase.table("anomaly_records")
            .select("*")
            .order("detected_at", desc=True)
            .limit(200)
            .execute()
        )
        report_rows = _safe_data(
            supabase.table("daily_reports")
            .select("*")
            .order("report_date", desc=True)
            .limit(200)
            .execute()
        )

        reports_by_department = {}
        for report in report_rows:
            department_id = report.get("department_id")
            if department_id and department_id not in reports_by_department:
                reports_by_department[department_id] = report

        anomalies_by_department = {}
        for anomaly in anomaly_rows:
            department_id = anomaly.get("department_id")
            anomalies_by_department.setdefault(department_id, []).append(anomaly)

        latest_kpis_by_department = {}
        combined_totals = {}
        timeline_map = {}

        for row in kpi_rows:
            department_id = row.get("department_id")
            recorded_at = str(row.get("recorded_at"))
            latest_kpis_by_department.setdefault(department_id, [])
            if len(latest_kpis_by_department[department_id]) < 6:
                latest_kpis_by_department[department_id].append(row)

            kpi_name = row["kpi_name"]
            combined_totals.setdefault(
                kpi_name,
                {"value": 0.0, "departments": set()},
            )
            combined_totals[kpi_name]["value"] += float(row.get("value", 0))
            if department_id:
                combined_totals[kpi_name]["departments"].add(department_id)

            dept_name = "Unassigned"
            if row.get("departments"):
                dept_name = row["departments"].get("name") or dept_name

            timeline_map.setdefault(
                recorded_at,
                {
                    "period": recorded_at,
                    "total_value": 0.0,
                    "department_breakdown": {},
                },
            )
            timeline_map[recorded_at]["total_value"] += float(row.get("value", 0))
            timeline_map[recorded_at]["department_breakdown"][dept_name] = (
                timeline_map[recorded_at]["department_breakdown"].get(dept_name, 0.0)
                + float(row.get("value", 0))
            )

        department_summaries = []
        for department in departments:
            report = reports_by_department.get(department["id"])
            department_summaries.append(
                {
                    "department_id": department["id"],
                    "department_name": department["name"],
                    "description": department.get("description"),
                    "heartbeat_schedule": department.get("heartbeat_schedule"),
                    "heartbeat_time": department.get("heartbeat_time"),
                    "kpis": latest_kpis_by_department.get(department["id"], []),
                    "anomaly_count": len(anomalies_by_department.get(department["id"], [])),
                    "narrative_preview": (report or {}).get("narrative", "")[:240],
                    "last_sync": (report or {}).get("report_date"),
                }
            )

        combined_kpis = [
            {
                "kpi_name": name,
                "total_value": round(values["value"], 2),
                "department_count": len(values["departments"]),
            }
            for name, values in combined_totals.items()
        ]
        combined_kpis.sort(key=lambda item: item["total_value"], reverse=True)

        timeline = list(timeline_map.values())
        timeline.sort(key=lambda item: item["period"])

        return {
            "departments": department_summaries,
            "combined_kpis": combined_kpis,
            "timeline": timeline,
            "total_departments": len(departments),
            "generated_at": datetime.now().isoformat(),
            "requested_by": context["user_id"],
        }
    except Exception as error:
        return {
            "departments": [],
            "combined_kpis": [],
            "timeline": [],
            "total_departments": 0,
            "generated_at": datetime.now().isoformat(),
            "error": str(error),
        }


@router.get("/combined-report")
def get_combined_report(
    report_date: Optional[str] = None,
    context: dict = Depends(require_role(["admin"])),
):
    supabase = get_supabase()
    try:
        query = supabase.table("combined_reports").select("*").order("report_date", desc=True)
        if report_date:
            query = query.eq("report_date", report_date)

        rows = _safe_data(query.limit(1).execute())
        if rows:
            return {"report": rows[0], "requested_by": context["user_id"]}
        return {"report": None, "message": "No combined report found."}
    except Exception as error:
        return {"report": None, "message": f"Error fetching report: {error}"}


@router.get("/lineage/{kpi_id}")
def get_kpi_lineage(kpi_id: str, context: dict = Depends(require_role(["admin"]))):
    supabase = get_supabase()
    try:
        kpi_rows = _safe_data(
            supabase.table("kpi_results")
            .select("*, departments(name)")
            .eq("id", kpi_id)
            .limit(1)
            .execute()
        )
        if not kpi_rows:
            raise HTTPException(status_code=404, detail="KPI not found")

        kpi = kpi_rows[0]
        department_name = None
        if kpi.get("departments"):
            department_name = kpi["departments"].get("name")

        lineage_records = _safe_data(
            supabase.table("source_lineage_records")
            .select("*")
            .eq("batch_source_id", kpi.get("source_id"))
            .eq("kpi_name", kpi.get("kpi_name"))
            .limit(100)
            .execute()
        )

        related_kpis = _safe_data(
            supabase.table("kpi_results")
            .select("id, kpi_name, value, recorded_at")
            .eq("department_id", kpi.get("department_id"))
            .eq("recorded_at", kpi.get("recorded_at"))
            .limit(20)
            .execute()
        )

        return {
            "kpi": {key: value for key, value in kpi.items() if key != "departments"},
            "department_name": department_name,
            "source_records": lineage_records,
            "related_kpis": related_kpis,
            "source_record_count": kpi.get("source_record_count", len(lineage_records)),
            "requested_by": context["user_id"],
        }
    except HTTPException:
        raise
    except Exception as error:
        return {
            "kpi": None,
            "department_name": None,
            "source_records": [],
            "related_kpis": [],
            "source_record_count": 0,
            "error": str(error),
        }


@router.get("/heartbeat/status")
def get_admin_heartbeat_status(context: dict = Depends(require_role(["admin"]))):
    supabase = get_supabase()
    try:
        departments = _safe_data(
            supabase.table("departments")
            .select("id, name, heartbeat_schedule, heartbeat_time")
            .order("created_at")
            .execute()
        )

        statuses = []
        for department in departments:
            kpi_rows = _safe_data(
                supabase.table("kpi_results")
                .select("recorded_at")
                .eq("department_id", department["id"])
                .order("recorded_at", desc=True)
                .limit(1)
                .execute()
            )
            validation_rows = _safe_data(
                supabase.table("validation_logs")
                .select("status")
                .eq("department_id", department["id"])
                .order("created_at", desc=True)
                .limit(10)
                .execute()
            )
            user_count_resp = (
                supabase.table("user_roles")
                .select("id", count="exact")
                .eq("department_id", department["id"])
                .execute()
            )

            passes = len([row for row in validation_rows if row.get("status") == "pass"])
            validation_score = round((passes / len(validation_rows)) * 100, 1) if validation_rows else None

            statuses.append(
                {
                    "department_id": department["id"],
                    "department_name": department["name"],
                    "heartbeat_schedule": department["heartbeat_schedule"],
                    "heartbeat_time": department["heartbeat_time"],
                    "last_sync": kpi_rows[0]["recorded_at"] if kpi_rows else None,
                    "status": "active" if kpi_rows else "pending",
                    "user_count": getattr(user_count_resp, "count", 0),
                    "validation_score": validation_score,
                }
            )

        return {"departments": statuses, "requested_by": context["user_id"]}
    except Exception as error:
        return {"departments": [], "error": str(error)}


@router.post("/heartbeat/trigger/{dept_id}")
def trigger_department_etl(
    dept_id: str,
    background_tasks: BackgroundTasks,
    context: dict = Depends(require_role(["admin"])),
):
    supabase = get_supabase()
    try:
        users = _safe_data(
            supabase.table("user_roles").select("user_id").eq("department_id", dept_id).execute()
        )
        if not users:
            raise HTTPException(status_code=404, detail="No users found in this department")

        for user_role in users:
            background_tasks.add_task(run_user_etl_pipeline, user_role["user_id"])

        return {
            "status": "triggered",
            "department_id": dept_id,
            "users_triggered": len(users),
            "triggered_by": context["user_id"],
        }
    except HTTPException:
        raise
    except Exception as error:
        return {
            "status": "error",
            "department_id": dept_id,
            "users_triggered": 0,
            "error": str(error),
        }
