"""
Goal-driven analysis engine for CNPS SAAS.
Users specify what to analyze; the engine plans and executes read-only queries.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, UTC
from typing import Any

from .groq_utils import execute_groq_completion, get_groq_model
from .nlq_service import _get_db_schema_hint, run_nlq

logger = logging.getLogger(__name__)

FORBIDDEN_SQL = ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "GRANT", "REVOKE")


def _validate_readonly_sql(sql: str) -> str:
    sql = sql.strip().rstrip(";")
    upper = sql.upper()
    if not upper.startswith(("SELECT", "WITH", "PRAGMA")):
        raise ValueError("Only read-only SELECT queries are permitted.")
    if any(tok in upper for tok in FORBIDDEN_SQL):
        raise ValueError("Query contains forbidden keywords.")
    return sql


def _preset_goal_map() -> dict[str, str]:
    return {
        "contributions-monitoring": (
            "Show monthly total contribution_amount grouped by regional_code "
            "and count of overdue payment_status from contributions table"
        ),
        "pension-analytics": (
            "Show monthly sum of pension_amount from pension_payments grouped by month"
        ),
        "workplace-accidents": (
            "Count workplace accidents by regional_code and claim_status"
        ),
        "employer-compliance": (
            "Count employers with overdue contributions grouped by regional_code"
        ),
        "regional-performance": (
            "Sum contribution_amount by regional_code for the last 12 months"
        ),
    }


def _plan_analysis_goal(goal_text: str, schema_hint: str, db_type: str) -> dict[str, Any]:
    prompt = f"""You are a CNPS institutional analytics planner.
Given the analysis goal and database schema, output a single JSON object:
{{"sql": "<read-only SELECT>", "summary_hint": "<one line>", "chart_type": "bar|line|pie|table", "x_column": "...", "y_column": "..."}}

Rules:
- SQL must be read-only SELECT only for {db_type}
- Limit rows to 100
- Use actual table/column names from schema
- Goal: {goal_text}

Schema:
{schema_hint}
"""
    try:
        completion = execute_groq_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500,
            model=get_groq_model(),
        )
        raw = completion.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.lower().startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as exc:
        logger.warning("Analysis plan LLM failed: %s", exc)
        return {"sql": None, "summary_hint": goal_text, "chart_type": "table"}


def _rule_based_sql(goal_text: str, db_type: str) -> str | None:
    g = goal_text.lower()
    if "contribution" in g and "region" in g:
        return (
            "SELECT regional_code, SUM(contribution_amount) AS total_contributions "
            "FROM contributions GROUP BY regional_code ORDER BY total_contributions DESC LIMIT 100"
        )
    if "pension" in g:
        return (
            "SELECT strftime('%Y-%m', payment_date) AS month, SUM(pension_amount) AS total "
            "FROM pension_payments GROUP BY month ORDER BY month LIMIT 24"
        ) if db_type == "sqlite" else (
            "SELECT DATE_TRUNC('month', payment_date) AS month, SUM(pension_amount) AS total "
            "FROM pension_payments GROUP BY 1 ORDER BY 1 LIMIT 24"
        )
    if "accident" in g or "at/mp" in g or "sinistre" in g:
        return (
            "SELECT regional_code, claim_status, COUNT(*) AS accident_count "
            "FROM workplace_accidents GROUP BY regional_code, claim_status LIMIT 100"
        )
    if "employer" in g and ("overdue" in g or "delinquent" in g or "compliance" in g):
        return (
            "SELECT regional_code, COUNT(DISTINCT employer_id) AS delinquent_employers "
            "FROM contributions WHERE payment_status = 'overdue' "
            "GROUP BY regional_code LIMIT 100"
        )
    return None


def _build_chart(rows: list[dict], plan: dict) -> dict:
    if not rows:
        return {"type": "table", "data": [], "title": "No data"}
    cols = list(rows[0].keys())
    x_col = plan.get("x_column") or cols[0]
    y_col = plan.get("y_column") or (cols[1] if len(cols) > 1 else cols[0])
    chart_type = plan.get("chart_type") or "bar"
    data = []
    for row in rows[:50]:
        data.append({
            "name": str(row.get(x_col, "")),
            str(y_col): row.get(y_col),
            **{k: v for k, v in row.items()},
        })
    return {
        "type": chart_type if chart_type in ("bar", "line", "pie", "area") else "bar",
        "data": data,
        "title": plan.get("summary_hint", "Analysis results"),
        "xKey": "name",
        "yKey": str(y_col),
    }


def _explain_results(*, goal_text: str, sql: str | None, metrics: dict, sample_rows: list[dict]) -> dict:
    """
    Return structured, human-friendly explanation for an analysis run.
    Falls back to deterministic text when no LLM is available.
    """
    prompt = f"""You are an institutional analytics assistant for CNPS.
Explain the results of this analysis clearly for a non-technical manager.

Return JSON with:
{{
  "what_this_means": "plain-language explanation",
  "assumptions": ["..."],
  "limitations": ["..."],
  "recommended_actions": ["..."]
}}

Analysis goal: {goal_text}
SQL used: {sql or "N/A"}
Metrics: {json.dumps({k: v for k, v in metrics.items() if k != "sample_rows"}, ensure_ascii=False)}
Sample rows: {json.dumps(sample_rows[:5], ensure_ascii=False)}
"""
    try:
        completion = execute_groq_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=600,
            model=get_groq_model(),
        )
        raw = completion.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.lower().startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception:
        row_count = metrics.get("row_count", 0)
        return {
            "what_this_means": f"This analysis returned {row_count} row(s). Review the top values and compare across regions/time.",
            "assumptions": [
                "The connected database is complete and up to date.",
                "The query is read-only and reflects current stored records.",
            ],
            "limitations": [
                "Results depend on naming conventions and available columns.",
                "This does not replace official accounting/audit procedures.",
            ],
            "recommended_actions": [
                "Validate suspicious spikes with the source department.",
                "Use the report feature to share findings with leadership.",
            ],
        }


def _extra_details_for_preset(*, user_id: str, preset_slug: str, supabase) -> dict:
    """Optional extra ranked tables for high-signal presets."""
    if preset_slug == "employer-compliance":
        sql = (
            "SELECT e.name AS employer, c.regional_code, COUNT(*) AS overdue_count, "
            "SUM(c.contribution_amount) AS overdue_amount "
            "FROM contributions c "
            "JOIN employers e ON e.id = c.employer_id "
            "WHERE c.payment_status = 'overdue' "
            "GROUP BY e.name, c.regional_code "
            "ORDER BY overdue_amount DESC "
            "LIMIT 10"
        )
        try:
            _, rows = _execute_sql(user_id, sql, supabase)
            return {"top_delinquent_employers": rows, "details_sql": {"top_delinquent_employers": sql}}
        except Exception:
            return {}
    return {}

def _execute_sql(user_id: str, sql: str, supabase) -> tuple[list[str], list[dict]]:
    from sqlalchemy import create_engine, text
    from .connection_crypto import maybe_decrypt_connection_row
    from .connection_utils import normalize_credentials, sqlalchemy_engine_kwargs
    from .etl_service import _get_free_local_port, _start_ssh_tunnel, _replace_db_url_host_port

    conn_resp = supabase.table("database_connections").select("*").eq("user_id", user_id).limit(1).execute()
    if not (hasattr(conn_resp, "data") and conn_resp.data):
        raise ValueError("No database connection configured.")
    if len(conn_resp.data) == 0:
        raise ValueError("No database connection found for user.")

    conn_info = maybe_decrypt_connection_row(conn_resp.data[0])
    db_type = (conn_info.get("db_type") or "sqlite").lower()
    credentials = conn_info.get("credentials", "")
    connection_method = conn_info.get("connection_method", "direct")
    connection_options = conn_info.get("connection_options") or {}

    if db_type == "mongodb":
        raise ValueError("Goal-driven SQL analysis requires a SQL database.")

    tunnel_proc = None
    engine = None
    try:
        db_url = credentials
        if connection_method == "ssh_tunnel":
            local_port = _get_free_local_port()
            tunnel_proc = _start_ssh_tunnel(
                ssh_host=str(connection_options.get("ssh_host") or conn_info.get("host")),
                ssh_user=str(connection_options.get("ssh_user")),
                remote_host=str(connection_options.get("remote_db_host") or conn_info.get("host")),
                remote_port=int(conn_info.get("port") or 5432),
                local_port=int(local_port),
            )
            db_url = _replace_db_url_host_port(credentials, "127.0.0.1", int(local_port))

        engine = create_engine(
            normalize_credentials(db_url, db_type),
            **sqlalchemy_engine_kwargs(db_url, db_type),
        )
        sql = _validate_readonly_sql(sql)
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            cols = list(result.keys())
            rows = []
            for row in result.fetchmany(200):
                record = {}
                for col, val in zip(cols, row):
                    if hasattr(val, "isoformat"):
                        record[col] = val.isoformat()
                    else:
                        record[col] = val
                rows.append(record)
            return cols, rows
    finally:
        if engine is not None:
            try:
                engine.dispose()
            except Exception:
                pass
        if tunnel_proc is not None:
            try:
                tunnel_proc.terminate()
            except Exception:
                pass


def validate_formula(expression: str) -> dict:
    """Validate a simple A/B style formula DSL."""
    expr = (expression or "").strip()
    if not expr:
        return {"valid": False, "error": "Expression is empty."}
    if len(expr) > 500:
        return {"valid": False, "error": "Expression too long."}
    if re.search(r"[;\"']", expr):
        return {"valid": False, "error": "Invalid characters in expression."}
    allowed = re.match(r"^[\w\s+\-*/().,%]+$", expr)
    if not allowed:
        return {"valid": False, "error": "Only letters, numbers, and + - * / ( ) are allowed."}
    return {"valid": True, "expression": expr}


def run_analysis(
    user_id: str,
    goal_text: str,
    goal_type: str = "natural_language",
    preset_slug: str | None = None,
    formula: str | None = None,
    department_id: str | None = None,
    supabase=None,
) -> dict:
    """Execute a goal-driven analysis run and persist results."""
    if preset_slug:
        goal_text = _preset_goal_map().get(preset_slug, goal_text)
        goal_type = "preset"

    if formula:
        v = validate_formula(formula)
        if not v.get("valid"):
            return {"error": v.get("error"), "status": "failed"}
        goal_text = f"Calculate: {formula}. Context: {goal_text}"
        goal_type = "formula"

    run_row = {
        "user_id": user_id,
        "department_id": department_id,
        "goal_text": goal_text,
        "goal_type": goal_type,
        "status": "planning",
    }
    if preset_slug:
        preset_resp = supabase.table("cnps_analysis_presets").select("id").eq("slug", preset_slug).limit(1).execute()
        if hasattr(preset_resp, "data") and preset_resp.data:
            run_row["preset_id"] = preset_resp.data[0]["id"]

    insert_resp = supabase.table("analysis_runs").insert(run_row).execute()
    run_id = insert_resp.data[0]["id"] if hasattr(insert_resp, "data") and insert_resp.data else None

    try:
        supabase.table("analysis_runs").update({"status": "running"}).eq("id", run_id).execute()

        # Try NLQ path as fallback execution
        nlq_result = run_nlq(user_id, goal_text, supabase)
        if nlq_result.get("rows") and not nlq_result.get("error"):
            rows = nlq_result["rows"]
            plan = {"summary_hint": goal_text, "chart_type": "bar", "sql": nlq_result.get("sql")}
        else:
            from sqlalchemy import create_engine
            from .connection_crypto import maybe_decrypt_connection_row
            from .connection_utils import normalize_credentials, sqlalchemy_engine_kwargs

            conn_resp = supabase.table("database_connections").select("*").eq("user_id", user_id).limit(1).execute()
            if not (hasattr(conn_resp, "data") and conn_resp.data):
                raise ValueError("No database connection configured.")
            if len(conn_resp.data) == 0:
                raise ValueError("No database connection found for user.")
            conn_info = maybe_decrypt_connection_row(conn_resp.data[0])
            db_type = (conn_info.get("db_type") or "sqlite").lower()
            db_url = conn_info.get("credentials", "")
            engine = create_engine(
                normalize_credentials(db_url, db_type),
                **sqlalchemy_engine_kwargs(db_url, db_type),
            )
            schema_hint = _get_db_schema_hint(engine)
            engine.dispose()

            plan = _plan_analysis_goal(goal_text, schema_hint, db_type)
            sql = plan.get("sql") or _rule_based_sql(goal_text, db_type)
            if not sql:
                raise ValueError(nlq_result.get("error") or "Could not generate analysis query.")
            _, rows = _execute_sql(user_id, sql, supabase)
            plan["sql"] = sql

        chart = _build_chart(rows, plan)
        metrics = {
            "row_count": len(rows),
            "columns": list(rows[0].keys()) if rows else [],
            "sample_rows": rows[:10],
        }
        details = _extra_details_for_preset(user_id=user_id, preset_slug=preset_slug or "", supabase=supabase)
        if details:
            metrics["details"] = details
        summary = plan.get("summary_hint") or f"Analysis completed with {len(rows)} rows."
        explanation = _explain_results(goal_text=goal_text, sql=plan.get("sql"), metrics=metrics, sample_rows=rows[:10])

        supabase.table("analysis_runs").update({
            "status": "completed",
            "plan_json": plan,
            "result_summary": summary,
            "chart_json": chart,
            "metrics_json": {**metrics, "explanation": explanation},
            "completed_at": datetime.now(UTC).isoformat(),
        }).eq("id", run_id).execute()

        # Publish primary metric to kpi_results for dashboard widgets
        if rows and len(rows[0]) >= 2:
            cols = list(rows[0].keys())
            val_col = cols[1] if len(cols) > 1 else cols[0]
            try:
                val = float(rows[0].get(val_col, 0) or 0)
                kpi_name = (preset_slug or "custom_analysis").replace("-", "_")[:80]
                supabase.table("kpi_results").insert({
                    "user_id": user_id,
                    "kpi_name": kpi_name,
                    "value": val,
                    "status": "normal",
                    "source": "goal_run",
                    "recorded_at": datetime.now(UTC).isoformat(),
                }).execute()
            except (TypeError, ValueError):
                pass

        return {
            "run_id": run_id,
            "status": "completed",
            "summary": summary,
            "chart": chart,
            "metrics": {**metrics, "explanation": explanation},
            "rows": rows[:50],
            "sql": plan.get("sql"),
        }
    except Exception as exc:
        logger.exception("Analysis run failed")
        if run_id:
            supabase.table("analysis_runs").update({
                "status": "failed",
                "error_message": str(exc)[:500],
                "completed_at": datetime.now(UTC).isoformat(),
            }).eq("id", run_id).execute()
        return {"run_id": run_id, "status": "failed", "error": str(exc)}


def list_presets(supabase, lang: str = "en") -> list[dict]:
    resp = supabase.table("cnps_analysis_presets").select("*").order("category").execute()
    rows = resp.data if hasattr(resp, "data") and resp.data else []
    for row in rows:
        row["title"] = row.get("title_fr" if lang == "fr" else "title_en") or row.get("title_en")
    return rows


def list_runs(user_id: str, supabase, limit: int = 20) -> list[dict]:
    resp = (
        supabase.table("analysis_runs")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return resp.data if hasattr(resp, "data") and resp.data else []
