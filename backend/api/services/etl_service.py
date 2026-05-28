import os
import uuid
import socket
import subprocess
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import numpy as np
import pandas as pd
from sqlalchemy import create_engine

from .connection_utils import normalize_credentials, sqlalchemy_engine_kwargs, detect_db_type


def _get_free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _replace_db_url_host_port(db_url: str, new_host: str, new_port: int) -> str:
    parsed = urlparse(db_url)
    username = parsed.username
    password = parsed.password
    auth = ""
    if username:
        auth = username
        if password:
            auth = f"{username}:{password}"
    netloc = f"{auth}@{new_host}:{new_port}" if auth else f"{new_host}:{new_port}"
    query = f"?{parsed.query}" if parsed.query else ""
    fragment = f"#{parsed.fragment}" if parsed.fragment else ""
    return f"{parsed.scheme}://{netloc}{parsed.path}{query}{fragment}"


def _start_ssh_tunnel(*, ssh_host, ssh_user, remote_host, remote_port, local_port):
    cmd = [
        "ssh", "-N", "-L", f"{local_port}:{remote_host}:{remote_port}",
        f"{ssh_user}@{ssh_host}",
        "-o", "ExitOnForwardFailure=yes",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ServerAliveInterval=30",
        "-o", "ServerAliveCountMax=3",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = datetime.now().timestamp() + 15
    while datetime.now().timestamp() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", local_port), timeout=0.5):
                return proc
        except Exception:
            pass
        time.sleep(0.2)
    try:
        proc.terminate()
    except Exception:
        pass
    raise RuntimeError("SSH tunnel failed to start (timeout waiting for local forwarded port).")


# Legacy demo KPI names — only used to strip old seed rows from API responses
LEGACY_DEMO_KPI_NAMES = frozenset({
    "net_revenue", "inventory_value", "support_tickets",
    "Total Revenue", "Inventory Value", "Support Tickets",
})

RAW_COLUMNS = {
    "date", "kpi_name", "value", "source_row_id",
    "record_label", "customer_id", "report_date",
}


def finalize_extracted_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["date", "kpi_name", "value", "source_row_id", "record_label", "customer_id", "report_date"])
    frame = df.copy()
    required = {"date", "kpi_name", "value"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Extracted data is missing required columns: {', '.join(sorted(missing))}")

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    before = len(frame)
    frame = frame.dropna(subset=["date", "kpi_name", "value"]).copy()
    if frame.empty:
        print(f"[{datetime.now().isoformat()}] All extracted rows were invalid after date/value coercion ({before} rows dropped).")
        return pd.DataFrame(columns=["date", "kpi_name", "value", "source_row_id", "record_label", "customer_id", "report_date"])
    if "source_row_id" not in frame.columns:
        frame["source_row_id"] = [str(uuid.uuid4()) for _ in range(len(frame))]
    else:
        frame["source_row_id"] = frame["source_row_id"].astype(str)
    if "record_label" not in frame.columns:
        frame["record_label"] = frame["kpi_name"]
    if "customer_id" not in frame.columns:
        frame["customer_id"] = [f"CUST-{i + 1:04d}" for i in range(len(frame))]
    frame["report_date"] = frame["date"].dt.date.astype(str)
    return frame


def _extract_from_mongodb(db_url: str) -> pd.DataFrame:
    """Extract data from a MongoDB database."""
    try:
        import pymongo
        client = pymongo.MongoClient(db_url, serverSelectionTimeoutMS=8000)
        db_name = pymongo.uri_parser.parse_uri(db_url).get("database") or "test"
        db = client[db_name]
        collections = db.list_collection_names()
        frames = []
        for col_name in collections:
            docs = list(db[col_name].find({}, {"_id": 0}).limit(100))
            if not docs:
                continue
            df = pd.DataFrame(docs)
            date_col = next((c for c in df.columns if "date" in c.lower() or "time" in c.lower() or "at" in c.lower()), None)
            numeric_cols = [
                c for c in df.columns
                if c != date_col and pd.to_numeric(df[c], errors="coerce").notna().sum() >= max(3, len(df) * 0.5)
            ]
            if date_col and numeric_cols:
                val_col = numeric_cols[0]
                sub = df[[date_col, val_col]].copy()
                sub.columns = ["date", "value"]
                sub["kpi_name"] = f"{col_name}.{val_col}"
                frames.append(sub)
        if frames:
            combined = pd.concat(frames, ignore_index=True)
            return finalize_extracted_frame(combined)
    except ImportError:
        print(f"[{datetime.now().isoformat()}] pymongo not installed. Run: pip install pymongo")
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] MongoDB extraction error: {e}")
    return pd.DataFrame()


def extract_from_source(user_id: str, db_connection_info: dict) -> pd.DataFrame:
    from .connection_crypto import maybe_decrypt_connection_row
    db_connection_info = maybe_decrypt_connection_row(db_connection_info or {})
    db_url = db_connection_info.get("credentials") if db_connection_info else os.getenv("DATABASE_URL")
    connection_method = (db_connection_info or {}).get("connection_method") or "direct"
    connection_options = (db_connection_info or {}).get("connection_options") or {}
    db_type = (db_connection_info or {}).get("db_type", "").lower()

    if db_url and db_type == "mongodb":
        result = _extract_from_mongodb(db_url)
        if not result.empty:
            return result
        print(f"[{datetime.now().isoformat()}] MongoDB returned no analyzable KPI rows.")
        return pd.DataFrame()

    if db_url:
        tunnel_proc = None
        engine = None
        try:
            safe_url = db_url.split("@")[-1] if "@" in db_url else "external source"
            print(f"[{datetime.now().isoformat()}] Fetching source data for user {user_id} from {safe_url}...")

            if connection_method == "ssh_tunnel":
                ssh_host = connection_options.get("ssh_host") or db_connection_info.get("host")
                ssh_user = connection_options.get("ssh_user")
                remote_host = connection_options.get("remote_db_host") or db_connection_info.get("host")
                remote_port = (
                    db_connection_info.get("port")
                    or connection_options.get("remote_db_port")
                    or (urlparse(db_url).port if urlparse(db_url).port else None)
                )
                if not ssh_host or not ssh_user or not remote_host or not remote_port:
                    raise ValueError("SSH tunnel requires ssh_host, ssh_user, remote_db_host, and port.")
                local_port = _get_free_local_port()
                tunnel_proc = _start_ssh_tunnel(
                    ssh_host=str(ssh_host), ssh_user=str(ssh_user),
                    remote_host=str(remote_host), remote_port=int(remote_port), local_port=int(local_port),
                )
                db_url_for_queries = _replace_db_url_host_port(db_url, "127.0.0.1", int(local_port))
            else:
                db_url_for_queries = db_url

            db_type_for_engine = detect_db_type(db_url_for_queries, db_type)
            engine = create_engine(
                normalize_credentials(db_url_for_queries, db_type_for_engine),
                **sqlalchemy_engine_kwargs(db_url_for_queries, db_type_for_engine),
            )

            # Generic introspection-driven extraction. Discover one
            #    amount-like + date-like column per "interesting" table and
            #    extract daily totals from it.
            print(f"[{datetime.now().isoformat()}] Falling back to schema introspection for extraction.")
            try:
                from .schema_introspector import introspect_sql
                schema = introspect_sql(
                    {"credentials": db_url_for_queries, "connection_method": "direct"},
                    sample_rows=0,
                    max_tables=80,
                )
                from sqlalchemy import text as _sql_text
                generic_frames: list[pd.DataFrame] = []
                for tbl in schema.get("tables", []):
                    if tbl.get("is_view"):
                        continue
                    amt = (tbl.get("amount_columns") or [None])[0]
                    dt = (tbl.get("date_columns") or [None])[0]
                    if not amt or not dt:
                        continue
                    label = (tbl.get("classifications") or [tbl["name"]])[0].title()
                    qname = tbl["qualified_name"]
                    schema_part, name_part = (qname.split(".", 1) + [None])[:2]
                    quoted = (
                        f'"{schema_part}"."{name_part}"' if name_part
                        else f'"{schema_part}"'
                    ) if engine.dialect.name != "mysql" else (
                        f"`{schema_part}`.`{name_part}`" if name_part else f"`{schema_part}`"
                    )
                    if engine.dialect.name == "postgresql":
                        gen_sql = (
                            f'SELECT date_trunc(\'day\', "{dt}") AS date, '
                            f"'{label}' AS kpi_name, SUM(\"{amt}\") AS value "
                            f"FROM {quoted} "
                            f"WHERE \"{dt}\" > NOW() - INTERVAL '30 days' "
                            f"GROUP BY 1 ORDER BY 1"
                        )
                    elif engine.dialect.name == "mysql":
                        gen_sql = (
                            f"SELECT DATE(`{dt}`) AS date, "
                            f"'{label}' AS kpi_name, SUM(`{amt}`) AS value "
                            f"FROM {quoted} "
                            f"WHERE `{dt}` > (NOW() - INTERVAL 30 DAY) "
                            f"GROUP BY 1 ORDER BY 1"
                        )
                    elif engine.dialect.name == "oracle":
                        gen_sql = (
                            f'SELECT TRUNC("{dt}") AS date, '
                            f"'{label}' AS kpi_name, SUM(\"{amt}\") AS value "
                            f"FROM {quoted} "
                            f"WHERE \"{dt}\" > SYSDATE - 30 "
                            f"GROUP BY TRUNC(\"{dt}\") ORDER BY 1 FETCH FIRST 30 ROWS ONLY"
                        )
                    else:
                        gen_sql = (
                            f'SELECT "{dt}" AS date, '
                            f"'{label}' AS kpi_name, SUM(\"{amt}\") AS value "
                            f"FROM {quoted} GROUP BY 1 ORDER BY 1 DESC LIMIT 30"
                        )
                    try:
                        with engine.connect() as connection:
                            sub = pd.read_sql(_sql_text(gen_sql), connection)
                        if not sub.empty:
                            generic_frames.append(sub)
                    except Exception as ex:
                        print(f"[{datetime.now().isoformat()}] Skipped {qname}: {ex}")
                if generic_frames:
                    combined = pd.concat(generic_frames, ignore_index=True)
                    return finalize_extracted_frame(combined)
            except Exception as introspect_err:
                print(f"[{datetime.now().isoformat()}] Introspection-driven extract failed: {introspect_err}")
            print(f"[{datetime.now().isoformat()}] Source DB returned no analyzable KPI rows.")
        except Exception as error:
            print(f"[{datetime.now().isoformat()}] Extraction error for user {user_id}: {error}.")
        finally:
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
    return pd.DataFrame()


def detect_anomalies_and_transform(df: pd.DataFrame):
    """
    Z-score anomaly detection with day-of-week correction.
    Robust null/missing data handling throughout.
    """
    kpis = []
    anomalies = []

    if df.empty or "kpi_name" not in df.columns:
        return kpis, anomalies

    for raw_kpi_name in df["kpi_name"].unique():
        kpi_df = df[df["kpi_name"] == raw_kpi_name].copy()
        kpi_df = kpi_df.dropna(subset=["value", "date"])
        kpi_df["value"] = pd.to_numeric(kpi_df["value"], errors="coerce")
        kpi_df = kpi_df.dropna(subset=["value"])
        kpi_df = kpi_df.sort_values("date")

        if len(kpi_df) < 2:
            continue

        historical = kpi_df.iloc[:-1]
        today = kpi_df.iloc[-1]

        try:
            today_weekday = pd.Timestamp(today["date"]).dayofweek
        except Exception:
            today_weekday = 0

        same_dow = historical[pd.to_datetime(historical["date"], errors="coerce").dt.dayofweek == today_weekday]
        if len(same_dow) >= 4:
            mean_baseline = float(same_dow["value"].mean())
            std_baseline = float(same_dow["value"].std())
        else:
            mean_baseline = float(historical["value"].mean())
            std_baseline = float(historical["value"].std())

        avg_7d = float(historical.tail(7)["value"].mean()) if len(historical) >= 1 else 0.0
        yesterday_val = float(historical.iloc[-1]["value"]) if len(historical) >= 1 else 0.0
        last_week_val = float(historical.iloc[-7]["value"]) if len(historical) >= 7 else float(historical.iloc[0]["value"])

        current_val = float(today["value"])
        dod_pct = ((current_val - yesterday_val) / yesterday_val * 100) if yesterday_val and yesterday_val != 0 else 0.0
        wow_pct = ((current_val - last_week_val) / last_week_val * 100) if last_week_val and last_week_val != 0 else 0.0
        z_score = abs(current_val - mean_baseline) / std_baseline if std_baseline and std_baseline > 0 else 0.0

        status = "NORMAL"
        if z_score > 2.5:
            status = "CRITICAL"
            anomalies.append({
                "id": str(uuid.uuid4()),
                "kpi_name": raw_kpi_name,
                "severity": "CRITICAL",
                "deviation": round(z_score, 2),
                "context": {"reason": f"Value {current_val:.2f} is exceptionally far from the same-weekday average of {mean_baseline:.2f}"},
                "detected_at": datetime.now(timezone.utc).isoformat(),
            })
        elif z_score > 1.5:
            status = "WARNING"
            anomalies.append({
                "id": str(uuid.uuid4()),
                "kpi_name": raw_kpi_name,
                "severity": "WARNING",
                "deviation": round(z_score, 2),
                "context": {"reason": f"Value {current_val:.2f} is notable compared to the same-weekday average of {mean_baseline:.2f}"},
                "detected_at": datetime.now(timezone.utc).isoformat(),
            })

        recorded_at = today["date"]
        try:
            recorded_at = recorded_at.date().isoformat() if hasattr(recorded_at, "date") else str(recorded_at)[:10]
        except Exception:
            recorded_at = str(recorded_at)[:10]

        kpis.append({
            "id": str(uuid.uuid4()),
            "kpi_name": raw_kpi_name,
            "value": round(current_val, 2),
            "dod_pct": round(dod_pct, 2),
            "wow_pct": round(wow_pct, 2),
            "avg_7d": round(avg_7d, 2),
            "status": status,
            "recorded_at": recorded_at,
        })

    return kpis, anomalies


def update_sync_status(user_id: str, status: str):
    from ..core.supabase_client import get_supabase
    supabase = get_supabase()
    try:
        supabase.table("user_preferences").upsert(
            {"user_id": user_id, "last_sync_status": status}, on_conflict="user_id"
        ).execute()
        print(f"[{datetime.now().isoformat()}] User {user_id} Sync Status: {status}")
    except Exception as error:
        print(f"[{datetime.now().isoformat()}] Failed to update sync status: {error}")


def apply_field_mappings(df: pd.DataFrame, user_id: str, supabase) -> pd.DataFrame:
    try:
        mappings_resp = (
            supabase.table("field_mappings")
            .select("local_column_name, template_field_id, transformation_rule, semantic_fields(global_field_name, data_type)")
            .eq("user_id", user_id)
            .execute()
        )
        if not hasattr(mappings_resp, "data") or not mappings_resp.data:
            return df
        frame = df.copy()
        for mapping in mappings_resp.data:
            local_column = mapping["local_column_name"]
            semantic_field = mapping.get("semantic_fields")
            if not semantic_field or local_column not in frame.columns:
                continue
            global_name = semantic_field["global_field_name"]
            frame[global_name] = frame[local_column]
            rule = mapping.get("transformation_rule") or {}
            rule_type = rule.get("type")
            if rule_type == "multiply":
                frame[global_name] = frame[global_name] * rule.get("factor", 1)
            elif rule_type == "add":
                frame[global_name] = frame[global_name] + rule.get("offset", 0)
            elif rule_type == "uppercase":
                frame[global_name] = frame[global_name].astype(str).str.upper()
            elif rule_type == "lowercase":
                frame[global_name] = frame[global_name].astype(str).str.lower()
        return frame
    except Exception as error:
        print(f"[{datetime.now().isoformat()}] Field mapping error: {error}. Proceeding with derived defaults.")
        return df


def get_department_id(user_id: str, supabase) -> str | None:
    try:
        resp = supabase.table("user_roles").select("department_id").eq("user_id", user_id).execute()
        if hasattr(resp, "data") and resp.data:
            for row in resp.data:
                if row.get("department_id"):
                    return row["department_id"]
        dept_resp = supabase.table("departments").select("id").eq("name", "General").limit(1).execute()
        if hasattr(dept_resp, "data") and dept_resp.data:
            return dept_resp.data[0]["id"]
    except Exception:
        pass
    return None


def get_required_fields(user_id: str, supabase) -> list:
    from .kpi_config import get_admin_kpi_fields
    fields = get_admin_kpi_fields(supabase, user_id)
    if not fields:
        return []
    # Filter out legacy demo fields so they are never required
    return [f for f in fields if f.get("required") and f.get("global_field_name") not in {"net_revenue", "inventory_value", "support_tickets"}]


def get_runtime_config(user_id: str, supabase) -> dict:
    config = {
        "null_threshold": 0.10, "anomaly_threshold": 0.50,
        "critical_anomaly_zscore": 3.0, "base_definitions": None,
        "base_prompt": None, "company_name": "your company",
    }
    try:
        department_id = get_department_id(user_id, supabase)
        if not department_id:
            return config
        dept_resp = supabase.table("departments").select("name, instance_template_id").eq("id", department_id).limit(1).execute()
        if hasattr(dept_resp, "data") and dept_resp.data:
            config["company_name"] = dept_resp.data[0].get("name") or config["company_name"]
            instance_template_id = dept_resp.data[0].get("instance_template_id")
        else:
            instance_template_id = None
        if instance_template_id:
            template_resp = supabase.table("instance_templates").select("config").eq("id", instance_template_id).limit(1).execute()
            if hasattr(template_resp, "data") and template_resp.data:
                template_config = template_resp.data[0].get("config") or {}
                vr = template_config.get("validation_rules") or {}
                config["null_threshold"] = vr.get("null_threshold", config["null_threshold"])
                config["anomaly_threshold"] = vr.get("anomaly_threshold", config["anomaly_threshold"])
                config["critical_anomaly_zscore"] = vr.get("critical_anomaly_zscore", config["critical_anomaly_zscore"])
                config["base_definitions"] = template_config.get("base_definitions")
                config["base_prompt"] = template_config.get("base_prompt")
    except Exception:
        pass
    return config


def build_validation_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["report_date", "customer_id"])
    frame = df.copy()
    if "report_date" in frame.columns:
        frame["report_date"] = frame["report_date"].fillna("")
    elif "date" in frame.columns:
        frame["report_date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date.astype(str)
    else:
        frame["report_date"] = datetime.now(timezone.utc).date().isoformat()
    if "customer_id" not in frame.columns:
        frame["customer_id"] = "ACCOUNT-PRIMARY"
    frame["customer_id"] = frame["customer_id"].fillna("ACCOUNT-PRIMARY")
    if "kpi_name" not in frame.columns:
        return frame[["report_date", "customer_id"]].drop_duplicates().reset_index(drop=True)
    frame["value"] = pd.to_numeric(frame.get("value"), errors="coerce")
    frame["derived_metric"] = frame["kpi_name"].astype(str)
    metric_rows = frame.dropna(subset=["derived_metric"])
    if metric_rows.empty:
        return frame[["report_date", "customer_id"]].drop_duplicates().reset_index(drop=True)
    pivot = (
        metric_rows.pivot_table(index=["report_date", "customer_id"], columns="derived_metric", values="value", aggfunc="sum")
        .reset_index()
    )
    pivot.columns.name = None
    additive_columns = [c for c in frame.columns if c not in RAW_COLUMNS and c not in pivot.columns]
    for column in additive_columns:
        grouped = frame[["report_date", "customer_id", column]].dropna(subset=[column]).groupby(["report_date", "customer_id"], as_index=False).first()
        if not grouped.empty:
            pivot = pivot.merge(grouped, on=["report_date", "customer_id"], how="left")
    return pivot.fillna(np.nan)


def store_lineage_records(supabase, user_id: str, department_id, batch_source_id: str, df: pd.DataFrame):
    records = []
    for row in df.to_dict(orient="records"):
        raw_value = row.get("value", 0)
        try:
            record_value = float(raw_value) if pd.notna(raw_value) else 0.0
        except Exception:
            record_value = 0.0
        records.append({
            "batch_source_id": batch_source_id,
            "user_id": user_id,
            "department_id": department_id,
            "kpi_name": row["kpi_name"],
            "source_record_id": row["source_row_id"],
            "record_label": row.get("record_label"),
            "record_date": row.get("report_date"),
            "record_value": record_value,
            "raw_payload": {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in row.items()},
        })
    if records:
        try:
            supabase.table("source_lineage_records").insert(records).execute()
        except Exception as error:
            print(f"[{datetime.now().isoformat()}] Source lineage storage skipped: {error}")


def refresh_combined_report(supabase, report_date: str):
    try:
        resp = supabase.table("kpi_results").select("kpi_name, value, department_id, departments(name)").eq("recorded_at", report_date).execute()
        rows = resp.data if hasattr(resp, "data") and resp.data else []
        if not rows:
            return
        department_breakdown = {}
        combined_kpis = {}
        for row in rows:
            dept_name = "Unassigned"
            if row.get("departments"):
                dept_name = row["departments"].get("name") or dept_name
            department_breakdown.setdefault(dept_name, {})
            kpi_name = row["kpi_name"]
            value = float(row.get("value", 0))
            department_breakdown[dept_name][kpi_name] = department_breakdown[dept_name].get(kpi_name, 0) + value
            combined_kpis[kpi_name] = combined_kpis.get(kpi_name, 0) + value
        narrative = f"Combined governed-mesh snapshot for {report_date}: {', '.join(f'{n} {v:,.2f}' for n, v in combined_kpis.items())}"
        supabase.table("combined_reports").insert({
            "report_date": report_date,
            "department_breakdown": department_breakdown,
            "combined_kpis": combined_kpis,
            "narrative": narrative,
        }).execute()
    except Exception as error:
        print(f"[{datetime.now().isoformat()}] Failed to refresh combined report: {error}")


def _run_database_overview_pipeline(user_id: str, supabase, db_connection_info: dict, department_id) -> dict:
    """Create dashboard/report content from the connected database schema.

    This is the no-KPI/no-semantic-mapping path. It reports what the database
    actually contains instead of inventing demo KPIs.
    """
    from .schema_introspector import introspect_sql, introspect_mongo
    from .narrative_service import generate_database_overview_narrative

    db_type = (db_connection_info.get("db_type") or "postgresql").lower()
    schema = (
        introspect_mongo(db_connection_info, sample_rows=3, max_tables=80)
        if db_type == "mongodb"
        else introspect_sql(db_connection_info, sample_rows=3, max_tables=80)
    )

    today = datetime.now(timezone.utc).date().isoformat()
    tables = sorted(
        schema.get("tables", []),
        key=lambda table: table.get("row_count") if table.get("row_count") is not None else -1,
        reverse=True,
    )
    batch_source_id = str(uuid.uuid4())
    kpis = []
    for table in tables[:10]:
        value = table.get("row_count")
        if value is None:
            value = len(table.get("sample_rows") or [])
        kpis.append({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "department_id": department_id,
            "source_id": batch_source_id,
            "source_record_count": int(value or 0),
            "kpi_name": f"Table rows: {table.get('qualified_name') or table.get('name')}",
            "value": float(value or 0),
            "dod_pct": None,
            "wow_pct": None,
            "avg_7d": None,
            "status": "NORMAL",
            "recorded_at": today,
        })

    validation_results = [{
        "user_id": user_id,
        "department_id": department_id,
        "check_type": "schema",
        "status": "pass" if tables else "warning",
        "message": f"Discovered {len(tables)} table(s)/collection(s) from the connected {schema.get('dialect', db_type)} database.",
        "details": {
            "dialect": schema.get("dialect"),
            "table_count": len(tables),
            "mode": "database_overview",
        },
    }]

    if kpis:
        supabase.table("kpi_results").insert(kpis).execute()
    supabase.table("validation_logs").insert(validation_results).execute()

    # Load ai tone and custom analysis instructions from user preferences
    tone = "insight-driven"
    instruction = None
    try:
        pref_response = supabase.table("user_preferences").select("*").eq("user_id", user_id).limit(1).execute()
        if hasattr(pref_response, "data") and pref_response.data:
            prefs = pref_response.data[0]
            tone = prefs.get("ai_tone", "insight-driven")
            instruction = prefs.get("analysis_instruction")
    except Exception as e:
        print(f"Failed to fetch user preferences: {e}")

    narrative_text = generate_database_overview_narrative(
        schema=schema,
        tone=tone,
        instruction=instruction,
        company_name=schema.get("dialect", db_type).title(),
    )

    supabase.table("daily_reports").insert({
        "user_id": user_id,
        "department_id": department_id,
        "narrative": narrative_text,
        "report_date": today,
    }).execute()
    return {
        "status": "success",
        "mode": "database_overview",
        "user_id": user_id,
        "kpis": len(kpis),
        "anomalies": 0,
        "forecasts": 0,
        "validation": validation_results,
    }


def run_user_etl_pipeline(user_id: str):
    print(f"[{datetime.now().isoformat()}] Starting ETL for user {user_id}...")

    from ..core.supabase_client import get_supabase
    from .email_service import send_automated_briefing
    from .narrative_service import generate_live_narrative
    from .validation_service import run_all_validations, store_validation_results
    from .forecast_service import generate_forecasts, store_forecasts

    supabase = get_supabase()

    try:
        conn_response = supabase.table("database_connections").select("*").eq("user_id", user_id).execute()
        db_connection_info = conn_response.data[0] if hasattr(conn_response, "data") and conn_response.data else {}

        department_id = get_department_id(user_id, supabase)
        runtime_config = get_runtime_config(user_id, supabase)
        from .kpi_config import resolve_kpi_mode

        kpi_mode_info = resolve_kpi_mode(supabase, user_id)
        required_fields = get_required_fields(user_id, supabase)

        update_sync_status(user_id, "FETCHING_DATA")
        raw_df = extract_from_source(user_id, db_connection_info)
        print(
            f"[{datetime.now().isoformat()}] Extraction complete. {len(raw_df)} rows retrieved. "
            f"KPI mode: {kpi_mode_info.get('mode')}."
        )
        if raw_df.empty:
            update_sync_status(user_id, "LOADING_DATA")
            result = _run_database_overview_pipeline(user_id, supabase, db_connection_info, department_id)
            result["kpi_mode"] = "overview"
            update_sync_status(user_id, "IDLE")
            return result

        update_sync_status(user_id, "MAPPING_FIELDS")
        mapped_df = apply_field_mappings(raw_df, user_id, supabase)
        validation_df = build_validation_frame(mapped_df)
        current_validation_df = validation_df
        historical_validation_df = validation_df

        if "report_date" in validation_df.columns and not validation_df.empty:
            dated = validation_df.copy()
            dated["report_date"] = pd.to_datetime(dated["report_date"])
            latest_date = dated["report_date"].max()
            current_validation_df = dated[dated["report_date"] == latest_date].copy()
            historical_validation_df = dated[dated["report_date"] < latest_date].copy()
            current_validation_df["report_date"] = current_validation_df["report_date"].dt.date.astype(str)
            historical_validation_df["report_date"] = historical_validation_df["report_date"].dt.date.astype(str)

        update_sync_status(user_id, "VALIDATING_DATA")
        validation_results = run_all_validations(
            current_validation_df,
            required_fields if required_fields else [],
            historical_df=historical_validation_df,
            null_threshold=runtime_config["null_threshold"],
            anomaly_threshold=runtime_config["anomaly_threshold"],
        )
        if not required_fields and validation_results:
            for vr in validation_results:
                if vr.check_type == "schema" and vr.status == "fail":
                    vr.status = "warning"
                    vr.message = (
                        "No admin KPI fields configured — using auto-discovered metrics from your database."
                    )
        store_validation_results(supabase, user_id, department_id, validation_results)

        if any(r.status == "fail" for r in validation_results):
            update_sync_status(user_id, "VALIDATION_FAILED")

        update_sync_status(user_id, "ANALYZING_ANOMALIES")
        kpis, anomalies = detect_anomalies_and_transform(raw_df)

        # Generate 7-day forecasts
        forecasts = generate_forecasts(raw_df)
        store_forecasts(supabase, user_id, department_id, forecasts)

        batch_source_id = str(uuid.uuid4())
        metric_counts = raw_df["kpi_name"].astype(str).value_counts(dropna=True).to_dict()

        for kpi in kpis:
            kpi["user_id"] = user_id
            kpi["department_id"] = department_id
            kpi["source_id"] = batch_source_id
            kpi["source_record_count"] = int(metric_counts.get(kpi["kpi_name"], len(raw_df)))

        for anomaly in anomalies:
            anomaly["user_id"] = user_id
            anomaly["department_id"] = department_id

        update_sync_status(user_id, "LOADING_DATA")
        store_lineage_records(supabase, user_id, department_id, batch_source_id, raw_df)
        if kpis:
            supabase.table("kpi_results").insert(kpis).execute()
        if anomalies:
            supabase.table("anomaly_records").insert(anomalies).execute()

        pref_response = supabase.table("user_preferences").select("*").eq("user_id", user_id).limit(1).execute()
        prefs = pref_response.data[0] if hasattr(pref_response, "data") and pref_response.data else {}
        user_tone = prefs.get("ai_tone", "insight-driven")
        user_instruction = prefs.get("analysis_instruction")

        if user_instruction:
            try:
                hist_resp = supabase.table("analysis_history").select("instruction").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
                latest_instruction = hist_resp.data[0]["instruction"] if hasattr(hist_resp, "data") and hist_resp.data else None
                if latest_instruction != user_instruction:
                    supabase.table("analysis_history").insert({"user_id": user_id, "instruction": user_instruction}).execute()
            except Exception as error:
                print(f"[{datetime.now().isoformat()}] Failed to sync instruction history: {error}")

        # Determine report type from sync frequency
        freq = prefs.get("sync_frequency", "daily").lower()
        report_type_map = {"daily": "Daily", "weekly": "Weekly", "monthly": "Monthly", "yearly": "Annual"}
        report_type = report_type_map.get(freq, "Daily")
        report_period = datetime.now().date().strftime("%B %d, %Y")
        custom_format = prefs.get("report_format") or None

        update_sync_status(user_id, "GENERATING_AI_NARRATIVE")
        narrative_text = generate_live_narrative(
            kpis, anomalies, tone=user_tone, instruction=user_instruction,
            base_definitions=runtime_config["base_definitions"],
            prompt_template=runtime_config["base_prompt"],
            company_name=runtime_config["company_name"],
            report_period=report_period,
            report_type=report_type,
            custom_format=custom_format,
        )

        report_date = datetime.now().date().isoformat()
        supabase.table("daily_reports").insert({
            "user_id": user_id, "department_id": department_id,
            "narrative": narrative_text, "report_date": report_date,
        }).execute()

        update_sync_status(user_id, "SENDING_EMAILS")
        try:
            send_automated_briefing(
                user_id, kpis, anomalies, narrative_text, raw_df,
                report_type=report_type, report_period=report_period,
            )
        except Exception as error:
            print(f"[{datetime.now().isoformat()}] Email delivery failed for user {user_id}: {error}")

        refresh_combined_report(supabase, report_date)
        update_sync_status(user_id, "IDLE")
        return {
            "status": "success", "user_id": user_id,
            "kpis": len(kpis), "anomalies": len(anomalies),
            "forecasts": len(forecasts),
            "validation": [r.to_dict() for r in validation_results],
        }
    except Exception as error:
        print(f"[{datetime.now().isoformat()}] CRITICAL ETL ERROR for user {user_id}: {error}")
        update_sync_status(user_id, "IDLE")
        return {"status": "error", "message": str(error)}
