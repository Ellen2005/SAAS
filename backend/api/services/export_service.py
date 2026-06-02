"""Export utilities for CNPS SAAS."""
from __future__ import annotations

import csv
import io
from datetime import datetime


def export_kpis_csv(user_id: str, supabase) -> bytes:
    resp = (
        supabase.table("kpi_results")
        .select("kpi_name, value, status, recorded_at, source")
        .eq("user_id", user_id)
        .order("recorded_at", desc=True)
        .limit(5000)
        .execute()
    )
    rows = resp.data if hasattr(resp, "data") and resp.data else []
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["kpi_name", "value", "status", "recorded_at", "source"])
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in writer.fieldnames})
    return buf.getvalue().encode("utf-8")


def export_analysis_runs_csv(user_id: str, supabase) -> bytes:
    resp = (
        supabase.table("analysis_runs")
        .select("id, goal_text, goal_type, status, result_summary, created_at, completed_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(500)
        .execute()
    )
    rows = resp.data if hasattr(resp, "data") and resp.data else []
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=["id", "goal_text", "goal_type", "status", "result_summary", "created_at", "completed_at"],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in writer.fieldnames})
    return buf.getvalue().encode("utf-8")
