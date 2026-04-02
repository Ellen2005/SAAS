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


def _get_free_local_port() -> int:
    """Get an available local TCP port for SSH port-forwarding."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _replace_db_url_host_port(db_url: str, new_host: str, new_port: int) -> str:
    """
    Replace host[:port] in a SQLAlchemy URL while keeping the scheme, auth, and path.
    Example: postgresql+psycopg2://user:pw@oldhost:5432/db -> ...@new_host:new_port/db
    """
    parsed = urlparse(db_url)
    username = parsed.username
    password = parsed.password

    auth = ""
    if username:
        auth = username
        if password:
            auth = f"{username}:{password}"

    if auth:
        netloc = f"{auth}@{new_host}:{new_port}"
    else:
        netloc = f"{new_host}:{new_port}"

    query = f"?{parsed.query}" if parsed.query else ""
    fragment = f"#{parsed.fragment}" if parsed.fragment else ""
    # urlunparse would be ideal, but reconstructing from parsed components is enough for our URLs.
    return f"{parsed.scheme}://{netloc}{parsed.path}{query}{fragment}"


def _start_ssh_tunnel(
    *,
    ssh_host: str,
    ssh_user: str,
    remote_host: str,
    remote_port: int,
    local_port: int,
) -> subprocess.Popen:
    """
    Start an SSH tunnel using local port forwarding.
    Assumes key/agent-based auth (BatchMode=yes avoids interactive password prompts).
    """
    cmd = [
        "ssh",
        "-N",
        "-L",
        f"{local_port}:{remote_host}:{remote_port}",
        f"{ssh_user}@{ssh_host}",
        "-o",
        "ExitOnForwardFailure=yes",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "ServerAliveInterval=30",
        "-o",
        "ServerAliveCountMax=3",
    ]

    # On Windows, ssh writes to stderr/stdout; keep it quiet.
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for the forwarded port to accept connections.
    deadline = datetime.now().timestamp() + 15
    while datetime.now().timestamp() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", local_port), timeout=0.5):
                return proc
        except Exception:
            pass
        # Avoid tight loop
        time.sleep(0.2)

    # If we timed out, terminate and raise.
    try:
        proc.terminate()
    except Exception:
        pass
    raise RuntimeError("SSH tunnel failed to start (timeout waiting for local forwarded port).")

KPI_NAME_MAP = {
    "Total Revenue": "net_revenue",
    "total_revenue": "net_revenue",
    "net_revenue": "net_revenue",
    "Inventory Value": "inventory_value",
    "inventory_value": "inventory_value",
    "Support Tickets": "support_tickets",
    "support_tickets": "support_tickets",
}

RAW_COLUMNS = {
    "date",
    "kpi_name",
    "value",
    "source_row_id",
    "record_label",
    "customer_id",
    "report_date",
}


def finalize_extracted_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "kpi_name",
                "value",
                "source_row_id",
                "record_label",
                "customer_id",
                "report_date",
            ]
        )

    frame = df.copy()
    frame["date"] = pd.to_datetime(frame["date"])

    if "source_row_id" not in frame.columns:
        frame["source_row_id"] = [str(uuid.uuid4()) for _ in range(len(frame))]
    else:
        frame["source_row_id"] = frame["source_row_id"].astype(str)

    if "record_label" not in frame.columns:
        frame["record_label"] = frame["kpi_name"]

    if "customer_id" not in frame.columns:
        frame["customer_id"] = [
            f"CUST-{index + 1:04d}" for index in range(len(frame))
        ]

    frame["report_date"] = frame["date"].dt.date.astype(str)
    return frame


def build_mock_frame() -> pd.DataFrame:
    dates = pd.date_range(end=pd.Timestamp.today(), periods=30)
    data = []

    base_revenue = 135000
    base_inventory = 450000
    base_tickets = 89

    for index, day in enumerate(dates):
        revenue = 190000 if index == 29 else base_revenue + np.random.normal(0, 5000)
        inventory = base_inventory + np.random.normal(0, 8000)
        tickets = 150 if index == 29 else max(10, int(base_tickets + np.random.normal(0, 15)))

        data.extend(
            [
                {
                    "date": day,
                    "kpi_name": "Total Revenue",
                    "value": revenue,
                    "source_row_id": str(uuid.uuid4()),
                    "record_label": f"Invoice Batch {index + 1}",
                    "customer_id": f"ACCT-{index + 1:04d}",
                },
                {
                    "date": day,
                    "kpi_name": "Inventory Value",
                    "value": inventory,
                    "source_row_id": str(uuid.uuid4()),
                    "record_label": f"Inventory Snapshot {index + 1}",
                    "customer_id": f"ACCT-{index + 1:04d}",
                },
                {
                    "date": day,
                    "kpi_name": "Support Tickets",
                    "value": tickets,
                    "source_row_id": str(uuid.uuid4()),
                    "record_label": f"Ticket Batch {index + 1}",
                    "customer_id": f"ACCT-{index + 1:04d}",
                },
            ]
        )

    return finalize_extracted_frame(pd.DataFrame(data))


def extract_from_source(user_id: str, db_connection_info: dict) -> pd.DataFrame:
    """
    Extract the last 30 days of KPI-like source data.
    Falls back to mock data when the connection is unavailable or mock mode is enabled.
    """
    mock_flag = os.getenv("MOCK_DATA", "False").lower() == "true"
    db_url = (
        db_connection_info.get("credentials")
        if db_connection_info
        else os.getenv("DATABASE_URL")
    )
    connection_method = (db_connection_info or {}).get("connection_method") or "direct"
    connection_options = (db_connection_info or {}).get("connection_options") or {}

    if not mock_flag and db_url:
        tunnel_proc = None
        try:
            safe_url = db_url.split("@")[-1] if "@" in db_url else "external source"
            print(
                f"[{datetime.now().isoformat()}] Fetching source data for user {user_id} from {safe_url}..."
            )
            # For firewalled databases, we support SSH tunneling by rewriting
            # the connection URL to point at a locally forwarded port.
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
                    raise ValueError(
                        "SSH tunnel requires connection_options.ssh_host + ssh_user + remote_db_host, "
                        "and a valid remote port."
                    )

                local_port = _get_free_local_port()
                tunnel_proc = _start_ssh_tunnel(
                    ssh_host=str(ssh_host),
                    ssh_user=str(ssh_user),
                    remote_host=str(remote_host),
                    remote_port=int(remote_port),
                    local_port=int(local_port),
                )

                db_url_for_queries = _replace_db_url_host_port(
                    db_url, "127.0.0.1", int(local_port)
                )
            else:
                db_url_for_queries = db_url

            engine = create_engine(db_url_for_queries, connect_args={"connect_timeout": 15})

            queries = [
                """
                SELECT
                    id AS source_row_id,
                    transaction_date AS date,
                    'Total Revenue' AS kpi_name,
                    amount AS value,
                    'Revenue Record' AS record_label
                FROM public.source_revenue
                WHERE transaction_date > NOW() - INTERVAL '30 days'
                """,
                """
                SELECT
                    id AS source_row_id,
                    recorded_at AS date,
                    'Inventory Value' AS kpi_name,
                    stock_value AS value,
                    'Inventory Snapshot' AS record_label
                FROM public.source_inventory
                WHERE recorded_at > NOW() - INTERVAL '30 days'
                """,
                """
                SELECT
                    id AS source_row_id,
                    recorded_at AS date,
                    'Support Tickets' AS kpi_name,
                    ticket_count AS value,
                    'Support Activity' AS record_label
                FROM public.source_tickets
                WHERE recorded_at > NOW() - INTERVAL '30 days'
                """,
            ]

            with engine.connect() as connection:
                frames = [pd.read_sql(query, connection) for query in queries]

            combined = pd.concat(frames, ignore_index=True)
            if not combined.empty:
                return finalize_extracted_frame(combined)

            print(
                f"[{datetime.now().isoformat()}] Source database was reachable but returned no rows. Falling back to mock data."
            )
        except Exception as error:
            print(
                f"[{datetime.now().isoformat()}] Extraction error for user {user_id}: {error}. Falling back to mock data."
            )
        finally:
            if tunnel_proc:
                try:
                    tunnel_proc.terminate()
                    tunnel_proc.wait(timeout=5)
                except Exception:
                    try:
                        tunnel_proc.kill()
                    except Exception:
                        pass
    return build_mock_frame()


def detect_anomalies_and_transform(df: pd.DataFrame):
    """
    Compare the most recent point against the 30-day mean/std deviation and emit standardized KPI names.
    """
    kpis = []
    anomalies = []

    for raw_kpi_name in df["kpi_name"].unique():
        kpi_df = df[df["kpi_name"] == raw_kpi_name].sort_values("date")
        if len(kpi_df) < 2:
            continue

        historical = kpi_df.iloc[:-1]
        today = kpi_df.iloc[-1]

        mean_30d = historical["value"].mean()
        std_30d = historical["value"].std()
        avg_7d = historical.tail(7)["value"].mean()

        yesterday_val = historical.iloc[-1]["value"]
        last_week_val = historical.iloc[-7]["value"] if len(historical) >= 7 else historical.iloc[0]["value"]

        dod_pct = (
            ((today["value"] - yesterday_val) / yesterday_val) * 100
            if yesterday_val
            else 0
        )
        wow_pct = (
            ((today["value"] - last_week_val) / last_week_val) * 100
            if last_week_val
            else 0
        )

        current_val = today["value"]
        z_score = abs(current_val - mean_30d) / std_30d if std_30d > 0 else 0

        status = "NORMAL"
        if z_score > 2.5:
            status = "CRITICAL"
            anomalies.append(
                {
                    "id": str(uuid.uuid4()),
                    "kpi_name": KPI_NAME_MAP.get(raw_kpi_name, raw_kpi_name),
                    "severity": "CRITICAL",
                    "deviation": round(z_score, 2),
                    "context": {
                        "reason": f"Value {current_val:.2f} is exceptionally far from the 30-day average of {mean_30d:.2f}"
                    },
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        elif z_score > 1.5:
            status = "WARNING"
            anomalies.append(
                {
                    "id": str(uuid.uuid4()),
                    "kpi_name": KPI_NAME_MAP.get(raw_kpi_name, raw_kpi_name),
                    "severity": "WARNING",
                    "deviation": round(z_score, 2),
                    "context": {
                        "reason": f"Value {current_val:.2f} is notable compared to the average of {mean_30d:.2f}"
                    },
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                }
            )

        kpis.append(
            {
                "id": str(uuid.uuid4()),
                "kpi_name": KPI_NAME_MAP.get(raw_kpi_name, raw_kpi_name),
                "value": round(float(current_val), 2),
                "dod_pct": round(dod_pct, 2),
                "wow_pct": round(wow_pct, 2),
                "avg_7d": round(avg_7d, 2),
                "status": status,
                "recorded_at": today["date"].date().isoformat(),
            }
        )

    return kpis, anomalies


def update_sync_status(user_id: str, status: str):
    from ..core.supabase_client import get_supabase

    supabase = get_supabase()
    try:
        supabase.table("user_preferences").upsert(
            {"user_id": user_id, "last_sync_status": status},
            on_conflict="user_id",
        ).execute()
        print(f"[{datetime.now().isoformat()}] User {user_id} Sync Status: {status}")
    except Exception as error:
        print(f"[{datetime.now().isoformat()}] Failed to update sync status: {error}")


def apply_field_mappings(df: pd.DataFrame, user_id: str, supabase) -> pd.DataFrame:
    """
    Apply semantic mappings as additive standardized columns without deleting the raw source columns.
    """
    try:
        mappings_resp = (
            supabase.table("field_mappings")
            .select(
                "local_column_name, template_field_id, transformation_rule, semantic_fields(global_field_name, data_type)"
            )
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
        print(
            f"[{datetime.now().isoformat()}] Field mapping error: {error}. Proceeding with derived defaults."
        )
        return df


def get_department_id(user_id: str, supabase) -> str | None:
    try:
        resp = (
            supabase.table("user_roles")
            .select("department_id")
            .eq("user_id", user_id)
            .execute()
        )
        if hasattr(resp, "data") and resp.data:
            for row in resp.data:
                if row.get("department_id"):
                    return row["department_id"]

        dept_resp = (
            supabase.table("departments")
            .select("id")
            .eq("name", "General")
            .limit(1)
            .execute()
        )
        if hasattr(dept_resp, "data") and dept_resp.data:
            return dept_resp.data[0]["id"]
    except Exception:
        pass
    return None


def get_required_fields(user_id: str, supabase) -> list:
    try:
        department_id = get_department_id(user_id, supabase)
        if not department_id:
            return []

        dept_resp = (
            supabase.table("departments")
            .select("template_id")
            .eq("id", department_id)
            .limit(1)
            .execute()
        )
        template_id = (
            dept_resp.data[0].get("template_id")
            if hasattr(dept_resp, "data") and dept_resp.data
            else None
        )

        if not template_id:
            return []

        fields_resp = (
            supabase.table("semantic_fields")
            .select("global_field_name, data_type, required")
            .eq("template_id", template_id)
            .execute()
        )
        if hasattr(fields_resp, "data") and fields_resp.data:
            return fields_resp.data
    except Exception:
        pass
    return []


def get_runtime_config(user_id: str, supabase) -> dict:
    config = {
        "null_threshold": 0.10,
        "anomaly_threshold": 0.50,
        "critical_anomaly_zscore": 3.0,
        "base_definitions": None,
        "base_prompt": None,
        "company_name": "your company",
    }

    try:
        department_id = get_department_id(user_id, supabase)
        if not department_id:
            return config

        dept_resp = (
            supabase.table("departments")
            .select("name, instance_template_id")
            .eq("id", department_id)
            .limit(1)
            .execute()
        )
        if hasattr(dept_resp, "data") and dept_resp.data:
            config["company_name"] = dept_resp.data[0].get("name") or config["company_name"]
            instance_template_id = dept_resp.data[0].get("instance_template_id")
        else:
            instance_template_id = None

        if instance_template_id:
            template_resp = (
                supabase.table("instance_templates")
                .select("config")
                .eq("id", instance_template_id)
                .limit(1)
                .execute()
            )
            if hasattr(template_resp, "data") and template_resp.data:
                template_config = template_resp.data[0].get("config") or {}
                validation_rules = template_config.get("validation_rules") or {}
                config["null_threshold"] = validation_rules.get("null_threshold", config["null_threshold"])
                config["anomaly_threshold"] = validation_rules.get("anomaly_threshold", config["anomaly_threshold"])
                config["critical_anomaly_zscore"] = validation_rules.get(
                    "critical_anomaly_zscore",
                    config["critical_anomaly_zscore"],
                )
                config["base_definitions"] = template_config.get("base_definitions")
                config["base_prompt"] = template_config.get("base_prompt")
    except Exception:
        pass

    return config


def build_validation_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["report_date", "customer_id"])

    frame = df.copy()
    frame["report_date"] = frame.get("report_date", frame["date"].dt.date.astype(str))
    if "customer_id" not in frame.columns:
        frame["customer_id"] = "ACCOUNT-PRIMARY"
    frame["customer_id"] = frame["customer_id"].fillna("ACCOUNT-PRIMARY")

    frame["derived_metric"] = frame["kpi_name"].map(KPI_NAME_MAP)
    metric_rows = frame.dropna(subset=["derived_metric"])

    if metric_rows.empty:
        return frame[["report_date", "customer_id"]].drop_duplicates().reset_index(drop=True)

    pivot = (
        metric_rows.pivot_table(
            index=["report_date", "customer_id"],
            columns="derived_metric",
            values="value",
            aggfunc="sum",
        )
        .reset_index()
    )
    pivot.columns.name = None

    additive_columns = [
        column
        for column in frame.columns
        if column not in RAW_COLUMNS and column not in pivot.columns
    ]
    for column in additive_columns:
        grouped = (
            frame[["report_date", "customer_id", column]]
            .dropna(subset=[column])
            .groupby(["report_date", "customer_id"], as_index=False)
            .first()
        )
        if not grouped.empty:
            pivot = pivot.merge(grouped, on=["report_date", "customer_id"], how="left")

    return pivot.fillna(np.nan)


def store_lineage_records(
    supabase,
    user_id: str,
    department_id: str | None,
    batch_source_id: str,
    df: pd.DataFrame,
):
    records = []
    for row in df.to_dict(orient="records"):
        records.append(
            {
                "batch_source_id": batch_source_id,
                "user_id": user_id,
                "department_id": department_id,
                "kpi_name": KPI_NAME_MAP.get(row["kpi_name"], row["kpi_name"]),
                "source_record_id": row["source_row_id"],
                "record_label": row.get("record_label"),
                "record_date": row.get("report_date"),
                "record_value": float(row.get("value", 0)),
                "raw_payload": {
                    key: (value.isoformat() if hasattr(value, "isoformat") else value)
                    for key, value in row.items()
                },
            }
        )

    if records:
        try:
            supabase.table("source_lineage_records").insert(records).execute()
        except Exception as error:
            print(
                f"[{datetime.now().isoformat()}] Source lineage storage skipped: {error}"
            )


def refresh_combined_report(supabase, report_date: str):
    try:
        resp = (
            supabase.table("kpi_results")
            .select("kpi_name, value, department_id, departments(name)")
            .eq("recorded_at", report_date)
            .execute()
        )
        rows = resp.data if hasattr(resp, "data") and resp.data else []
        if not rows:
            return

        department_breakdown = {}
        combined_kpis = {}
        for row in rows:
            department_name = "Unassigned"
            if row.get("departments"):
                department_name = row["departments"].get("name") or department_name

            department_breakdown.setdefault(department_name, {})
            kpi_name = row["kpi_name"]
            value = float(row.get("value", 0))

            department_breakdown[department_name][kpi_name] = (
                department_breakdown[department_name].get(kpi_name, 0) + value
            )
            combined_kpis[kpi_name] = combined_kpis.get(kpi_name, 0) + value

        narrative = (
            f"Combined governed-mesh snapshot for {report_date}: "
            f"{', '.join(f'{name} {value:,.2f}' for name, value in combined_kpis.items())}"
        )

        supabase.table("combined_reports").insert(
            {
                "report_date": report_date,
                "department_breakdown": department_breakdown,
                "combined_kpis": combined_kpis,
                "narrative": narrative,
            }
        ).execute()
    except Exception as error:
        print(f"[{datetime.now().isoformat()}] Failed to refresh combined report: {error}")


def run_user_etl_pipeline(user_id: str):
    """
    Main orchestrator for a single user's ETL execution.
    Governed-mesh features included:
    - semantic standardization
    - validation gatekeeper
    - lineage tagging
    - department-aware reporting
    """
    print(f"[{datetime.now().isoformat()}] Starting ETL for user {user_id}...")

    from ..core.supabase_client import get_supabase
    from .email_service import send_automated_briefing
    from .narrative_service import generate_live_narrative
    from .validation_service import run_all_validations, store_validation_results

    supabase = get_supabase()

    try:
        conn_response = (
            supabase.table("database_connections")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        db_connection_info = (
            conn_response.data[0]
            if hasattr(conn_response, "data") and conn_response.data
            else {}
        )

        department_id = get_department_id(user_id, supabase)
        runtime_config = get_runtime_config(user_id, supabase)
        required_fields = get_required_fields(user_id, supabase)

        update_sync_status(user_id, "FETCHING_DATA")
        raw_df = extract_from_source(user_id, db_connection_info)
        print(
            f"[{datetime.now().isoformat()}] Extraction complete. {len(raw_df)} rows retrieved."
        )

        update_sync_status(user_id, "MAPPING_FIELDS")
        mapped_df = apply_field_mappings(raw_df, user_id, supabase)
        validation_df = build_validation_frame(mapped_df)
        current_validation_df = validation_df
        historical_validation_df = validation_df

        if "report_date" in validation_df.columns and not validation_df.empty:
            dated_validation_df = validation_df.copy()
            dated_validation_df["report_date"] = pd.to_datetime(dated_validation_df["report_date"])
            latest_report_date = dated_validation_df["report_date"].max()
            current_validation_df = dated_validation_df[
                dated_validation_df["report_date"] == latest_report_date
            ].copy()
            historical_validation_df = dated_validation_df[
                dated_validation_df["report_date"] < latest_report_date
            ].copy()
            current_validation_df["report_date"] = current_validation_df["report_date"].dt.date.astype(str)
            historical_validation_df["report_date"] = historical_validation_df["report_date"].dt.date.astype(str)

        update_sync_status(user_id, "VALIDATING_DATA")
        validation_results = run_all_validations(
            current_validation_df,
            required_fields,
            historical_df=historical_validation_df,
            null_threshold=runtime_config["null_threshold"],
            anomaly_threshold=runtime_config["anomaly_threshold"],
        )
        store_validation_results(supabase, user_id, department_id, validation_results)

        if any(result.status == "fail" for result in validation_results):
            update_sync_status(user_id, "VALIDATION_FAILED")

        update_sync_status(user_id, "ANALYZING_ANOMALIES")
        kpis, anomalies = detect_anomalies_and_transform(raw_df)

        batch_source_id = str(uuid.uuid4())
        metric_counts = (
            raw_df["kpi_name"].map(KPI_NAME_MAP).value_counts(dropna=True).to_dict()
        )

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

        pref_response = (
            supabase.table("user_preferences")
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        prefs = (
            pref_response.data[0]
            if hasattr(pref_response, "data") and pref_response.data
            else {}
        )
        user_tone = prefs.get("ai_tone", "insight-driven")
        user_instruction = prefs.get("analysis_instruction")

        if user_instruction:
            try:
                hist_resp = (
                    supabase.table("analysis_history")
                    .select("instruction")
                    .eq("user_id", user_id)
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )
                latest_instruction = (
                    hist_resp.data[0]["instruction"]
                    if hasattr(hist_resp, "data") and hist_resp.data
                    else None
                )
                if latest_instruction != user_instruction:
                    supabase.table("analysis_history").insert(
                        {"user_id": user_id, "instruction": user_instruction}
                    ).execute()
            except Exception as error:
                print(
                    f"[{datetime.now().isoformat()}] Failed to sync instruction history: {error}"
                )

        update_sync_status(user_id, "GENERATING_AI_NARRATIVE")
        narrative_text = generate_live_narrative(
            kpis,
            anomalies,
            tone=user_tone,
            instruction=user_instruction,
            base_definitions=runtime_config["base_definitions"],
            prompt_template=runtime_config["base_prompt"],
            company_name=runtime_config["company_name"],
        )

        report_date = datetime.now().date().isoformat()
        supabase.table("daily_reports").insert(
            {
                "user_id": user_id,
                "department_id": department_id,
                "narrative": narrative_text,
                "report_date": report_date,
            }
        ).execute()

        update_sync_status(user_id, "SENDING_EMAILS")
        send_automated_briefing(user_id, kpis, anomalies, narrative_text, raw_df)
        refresh_combined_report(supabase, report_date)

        update_sync_status(user_id, "IDLE")
        return {
            "status": "success",
            "user_id": user_id,
            "kpis": len(kpis),
            "anomalies": len(anomalies),
            "validation": [result.to_dict() for result in validation_results],
        }
    except Exception as error:
        print(
            f"[{datetime.now().isoformat()}] CRITICAL ETL ERROR for user {user_id}: {error}"
        )
        update_sync_status(user_id, "IDLE")
        return {"status": "error", "message": str(error)}
