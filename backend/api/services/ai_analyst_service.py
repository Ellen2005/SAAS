"""
AI Analyst Service — autonomous data analysis engine.

Covers:
  • Auto-modelling        : detect data types, relationships, KPI formulas
  • Augmented analytics   : proactive insight generation without user prompts
  • Explainable AI        : plain-language explanations for every finding
  • Collaboration layer   : shareable insight snapshots with comments
  • Auto data preparation : null imputation, outlier capping, type coercion
  • Governance checks     : lineage, freshness, completeness scoring
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import date, datetime, timezone
import math
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Auto Data Preparation
# ─────────────────────────────────────────────────────────────────────────────

def auto_prepare(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """
    Clean a raw DataFrame:
      - Coerce numeric columns
      - Impute nulls (median for numeric, mode for categorical)
      - Cap outliers at 3-sigma
      - Parse date columns

    Returns (cleaned_df, list_of_actions_taken).
    """
    actions: list[dict] = []
    out = df.copy()
    if out.empty:
        return out, actions

    for col in out.columns:
        series = out[col]
        null_count = int(series.isnull().sum())

        # Try numeric coercion
        coerced = pd.to_numeric(series, errors="coerce")
        if coerced.notna().sum() > series.notna().sum() * 0.5:
            out[col] = coerced
            series = out[col]

        if pd.api.types.is_numeric_dtype(series):
            if null_count > 0:
                median_val = series.median()
                fill_value = 0.0 if pd.isna(median_val) else float(median_val)
                out[col] = series.fillna(fill_value)
                actions.append({"col": col, "action": "impute_median", "filled": null_count, "value": round(fill_value, 4)})

            # Outlier capping
            mu, sd = series.mean(), series.std()
            if sd and sd > 0:
                lo, hi = mu - 3 * sd, mu + 3 * sd
                capped = int(((series < lo) | (series > hi)).sum())
                if capped:
                    out[col] = series.clip(lo, hi)
                    actions.append({"col": col, "action": "cap_outliers", "capped": capped, "range": [round(float(lo), 2), round(float(hi), 2)]})
        else:
            if null_count > 0:
                mode_val = series.mode()
                fill = mode_val.iloc[0] if not mode_val.empty else "UNKNOWN"
                out[col] = series.fillna(fill)
                actions.append({"col": col, "action": "impute_mode", "filled": null_count, "value": str(fill)})

            # Try date parsing on string columns with date-like names
            if any(kw in col.lower() for kw in ("date", "time", "at", "_on", "created", "updated")):
                try:
                    parsed = pd.to_datetime(out[col], errors="coerce")
                    if parsed.notna().sum() > len(out) * 0.5:
                        out[col] = parsed
                        actions.append({"col": col, "action": "parse_datetime"})
                except Exception:
                    pass

    return out, actions


# ─────────────────────────────────────────────────────────────────────────────
# Auto Modelling
# ─────────────────────────────────────────────────────────────────────────────

def auto_model(df: pd.DataFrame) -> dict[str, Any]:
    """
    Detect:
      - Column roles (id, date, amount, category, text, boolean)
      - Likely KPI columns (high-variance numeric)
      - Candidate relationships (FK-like columns)
      - Suggested aggregations
    """
    roles: dict[str, str] = {}
    kpi_candidates: list[str] = []
    relationship_hints: list[dict] = []

    for col in df.columns:
        series = df[col].dropna()
        if series.empty:
            roles[col] = "empty"
            continue
        cname = col.lower()

        if pd.api.types.is_datetime64_any_dtype(df[col]):
            roles[col] = "date"
        elif pd.api.types.is_bool_dtype(df[col]):
            roles[col] = "boolean"
        elif pd.api.types.is_numeric_dtype(df[col]):
            mean = series.mean()
            cv = series.std() / mean if mean not in (0, None) and not pd.isna(mean) else 0
            if any(kw in cname for kw in ("id", "code", "num", "ref", "key")):
                roles[col] = "identifier"
            elif cv > 0.1:
                roles[col] = "metric"
                kpi_candidates.append(col)
            else:
                roles[col] = "dimension_numeric"
        else:
            n_unique = series.nunique()
            if n_unique <= 20:
                roles[col] = "category"
            elif any(kw in cname for kw in ("id", "_id", "code", "ref", "key", "uuid")):
                roles[col] = "identifier"
                # Detect FK-like columns
                if cname.endswith("_id") or cname.endswith("_code"):
                    ref_table = cname.replace("_id", "").replace("_code", "")
                    relationship_hints.append({"column": col, "likely_references": ref_table})
            else:
                roles[col] = "text"

    # Suggested aggregations
    suggestions: list[dict] = []
    date_cols = [c for c, r in roles.items() if r == "date"]
    metric_cols = [c for c, r in roles.items() if r == "metric"]
    cat_cols = [c for c, r in roles.items() if r == "category"]

    for m in metric_cols[:3]:
        for d in date_cols[:1]:
            suggestions.append({"type": "time_series", "metric": m, "date": d, "agg": "sum"})
        for c in cat_cols[:2]:
            suggestions.append({"type": "group_by", "metric": m, "dimension": c, "agg": "sum"})

    return {
        "column_roles": roles,
        "kpi_candidates": kpi_candidates,
        "relationship_hints": relationship_hints,
        "suggested_aggregations": suggestions,
        "row_count": len(df),
        "column_count": len(df.columns),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Augmented Analytics — proactive insight generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_augmented_insights(df: pd.DataFrame, kpis: list[dict], anomalies: list[dict]) -> list[dict]:
    """
    Proactively surface insights the user didn't ask for:
      - Trend direction changes
      - Correlation between KPIs
      - Concentration risk (top-N accounts dominate)
      - Seasonality signals
      - Data freshness warnings
    """
    insights: list[dict] = []

    if df.empty or "kpi_name" not in df.columns:
        return insights

    # 1. Trend direction change detection
    for kpi_name in df["kpi_name"].unique():
        kpi_df = df[df["kpi_name"] == kpi_name].sort_values("date")
        if len(kpi_df) < 7:
            continue
        vals = pd.to_numeric(kpi_df["value"], errors="coerce").dropna().values
        if len(vals) < 7:
            continue
        first_half = vals[:len(vals)//2].mean()
        second_half = vals[len(vals)//2:].mean()
        if first_half > 0:
            change = (second_half - first_half) / first_half
            if abs(change) > 0.15:
                direction = "upward" if change > 0 else "downward"
                insights.append({
                    "type": "trend_shift",
                    "kpi": kpi_name,
                    "severity": "warning" if abs(change) > 0.3 else "info",
                    "title": f"Trend shift detected in {kpi_name.replace('_', ' ').title()}",
                    "explanation": (
                        f"The second half of the observed period shows a {abs(change)*100:.1f}% "
                        f"{direction} trend compared to the first half. "
                        f"{'This may indicate a structural change worth investigating.' if abs(change) > 0.3 else 'Monitor closely.'}"
                    ),
                    "value": round(float(change), 4),
                })

    # 2. KPI correlation
    kpi_names = df["kpi_name"].unique()
    if len(kpi_names) >= 2:
        pivot = df.pivot_table(index="date", columns="kpi_name", values="value", aggfunc="sum")
        pivot = pivot.dropna()
        if len(pivot) >= 5:
            for i, k1 in enumerate(kpi_names):
                for k2 in list(kpi_names)[i+1:]:
                    if k1 in pivot.columns and k2 in pivot.columns:
                        try:
                            corr = float(pivot[k1].corr(pivot[k2]))
                            if not math.isnan(corr) and abs(corr) > 0.75:
                                insights.append({
                                    "type": "correlation",
                                    "kpi": f"{k1} ↔ {k2}",
                                    "severity": "info",
                                    "title": f"Strong correlation: {k1.replace('_',' ').title()} & {k2.replace('_',' ').title()}",
                                    "explanation": (
                                        f"These two metrics move together with a correlation of {corr:.2f}. "
                                        f"{'They likely share a common driver.' if corr > 0 else 'They move inversely — a rise in one predicts a fall in the other.'}"
                                    ),
                                    "value": round(corr, 3),
                                })
                        except Exception:
                            pass

    # 3. Concentration risk
    if "customer_id" in df.columns and "value" in df.columns:
        try:
            top5 = df.groupby("customer_id")["value"].sum().nlargest(5)
            total = df["value"].sum()
            if total > 0:
                concentration = float(top5.sum() / total)
                if concentration > 0.5:
                    insights.append({
                        "type": "concentration_risk",
                        "kpi": "revenue_concentration",
                        "severity": "warning",
                        "title": "High revenue concentration risk",
                        "explanation": (
                            f"Top 5 accounts represent {concentration*100:.1f}% of total value. "
                            "This concentration creates dependency risk — losing one key account would have outsized impact."
                        ),
                        "value": round(concentration, 3),
                    })
        except Exception:
            pass

    # 4. Data freshness
    if "date" in df.columns:
        try:
            latest = pd.to_datetime(df["date"]).max()
            days_stale = (pd.Timestamp.now() - latest).days
            if days_stale > 3:
                insights.append({
                    "type": "data_freshness",
                    "kpi": "data_age",
                    "severity": "warning" if days_stale > 7 else "info",
                    "title": f"Data is {days_stale} days old",
                    "explanation": (
                        f"The most recent data point is from {latest.strftime('%Y-%m-%d')}. "
                        f"{'Consider triggering a sync to get current data.' if days_stale > 7 else 'Data is slightly stale.'}"
                    ),
                    "value": days_stale,
                })
        except Exception:
            pass

    return insights


# ─────────────────────────────────────────────────────────────────────────────
# Explainable AI
# ─────────────────────────────────────────────────────────────────────────────

def explain_anomaly(anomaly: dict, historical_context: dict | None = None) -> str:
    """
    Generate a plain-language explanation for an anomaly finding.
    Uses Groq if available, otherwise builds a rule-based explanation.
    """
    kpi = anomaly.get("kpi_name", "").replace("_", " ").title()
    severity = anomaly.get("severity", "WARNING")
    deviation = anomaly.get("deviation", 0)
    reason = anomaly.get("context", {}).get("reason", "")

    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            from .groq_utils import execute_groq_completion, get_groq_model
            prompt = f"""You are an AI data analyst explaining an anomaly to a non-technical business manager.

ANOMALY:
- KPI: {kpi}
- Severity: {severity}
- Statistical deviation: {deviation:.1f} standard deviations from normal
- System finding: {reason}
{f'- Historical context: {historical_context}' if historical_context else ''}

Write a 2-3 sentence plain-English explanation:
1. What happened (in business terms, not statistics)
2. Why it matters
3. What to check first

Be specific, avoid jargon, use the actual KPI name."""

            completion = execute_groq_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200,
                model=get_groq_model(),
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Groq explain_anomaly failed: {e}")

    # Rule-based fallback
    severity_text = "critical issue" if severity == "CRITICAL" else "notable deviation"
    return (
        f"{kpi} shows a {severity_text} with a {deviation:.1f}σ deviation from its normal range. "
        f"{reason} "
        f"{'Immediate investigation is recommended.' if severity == 'CRITICAL' else 'Monitor this metric closely over the next 24-48 hours.'}"
    )


def explain_kpi_movement(kpi: dict) -> str:
    """Generate a plain-language explanation for a KPI's current value and trend."""
    name = kpi.get("kpi_name", "").replace("_", " ").title()
    value = kpi.get("value", 0)
    dod = kpi.get("dod_pct", 0) or 0
    wow = kpi.get("wow_pct", 0) or 0
    status = kpi.get("status", "NORMAL")

    direction_dod = "increased" if dod > 0 else "decreased"
    direction_wow = "up" if wow > 0 else "down"

    if status == "CRITICAL":
        urgency = "This requires immediate attention."
    elif status == "WARNING":
        urgency = "This warrants close monitoring."
    else:
        urgency = "Performance is within normal parameters."

    return (
        f"{name} is currently {value:,.2f}, {direction_dod} {abs(dod):.1f}% day-over-day "
        f"and {direction_wow} {abs(wow):.1f}% week-over-week. {urgency}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Governance scoring
# ─────────────────────────────────────────────────────────────────────────────

def compute_governance_score(
    df: pd.DataFrame,
    validation_results: list,
    days_since_last_sync: int,
    has_semantic_mappings: bool,
) -> dict[str, Any]:
    """
    Compute a 0-100 governance health score across 4 dimensions:
      - Completeness (null rates)
      - Freshness (days since last sync)
      - Validity (validation pass rate)
      - Traceability (semantic mappings configured)
    """
    scores: dict[str, float] = {}

    # Completeness
    if not df.empty:
        null_rate = float(df.isnull().sum().sum()) / max(df.size, 1)
        scores["completeness"] = round(max(0.0, 1.0 - null_rate * 10) * 100, 1)
    else:
        scores["completeness"] = 0.0

    # Freshness
    if days_since_last_sync <= 1:
        scores["freshness"] = 100.0
    elif days_since_last_sync <= 3:
        scores["freshness"] = 80.0
    elif days_since_last_sync <= 7:
        scores["freshness"] = 60.0
    elif days_since_last_sync <= 30:
        scores["freshness"] = 30.0
    else:
        scores["freshness"] = 0.0

    # Validity
    if validation_results:
        passed = sum(1 for r in validation_results if getattr(r, "status", r.get("status") if isinstance(r, dict) else "fail") == "pass")
        scores["validity"] = round(passed / len(validation_results) * 100, 1)
    else:
        scores["validity"] = 50.0  # unknown

    # Traceability
    scores["traceability"] = 100.0 if has_semantic_mappings else 40.0

    overall = round(sum(scores.values()) / len(scores), 1)

    grade = "A" if overall >= 90 else "B" if overall >= 75 else "C" if overall >= 60 else "D" if overall >= 40 else "F"

    return {
        "overall": overall,
        "grade": grade,
        "dimensions": scores,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "recommendations": _governance_recommendations(scores),
    }


def _governance_recommendations(scores: dict[str, float]) -> list[str]:
    recs = []
    if scores.get("completeness", 100) < 70:
        recs.append("High null rates detected — review source data quality and consider imputation rules.")
    if scores.get("freshness", 100) < 60:
        recs.append("Data is stale — trigger a sync or check your scheduled sync configuration.")
    if scores.get("validity", 100) < 70:
        recs.append("Validation checks are failing — review schema mappings and data types.")
    if scores.get("traceability", 100) < 60:
        recs.append("Semantic mappings are incomplete — configure field mappings in Settings for better lineage tracking.")
    if not recs:
        recs.append("Governance health is good. Continue monitoring regularly.")
    return recs


# ─────────────────────────────────────────────────────────────────────────────
# Collaboration — insight snapshots
# ─────────────────────────────────────────────────────────────────────────────

def create_insight_snapshot(
    supabase,
    user_id: str,
    title: str,
    content: str,
    insight_type: str,
    kpi_name: str | None = None,
    metadata: dict | None = None,
) -> dict:
    """Persist a shareable insight snapshot to the database."""
    record = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": title,
        "content": content,
        "insight_type": insight_type,
        "kpi_name": kpi_name,
        "metadata": metadata or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        supabase.table("insight_snapshots").insert(record).execute()
    except Exception as e:
        logger.warning(f"insight_snapshots insert failed (table may not exist yet): {e}")
    return record


def get_insight_snapshots(supabase, user_id: str, limit: int = 20) -> list[dict]:
    """Retrieve recent insight snapshots for a user."""
    try:
        resp = (
            supabase.table("insight_snapshots")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return resp.data if hasattr(resp, "data") and resp.data else []
    except Exception as e:
        logger.warning(f"insight_snapshots fetch failed: {e}")
        return []
