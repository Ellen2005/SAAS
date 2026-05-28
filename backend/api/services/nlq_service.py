"""
Natural Language Query (NLQ) Service
Converts plain-English (or French) questions into SQL/MongoDB queries,
executes them against the user's connected database, and returns results.
"""
import os
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
            except Exception:
                schema_lines.append(f"  {table}(...)")
        return "\n".join(schema_lines)
    except Exception:
        return "(schema unavailable)"


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

    import re
    match = re.search(r"(?:describe|columns? (?:of|for)|schema (?:of|for))\s+([a-zA-Z0-9_.]+)", q)
    if match:
        table = match.group(1).strip(".")
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
            return f"PRAGMA table_info({table_name!r});", f"Describing columns for {table_name}."

    match = re.search(r"(?:show|sample|preview).{0,20}(?:from\s+)?([a-zA-Z0-9_.]+)", q)
    if match:
        table = match.group(1).strip(".")
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


def _ask_groq_for_sql(question: str, schema_hint: str, db_type: str) -> str:
    """Use Groq LLM to convert a natural language question to SQL."""
    dialect_note = ""
    if db_type in ("mysql",):
        dialect_note = "Use MySQL syntax."
    elif db_type in ("sqlserver",):
        dialect_note = "Use T-SQL (SQL Server) syntax."
    elif db_type in ("oracle",):
        dialect_note = "Use Oracle SQL syntax."
    else:
        dialect_note = "Use PostgreSQL syntax."

    prompt = f"""You are a SQL expert. Convert the user's question into a safe, read-only SQL SELECT query.
{dialect_note}

DATABASE SCHEMA:
{schema_hint}

RULES:
- Only generate SELECT statements. Never INSERT, UPDATE, DELETE, DROP, or ALTER.
- Return ONLY the raw SQL query, no explanation, no markdown, no code fences.
- Limit results to 200 rows maximum using LIMIT 200 (or TOP 200 for SQL Server).
- If the question cannot be answered with the available schema, return: SELECT 'Query not possible with available schema' AS message;

USER QUESTION: {question}

SQL QUERY:"""

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
    return sql.strip()


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
    from sqlalchemy import create_engine, text
    from ..services.etl_service import _get_free_local_port, _start_ssh_tunnel, _replace_db_url_host_port

    tunnel_proc = None
    engine = None
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

        from .connection_utils import normalize_credentials, sqlalchemy_engine_kwargs
        engine = create_engine(
            normalize_credentials(db_url, db_type),
            **sqlalchemy_engine_kwargs(db_url, db_type),
        )
        schema_hint = _get_db_schema_hint(engine)
        assistant_note = "I generated a read-only query from your question and ran it against the connected database."
        sql = None
        try:
            sql = _ask_groq_for_sql(question, schema_hint, db_type)
        except Exception as model_error:
            logger.warning(f"NLQ model unavailable, using deterministic fallback: {model_error}")

        if not sql:
            sql, assistant_note = _fallback_sql_for_question(question, engine)

        if not sql:
            return {
                "answer": assistant_note,
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
            forbidden = ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "GRANT", "REVOKE")
            if any(tok in sql_upper for tok in forbidden):
                raise ValueError("Query contains forbidden keywords.")
            with engine.connect() as conn:
                result = conn.execute(text(query))
                cols = list(result.keys())
                raw_rows = result.fetchmany(200)
                out_rows = []
                for row in raw_rows:
                    record = {}
                    for col, val in zip(cols, row):
                        if hasattr(val, "isoformat"):
                            record[col] = val.isoformat()
                        elif isinstance(val, (bytes, bytearray)):
                            record[col] = val.decode("utf-8", errors="replace")
                        else:
                            record[col] = val
                    out_rows.append(record)
                return cols, out_rows

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
        return {"error": str(e), "rows": [], "sql": None}
    finally:
        if engine:
            try:
                engine.dispose()
            except Exception:
                pass
        if tunnel_proc:
            try:
                tunnel_proc.terminate()
                tunnel_proc.wait(timeout=5)
            except Exception:
                pass


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
        return {"error": str(e), "rows": [], "sql": None}
