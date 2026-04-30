"""
Natural Language Query (NLQ) Service
Converts plain-English (or French) questions into SQL/MongoDB queries,
executes them against the user's connected database, and returns results.
"""
import os
import logging
from datetime import datetime

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


def _ask_groq_for_sql(question: str, schema_hint: str, db_type: str) -> str:
    """Use Groq LLM to convert a natural language question to SQL."""
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise RuntimeError("GROQ_API_KEY not configured")

    from groq import Groq
    client = Groq(api_key=groq_api_key)

    dialect_note = ""
    if db_type in ("mysql",):
        dialect_note = "Use MySQL syntax."
    elif db_type in ("sqlserver",):
        dialect_note = "Use T-SQL (SQL Server) syntax."
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

    completion = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=400,
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
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise RuntimeError("GROQ_API_KEY not configured")

    from groq import Groq
    client = Groq(api_key=groq_api_key)

    prompt = f"""You are a MongoDB expert. Convert the user's question into a MongoDB find query.

AVAILABLE COLLECTIONS: {', '.join(collections[:20])}

RULES:
- Return ONLY valid JSON with keys: "collection" (string), "filter" (object), "projection" (object or null), "limit" (integer max 200)
- Only read operations. No insert/update/delete.
- If not possible, return: {{"collection": "", "filter": {{}}, "projection": null, "limit": 1, "error": "Not possible"}}

USER QUESTION: {question}

JSON:"""

    completion = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=300,
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

    conn_info = conn_resp.data[0]
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

        engine = create_engine(db_url, connect_args={"connect_timeout": 10}, pool_pre_ping=True)
        schema_hint = _get_db_schema_hint(engine)
        sql = _ask_groq_for_sql(question, schema_hint, db_type)

        # Safety check — block any non-SELECT
        sql_upper = sql.strip().upper()
        if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
            return {"error": "Only SELECT queries are permitted.", "rows": [], "sql": sql}

        with engine.connect() as conn:
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows = [dict(zip(columns, row)) for row in result.fetchmany(200)]

        return {
            "sql": sql,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "schema_used": schema_hint,
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
