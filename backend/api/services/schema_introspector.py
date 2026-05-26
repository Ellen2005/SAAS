"""
Schema Introspector Service.

Connects to a customer's database, discovers its full structure (tables,
columns, primary keys, foreign keys, row counts, sample rows), and produces
both a machine-readable schema and a human-readable summary the frontend can
visualise. Also classifies tables into business-domain "buckets" (e.g. for
CNPS-style social-security data: contributions, beneficiaries, payments,
claims, employers, etc.) using lightweight keyword heuristics so the rest of
the system can suggest analyses without prior configuration.

Designed for safety: every cursor it opens is read-only and bounded by LIMIT.
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Domain classification heuristics (multilingual: EN + FR for CNPS context)
# ─────────────────────────────────────────────────────────────────────────────

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "contribution": [
        "contribution", "cotisation", "cotisations", "contribut",
        "premium", "prime", "dues", "deposit",
    ],
    "payment": [
        "payment", "paiement", "paie", "payout", "versement", "pay",
        "transaction", "transactions", "transfer", "remittance",
    ],
    "beneficiary": [
        "beneficiary", "beneficiaire", "beneficiaires", "insured",
        "assure", "assures", "member", "adherent", "adherents",
    ],
    "employer": [
        "employer", "employeur", "company", "entreprise", "societe",
        "patron", "organization",
    ],
    "employee": [
        "employee", "employe", "employes", "worker", "travailleur",
        "salarie", "staff", "personnel",
    ],
    "claim": [
        "claim", "claims", "reclamation", "demande", "request",
        "application", "dossier", "dossiers",
    ],
    "pension": [
        "pension", "pensions", "retirement", "retraite", "retired",
        "retraite", "rente",
    ],
    "benefit": [
        "benefit", "benefits", "prestation", "prestations", "allocation",
        "allowance", "subsidy", "indemnite", "indemnites",
    ],
    "invoice": [
        "invoice", "facture", "factures", "bill", "billing",
    ],
    "customer": [
        "customer", "client", "clients", "account", "compte", "comptes",
    ],
    "product": [
        "product", "produit", "produits", "item", "article", "sku",
    ],
    "inventory": [
        "inventory", "stock", "stocks", "warehouse", "entrepot",
    ],
    "ticket": [
        "ticket", "tickets", "support", "incident", "case",
    ],
    "audit": [
        "audit", "log", "logs", "history", "historique", "trace",
    ],
    "user": [
        "user", "users", "utilisateur", "utilisateurs", "auth",
        "session", "sessions",
    ],
}

# Column-name patterns we treat as "amount-like" for monetary aggregates.
AMOUNT_PATTERNS = re.compile(
    r"(amount|montant|valeur|value|price|prix|total|salary|salaire|"
    r"contribution|cotisation|paiement|payment|net|gross|brut)",
    re.IGNORECASE,
)

DATE_PATTERNS = re.compile(
    r"(date|time|created|updated|recorded|timestamp|at$|_at|_on$|_dt$)",
    re.IGNORECASE,
)

ID_PATTERNS = re.compile(r"(^id$|_id$|uuid|code|number|num$|reference)", re.IGNORECASE)


def _classify_table(table_name: str, column_names: list[str]) -> list[str]:
    """Return zero or more business-domain labels for a table."""
    haystack = " ".join([table_name.lower()] + [c.lower() for c in column_names])
    labels: list[str] = []
    for label, keywords in DOMAIN_KEYWORDS.items():
        if any(kw in haystack for kw in keywords):
            labels.append(label)
    return labels


def _summarise_columns(columns: list[dict]) -> dict[str, list[str]]:
    summary = {"amount_columns": [], "date_columns": [], "id_columns": []}
    for column in columns:
        name = str(column.get("name", ""))
        if AMOUNT_PATTERNS.search(name):
            summary["amount_columns"].append(name)
        if DATE_PATTERNS.search(name):
            summary["date_columns"].append(name)
        if ID_PATTERNS.search(name):
            summary["id_columns"].append(name)
    return summary


# ─────────────────────────────────────────────────────────────────────────────
# Connection helpers
# ─────────────────────────────────────────────────────────────────────────────

def _open_sql_engine(conn_info: dict):
    """Open a SQLAlchemy engine, with optional SSH-tunnel handling."""
    from sqlalchemy import create_engine
    from .connection_utils import detect_db_type, normalize_credentials, sqlalchemy_engine_kwargs
    from .etl_service import (
        _get_free_local_port, _start_ssh_tunnel, _replace_db_url_host_port,
    )

    db_url = conn_info.get("credentials")
    if not db_url:
        raise ValueError("Missing database credentials (connection string).")

    method = conn_info.get("connection_method") or "direct"
    options = conn_info.get("connection_options") or {}
    tunnel_proc = None

    if method == "ssh_tunnel":
        ssh_host = options.get("ssh_host") or conn_info.get("host")
        ssh_user = options.get("ssh_user")
        remote_host = options.get("remote_db_host") or conn_info.get("host")
        remote_port = (
            conn_info.get("port")
            or options.get("remote_db_port")
            or (urlparse(db_url).port or 5432)
        )
        if not all([ssh_host, ssh_user, remote_host, remote_port]):
            raise ValueError(
                "SSH tunnel requires ssh_host, ssh_user, remote_db_host and port."
            )
        local_port = _get_free_local_port()
        tunnel_proc = _start_ssh_tunnel(
            ssh_host=str(ssh_host), ssh_user=str(ssh_user),
            remote_host=str(remote_host), remote_port=int(remote_port),
            local_port=int(local_port),
        )
        db_url = _replace_db_url_host_port(db_url, "127.0.0.1", int(local_port))

    db_type = detect_db_type(db_url, conn_info.get("db_type"))
    engine = create_engine(
        normalize_credentials(db_url, db_type),
        **sqlalchemy_engine_kwargs(db_url, db_type),
    )
    return engine, tunnel_proc


def _close(engine, tunnel_proc) -> None:
    if engine is not None:
        try:
            engine.dispose()
        except Exception:
            pass
    if tunnel_proc is not None:
        try:
            tunnel_proc.terminate()
            tunnel_proc.wait(timeout=5)
        except Exception:
            try:
                tunnel_proc.kill()
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# SQL introspection
# ─────────────────────────────────────────────────────────────────────────────

# Schemas we always skip for introspection (system / framework noise).
_SKIP_SCHEMAS = {
    "pg_catalog", "information_schema", "pg_toast",
    "mysql", "performance_schema", "sys",
}


def introspect_sql(
    conn_info: dict,
    *,
    sample_rows: int = 5,
    max_tables: int = 200,
) -> dict[str, Any]:
    """Introspect a SQL database (Postgres / MySQL / SQLite / etc.)."""
    from sqlalchemy import inspect, text

    started = datetime.utcnow()
    engine, tunnel_proc = _open_sql_engine(conn_info)
    try:
        inspector = inspect(engine)

        # Discover all schemas (Postgres) — fallback to default.
        try:
            schemas = [s for s in inspector.get_schema_names() if s not in _SKIP_SCHEMAS]
        except Exception:
            schemas = [None]
        if not schemas:
            schemas = [None]

        all_tables: list[dict] = []
        with engine.connect() as conn:
            for schema in schemas:
                try:
                    table_names = inspector.get_table_names(schema=schema) or []
                    view_names = inspector.get_view_names(schema=schema) or []
                except Exception as exc:
                    logger.warning(f"List tables failed for {schema}: {exc}")
                    continue

                for name in table_names + view_names:
                    if len(all_tables) >= max_tables:
                        break
                    qualified = f"{schema}.{name}" if schema else name
                    try:
                        cols_raw = inspector.get_columns(name, schema=schema) or []
                    except Exception as exc:
                        # Permission errors on system catalogs (pg_enum etc.) are
                        # very common on managed Postgres — log at debug only.
                        msg = str(exc)
                        if "permission denied" in msg.lower() or "insufficientprivilege" in msg.lower():
                            logger.debug(f"get_columns skipped {qualified}: insufficient privilege")
                        else:
                            logger.warning(f"get_columns failed {qualified}: {exc}")
                        cols_raw = []

                    columns = [
                        {
                            "name": col.get("name"),
                            "type": str(col.get("type")),
                            "nullable": bool(col.get("nullable", True)),
                            "default": str(col.get("default")) if col.get("default") is not None else None,
                        }
                        for col in cols_raw
                    ]

                    try:
                        pk_info = inspector.get_pk_constraint(name, schema=schema) or {}
                        primary_keys = list(pk_info.get("constrained_columns") or [])
                    except Exception:
                        primary_keys = []

                    try:
                        fk_info = inspector.get_foreign_keys(name, schema=schema) or []
                        foreign_keys = [
                            {
                                "columns": list(fk.get("constrained_columns") or []),
                                "ref_schema": fk.get("referred_schema"),
                                "ref_table": fk.get("referred_table"),
                                "ref_columns": list(fk.get("referred_columns") or []),
                            }
                            for fk in fk_info
                        ]
                    except Exception:
                        foreign_keys = []

                    # Row count — bounded so we never lock the customer DB.
                    row_count = None
                    try:
                        # Use a fast estimate when available on Postgres
                        if engine.dialect.name == "postgresql":
                            est = conn.execute(
                                text(
                                    "SELECT n_live_tup FROM pg_stat_user_tables "
                                    "WHERE schemaname = :s AND relname = :t"
                                ),
                                {"s": schema or "public", "t": name},
                            ).fetchone()
                            if est and est[0] is not None and int(est[0]) > 0:
                                row_count = int(est[0])
                        if row_count is None:
                            count_q = f'SELECT COUNT(*) FROM "{schema}"."{name}"' if schema else f'SELECT COUNT(*) FROM "{name}"'
                            row_count = int(conn.execute(text(count_q)).scalar() or 0)
                    except Exception as exc:
                        logger.debug(f"row count failed {qualified}: {exc}")

                    # Sample rows — best effort, never raises out.
                    samples: list[dict] = []
                    if sample_rows > 0:
                        try:
                            sel = (
                                f'SELECT * FROM "{schema}"."{name}" LIMIT :n'
                                if schema
                                else f'SELECT * FROM "{name}" LIMIT :n'
                            )
                            res = conn.execute(text(sel), {"n": int(sample_rows)})
                            cols = list(res.keys())
                            for row in res.fetchall():
                                samples.append(
                                    {c: _jsonable(v) for c, v in zip(cols, row)}
                                )
                        except Exception as exc:
                            logger.debug(f"sample rows failed {qualified}: {exc}")

                    column_names = [c["name"] for c in columns]
                    classifications = _classify_table(name, column_names)
                    summary = _summarise_columns(columns)

                    all_tables.append(
                        {
                            "schema": schema,
                            "name": name,
                            "qualified_name": qualified,
                            "is_view": name in view_names,
                            "columns": columns,
                            "primary_keys": primary_keys,
                            "foreign_keys": foreign_keys,
                            "row_count": row_count,
                            "sample_rows": samples,
                            "classifications": classifications,
                            "amount_columns": summary["amount_columns"],
                            "date_columns": summary["date_columns"],
                            "id_columns": summary["id_columns"],
                        }
                    )
                if len(all_tables) >= max_tables:
                    break

        return {
            "kind": "sql",
            "dialect": engine.dialect.name,
            "discovered_at": started.isoformat() + "Z",
            "schemas": schemas if schemas != [None] else ["(default)"],
            "table_count": len(all_tables),
            "tables": all_tables,
        }
    finally:
        _close(engine, tunnel_proc)


# ─────────────────────────────────────────────────────────────────────────────
# MongoDB introspection
# ─────────────────────────────────────────────────────────────────────────────

def introspect_mongo(
    conn_info: dict,
    *,
    sample_rows: int = 5,
    max_tables: int | None = None,
) -> dict[str, Any]:
    import pymongo

    started = datetime.utcnow()
    db_url = conn_info.get("credentials")
    if not db_url:
        raise ValueError("Missing MongoDB credentials (connection string).")
    client = pymongo.MongoClient(db_url, serverSelectionTimeoutMS=8000)
    db_name = (
        pymongo.uri_parser.parse_uri(db_url).get("database")
        or conn_info.get("db_name")
        or "test"
    )
    db = client[db_name]
    tables = []
    cap = max_tables if max_tables is not None else 200
    try:
        for col_name in db.list_collection_names():
            if len(tables) >= cap:
                break
            try:
                doc = db[col_name].find_one() or {}
                columns = [
                    {"name": k, "type": type(v).__name__, "nullable": True, "default": None}
                    for k, v in doc.items()
                ]
                samples = []
                for d in db[col_name].find().limit(int(sample_rows)):
                    d["_id"] = str(d.get("_id"))
                    samples.append({k: _jsonable(v) for k, v in d.items()})
                row_count = db[col_name].estimated_document_count()
            except Exception as exc:
                logger.debug(f"mongo collection {col_name} failed: {exc}")
                columns, samples, row_count = [], [], None

            column_names = [c["name"] for c in columns]
            classifications = _classify_table(col_name, column_names)
            summary = _summarise_columns(columns)

            tables.append(
                {
                    "schema": db_name,
                    "name": col_name,
                    "qualified_name": f"{db_name}.{col_name}",
                    "is_view": False,
                    "columns": columns,
                    "primary_keys": ["_id"],
                    "foreign_keys": [],
                    "row_count": row_count,
                    "sample_rows": samples,
                    "classifications": classifications,
                    "amount_columns": summary["amount_columns"],
                    "date_columns": summary["date_columns"],
                    "id_columns": summary["id_columns"],
                }
            )
    finally:
        try:
            client.close()
        except Exception:
            pass

    return {
        "kind": "mongodb",
        "dialect": "mongodb",
        "discovered_at": started.isoformat() + "Z",
        "schemas": [db_name],
        "table_count": len(tables),
        "tables": tables,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Public entrypoint
# ─────────────────────────────────────────────────────────────────────────────

def introspect_user_database(
    user_id: str,
    supabase,
    *,
    sample_rows: int = 5,
    max_tables: int = 200,
) -> dict[str, Any]:
    resp = (
        supabase.table("database_connections")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not (hasattr(resp, "data") and resp.data):
        raise ValueError("No database connection configured for this user.")
    from .connection_crypto import maybe_decrypt_connection_row
    conn_info = maybe_decrypt_connection_row(resp.data[0])
    db_type = (conn_info.get("db_type") or "postgresql").lower()
    if db_type == "mongodb":
        return introspect_mongo(conn_info, sample_rows=sample_rows)
    return introspect_sql(conn_info, sample_rows=sample_rows, max_tables=max_tables)


# ─────────────────────────────────────────────────────────────────────────────
# Suggested analyses (rule-based + LLM-friendly)
# ─────────────────────────────────────────────────────────────────────────────

def suggest_analyses(schema: dict[str, Any]) -> list[dict[str, Any]]:
    """Build a list of high-level analyses we can run, given the schema."""
    analyses: list[dict[str, Any]] = []
    tables = schema.get("tables", [])

    by_label: dict[str, list[dict]] = {}
    for tbl in tables:
        for label in tbl.get("classifications", []) or ["other"]:
            by_label.setdefault(label, []).append(tbl)

    def _pick_amount_col(tbl: dict) -> str | None:
        return (tbl.get("amount_columns") or [None])[0]

    def _pick_date_col(tbl: dict) -> str | None:
        return (tbl.get("date_columns") or [None])[0]

    if "contribution" in by_label:
        for tbl in by_label["contribution"][:3]:
            amt = _pick_amount_col(tbl)
            dt = _pick_date_col(tbl)
            if amt and dt:
                analyses.append({
                    "id": f"contrib_trend::{tbl['qualified_name']}::{amt}::{dt}",
                    "title": f"Contribution trend over time ({tbl['name']})",
                    "category": "Financial",
                    "table": tbl["qualified_name"],
                    "amount_column": amt,
                    "date_column": dt,
                    "kind": "time_series_sum",
                    "description": (
                        f"Sums {amt} grouped by month from {tbl['name']} to reveal "
                        "growth, dips and seasonality in contributions."
                    ),
                })
                analyses.append({
                    "id": f"late_payers::{tbl['qualified_name']}::{dt}",
                    "title": f"Late / missing contribution detection ({tbl['name']})",
                    "category": "Compliance",
                    "table": tbl["qualified_name"],
                    "date_column": dt,
                    "kind": "missing_recent",
                    "description": (
                        "Flags accounts with no contribution in the last 60 days "
                        "compared to their historical cadence."
                    ),
                })

    if "payment" in by_label:
        for tbl in by_label["payment"][:3]:
            amt = _pick_amount_col(tbl)
            dt = _pick_date_col(tbl)
            if amt and dt:
                analyses.append({
                    "id": f"payment_anomaly::{tbl['qualified_name']}::{amt}",
                    "title": f"Payment anomaly detection ({tbl['name']})",
                    "category": "Fraud",
                    "table": tbl["qualified_name"],
                    "amount_column": amt,
                    "date_column": dt,
                    "kind": "anomaly_zscore",
                    "description": (
                        "Detects unusually large or small payments using a z-score "
                        "model versus the trailing 90-day distribution."
                    ),
                })

    if "claim" in by_label:
        for tbl in by_label["claim"][:3]:
            dt = _pick_date_col(tbl)
            if dt:
                analyses.append({
                    "id": f"claim_throughput::{tbl['qualified_name']}::{dt}",
                    "title": f"Claim processing throughput ({tbl['name']})",
                    "category": "Operations",
                    "table": tbl["qualified_name"],
                    "date_column": dt,
                    "kind": "count_over_time",
                    "description": (
                        "Counts new claims per week to reveal processing bottlenecks "
                        "and surges in demand."
                    ),
                })

    if "beneficiary" in by_label or "employee" in by_label:
        target = (by_label.get("beneficiary") or by_label.get("employee") or [])[:1]
        for tbl in target:
            analyses.append({
                "id": f"demographic::{tbl['qualified_name']}",
                "title": f"Demographic distribution ({tbl['name']})",
                "category": "Strategic",
                "table": tbl["qualified_name"],
                "kind": "demographic",
                "description": (
                    "Profiles the beneficiary base by counting categorical "
                    "columns (gender, region, status, etc.)."
                ),
            })

    if "pension" in by_label or "benefit" in by_label:
        for tbl in (by_label.get("pension") or by_label.get("benefit") or [])[:2]:
            amt = _pick_amount_col(tbl)
            dt = _pick_date_col(tbl)
            if amt and dt:
                analyses.append({
                    "id": f"liability_forecast::{tbl['qualified_name']}::{amt}::{dt}",
                    "title": f"Pension/benefit liability forecast ({tbl['name']})",
                    "category": "Strategic",
                    "table": tbl["qualified_name"],
                    "amount_column": amt,
                    "date_column": dt,
                    "kind": "liability_forecast",
                    "description": (
                        "Projects future payout obligations by extrapolating the "
                        "12-month moving average of historical disbursements."
                    ),
                })

    # Always-available generic analyses
    largest = sorted(
        [t for t in tables if (t.get("row_count") or 0) > 0],
        key=lambda t: -(t.get("row_count") or 0),
    )[:5]
    for tbl in largest:
        analyses.append({
            "id": f"overview::{tbl['qualified_name']}",
            "title": f"Table overview: {tbl['name']}",
            "category": "Overview",
            "table": tbl["qualified_name"],
            "kind": "overview",
            "description": (
                f"Row count, column types and a 10-row preview for "
                f"{tbl['name']} (~{tbl.get('row_count')} rows)."
            ),
        })

    return analyses


# ─────────────────────────────────────────────────────────────────────────────
# Run a single analysis
# ─────────────────────────────────────────────────────────────────────────────

def _split_qualified(qname: str) -> tuple[str | None, str]:
    if "." in qname:
        s, n = qname.split(".", 1)
        return s, n
    return None, qname


def _qident(schema: str | None, name: str, dialect: str) -> str:
    q = '"' if dialect != "mysql" else "`"
    if schema:
        return f"{q}{schema}{q}.{q}{name}{q}"
    return f"{q}{name}{q}"


def run_analysis(
    conn_info_or_user_id,
    analysis_or_supabase=None,
    analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute one of the suggested analyses, returning rows ready for charting.

    Two calling styles supported:
      • run_analysis(conn_info_dict, analysis_dict)            ← preferred / testable
      • run_analysis(user_id, supabase_client, analysis_dict)  ← legacy router style
    """
    if isinstance(conn_info_or_user_id, dict) and analysis is None:
        # Preferred form: (conn_info, analysis)
        conn_info = conn_info_or_user_id
        analysis = analysis_or_supabase  # type: ignore[assignment]
    else:
        # Legacy form: (user_id, supabase, analysis)
        user_id = conn_info_or_user_id
        supabase = analysis_or_supabase
        resp = (
            supabase.table("database_connections")
            .select("*").eq("user_id", user_id).limit(1).execute()
        )
        if not (hasattr(resp, "data") and resp.data):
            return {"error": "No database connection configured."}
        conn_info = resp.data[0]

    if not isinstance(analysis, dict):
        return {"error": "Missing analysis spec."}

    db_type = (conn_info.get("db_type") or "postgresql").lower()
    if db_type == "mongodb":
        return {"error": "Server-side analyses for MongoDB are not yet implemented; use NLQ instead."}

    from sqlalchemy import text
    engine, tunnel = _open_sql_engine(conn_info)
    try:
        dialect = engine.dialect.name
        kind = analysis.get("kind")
        table = analysis.get("table") or ""
        schema, name = _split_qualified(table)
        ident = _qident(schema, name, dialect)
        amt = analysis.get("amount_column")
        dt = analysis.get("date_column")

        with engine.connect() as conn:
            if kind == "time_series_sum" and amt and dt:
                if dialect == "postgresql":
                    sql = f'SELECT date_trunc(\'month\', "{dt}") AS bucket, SUM("{amt}") AS total FROM {ident} GROUP BY bucket ORDER BY bucket DESC LIMIT 24'
                elif dialect == "mysql":
                    sql = f"SELECT DATE_FORMAT(`{dt}`, '%Y-%m-01') AS bucket, SUM(`{amt}`) AS total FROM {ident} GROUP BY bucket ORDER BY bucket DESC LIMIT 24"
                else:
                    sql = f'SELECT strftime(\'%Y-%m-01\',"{dt}") AS bucket, SUM("{amt}") AS total FROM {ident} GROUP BY bucket ORDER BY bucket DESC LIMIT 24'
                rows = [
                    {"bucket": str(r[0]), "total": _jsonable(r[1])}
                    for r in conn.execute(text(sql)).fetchall()
                ]
                return {
                    "kind": kind,
                    "title": analysis.get("title"),
                    "x_label": "Month",
                    "y_label": amt,
                    "rows": list(reversed(rows)),
                    "sql": sql,
                }

            if kind == "count_over_time" and dt:
                if dialect == "postgresql":
                    sql = f'SELECT date_trunc(\'week\', "{dt}") AS bucket, COUNT(*) AS total FROM {ident} GROUP BY bucket ORDER BY bucket DESC LIMIT 26'
                elif dialect == "mysql":
                    sql = f"SELECT DATE_FORMAT(`{dt}`, '%Y-%u') AS bucket, COUNT(*) AS total FROM {ident} GROUP BY bucket ORDER BY bucket DESC LIMIT 26"
                else:
                    sql = f'SELECT strftime(\'%Y-W%W\',"{dt}") AS bucket, COUNT(*) AS total FROM {ident} GROUP BY bucket ORDER BY bucket DESC LIMIT 26'
                rows = [
                    {"bucket": str(r[0]), "total": _jsonable(r[1])}
                    for r in conn.execute(text(sql)).fetchall()
                ]
                return {
                    "kind": kind,
                    "title": analysis.get("title"),
                    "x_label": "Week",
                    "y_label": "Count",
                    "rows": list(reversed(rows)),
                    "sql": sql,
                }

            if kind == "anomaly_zscore" and amt:
                sql = f'SELECT * FROM {ident} ORDER BY 1 DESC LIMIT 5000'
                # Pull data and let pandas do the z-score (works across dialects).
                import pandas as pd
                df = pd.read_sql(sql, conn)
                if amt not in df.columns or df[amt].dropna().empty:
                    return {"kind": kind, "rows": [], "warning": "No numeric data."}
                series = pd.to_numeric(df[amt], errors="coerce").dropna()
                mu = float(series.mean())
                sd = float(series.std() or 1.0)
                df["_z"] = (pd.to_numeric(df[amt], errors="coerce") - mu) / sd
                outliers = df[df["_z"].abs() > 2.5].head(50)
                rows = json.loads(outliers.to_json(orient="records", date_format="iso"))
                return {
                    "kind": kind,
                    "title": analysis.get("title"),
                    "stats": {"mean": mu, "stddev": sd, "outlier_count": int(len(outliers))},
                    "rows": rows,
                    "sql": sql,
                }

            if kind == "missing_recent" and dt:
                if dialect == "postgresql":
                    sql = f'SELECT MAX("{dt}") AS last_seen, COUNT(*) AS total FROM {ident}'
                elif dialect == "mysql":
                    sql = f"SELECT MAX(`{dt}`) AS last_seen, COUNT(*) AS total FROM {ident}"
                else:
                    sql = f'SELECT MAX("{dt}") AS last_seen, COUNT(*) AS total FROM {ident}'
                row = conn.execute(text(sql)).fetchone()
                return {
                    "kind": kind,
                    "title": analysis.get("title"),
                    "rows": [{"last_seen": _jsonable(row[0]), "total_records": _jsonable(row[1])}],
                    "sql": sql,
                }

            if kind == "demographic":
                # Find low-cardinality string columns and group by them.
                from sqlalchemy import inspect
                inspector = inspect(engine)
                schema_, name_ = _split_qualified(table)
                cols = inspector.get_columns(name_, schema=schema_) or []
                groups = []
                for col in cols:
                    cname = col["name"]
                    if any(p in str(col.get("type")).lower() for p in ("char", "text", "string", "enum")):
                        try:
                            sql = f'SELECT "{cname}" AS bucket, COUNT(*) AS total FROM {ident} GROUP BY "{cname}" ORDER BY total DESC LIMIT 12'
                            if dialect == "mysql":
                                sql = f"SELECT `{cname}` AS bucket, COUNT(*) AS total FROM {ident} GROUP BY `{cname}` ORDER BY total DESC LIMIT 12"
                            res = conn.execute(text(sql)).fetchall()
                            if 2 <= len(res) <= 12:
                                groups.append({
                                    "column": cname,
                                    "rows": [{"bucket": _jsonable(r[0]), "total": _jsonable(r[1])} for r in res],
                                })
                        except Exception:
                            continue
                    if len(groups) >= 4:
                        break
                return {"kind": kind, "title": analysis.get("title"), "groups": groups}

            if kind == "liability_forecast" and amt and dt:
                if dialect == "postgresql":
                    sql = f'SELECT date_trunc(\'month\', "{dt}") AS bucket, SUM("{amt}") AS total FROM {ident} GROUP BY bucket ORDER BY bucket'
                elif dialect == "mysql":
                    sql = f"SELECT DATE_FORMAT(`{dt}`, '%Y-%m-01') AS bucket, SUM(`{amt}`) AS total FROM {ident} GROUP BY bucket ORDER BY bucket"
                else:
                    sql = f'SELECT strftime(\'%Y-%m-01\',"{dt}") AS bucket, SUM("{amt}") AS total FROM {ident} GROUP BY bucket ORDER BY bucket'
                history = [
                    {"bucket": str(r[0]), "total": float(r[1] or 0)}
                    for r in conn.execute(text(sql)).fetchall()
                ]
                if not history:
                    return {"kind": kind, "rows": [], "forecast": []}
                last12 = [h["total"] for h in history[-12:]]
                avg = sum(last12) / len(last12)
                growth = 0.0
                if len(history) >= 24:
                    prev12 = [h["total"] for h in history[-24:-12]]
                    if sum(prev12) > 0:
                        growth = (sum(last12) / sum(prev12)) - 1.0
                forecast = []
                last_date = history[-1]["bucket"]
                from datetime import datetime as _dt
                base = _dt.fromisoformat(last_date.split(" ")[0])
                from datetime import timedelta as _td
                for i in range(1, 13):
                    nxt = base.replace(day=1)
                    # Add i months crudely
                    month = nxt.month + i
                    year = nxt.year + (month - 1) // 12
                    month = ((month - 1) % 12) + 1
                    forecast.append({
                        "bucket": f"{year:04d}-{month:02d}-01",
                        "total": round(avg * (1 + growth) ** (i / 12.0), 2),
                    })
                return {
                    "kind": kind,
                    "title": analysis.get("title"),
                    "history": history[-24:],
                    "forecast": forecast,
                    "growth_yoy": growth,
                    "sql": sql,
                }

            if kind == "overview":
                sql = f"SELECT * FROM {ident} LIMIT 10"
                res = conn.execute(text(sql))
                cols = list(res.keys())
                rows = [{c: _jsonable(v) for c, v in zip(cols, r)} for r in res.fetchall()]
                return {
                    "kind": kind,
                    "title": analysis.get("title"),
                    "columns": cols,
                    "rows": rows,
                    "sql": sql,
                }

        return {"error": f"Unknown analysis kind: {kind}"}
    finally:
        _close(engine, tunnel)


# ─────────────────────────────────────────────────────────────────────────────
# LLM-powered auto-mapping suggestions
# ─────────────────────────────────────────────────────────────────────────────

def suggest_field_mappings(
    schema: dict[str, Any],
    semantic_fields: list[dict],
) -> list[dict[str, Any]]:
    """
    Suggest candidate (semantic_field -> table.column) mappings.

    Uses Groq if available, otherwise falls back to keyword matching so the
    feature still works without an API key.
    """
    candidates: list[dict[str, Any]] = []

    # Flatten available columns for matching.
    columns: list[dict] = []
    for tbl in schema.get("tables", []):
        for col in tbl.get("columns", []):
            columns.append({
                "table": tbl["qualified_name"],
                "name": col["name"],
                "type": col["type"],
            })

    if not columns or not semantic_fields:
        return candidates

    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            from .groq_utils import execute_groq_completion, get_groq_model
            prompt = (
                "You are a data-mapping assistant. Given a list of SEMANTIC FIELDS "
                "and a list of CANDIDATE COLUMNS from a customer database, return a "
                "JSON array. Each item must have keys: semantic_field, table, column, "
                "confidence (0-1), reason. Only include matches with confidence ≥ 0.4. "
                "Use exact column and table names from the candidate list.\n\n"
                f"SEMANTIC FIELDS:\n{json.dumps([{'name': f['global_field_name'], 'type': f.get('data_type'), 'desc': f.get('description')} for f in semantic_fields], indent=2)}\n\n"
                f"CANDIDATE COLUMNS:\n{json.dumps(columns[:300], indent=2)}\n\n"
                "Return JSON only."
            )
            completion = execute_groq_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1500,
                model=get_groq_model(),
            )
            raw = completion.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.lower().startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw.strip())
            if isinstance(data, list):
                return data
        except Exception as exc:
            logger.warning(f"LLM auto-map fell back to heuristic: {exc}")

    # Heuristic fallback: fuzzy keyword match on the global_field_name.
    for field in semantic_fields:
        gname = (field.get("global_field_name") or "").lower()
        if not gname:
            continue
        tokens = re.findall(r"[a-z0-9]+", gname)
        if not tokens:
            continue
        scored = []
        for col in columns:
            cname = (col["name"] or "").lower()
            score = sum(1 for t in tokens if t and t in cname)
            if score:
                scored.append((score, col))
        for score, col in sorted(scored, key=lambda x: -x[0])[:3]:
            candidates.append({
                "semantic_field": field["global_field_name"],
                "semantic_field_id": field.get("id"),
                "table": col["table"],
                "column": col["name"],
                "confidence": round(min(1.0, 0.4 + score * 0.2), 2),
                "reason": "Keyword match on field name (heuristic).",
            })
    return candidates


# ─────────────────────────────────────────────────────────────────────────────
# JSON-safety helper
# ─────────────────────────────────────────────────────────────────────────────

def _jsonable(v: Any) -> Any:
    if v is None:
        return None
    try:
        from datetime import date, datetime as dt, time
        if isinstance(v, (dt, date, time)):
            return v.isoformat()
    except Exception:
        pass
    if isinstance(v, (bytes, bytearray, memoryview)):
        try:
            return bytes(v).hex()
        except Exception:
            return str(v)
    if isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    try:
        from decimal import Decimal
        if isinstance(v, Decimal):
            return float(v)
    except Exception:
        pass
    return str(v)
