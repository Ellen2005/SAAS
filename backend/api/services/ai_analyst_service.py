"""
AI Data Analyst Service
=======================
Complete autonomous data analysis engine.

Capabilities:
  1. Auto Data Preparation (clean, impute, cap outliers)
  2. Auto Modelling (detect column roles, KPI candidates)
  3. Augmented Analytics (trend shifts, correlations, concentration, freshness)
  4. Explainable AI (plain-language explanations via Groq/rule-based)
  5. Governance Scoring (4-dimension health score)
  6. **Statistical Engine** (mean, median, std, correlation, regression, outliers)
  7. **Rich Insight Generation** (11-point response format)
  8. **Context Memory** (remembers previous analyses, datasets)
"""

import json
import logging
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone, date as date_type
from typing import Any, Optional

import numpy as np
import pandas as pd

from .statistical_engine import (
    run_full_statistical_analysis,
    compute_correlation,
    compute_linear_regression,
    detect_outliers_zscore,
    detect_outliers_iqr,
    get_formula,
    explain_formula,
)

logger = logging.getLogger(__name__)


# ─── Context Memory ──────────────────────────────────────────────────────────

class AnalysisContext:
    """Remembers previous analyses, datasets, and questions for follow-up."""
    
    def __init__(self):
        self.history: list[dict] = []
        self.last_dataset: str = ""
        self.last_question: str = ""
        self.last_results: dict = {}
        self.filters: dict = {}
    
    def add_analysis(self, question: str, dataset: str, results: dict, filters: dict = None):
        self.history.append({
            "question": question,
            "dataset": dataset,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "filters": filters or {},
        })
        self.last_question = question
        self.last_dataset = dataset
        self.last_results = results
        if filters:
            self.filters.update(filters)
        # Keep last 20
        if len(self.history) > 20:
            self.history = self.history[-20:]
    
    def get_context(self) -> str:
        """Generate context string for LLM prompts."""
        if not self.history:
            return ""
        last = self.history[-1]
        parts = [f"Previous analysis: {last['question']}"]
        if last.get("filters"):
            parts.append(f"Filters: {json.dumps(last['filters'])}")
        return ". ".join(parts)

# Per-user context instances (prevents data leakage between users)
_user_contexts: dict[str, AnalysisContext] = {}

def get_analysis_context(user_id: str = None) -> AnalysisContext:
    """Get or create a per-user analysis context."""
    if not user_id:
        # Fallback for backward compatibility, but log a warning
        logger.warning("get_analysis_context called without user_id - using shared context")
        return _user_contexts.setdefault("_shared", AnalysisContext())
    if user_id not in _user_contexts:
        _user_contexts[user_id] = AnalysisContext()
    return _user_contexts[user_id]


# ─── Helper Functions ────────────────────────────────────────────────────────

def _safe(resp) -> list:
    return resp.data if hasattr(resp, "data") and resp.data else []


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


# ─── 1. Auto Data Preparation ────────────────────────────────────────────────

def auto_prepare(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """
    Clean and prepare raw data.
    
    Steps:
    1. Numeric coercion
    2. Null imputation (median for numerics, mode for categoricals)
    3. Outlier capping (3-sigma)
    4. Date parsing
    """
    actions = []
    frame = df.copy()
    
    # Numeric coercion
    numeric_cols = frame.select_dtypes(include=[np.number]).columns.tolist()
    for col in frame.columns:
        if col not in numeric_cols:
            try:
                frame[col] = pd.to_numeric(frame[col], errors="coerce")
                if frame[col].notna().sum() >= len(frame) * 0.5:
                    actions.append({"action": "coerce", "column": col, "to": "numeric"})
            except (ValueError, TypeError):
                pass
    
    numeric_cols = frame.select_dtypes(include=[np.number]).columns.tolist()
    text_cols = frame.select_dtypes(include=["object"]).columns.tolist()
    
    # Null imputation for numerics
    for col in numeric_cols:
        null_count = frame[col].isna().sum()
        if null_count > 0:
            median_val = frame[col].median()
            frame[col] = frame[col].fillna(median_val)
            actions.append({"action": "impute", "column": col, "method": "median", "filled": int(null_count)})
    
    # Null imputation for text
    for col in text_cols:
        null_count = frame[col].isna().sum()
        if null_count > 0:
            mode_val = frame[col].mode()
            if not mode_val.empty:
                frame[col] = frame[col].fillna(mode_val[0])
                actions.append({"action": "impute", "column": col, "method": "mode", "filled": int(null_count)})
    
    # Outlier capping (3-sigma)
    for col in numeric_cols:
        mean = frame[col].mean()
        std = frame[col].std()
        if std > 0:
            before = len(frame[frame[col] > mean + 3 * std]) + len(frame[frame[col] < mean - 3 * std])
            frame[col] = frame[col].clip(mean - 3 * std, mean + 3 * std)
            if before > 0:
                actions.append({"action": "cap_outliers", "column": col, "method": "3-sigma", "capped": int(before)})
    
    # Date parsing
    for col in frame.columns:
        if col.lower() in ("date", "time", "at", "timestamp", "created_at", "updated_at", "recorded_at"):
            try:
                frame[col] = pd.to_datetime(frame[col], errors="coerce")
                actions.append({"action": "parse_date", "column": col})
            except Exception:
                pass
    
    return frame, actions


# ─── 2. Auto Modelling ──────────────────────────────────────────────────────

def auto_model(df: pd.DataFrame) -> dict[str, Any]:
    """
    Automatically detect column roles, KPI candidates, and relationships.
    """
    if df.empty:
        return {"message": "Empty dataset", "columns": {}, "kpi_candidates": [], "relationships": []}
    
    # Detect column roles
    columns = {}
    for col in df.columns:
        col_lower = col.lower()
        
        if col_lower in ("id", "_id", "user_id", "department_id", "customer_id"):
            role = "id"
        elif col_lower in ("date", "time", "at", "timestamp", "created_at", "updated_at", "recorded_at", "year", "month", "day"):
            role = "date"
        elif df[col].dtype in (np.int64, np.float64) or pd.to_numeric(df[col], errors="coerce").notna().sum() >= len(df) * 0.7:
            role = "metric"
            # Check if it's a KPI candidate (high coefficient of variation)
            vals = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(vals) > 2:
                cv = vals.std() / vals.mean() if vals.mean() != 0 else 0
                if cv > 0.3:
                    role = "kpi_candidate"
        elif df[col].nunique() <= 2:
            role = "boolean"
        elif df[col].nunique() <= 20:
            role = "category"
        elif df[col].str.len().max() > 100 if df[col].dtype == "object" else False:
            role = "text"
        else:
            role = "text"
        
        columns[col] = {
            "role": role,
            "dtype": str(df[col].dtype),
            "unique_values": int(df[col].nunique()),
            "null_count": int(df[col].isna().sum()),
            "null_pct": round(float(df[col].isna().sum() / len(df) * 100), 1),
        }
    
    # Detect KPI candidates (numeric columns with high variation)
    kpi_candidates = []
    for col, info in columns.items():
        if info["role"] == "kpi_candidate":
            vals = pd.to_numeric(df[col], errors="coerce").dropna()
            kpi_candidates.append({
                "name": col,
                "mean": round(float(vals.mean()), 2),
                "min": round(float(vals.min()), 2),
                "max": round(float(vals.max()), 2),
                "suggested_widget": "line" if "date" in str(df.columns).lower() else "bar",
            })
    
    # Detect FK-like relationships
    relationships = []
    for col in df.columns:
        if col.lower().endswith("_id") and col.lower() != "id":
            target_table = col[:-3]  # Remove "_id" suffix
            relationships.append({
                "source_column": col,
                "suggested_target": target_table,
                "type": "foreign_key",
            })
    
    # Detect time-series columns
    date_cols = [col for col, info in columns.items() if info["role"] == "date"]
    time_series = bool(date_cols)
    
    return {
        "columns": columns,
        "kpi_candidates": kpi_candidates,
        "relationships": relationships,
        "time_series": time_series,
        "date_columns": date_cols,
        "total_columns": len(columns),
        "total_rows": len(df),
        "suggested_aggregations": {
            "time_series": time_series,
            "group_by": [col for col, info in columns.items() if info["role"] == "category"],
            "metrics": [col for col, info in columns.items() if info["role"] in ("metric", "kpi_candidate")],
        },
    }


# ─── 3. Augmented Insights ──────────────────────────────────────────────────

def generate_augmented_insights(df: pd.DataFrame, kpis: list, anomalies: list) -> list[dict]:
    """
    Generate proactive insights:
    1. Trend shifts (>15% change)
    2. Correlations (>0.75)
    3. Concentration risk (>50% top-5)
    4. Data freshness (>3 days stale)
    """
    insights = []
    
    if df.empty:
        return insights
    
    # 1. Trend shifts
    if "kpi_name" in df.columns and "value" in df.columns and "date" in df.columns:
        for kpi_name in df["kpi_name"].unique():
            kpi_df = df[df["kpi_name"] == kpi_name].copy()
            kpi_df = kpi_df.sort_values("date")
            if len(kpi_df) >= 4:
                mid = len(kpi_df) // 2
                recent = kpi_df.iloc[mid:]["value"].mean()
                older = kpi_df.iloc[:mid]["value"].mean()
                if older > 0:
                    change = ((recent - older) / older) * 100
                    if abs(change) > 15:
                        insights.append({
                            "type": "trend_shift",
                            "kpi_name": kpi_name,
                            "severity": "critical" if abs(change) > 30 else "warning",
                            "description": f"Shift of {change:.1f}% in {kpi_name}",
                            "details": f"{'Increase' if change > 0 else 'Decrease'} from {older:.2f} to {recent:.2f}",
                            "change_pct": round(change, 1),
                            "explanation": f"The metric {kpi_name} {'increased' if change > 0 else 'decreased'} by {abs(change):.1f}% between the two periods.",
                        })
    
    # 2. Correlations
    if "kpi_name" in df.columns and "value" in df.columns:
        pivot = df.pivot_table(index="date", columns="kpi_name", values="value", aggfunc="mean")
        numeric_cols = pivot.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) >= 2:
            corr_matrix = pivot[numeric_cols].corr()
            for i, col1 in enumerate(numeric_cols):
                for col2 in numeric_cols[i + 1:]:
                    if i < len(numeric_cols) - 1:
                        r = corr_matrix.loc[col1, col2]
                        if abs(r) > 0.75:
                            insights.append({
                                "type": "correlation",
                                "kpi_name": f"{col1} vs {col2}",
                                "severity": "info",
                                "description": f"Strong correlation ({r:.2f}) between {col1} and {col2}",
                                "correlation": round(r, 3),
                                "explanation": f"A strong correlation (r={r:.3f}) exists between {col1} and {col2}.",
                            })
    
    # 3. Concentration risk
    if "customer_id" in df.columns and "value" in df.columns:
        total = df["value"].sum()
        if total > 0:
            top5 = df.groupby("customer_id")["value"].sum().nlargest(5)
            top5_pct = top5.sum() / total * 100
            if top5_pct > 50:
                insights.append({
                    "type": "concentration_risk",
                    "kpi_name": "Top 5 customers",
                    "severity": "warning",
                    "description": f"Top 5 entities represent {top5_pct:.1f}% of total value",
                    "concentration_pct": round(top5_pct, 1),
                    "explanation": f"The top 5 entities represent {top5_pct:.1f}% of total value, presenting a concentration risk.",
                })
    
    # 4. Data freshness
    if "date" in df.columns:
        try:
            latest = pd.to_datetime(df["date"].max())
            now = pd.Timestamp.now()
            days_stale = (now - latest).days
            if days_stale > 3:
                insights.append({
                    "type": "data_freshness",
                    "kpi_name": "Data freshness",
                    "severity": "warning" if days_stale > 7 else "info",
                    "description": f"Data is {days_stale} days stale (last: {latest.date()})",
                    "days_stale": days_stale,
                    "explanation": f"Data has not been updated for {days_stale} days. The most recent data is from {latest.date()}.",
                })
        except Exception:
            pass
    
    return insights


# ─── 4. Explainable AI ──────────────────────────────────────────────────────

def explain_anomaly(anomaly: dict) -> str:
    """Generate plain-language explanation for an anomaly."""
    kpi_name = anomaly.get("kpi_name", "Unknown")
    severity = anomaly.get("severity", "WARNING")
    deviation = float(anomaly.get("deviation", 0))
    context = anomaly.get("context", {})
    reason = context.get("reason", "")
    
    sev_labels = {"CRITICAL": "critical", "WARNING": "notable"}
    sev_label = sev_labels.get(severity, "notable")
    
    # Try orchestrator first, then direct Groq
    try:
        from .ai_orchestrator import execute_llm_sync
        prompt = f"""Explain this CNPS data anomaly in simple English (max 3 sentences):
KPI: {kpi_name}
Severity: {sev_label}
Deviation: {deviation:.1f}%
Context: {reason}

Format: Plain explanation, no technical jargon."""
        result = execute_llm_sync(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=150,
        )
        if result and hasattr(result, "choices") and result.choices:
            return result.choices[0].message.content
    except Exception:
        pass
    
    try:
        from .groq_utils import execute_groq_completion
        prompt = f"""Explain this CNPS data anomaly in simple English (max 3 sentences):
KPI: {kpi_name}
Severity: {sev_label}
Deviation: {deviation:.1f}%
Context: {reason}

Format: Plain explanation, no technical jargon."""
        from .ai_orchestrator import execute_llm_sync
        response = execute_llm_sync(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=150,
        )
        if response and "error" not in str(response).lower():
            return response
    except Exception:
        pass
    
    # Fallback
    return f"A {sev_label} anomaly was detected on {kpi_name} with a deviation of {deviation:.1f}%. {reason}"


def explain_kpi_movement(kpi: dict) -> str:
    """Generate plain-language explanation for a KPI movement."""
    kpi_name = kpi.get("kpi_name", "Unknown")
    value = float(kpi.get("value", 0))
    dod = float(kpi.get("dod_pct", 0)) if kpi.get("dod_pct") is not None else None
    wow = float(kpi.get("wow_pct", 0)) if kpi.get("wow_pct") is not None else None
    
    parts = [f"{kpi_name} is currently at {value:,.2f}."]
    
    if dod is not None and abs(dod) > 0.5:
        direction = "increased" if dod > 0 else "decreased"
        parts.append(f"Compared to yesterday, it has {direction} by {abs(dod):.1f}%.")
    
    if wow is not None and abs(wow) > 0.5:
        direction = "increased" if wow > 0 else "decreased"
        parts.append(f"Compared to last week, it has {direction} by {abs(wow):.1f}%.")
    
    return " ".join(parts)


# ─── 5. Governance Score ────────────────────────────────────────────────────

def compute_governance_score(
    df: pd.DataFrame,
    validation_results: list,
    days_since_last_sync: int,
    has_semantic_mappings: bool,
) -> dict:
    """
    Compute 4-dimension governance health score.
    
    Dimensions:
    1. Completeness (missing data ratio)
    2. Freshness (time since last sync)
    3. Validity (validation pass rate)
    4. Traceability (field mappings + lineage)
    """
    # 1. Completeness
    completeness = 100.0
    if not df.empty:
        null_ratio = df.isna().sum().sum() / (df.shape[0] * df.shape[1]) if df.shape[1] > 0 else 0
        completeness = max(0, round((1 - null_ratio) * 100, 1))
    
    # 2. Freshness
    if days_since_last_sync >= 30:
        freshness = 0
    elif days_since_last_sync >= 14:
        freshness = 25
    elif days_since_last_sync >= 7:
        freshness = 50
    elif days_since_last_sync >= 3:
        freshness = 75
    else:
        freshness = 100
    
    # 3. Validity
    validity = 100.0
    if validation_results:
        passes = sum(1 for r in validation_results if (r.get("status") if isinstance(r, dict) else getattr(r, "status", None)) == "pass")
        total = len(validation_results)
        validity = round(passes / total * 100, 1) if total > 0 else 100.0
    
    # 4. Traceability
    traceability = 50.0 if has_semantic_mappings else 0.0
    if not df.empty and "source_row_id" in df.columns:
        traceability = max(traceability, 75.0)
    
    # Composite score (weighted)
    weights = {"completeness": 0.25, "freshness": 0.25, "validity": 0.30, "traceability": 0.20}
    composite = (
        completeness * weights["completeness"]
        + freshness * weights["freshness"]
        + validity * weights["validity"]
        + traceability * weights["traceability"]
    )
    
    # Letter grade
    if composite >= 90:
        grade = "A"
    elif composite >= 75:
        grade = "B"
    elif composite >= 60:
        grade = "C"
    elif composite >= 45:
        grade = "D"
    else:
        grade = "F"
    
    return {
        "score": round(composite, 1),
        "grade": grade,
        "dimensions": {
            "completeness": round(completeness, 1),
            "freshness": round(freshness, 1),
            "validity": round(validity, 1),
            "traceability": round(traceability, 1),
        },
        "recommendations": _generate_governance_recommendations(completeness, freshness, validity, traceability),
    }


def _generate_governance_recommendations(
    completeness: float, freshness: float, validity: float, traceability: float,
) -> list:
    recommendations = []
    if completeness < 80:
        recommendations.append({
            "priority": "HIGH",
            "area": "Complétude",
            "action": "Corriger les données manquantes dans vos sources de données.",
        })
    if freshness < 50:
        recommendations.append({
            "priority": "HIGH",
            "area": "Actualité",
            "action": "Augmenter la fréquence de synchronisation des données.",
        })
    if validity < 80:
        recommendations.append({
            "priority": "MEDIUM",
            "area": "Validité",
            "action": "Examiner les échecs de validation et corriger les données sources.",
        })
    if traceability < 50:
        recommendations.append({
            "priority": "MEDIUM",
            "area": "Traçabilité",
            "action": "Configurer les mappings sémantiques pour améliorer la traçabilité.",
        })
    if not recommendations:
        recommendations.append({
            "priority": "LOW",
            "area": "Général",
            "action": "Continuer la maintenance régulière pour maintenir la note de gouvernance.",
        })
    return recommendations


# ─── 7. Rich Insight Generation (11-Point Format) ───────────────────────────

def generate_rich_insight(
    question: str,
    data: list[dict],
    columns: list[str],
    method: str,
    sql: str = None,
) -> dict:
    """
    Generate a comprehensive insight response with 11 points.
    
    1. Understanding
    2. Method Used
    3. Formula Used
    4. Processing Steps
    5. Results
    6. Visualizations (chart spec)
    7. Key Findings
    8. Risks
    9. Opportunities
    10. Recommendations
    11. Confidence Score
    """
    from .chart_service import build_chart_from_rows
    
    # Extract numeric values
    all_values = []
    for row in data:
        for col in columns:
            try:
                val = float(row.get(col, 0))
                all_values.append(val)
            except (TypeError, ValueError):
                pass
    
    # Run statistical analysis
    stats = run_full_statistical_analysis(all_values, label=question[:60]) if all_values else {}
    
    # Build chart
    chart_spec = build_chart_from_rows(data, columns, title=question[:80])
    
    # Key findings from stats
    findings = []
    if stats and "descriptive" in stats:
        desc = stats["descriptive"]
        if isinstance(desc.get("mean"), dict):
            mean_val = desc["mean"].get("result", 0)
            findings.append(f"La valeur moyenne est de {mean_val:,.2f}.")
        if "min" in desc and "max" in desc:
            findings.append(f"Les valeurs s'échelonnent de {desc['min']:,.2f} à {desc['max']:,.2f}.")
        if isinstance(desc.get("std_dev"), dict):
            std_val = desc["std_dev"].get("result", 0)
            findings.append(f"L'écart-type est de {std_val:,.2f}.")
        if isinstance(desc.get("quartiles"), dict):
            q_res = desc["quartiles"].get("result", {})
            if q_res:
                findings.append(f"La médiane est de {q_res.get('Q2 (Median)', 'N/A')}.")
    
    # Risks
    risks = []
    if stats and "outliers" in stats:
        zscore_outliers = stats["outliers"].get("zscore", {}).get("result", {}).get("count", 0)
        iqr_outliers = stats["outliers"].get("iqr", {}).get("result", {}).get("count", 0)
        total_outliers = max(zscore_outliers, iqr_outliers)
        if total_outliers > 0:
            risks.append(f"{total_outliers} valeur(s) anormale(s) détectée(s). Investigation recommandée.")
    
    # Opportunities
    opportunities = []
    if len(data) > 5:
        opportunities.append("Analyser la tendance sur une période plus longue pour identifier des patterns saisonniers.")
    if len(columns) > 2:
        opportunities.append("Explorer les relations entre les différentes colonnes pour découvrir des corrélations cachées.")
    
    # Confidence
    confidence = min(0.95, 0.5 + len(data) * 0.01) if data else 0
    if method == "nlq":
        confidence = min(confidence, 0.85)  # NLQ has inherent uncertainty
    
    return {
        "understanding": f"J'ai analysé votre question: '{question}'. Les données comportent {len(data)} lignes et {len(columns)} colonnes.",
        "method_used": method,
        "formula_used": explain_formula(question, method.split("_")[0] if "_" in method else method),
        "processing_steps": [
            f"Récupération de {len(data)} enregistrements",
            "Identification des colonnes numériques et catégorielles",
            f"Application de la méthode: {method}",
            "Génération des visualisations et statistiques",
        ],
        "results": {
            "row_count": len(data),
            "column_count": len(columns),
            "columns": columns,
            "statistics": stats.get("descriptive", {}),
        },
        "visualizations": chart_spec,
        "key_findings": findings,
        "risks": risks,
        "opportunities": opportunities,
        "recommendations": [
            "Configurer des alertes automatiques pour les variations significatives",
            "Planifier des analyses régulières pour suivre les tendances",
        ],
        "confidence_score": round(confidence, 3),
        "sql_used": sql,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ─── Insight Snapshots ──────────────────────────────────────────────────────

def create_insight_snapshot(supabase, user_id: str, title: str, content: str,
                            insight_type: str = "manual", kpi_name: str = None,
                            metadata: dict = None) -> dict:
    """Save an insight snapshot to the database."""
    snapshot = {
        "user_id": user_id,
        "title": title,
        "content": content,
        "insight_type": insight_type,
        "kpi_name": kpi_name,
        "metadata": metadata or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        supabase.table("insight_snapshots").insert(snapshot).execute()
    except Exception as e:
        logger.warning(f"Failed to save insight snapshot: {e}")
    return snapshot


def get_insight_snapshots(supabase, user_id: str, limit: int = 20) -> list:
    """Retrieve insight snapshots."""
    try:
        rows = _safe(
            supabase.table("insight_snapshots")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return rows
    except Exception as e:
        logger.warning(f"Failed to get insight snapshots: {e}")
        return []