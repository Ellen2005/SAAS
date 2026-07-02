"""
Natural Language Query (NLQ) Service
Converts plain-English (or French) questions into SQL/MongoDB queries,
executes them against the user's connected database, and returns results.

Enterprise Integration:
  - Semantic Layer: Translates business terms ↔ raw schema
  - Prompt Manager: Loads prompts from library instead of inline strings
"""
import os
import re
import logging
from datetime import datetime
from .groq_utils import execute_groq_completion, get_groq_model

logger = logging.getLogger(__name__)


def _get_db_schema_hint(engine) -> str:
    """Extract table/column names from the connected DB for context."""
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        schema_lines = []
        for table in tables[:20]:  # limit to 20 tables
            try:
                cols = [c["name"] for c in inspector.get_columns(table)]
                schema_lines.append(f"  {table}({', '.join(cols[:15])})")
            except Exception as e:
                logger.debug(f"Failed to get columns for {table}: {e}")
                schema_lines.append(f"  {table}(...)")
        return "\n".join(schema_lines)
    except Exception as e:
        logger.debug(f"Schema introspection failed: {e}")
        return "(schema unavailable)"


def _sanitize_identifier(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.]", "", name)


def _fallback_sql_for_question(question: str, engine) -> tuple[str | None, str]:
    """Deterministic support-guide queries when no LLM key is configured."""
    q = question.lower()
    dialect = engine.dialect.name

    if "what can" in q or "help" in q or "guide" in q or "lost" in q:
        return None, (
            "I can help you explore the connected database, list tables, describe a table, "
            "preview records, count rows, and explain generated SQL. Try: 'list all tables', "
            "'describe rnc_database', or 'show 10 rows from rnc_database'."
        )

    if "how many table" in q or "count table" in q:
        if dialect == "postgresql":
            return (
                "SELECT COUNT(*) AS table_count FROM information_schema.tables "
                "WHERE table_schema NOT IN ('pg_catalog', 'information_schema');"
            ), "Counting readable non-system tables."
        if dialect == "mysql":
            return (
                "SELECT COUNT(*) AS table_count FROM information_schema.tables "
                "WHERE table_schema = DATABASE();"
            ), "Counting tables in the active MySQL database."
        if dialect == "oracle":
            return (
                "SELECT COUNT(*) AS table_count FROM user_tables"
            ), "Counting tables in the active Oracle schema."
        if dialect == "sqlite":
            return (
                "SELECT COUNT(*) AS table_count FROM sqlite_master "
                "WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%';"
            ), "Counting SQLite tables and views."

    if re.search(r"\bshow\b.*\btable(?:s)?\b", q) and "from" not in q:
        if dialect == "postgresql":
            return (
                "SELECT table_schema, table_name, table_type FROM information_schema.tables "
                "WHERE table_schema NOT IN ('pg_catalog', 'information_schema') "
                "ORDER BY table_schema, table_name LIMIT 200;"
            ), "Listing readable non-system tables."
        if dialect == "mysql":
            return (
                "SELECT table_schema, table_name, table_type FROM information_schema.tables "
                "WHERE table_schema = DATABASE() ORDER BY table_name LIMIT 200;"
            ), "Listing tables in the active MySQL database."
        if dialect == "oracle":
            return (
                "SELECT table_name FROM user_tables ORDER BY table_name FETCH FIRST 200 ROWS ONLY"
            ), "Listing tables in the active Oracle schema."
        if dialect == "sqlite":
            return (
                "SELECT type AS table_type, name AS table_name FROM sqlite_master "
                "WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%' ORDER BY name LIMIT 200;"
            ), "Listing SQLite tables and views."

    if "list" in q and "table" in q:
        if dialect == "postgresql":
            return (
                "SELECT table_schema, table_name, table_type FROM information_schema.tables "
                "WHERE table_schema NOT IN ('pg_catalog', 'information_schema') "
                "ORDER BY table_schema, table_name LIMIT 200;"
            ), "Listing readable non-system tables."
        if dialect == "mysql":
            return (
                "SELECT table_schema, table_name, table_type FROM information_schema.tables "
                "WHERE table_schema = DATABASE() ORDER BY table_name LIMIT 200;"
            ), "Listing tables in the active MySQL database."
        if dialect == "oracle":
            return (
                "SELECT table_name FROM user_tables ORDER BY table_name FETCH FIRST 200 ROWS ONLY"
            ), "Listing tables in the active Oracle schema."
        if dialect == "sqlite":
            return (
                "SELECT type AS table_type, name AS table_name FROM sqlite_master "
                "WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%' ORDER BY name LIMIT 200;"
            ), "Listing SQLite tables and views."

    match = re.search(r"(?:describe|columns? (?:of|for)|schema (?:of|for))\s+([a-zA-Z0-9_.]+)", q)
    if match:
        table = match.group(1).strip(".")
        table = _sanitize_identifier(table)
        if "." in table:
            schema_name, table_name = table.split(".", 1)
        else:
            schema_name, table_name = "public", table
        if dialect == "postgresql":
            return (
                "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
                f"WHERE table_schema = '{schema_name}' AND table_name = '{table_name}' "
                "ORDER BY ordinal_position LIMIT 200;"
            ), f"Describing columns for {table}."
        if dialect == "mysql":
            return (
                "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
                f"WHERE table_schema = DATABASE() AND table_name = '{table_name}' "
                "ORDER BY ordinal_position LIMIT 200;"
            ), f"Describing columns for {table_name}."
        if dialect == "oracle":
            return (
                "SELECT column_name, data_type, nullable FROM user_tab_columns "
                f"WHERE table_name = UPPER('{table_name}') ORDER BY column_id"
            ), f"Describing columns for {table_name}."
        if dialect == "sqlite":
            return f"PRAGMA table_info('{table_name}');", f"Describing columns for {table_name}."

    match = re.search(r"(?:show|sample|preview).{0,20}(?:from\s+)?([a-zA-Z0-9_.]+)", q)
    if match:
        table = match.group(1).strip(".")
        table = _sanitize_identifier(table)
        if table not in {"rows", "records", "data", "table", "tables"}:
            ident = (
                ".".join(f'"{part}"' for part in table.split("."))
                if dialect != "mysql"
                else ".".join(f"`{part}`" for part in table.split("."))
            )
            if dialect == "oracle":
                return f"SELECT * FROM {ident} FETCH FIRST 20 ROWS ONLY", f"Previewing up to 20 rows from {table}."
            return f"SELECT * FROM {ident} LIMIT 20;", f"Previewing up to 20 rows from {table}."

    return None, (
        "I need either a clearer exploration request or GROQ_API_KEY for open-ended text-to-SQL. "
        "Try 'list all tables', 'describe <table>', or 'show rows from <table>'."
    )


_ORACLE_TO_STRFTIME_MAP = {
    "YYYY": "%Y", "YY": "%y",
    "MM": "%m", "MON": "%m",
    "DD": "%d",
    "HH24": "%H", "HH": "%I",
    "MI": "%M", "SS": "%S",
    "DAY": "%w", "DY": "%a",
    "MONTH": "%m",
}


def _oracle_to_sqlite_strftime(col: str, fmt: str) -> str:
    """Convert TO_CHAR(col, 'YYYY-MM') to strftime('%Y-%m', col)."""
    sqlite_fmt = fmt
    for oracle_tok, sqlite_tok in sorted(_ORACLE_TO_STRFTIME_MAP.items(), key=lambda x: -len(x[0])):
        sqlite_fmt = sqlite_fmt.replace(oracle_tok, sqlite_tok)
    return f"strftime('{sqlite_fmt}', {col.strip()})"


def _sanitize_sql_for_dialect(sql: str, dialect: str) -> str:
    normalized = sql.strip()
    if dialect == "sqlite":
        # Convert PostgreSQL-specific functions to SQLite equivalents
        normalized = re.sub(r"\bILIKE\b", "LIKE", normalized, flags=re.IGNORECASE)
        normalized = re.sub(
            r"\bNOW\(\)\s*-\s*INTERVAL\s*'([0-9]+)\s+day[s]?'\b",
            lambda m: f"datetime('now', '-{m.group(1)} days')",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(
            r"\bNOW\(\)\s*-\s*INTERVAL\s+'(\d+)\s+month[s]'\b",
            lambda m: f"datetime('now', '-{m.group(1)} months')",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(r"\bNOW\(\)\b", "datetime('now')", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bSYSDATE\b", "datetime('now')", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bCURRENT_DATE\b", "date('now')", normalized, flags=re.IGNORECASE)
        
        # Convert ADD_MONTHS to SQLite
        normalized = re.sub(
            r"\bADD_MONTHS\s*\(\s*SYSDATE\s*,\s*(-?\d+)\s*\)",
            lambda m: f"datetime('now', '{m.group(1)} months')",
            normalized,
            flags=re.IGNORECASE,
        )
        
        # Convert TO_CHAR to strftime
        normalized = re.sub(
            r"\bTO_CHAR\s*\(\s*([^,]+)\s*,\s*'([^']+)'\s*\)",
            lambda m: _oracle_to_sqlite_strftime(m.group(1), m.group(2)),
            normalized,
            flags=re.IGNORECASE,
        )
        
        # Convert TRUNC(date, 'MM') to strftime
        normalized = re.sub(
            r"\bTRUNC\s*\(\s*([^,]+)\s*,\s*'MM'\s*\)",
            r"strftime('%Y-%m-01', \1)",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(
            r"\bTRUNC\s*\(\s*([^,]+)\s*,\s*'YY'\s*\)",
            r"strftime('%Y-01-01', \1)",
            normalized,
            flags=re.IGNORECASE,
        )
        
        # Convert EXTRACT functions to SQLite equivalents
        normalized = re.sub(
            r"EXTRACT\(MONTH\s+FROM\s+([^)]+)\)",
            r"strftime('%m', \1)",
            normalized,
            flags=re.IGNORECASE
        )
        normalized = re.sub(
            r"EXTRACT\(YEAR\s+FROM\s+([^)]+)\)",
            r"strftime('%Y', \1)",
            normalized,
            flags=re.IGNORECASE
        )
        normalized = re.sub(
            r"EXTRACT\(DAY\s+FROM\s+([^)]+)\)",
            r"strftime('%d', \1)",
            normalized,
            flags=re.IGNORECASE
        )
        
        # Convert AGE function to SQLite date arithmetic
        normalized = re.sub(
            r"AGE\(([^,]+),\s*([^)]+)\)",
            r"julianday(\1) - julianday(\2)",
            normalized,
            flags=re.IGNORECASE
        )
        
        # Convert DATE_TRUNC to strftime
        normalized = re.sub(
            r"DATE_TRUNC\('month',\s*([^)]+)\)",
            r"strftime('%Y-%m-01', \1)",
            normalized,
            flags=re.IGNORECASE
        )
        normalized = re.sub(
            r"DATE_TRUNC\(\s*'month'\s*,\s*([^)]+)\)",
            r"strftime('%Y-%m-01', \1)",
            normalized,
            flags=re.IGNORECASE
        )
        
        # Convert INTERVAL 'N' month to SQLite
        normalized = re.sub(
            r"INTERVAL\s+'(\d+)'\s+MONTH",
            lambda m: f"{m.group(1)} months",
            normalized,
            flags=re.IGNORECASE,
        )
        
    if dialect == "oracle":
        normalized = re.sub(r"\bLIMIT\s+(\d+)\b", r"FETCH FIRST \1 ROWS ONLY", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bILIKE\b", "LIKE", normalized, flags=re.IGNORECASE)
        # Convert PostgreSQL DATE_TRUNC to Oracle TRUNC
        normalized = re.sub(
            r"DATE_TRUNC\(\s*'month'\s*,\s*([^)]+)\)",
            r"TRUNC(\1, 'MM')",
            normalized,
            flags=re.IGNORECASE
        )
        normalized = re.sub(
            r"DATE_TRUNC\(\s*'year'\s*,\s*([^)]+)\)",
            r"TRUNC(\1, 'YY')",
            normalized,
            flags=re.IGNORECASE
        )
        # Remove trailing semicolons
        normalized = normalized.rstrip().rstrip(";").rstrip()
    return normalized


def _ask_groq_for_sql(question: str, schema_hint: str, db_type: str, prompt_manager=None) -> str:
    """Use Groq LLM to convert a natural language question to SQL."""
    dialect_note = ""
    if db_type in ("mysql",):
        dialect_note = "Use MySQL syntax."
    elif db_type in ("sqlserver",):
        dialect_note = "Use T-SQL (SQL Server) syntax."
    elif db_type in ("oracle",):
        dialect_note = (
            "Use Oracle SQL syntax. CRITICAL RULES for Oracle:\n"
            "- Use FETCH FIRST N ROWS ONLY instead of LIMIT\n"
            "- Use TRUNC(date_column, 'MM') for month truncation, NOT DATE_TRUNC\n"
            "- Use TO_CHAR(date_column, 'YYYY-MM') for formatting\n"
            "- Use SYSDATE instead of NOW() or CURRENT_DATE\n"
            "- Use ADD_MONTHs(SYSDATE, -N) for date arithmetic\n"
            "- Do NOT use semicolons at the end of queries\n"
            "- Use column aliases without quotes\n"
        )
    elif db_type in ("sqlite",):
        dialect_note = (
            "Use SQLite syntax. CRITICAL RULES for SQLite:\n"
            "- Use strftime('%Y-%m', date_column) instead of TO_CHAR or DATE_TRUNC\n"
            "- Use datetime('now') instead of SYSDATE or NOW()\n"
            "- Use date(date_column, 'start of month') for month truncation\n"
            "- Use LIMIT N instead of FETCH FIRST N ROWS ONLY\n"
            "- Do NOT use ADD_MONTHS, INTERVAL, EXTRACT, or AGE functions\n"
            "- Use date(date_column, '+N months') for date arithmetic\n"
            "- Use CAST(column AS REAL) for decimal division\n"
        )
    else:
        dialect_note = "Use PostgreSQL syntax."

    prompt = f"""You are a SQL expert. Convert the user's question into a safe, read-only SQL SELECT query.
{dialect_note}

DATABASE SCHEMA:
{schema_hint}

RULES:
- Only generate SELECT statements. Never INSERT, UPDATE, DELETE, DROP, or ALTER.
- Return ONLY the raw SQL query, no explanation, no markdown, no code fences.
- Do NOT include semicolons at the end of the query.
- If using JOINs, qualify all column names with table aliases to avoid ambiguity.
- Limit results to 200 rows maximum (use FETCH FIRST 200 ROWS ONLY for Oracle, LIMIT 200 for others).
- If the question cannot be answered with the available schema, return: SELECT 'Query not possible with available schema' AS message;

USER QUESTION: {question}

SQL QUERY:"""

    # Use orchestrator if available, fall back to direct Groq call
    completion = None
    try:
        from .ai_orchestrator import AIOrchestrator
        orchestrator = AIOrchestrator()
        result = orchestrator.execute_sync(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=400,
            model=get_groq_model(),
        )
        completion = result
    except Exception as e:
        logger.debug(f"Primary completion failed, using fallback: {e}")
        completion = execute_groq_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=400,
            model=get_groq_model(),
        )
    sql = completion.choices[0].message.content.strip()
    # Strip markdown fences if model adds them
    if sql.startswith("```"):
        sql = sql.split("```")[1]
        if sql.lower().startswith("sql"):
            sql = sql[3:]
    return _sanitize_sql_for_dialect(sql, db_type).strip()


def _ask_groq_for_mongo(question: str, collections: list) -> dict:
    """Use Groq LLM to convert a natural language question to a MongoDB query."""
    prompt = f"""You are a MongoDB expert. Convert the user's question into a MongoDB find query.

AVAILABLE COLLECTIONS: {', '.join(collections[:20])}

RULES:
- Return ONLY valid JSON with keys: "collection" (string), "filter" (object), "projection" (object or null), "limit" (integer max 200)
- Only read operations. No insert/update/delete.
- If not possible, return: {{"collection": "", "filter": {{}}, "projection": null, "limit": 1, "error": "Not possible"}}

USER QUESTION: {question}

JSON:"""

    completion = None
    try:
        from .ai_orchestrator import AIOrchestrator
        orchestrator = AIOrchestrator()
        result = orchestrator.execute_sync(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300,
            model=get_groq_model(),
        )
        completion = result
    except Exception as e:
        logger.debug(f"Primary completion failed, using fallback: {e}")
        completion = execute_groq_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300,
            model=get_groq_model(),
        )
    import json
    raw = completion.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.lower().startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def run_nlq(user_id: str, question: str, supabase) -> dict:
    """
    Main entry point: resolve user's DB connection, generate query via AI, execute, return results.
    """
    # 1. Get user's DB connection
    conn_resp = supabase.table("database_connections").select("*").eq("user_id", user_id).limit(1).execute()
    if not (hasattr(conn_resp, "data") and conn_resp.data):
        return {"error": "No database connection configured. Please set up your connection in Settings.", "rows": [], "sql": None}

    from .connection_crypto import maybe_decrypt_connection_row
    conn_info = maybe_decrypt_connection_row(conn_resp.data[0])
    db_type = conn_info.get("db_type", "postgresql").lower()
    credentials = conn_info.get("credentials", "")
    connection_method = conn_info.get("connection_method", "direct")
    connection_options = conn_info.get("connection_options") or {}

    # 2. MongoDB path
    if db_type == "mongodb":
        return _run_mongo_nlq(question, credentials)

    # 3. SQL path
    from sqlalchemy import text
    from ..services.etl_service import _get_free_local_port, _start_ssh_tunnel, _replace_db_url_host_port
    from ..services.connection_pool import get_engine

    tunnel_proc = None
    try:
        db_url = credentials
        if connection_method == "ssh_tunnel":
            ssh_host = connection_options.get("ssh_host") or conn_info.get("host")
            ssh_user = connection_options.get("ssh_user")
            remote_host = connection_options.get("remote_db_host") or conn_info.get("host")
            remote_port = conn_info.get("port")
            local_port = _get_free_local_port()
            tunnel_proc = _start_ssh_tunnel(
                ssh_host=str(ssh_host), ssh_user=str(ssh_user),
                remote_host=str(remote_host), remote_port=int(remote_port), local_port=int(local_port)
            )
            db_url = _replace_db_url_host_port(credentials, "127.0.0.1", int(local_port))

        engine = get_engine(db_url, db_type)
        schema_hint = _get_db_schema_hint(engine)
        assistant_note = "I generated a read-only query from your question and ran it against the connected database."
        sql = None

        # Enterprise: Load semantic layer for business-friendly schema context
        semantic_ctx = ""
        try:
            from .semantic_layer import SemanticLayer
            sem = SemanticLayer(supabase, user_id)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(sem.load_mappings())
            except RuntimeError:
                pass
            if sem.has_mappings():
                semantic_ctx = sem.get_schema_context()
        except Exception as e:
            logger.debug(f"Semantic layer unavailable: {e}")

        # Enterprise: Use prompt manager for SQL generation
        pm = None
        try:
            from .prompt_manager import PromptManager
            pm = PromptManager(supabase)
        except Exception as e:
            logger.debug(f"Import failed (optional dependency): {e}")

        try:
            sql = _ask_groq_for_sql(question, schema_hint, db_type, prompt_manager=pm)
        except Exception as model_error:
            logger.warning(f"NLQ model unavailable, using deterministic fallback: {model_error}")

        if not sql:
            sql, assistant_note = _fallback_sql_for_question(question, engine)

        if sql:
            sql = _sanitize_sql_for_dialect(sql, db_type)

        if not sql:
            friendly = (
                "Could not generate a valid SQL response for that question. "
                "Please try a more specific question or verify your database connection."
            )
            return {
                "error": friendly,
                "answer": friendly,
                "rows": [],
                "columns": [],
                "row_count": 0,
                "sql": None,
                "schema_used": schema_hint,
            }

        def _execute_readonly(query: str):
            sql_upper = query.strip().upper()
            allowed_starts = ("SELECT", "WITH", "PRAGMA")
            if not sql_upper.startswith(allowed_starts):
                raise ValueError("Only read-only SELECT or PRAGMA queries are permitted.")
            # Strip SQL comments and string literals before checking for forbidden keywords
            # to prevent bypass via /*INSERT*/ or 'DELETE'
            import re as _re
            stripped = _re.sub(r'--.*$', '', sql_upper, flags=_re.MULTILINE)
            stripped = _re.sub(r'/\*.*?\*/', '', stripped, flags=_re.DOTALL)
            stripped = _re.sub(r"'[^']*'", '', stripped)
            forbidden = ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "GRANT", "REVOKE")
            # Use word boundary matching to prevent false positives on column aliases like "status"
            for tok in forbidden:
                if _re.search(rf'\b{tok}\b', stripped):
                    raise ValueError(f"Query contains forbidden keyword: {tok}")
            with engine.connect() as conn:
                result = conn.execute(text(query))
                cols = list(result.keys())
                # normalize column names to lowercase for stable keys across DB drivers
                cols_lower = [c.lower() for c in cols]
                raw_rows = result.fetchmany(200)
                out_rows = []
                from decimal import Decimal as _Decimal
                for row in raw_rows:
                    record = {}
                    for col, val in zip(cols_lower, row):
                        if hasattr(val, "isoformat"):
                            record[col] = val.isoformat()
                        elif isinstance(val, (bytes, bytearray)):
                            record[col] = val.decode("utf-8", errors="replace")
                        elif isinstance(val, _Decimal):
                            record[col] = float(val)
                        elif hasattr(val, "__float__"):
                            try:
                                record[col] = float(val)
                            except (TypeError, ValueError):
                                record[col] = str(val)
                        else:
                            record[col] = val
                    # provide common aliases for compatibility
                    if "name" in record and "table_name" not in record:
                        record["table_name"] = record["name"]
                    if "table_name" in record and "name" not in record:
                        record["name"] = record["table_name"]
                    out_rows.append(record)
                return cols_lower, out_rows

        try:
            columns, rows = _execute_readonly(sql)
        except Exception as exec_err:
            logger.warning(f"NLQ primary query failed, retrying fallback: {exec_err}")
            fb_sql, fb_note = _fallback_sql_for_question(question, engine)
            if not fb_sql:
                raise exec_err
            sql = fb_sql
            assistant_note = fb_note
            columns, rows = _execute_readonly(sql)

        from .chart_service import build_chart_from_rows
        chart_spec = build_chart_from_rows(rows, columns, title=f"Results: {question[:60]}")

        # Enterprise: Translate results using semantic layer
        if sem and sem.has_mappings():
            try:
                columns, rows = sem.reverse_translate_results(rows, columns)
            except Exception as e:
                logger.debug(f"Reverse translation failed (non-critical): {e}")  # Keep raw column names on translation failure

        # Enterprise: Log NLQ query for governance
        try:
            from .audit_service import log_config_change
            log_config_change(
                supabase, user_id, "query", "nlq_query",
                {"question": question, "sql": sql, "row_count": len(rows)}
            )
        except Exception as e:
            logger.debug(f"Audit logging failed (non-critical): {e}")

        if os.environ.get("NLQ_DEBUG"):
            logger.debug("NLQ debug sql: %s", sql)
            logger.debug("NLQ debug columns: %s", columns)
            logger.debug("NLQ debug rows: %s", rows)

        return {
            "answer": assistant_note,
            "sql": sql,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "schema_used": schema_hint,
            "chart": chart_spec,
        }

    except Exception as e:
        logger.error(f"NLQ error for user {user_id}: {e}")
        return {
            "error": (
                "Unable to execute the requested query. "
                "Please try again with a different question or check your database connection."
            ),
            "rows": [],
            "columns": [],
            "row_count": 0,
            "sql": None,
        }
    finally:
        if tunnel_proc:
            try:
                tunnel_proc.terminate()
                tunnel_proc.wait(timeout=5)
            except Exception as e:
                logger.debug(f"Tunnel terminate failed (non-critical): {e}")


def _run_mongo_nlq(question: str, connection_string: str) -> dict:
    """Execute a natural language query against MongoDB."""
    try:
        import pymongo
        client = pymongo.MongoClient(connection_string, serverSelectionTimeoutMS=8000)
        db_name = pymongo.uri_parser.parse_uri(connection_string).get("database") or "test"
        db = client[db_name]
        collections = db.list_collection_names()

        query_spec = _ask_groq_for_mongo(question, collections)

        if query_spec.get("error"):
            return {"error": query_spec["error"], "rows": [], "sql": None}

        collection_name = query_spec.get("collection", "")
        if not collection_name or collection_name not in collections:
            return {"error": f"Collection '{collection_name}' not found.", "rows": [], "sql": None}

        col = db[collection_name]
        cursor = col.find(
            query_spec.get("filter", {}),
            query_spec.get("projection"),
        ).limit(query_spec.get("limit", 50))

        rows = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            rows.append(doc)

        columns = list(rows[0].keys()) if rows else []
        return {
            "sql": f"db.{collection_name}.find({query_spec.get('filter', {})})",
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "mongo_query": query_spec,
        }
    except ImportError:
        return {"error": "pymongo not installed. Run: pip install pymongo", "rows": [], "sql": None}
    except Exception as e:
        logger.debug(f"MongoDB query failed: {e}")
        return {"error": "MongoDB query failed.", "rows": [], "sql": None}
