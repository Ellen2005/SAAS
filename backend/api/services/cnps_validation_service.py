"""
CNPS-specific data quality checks beyond generic validation.
"""
from __future__ import annotations

from datetime import datetime, timedelta, UTC
from typing import Any

import pandas as pd


def check_contribution_date_staleness(df: pd.DataFrame, max_days: int = 30) -> dict[str, Any]:
    """Warn if latest contribution data is older than max_days."""
    date_col = None
    for c in ("contribution_date", "date", "payment_date"):
        if c in df.columns:
            date_col = c
            break
    if not date_col:
        return {"check": "contribution_staleness", "status": "skipped", "message": "No date column found."}

    series = pd.to_datetime(df[date_col], errors="coerce").dropna()
    if series.empty:
        return {"check": "contribution_staleness", "status": "failed", "message": "No valid contribution dates."}

    latest = series.max()
    age_days = (datetime.now(UTC).date() - latest.to_pydatetime().date()).days
    if age_days > max_days:
        return {
            "check": "contribution_staleness",
            "status": "warning",
            "message": f"Latest contribution data is {age_days} days old (threshold {max_days}).",
        }
    return {
        "check": "contribution_staleness",
        "status": "passed",
        "message": f"Contribution data is current (latest {latest.date()}).",
    }


def check_duplicate_contributions(df: pd.DataFrame) -> dict[str, Any]:
    """Flag duplicate employee_id + period combinations."""
    emp_col = "employee_id" if "employee_id" in df.columns else None
    period_col = next((c for c in ("period_month", "contribution_date", "date") if c in df.columns), None)
    if not emp_col or not period_col:
        return {"check": "duplicate_contributions", "status": "skipped", "message": "Missing employee or period column."}

    dupes = df.duplicated(subset=[emp_col, period_col], keep=False).sum()
    if dupes > 0:
        return {
            "check": "duplicate_contributions",
            "status": "warning",
            "message": f"Found {dupes} potential duplicate contribution records.",
        }
    return {"check": "duplicate_contributions", "status": "passed", "message": "No duplicate contributions detected."}


def check_regional_data_coverage(df: pd.DataFrame, expected_regions: list[str] | None = None) -> dict[str, Any]:
    """Ensure expected regions appear in the dataset."""
    region_col = next((c for c in ("regional_code", "region", "regional_office") if c in df.columns), None)
    if not region_col:
        return {"check": "regional_coverage", "status": "skipped", "message": "No regional column found."}

    present = set(df[region_col].dropna().astype(str).unique())
    expected = set(expected_regions or ["DOU", "YAO", "BUE", "GAR", "BAF"])
    missing = expected - present
    if missing:
        return {
            "check": "regional_coverage",
            "status": "warning",
            "message": f"Missing data for regions: {', '.join(sorted(missing))}.",
        }
    return {
        "check": "regional_coverage",
        "status": "passed",
        "message": f"All {len(expected)} expected regions have data.",
    }


def run_cnps_validations(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Run all CNPS-specific checks on an extracted frame."""
    if df is None or df.empty:
        return [{"check": "cnps_suite", "status": "skipped", "message": "Empty dataset."}]
    return [
        check_contribution_date_staleness(df),
        check_duplicate_contributions(df),
        check_regional_data_coverage(df),
    ]
