import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import List, Optional
import uuid


class ValidationResult:
    def __init__(
        self, check_type: str, status: str, message: str, details: Optional[dict] = None
    ):
        self.check_type = check_type
        self.status = status  # pass, warning, fail
        self.message = message
        self.details = details or {}

    def to_dict(self):
        return {
            "check_type": self.check_type,
            "status": self.status,
            "message": self.message,
            "details": self.details,
        }


def run_schema_check(df: pd.DataFrame, required_fields: list) -> ValidationResult:
    """
    Verify all required global fields are present in the DataFrame columns.
    required_fields: list of dicts with 'global_field_name' key.
    """
    if not required_fields:
        return ValidationResult(
            "schema", "pass", "No required fields defined — skipping schema check."
        )

    required_names = [
        str(f["global_field_name"]) for f in required_fields
        if isinstance(f, dict) and f.get("required") and f.get("global_field_name")
    ]
    present_columns = set(df.columns)
    missing = [name for name in required_names if name not in present_columns]

    if missing:
        return ValidationResult(
            "schema",
            "fail",
            f"Missing required fields: {', '.join(missing)}",
            {"missing_fields": missing, "present_columns": list(present_columns)},
        )

    return ValidationResult(
        "schema", "pass", f"All {len(required_names)} required fields present."
    )


def run_null_check(df: pd.DataFrame, threshold: float = 0.10) -> ValidationResult:
    """
    For each column: if null_count / total_rows > threshold, flag as warning.
    """
    if df.empty:
        return ValidationResult("null", "pass", "No data to check for nulls.")

    threshold = min(max(float(threshold), 0.0), 1.0)
    total_rows = len(df)
    flagged_columns = {}

    for col in df.columns:
        null_count = int(df[col].isnull().sum())
        null_pct = null_count / total_rows
        if null_pct > threshold:
            flagged_columns[col] = {
                "null_count": null_count,
                "total_rows": total_rows,
                "null_pct": round(null_pct * 100, 1),
            }

    if flagged_columns:
        worst = max(flagged_columns.values(), key=lambda x: x["null_pct"])
        return ValidationResult(
            "null",
            "warning",
            f"{len(flagged_columns)} column(s) exceed {threshold * 100:.0f}% null threshold. Worst: {worst['null_pct']}% nulls.",
            {"flagged_columns": flagged_columns, "threshold_pct": threshold * 100},
        )

    return ValidationResult(
        "null", "pass", f"All columns below {threshold * 100:.0f}% null threshold."
    )


def run_anomaly_check(
    current_df: pd.DataFrame,
    historical_df: Optional[pd.DataFrame],
    threshold: float = 0.50,
) -> ValidationResult:
    """
    For each KPI: check if current month's total differs from prior month by more than threshold.
    current_df: today's data
    historical_df: previous data (excluding today)
    """
    threshold = min(max(float(threshold), 0.0), 10.0)
    if historical_df is None or historical_df.empty or current_df.empty:
        return ValidationResult(
            "anomaly",
            "pass",
            "Insufficient historical data for anomaly magnitude check.",
        )

    flagged_kpis = {}

    LEGACY_DEMO_KPI_NAMES = {"net_revenue", "inventory_value", "support_tickets", "Total Revenue", "Inventory Value", "Support Tickets"}
    numeric_columns = [
        col
        for col in current_df.columns
        if col not in {"report_date", "customer_id"}
        and col not in LEGACY_DEMO_KPI_NAMES
        and col.replace("_", " ").title() not in LEGACY_DEMO_KPI_NAMES
        and pd.api.types.is_numeric_dtype(current_df[col])
    ]

    for column in numeric_columns:
        current_total = pd.to_numeric(current_df[column], errors="coerce").fillna(0).sum()

        if column not in historical_df.columns:
            continue

        hist_series = pd.to_numeric(historical_df[column], errors="coerce").fillna(0)
        if hist_series.empty:
            continue

        prev_total = hist_series.sum()
        if prev_total == 0:
            continue

        change_pct = abs(current_total - prev_total) / abs(prev_total)
        if change_pct > threshold:
            flagged_kpis[column] = {
                "current_total": round(float(current_total), 2),
                "previous_total": round(float(prev_total), 2),
                "change_pct": round(change_pct * 100, 1),
            }

    if flagged_kpis:
        kpi_names = ", ".join(flagged_kpis.keys())
        return ValidationResult(
            "anomaly",
            "warning",
            f"Month-over-month change exceeds {threshold * 100:.0f}% for: {kpi_names}",
            {"flagged_kpis": flagged_kpis, "threshold_pct": threshold * 100},
        )

    return ValidationResult(
        "anomaly",
        "pass",
        f"No KPIs exceed {threshold * 100:.0f}% month-over-month change.",
    )


def run_all_validations(
    current_df: pd.DataFrame,
    required_fields: list,
    historical_df: Optional[pd.DataFrame] = None,
    null_threshold: float = 0.10,
    anomaly_threshold: float = 0.50,
) -> List[ValidationResult]:
    """
    Runs all three validation checks and returns results.
    """
    results = []

    # 1. Schema check
    results.append(run_schema_check(current_df, required_fields))

    # 2. Null check
    results.append(run_null_check(current_df, threshold=null_threshold))

    # 3. Anomaly magnitude check
    results.append(
        run_anomaly_check(current_df, historical_df, threshold=anomaly_threshold)
    )

    return results


def store_validation_results(
    supabase,
    user_id: str,
    department_id: Optional[str],
    results: List[ValidationResult],
):
    """Persist validation results to the validation_logs table."""
    for result in results:
        try:
            data = {
                "user_id": user_id,
                "department_id": department_id,
                "check_type": result.check_type,
                "status": result.status,
                "message": result.message,
                "details": result.details,
            }
            supabase.table("validation_logs").insert(data).execute()
        except Exception as e:
            print(
                f"[{datetime.now().isoformat()}] Failed to store validation result: {e}"
            )
