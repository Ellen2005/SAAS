"""
Goal-driven analysis engine for CNPS SAAS.
Users specify what to analyze; the engine plans and executes read-only queries.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
UTC = timezone.utc
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
    oracle_rules = ""
    if db_type == "oracle":
        oracle_rules = """
- For Oracle: Use FETCH FIRST N ROWS ONLY (NOT LIMIT), TRUNC(col,'MM') (NOT DATE_TRUNC), SYSDATE (NOT NOW), TO_CHAR for date formatting.
- Do NOT use semicolons at the end of queries.
- Qualify all column names with table aliases when using JOINs to avoid ambiguity."""

    prompt = f"""You are a CNPS institutional analytics planner.
Given the analysis goal and database schema, output a single JSON object:
{{"sql": "<read-only SELECT>", "summary_hint": "<one line>", "chart_type": "bar|line|pie|table", "x_column": "...", "y_column": "..."}}

Rules:
- SQL must be read-only SELECT only for {db_type} database
- Limit rows to 100
- Use actual table/column names from schema
- Goal: {goal_text}
{oracle_rules}

Schema:
{schema_hint}
"""
    try:
        try:
            from .ai_orchestrator import AIOrchestrator
            orchestrator = AIOrchestrator()
            result = orchestrator.execute_sync(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500,
                model=get_groq_model(),
            )
            completion = result
        except Exception:
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
    limit_clause = "FETCH FIRST 100 ROWS ONLY" if db_type == "oracle" else "LIMIT 100"
    limit_clause_24 = "FETCH FIRST 24 ROWS ONLY" if db_type == "oracle" else "LIMIT 24"
    if "contribution" in g and "region" in g:
        return (
            "SELECT regional_code, SUM(contribution_amount) AS total_contributions "
            f"FROM contributions GROUP BY regional_code ORDER BY total_contributions DESC {limit_clause}"
        )
    if "pension" in g:
        if db_type == "sqlite":
            return (
                "SELECT strftime('%Y-%m', payment_date) AS month, SUM(pension_amount) AS total "
                f"FROM pension_payments GROUP BY month ORDER BY month {limit_clause_24}"
            )
        elif db_type == "oracle":
            return (
                "SELECT TO_CHAR(payment_date, 'YYYY-MM') AS month, SUM(pension_amount) AS total "
                f"FROM pension_payments GROUP BY TO_CHAR(payment_date, 'YYYY-MM') ORDER BY month {limit_clause_24}"
            )
        else:
            return (
                "SELECT DATE_TRUNC('month', payment_date) AS month, SUM(pension_amount) AS total "
                f"FROM pension_payments GROUP BY 1 ORDER BY 1 {limit_clause_24}"
            )
    if "accident" in g or "at/mp" in g or "sinistre" in g:
        return (
            "SELECT regional_code, claim_status, COUNT(*) AS accident_count "
            f"FROM workplace_accidents GROUP BY regional_code, claim_status {limit_clause}"
        )
    if "employer" in g and ("overdue" in g or "delinquent" in g or "compliance" in g):
        return (
            "SELECT regional_code, COUNT(DISTINCT employer_id) AS delinquent_employers "
            f"FROM contributions WHERE payment_status = 'overdue' "
            f"GROUP BY regional_code {limit_clause}"
        )
    return None


def _build_chart(rows: list[dict], plan: dict) -> dict:
    from .chart_service import build_chart_from_rows
    if not rows:
        return {"type": "table", "data": [], "title": "No data"}
    cols = list(rows[0].keys())
    chart_type = plan.get("chart_type") or "auto"
    chart = build_chart_from_rows(
        rows, cols,
        chart_type=chart_type,
        title=plan.get("summary_hint", "Analysis results"),
    )
    if chart is None:
        return {"type": "table", "data": [], "title": "No data"}
    return chart


def _explain_results(*, goal_text: str, sql: str | None, metrics: dict, sample_rows: list[dict]) -> dict:
    """
    Return structured, human-friendly analysis with overview, insights,
    observations, forecasts, risk analysis, and recommendations.
    """
    row_count = metrics.get("row_count", 0)
    columns = metrics.get("columns", [])

    # Compute data quality stats
    null_counts = {}
    if sample_rows:
        for col in columns:
            nulls = sum(1 for r in sample_rows if r.get(col) is None or r.get(col) == "" or r.get(col) == "null")
            if nulls > 0:
                null_counts[col] = nulls
    total_cells = max(row_count * len(columns), 1)
    null_total = sum(null_counts.values())
    completeness_pct = round((1 - null_total / total_cells) * 100, 1) if total_cells > 0 else 100

    # Compute basic stats for numeric columns
    col_stats = {}
    for col in columns:
        vals = []
        for r in sample_rows:
            v = r.get(col)
            try:
                vals.append(float(v))
            except (TypeError, ValueError):
                continue
        if vals:
            col_stats[col] = {
                "min": min(vals),
                "max": max(vals),
                "avg": round(sum(vals) / len(vals), 2),
                "count": len(vals),
            }

    # Identify top/bottom values
    insights_list = []
    if sample_rows and len(columns) >= 2:
        text_col = columns[0]
        num_col = None
        for c in columns[1:]:
            try:
                float(sample_rows[0].get(c))
                num_col = c
                break
            except (TypeError, ValueError):
                continue
        if num_col:
            sorted_rows = sorted(sample_rows, key=lambda r: float(r.get(num_col, 0) or 0), reverse=True)
            if sorted_rows:
                top = sorted_rows[0]
                insights_list.append(f"Top performer: {top.get(text_col, 'N/A')} with {float(top.get(num_col, 0)):,.2f}")
            if len(sorted_rows) > 1:
                bottom = sorted_rows[-1]
                insights_list.append(f"Lowest performer: {bottom.get(text_col, 'N/A')} with {float(bottom.get(num_col, 0)):,.2f}")
            if len(sorted_rows) > 2:
                vals = [float(r.get(num_col, 0) or 0) for r in sorted_rows]
                avg_val = sum(vals) / len(vals)
                above_avg = sum(1 for v in vals if v > avg_val)
                below_avg = len(vals) - above_avg
                insights_list.append(f"{above_avg} of {len(vals)} records are above average ({avg_val:,.2f}), {below_avg} are below.")

    # Build the structured explanation
    prompt = f"""You are an institutional analytics assistant for CNPS (Caisse Nationale de Prevoyance Sociale).

Analyze the results of this goal-driven analysis and produce a rich, human-readable report.

GOAL: {goal_text}

SQL QUERY USED:
{sql or "N/A"}

DATA SUMMARY:
- Total rows returned: {row_count}
- Columns: {', '.join(columns)}
- Data completeness: {completeness_pct}% ({null_total} null/empty values out of {total_cells} cells)
- Columns with missing data: {json.dumps(null_counts) if null_counts else "None"}

COLUMN STATISTICS:
{json.dumps(col_stats, indent=2)}

TOP/BOTTOM INSIGHTS:
{chr(10).join(insights_list) if insights_list else "Not enough data for ranking insights"}

SAMPLE DATA (first 5 rows):
{json.dumps(sample_rows[:5], indent=2, default=str)}

Return a JSON object with these sections:
{{
  "overview": "A clear 2-3 sentence summary of what this analysis covers and what was found. Start with 'This analysis examines...' or 'Based on your goal...'",
  "tables_explored": "Which tables/columns were queried and why. Be specific about the data sources.",
  "observations": [
    "Specific observation from the data, e.g. 'Region X has the highest contribution rate at Y%'",
    "Note any null/missing data: 'Column Z has N missing values which may affect accuracy'",
    "Note any data quality issues: 'Dates appear inconsistent...' or 'Some employer IDs are missing...'"
  ],
  "insights": [
    "Data-driven insight, e.g. 'Contributions in Q1 are 23% higher than Q4 suggesting seasonal patterns'",
    "Pattern detected: 'There is a clear downward trend in...'",
    "Comparison: 'Douala contributes 3x more than...'"
  ],
  "forecasts": {{
    "projection": "Based on current trends, describe what is likely to happen in the next 3-6 months. Be specific with numbers if possible.",
    "scenario_best": "Best case scenario if conditions improve",
    "scenario_worst": "Worst case if no action is taken",
    "trigger": "What specific action or event would change the trajectory"
  }},
  "risk_analysis": [
    "Risk factor with severity (high/medium/low) and impact description",
    "E.g. {{'risk': 'Declining contribution rates in 3 regions', 'severity': 'high', 'impact': 'Could reduce fund reserves by X% within 6 months'}}"
  ],
  "recommendations": [
    {{
      "priority": "high/medium/low",
      "action": "Specific actionable recommendation",
      "expected_impact": "What this would achieve",
      "timeline": "When to act (immediate/short-term/long-term)"
    }}
  ],
  "what_this_means": "Plain-language explanation for a non-technical manager",
  "assumptions": ["List any assumptions made"],
  "limitations": ["List limitations of this analysis"]
}}

IMPORTANT:
- Be specific with numbers, percentages, and dates from the actual data
- Reference actual column names and table names
- If data is missing or incomplete, call it out explicitly
- Forecasts should be grounded in the actual trends observed
- Recommendations should be actionable and specific to CNPS context
"""
    try:
        try:
            from .ai_orchestrator import AIOrchestrator
            orchestrator = AIOrchestrator()
            result = orchestrator.execute_sync(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1500,
                model=get_groq_model(),
            )
            completion = result
        except Exception:
            completion = execute_groq_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1500,
                model=get_groq_model(),
            )
        raw = completion.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.lower().startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        # Ensure all keys exist
        for key in ["overview", "tables_explored", "observations", "insights", "forecasts",
                     "risk_analysis", "recommendations", "what_this_means", "assumptions", "limitations"]:
            if key not in result:
                result[key] = [] if key in ("observations", "insights", "risk_analysis", "recommendations", "assumptions", "limitations") else ""
        return result
    except Exception:
        # Rich fallback based on actual data
        null_notes = []
        for col, count in null_counts.items():
            null_notes.append(f"{col} has {count} missing value(s)")
        null_summary = "; ".join(null_notes) if null_notes else "No missing values detected"

        obs = [f"Query returned {row_count} record(s) across {len(columns)} columns"]
        if null_counts:
            obs.append(f"Data quality note: {null_summary}. This may affect accuracy of results.")
        obs.append(f"Data completeness: {completeness_pct}%")
        for col, stats in col_stats.items():
            obs.append(f"{col}: ranges from {stats['min']:,.2f} to {stats['max']:,.2f} (average: {stats['avg']:,.2f})")
        obs.extend(insights_list)

        return {
            "overview": f"This analysis examines '{goal_text}'. The query returned {row_count} record(s) from the connected database. "
                        f"Data completeness is {completeness_pct}% with {null_total} missing value(s) across all cells.",
            "tables_explored": f"The analysis queried columns: {', '.join(columns)}. "
                               f"The SQL used was: {sql or 'Generated via natural language query'}.",
            "observations": obs,
            "insights": insights_list or [f"Based on {row_count} records, review the values for patterns and trends."],
            "forecasts": {
                "projection": f"If current trends continue over the next 3-6 months based on {row_count} data points, "
                              "monitor for changes in the metrics shown. Set up alerts for significant deviations.",
                "scenario_best": "If all regions/employers improve performance by 10%, overall metrics would show positive growth.",
                "scenario_worst": "Without intervention, declining regions may continue to underperform, dragging down overall averages.",
                "trigger": "Set a review threshold — if any metric drops below the average, trigger an investigation.",
            },
            "risk_analysis": [
                {"risk": "Incomplete data", "severity": "medium",
                 "impact": f"{null_total} missing values detected. Results should be validated against official records."},
                {"risk": "Limited sample size", "severity": "low" if row_count >= 10 else "medium",
                 "impact": f"Only {row_count} records available. Larger samples would provide more reliable insights."},
            ],
            "recommendations": [
                {"priority": "high", "action": "Review and validate the data shown above with the source department.",
                 "expected_impact": "Ensures decision-making is based on accurate data.", "timeline": "Immediate"},
                {"priority": "medium", "action": "Set up regular monitoring for the metrics identified in this analysis.",
                 "expected_impact": "Early detection of trends and anomalies.", "timeline": "Short-term"},
                {"priority": "medium", "action": "Address missing data by following up with the responsible departments.",
                 "expected_impact": "Improved data completeness for future analyses.", "timeline": "Short-term"},
            ],
            "what_this_means": f"This analysis returned {row_count} row(s). The key columns are: {', '.join(columns)}. "
                               f"Review the top values and compare across categories. {null_summary}.",
            "assumptions": [
                "The connected database is complete and up to date.",
                "The query is read-only and reflects current stored records.",
                "Column naming conventions match expected patterns.",
            ],
            "limitations": [
                f"Results depend on {row_count} sample row(s) — larger datasets may yield different conclusions.",
                "This does not replace official accounting or audit procedures.",
                "Null/missing values may affect aggregate calculations.",
            ],
        }


def _extra_details_for_preset(*, user_id: str, preset_slug: str, supabase) -> dict:
    """Optional extra ranked tables for high-signal presets."""
    if preset_slug == "employer-compliance":
        from .connection_crypto import maybe_decrypt_connection_row
        from .connection_pool import get_engine
        conn_resp = supabase.table("database_connections").select("*").eq("user_id", user_id).limit(1).execute()
        db_type = "sqlite"
        if hasattr(conn_resp, "data") and conn_resp.data:
            conn_info = maybe_decrypt_connection_row(conn_resp.data[0])
            db_type = (conn_info.get("db_type") or "sqlite").lower()
        limit_clause = "FETCH FIRST 10 ROWS ONLY" if db_type == "oracle" else "LIMIT 10"
        sql = (
            "SELECT e.name AS employer, c.regional_code, COUNT(*) AS overdue_count, "
            "SUM(c.contribution_amount) AS overdue_amount "
            "FROM contributions c "
            "JOIN employers e ON e.id = c.employer_id "
            "WHERE c.payment_status = 'overdue' "
            "GROUP BY e.name, c.regional_code "
            f"ORDER BY overdue_amount DESC {limit_clause}"
        )
        try:
            _, rows = _execute_sql(user_id, sql, supabase)
            return {"top_delinquent_employers": rows, "details_sql": {"top_delinquent_employers": sql}}
        except Exception:
            return {}
    return {}

def _execute_sql(user_id: str, sql: str, supabase) -> tuple[list[str], list[dict]]:
    from sqlalchemy import text
    from .connection_crypto import maybe_decrypt_connection_row
    from .connection_pool import get_engine
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

        engine = get_engine(db_url, db_type)
        sql = _validate_readonly_sql(sql)
        from decimal import Decimal as _Decimal
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            cols = list(result.keys())
            rows = []
            for row in result.fetchmany(200):
                record = {}
                for col, val in zip(cols, row):
                    if hasattr(val, "isoformat"):
                        record[col] = val.isoformat()
                    elif isinstance(val, _Decimal):
                        record[col] = float(val)
                    elif hasattr(val, "__float__") and not isinstance(val, bool):
                        try:
                            record[col] = float(val)
                        except (TypeError, ValueError):
                            record[col] = str(val)
                    else:
                        record[col] = val
                rows.append(record)
            return cols, rows
    finally:
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
    if not (hasattr(insert_resp, "data") and insert_resp.data):
        raise RuntimeError("Failed to create analysis run record")
    run_id = insert_resp.data[0]["id"]

    try:
        supabase.table("analysis_runs").update({"status": "running"}).eq("id", run_id).execute()

        # Try NLQ path as fallback execution
        nlq_result = run_nlq(user_id, goal_text, supabase)
        if nlq_result.get("rows") and not nlq_result.get("error"):
            rows = nlq_result["rows"]
            plan = {"summary_hint": goal_text, "chart_type": "bar", "sql": nlq_result.get("sql")}
        else:
            from .connection_crypto import maybe_decrypt_connection_row
            from .connection_pool import get_engine

            conn_resp = supabase.table("database_connections").select("*").eq("user_id", user_id).limit(1).execute()
            if not (hasattr(conn_resp, "data") and conn_resp.data):
                raise ValueError("No database connection configured.")
            if len(conn_resp.data) == 0:
                raise ValueError("No database connection found for user.")
            conn_info = maybe_decrypt_connection_row(conn_resp.data[0])
            db_type = (conn_info.get("db_type") or "sqlite").lower()
            db_url = conn_info.get("credentials", "")
            engine = get_engine(db_url, db_type)
            schema_hint = _get_db_schema_hint(engine)

            plan = _plan_analysis_goal(goal_text, schema_hint, db_type)
            sql = plan.get("sql") or _rule_based_sql(goal_text, db_type)
            if not sql:
                raise ValueError(nlq_result.get("error") or "Could not generate analysis query.")
            # Sanitize SQL for the target dialect
            from .nlq_service import _sanitize_sql_for_dialect
            sql = _sanitize_sql_for_dialect(sql, db_type)
            # Try executing the query; if it fails, retry with rule-based fallback
            try:
                _, rows = _execute_sql(user_id, sql, supabase)
            except Exception as sql_err:
                logger.warning(f"SQL execution failed, trying rule-based fallback: {sql_err}")
                fallback_sql = _rule_based_sql(goal_text, db_type)
                if fallback_sql:
                    fallback_sql = _sanitize_sql_for_dialect(fallback_sql, db_type)
                    _, rows = _execute_sql(user_id, fallback_sql, supabase)
                    plan["sql"] = fallback_sql
                else:
                    raise
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
            "explanation": explanation,
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
    try:
        resp = supabase.table("cnps_analysis_presets").select("*").order("category").execute()
        rows = resp.data if hasattr(resp, "data") and resp.data else []
        for row in rows:
            row["title"] = row.get("title_fr" if lang == "fr" else "title_en") or row.get("title_en")
        return rows
    except Exception as e:
        logger.warning(f"Could not load analysis presets: {e}")
        return []


def list_runs(user_id: str, supabase, limit: int = 20) -> list[dict]:
    try:
        resp = (
            supabase.table("analysis_runs")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return resp.data if hasattr(resp, "data") and resp.data else []
    except Exception as e:
        logger.warning(f"Could not load analysis runs: {e}")
        return []
