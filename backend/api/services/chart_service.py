"""
Enterprise Chart Service
========================
Power BI-style chart engine with auto-recommendation.
Supports 12+ chart types with intelligent defaults.

Chart Types:
  - KPI Cards, Bar, Horizontal Bar, Line, Area, Pie, Doughnut,
    Scatter, Bubble, Histogram, Radar, Heatmap, Treemap, Table, Gauge
"""

from __future__ import annotations

import json
import math
import urllib.parse
from typing import Any, Optional

import pandas as pd

CHART_COLORS = [
    "#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444",
    "#06b6d4", "#ec4899", "#84cc16", "#f97316", "#6366f1",
    "#14b8a6", "#a855f7", "#e11d48", "#0ea5e9",
]
CHART_COLORS_HEX = [c.strip("#") for c in CHART_COLORS]


def _label(name: str) -> str:
    return str(name).replace("_", " ").replace("-", " ").strip().title()


def _is_numeric(val) -> bool:
    try:
        float(val)
        return True
    except (TypeError, ValueError):
        return False


def _auto_chart_type(x_col: str | None, data: list[dict]) -> str:
    """Auto-recommend the best chart type based on data shape."""
    if not data or len(data) == 0:
        return "table"
    
    # Single KPI value → gauge
    if len(data) == 1:
        return "gauge"
    
    # Count unique labels
    unique_labels = len(set(d.get("label", "") for d in data if d.get("label")))
    
    # Date/time on X → line
    if x_col and any(h in x_col.lower() for h in ("date", "time", "at", "day", "month", "year", "period")):
        if unique_labels <= 30:
            return "line"
        return "area"
    
    # Few categories → pie or bar
    if unique_labels <= 5:
        return "pie"
    elif unique_labels <= 12:
        return "bar"
    
    # Many categories → horizontal bar
    return "horizontalBar"


def _pick_columns(columns: list[str], rows: list[dict]) -> tuple[str | None, str | None]:
    """Intelligently pick X (categorical/date) and Y (numeric) columns."""
    if not columns or not rows:
        return None, None
    
    # Separate numeric vs non-numeric
    numeric_cols = []
    text_cols = []
    date_cols = []
    
    date_hints = ("date", "time", "at", "day", "month", "year", "period")
    id_hints = ("id", "code", "key", "ref")
    
    for col in columns:
        sample = rows[0].get(col)
        col_lower = col.lower()
        
        if col_lower in ("id", "_id", "user_id", "department_id"):
            continue  # Skip ID columns
        
        if isinstance(sample, (int, float)) and not isinstance(sample, bool):
            numeric_cols.append(col)
            continue
        
        try:
            float(sample) if sample is not None else None
            numeric_cols.append(col)
            continue
        except (TypeError, ValueError):
            pass
        
        # Check if it looks like a date
        if any(h in col_lower for h in date_hints):
            date_cols.append(col)
        elif not any(h in col_lower for h in id_hints):
            text_cols.append(col)
    
    # Prefer date column as X axis
    x_col = date_cols[0] if date_cols else None
    if not x_col:
        x_col = text_cols[0] if text_cols else None
    if not x_col:
        x_col = columns[0] if columns else None
    
    # Y axis = first numeric column
    y_col = numeric_cols[0] if numeric_cols else None
    
    # If we have 2+ numeric columns, second one can be additional metric
    # (used for bubble charts, scatter, etc.)
    
    return x_col, y_col


def build_kpi_snapshot_chart(kpis: list[dict]) -> dict | None:
    """Horizontal bar chart of current KPI values on the dashboard."""
    if not kpis:
        return None
    rows = sorted(kpis, key=lambda k: float(k.get("value") or 0), reverse=True)[:12]
    return {
        "type": "horizontalBar",
        "title": "Current metrics",
        "xKey": "value",
        "yKey": "name",
        "data": [
            {
                "name": _label(k.get("kpi_name", "metric")),
                "value": float(k.get("value") or 0),
                "status": k.get("status", "NORMAL"),
            }
            for k in rows
        ],
        "colors": CHART_COLORS,
    }


def build_chart_from_rows(
    rows: list[dict],
    columns: list[str] | None = None,
    *,
    chart_type: str = "auto",
    title: str = "Query result",
) -> dict | None:
    """Build a chart spec from query result rows.
    
    Auto-detects best chart type if not specified.
    Supports: bar, horizontalBar, line, area, pie, doughnut,
              scatter, bubble, radar, gauge, table
    """
    if not rows:
        return None
    
    columns = columns or list(rows[0].keys())
    x_col, y_col = _pick_columns(columns, rows)
    
    if not y_col:
        return {
            "type": "table",
            "title": title,
            "columns": columns,
            "data": rows[:50],
            "message": "No numeric column detected for charting.",
        }
    
    # Build data points
    data = []
    for row in rows[:100]:
        try:
            label_val = str(row.get(x_col, ""))[:60] if x_col else str(len(data) + 1)
            val = float(row.get(y_col))
        except (TypeError, ValueError):
            continue
        
        point = {"label": label_val, "value": val}
        
        # Add second numeric column for bubble/scatter
        numeric_cols = [c for c in columns if c != y_col and _is_numeric(rows[0].get(c))]
        if numeric_cols:
            try:
                point["value2"] = float(row.get(numeric_cols[0]))
            except (TypeError, ValueError):
                point["value2"] = 0
        if len(numeric_cols) >= 2:
            try:
                point["value3"] = float(row.get(numeric_cols[1]))
            except (TypeError, ValueError):
                point["value3"] = 0
        
        data.append(point)
    
    if not data:
        return None
    
    # Auto-detect chart type
    ctype = chart_type.lower().strip() if chart_type else "auto"
    if ctype == "auto":
        ctype = _auto_chart_type(x_col, data)
    elif ctype not in {"bar", "horizontalBar", "line", "area", "pie", "doughnut",
                        "scatter", "bubble", "radar", "histogram", "gauge", "table"}:
        ctype = "bar"
    
    spec = {
        "type": ctype,
        "title": title,
        "xKey": "label",
        "yKey": "value",
        "data": data,
        "colors": CHART_COLORS,
        "meta": {
            "x_column": x_col,
            "y_column": y_col,
            "row_count": len(data),
            "total_rows": len(rows),
        },
    }
    
    # Add extra keys for specific chart types
    if ctype in ("bubble", "scatter") and "value2" in data[0]:
        spec["zKey"] = "value2"
    if ctype == "radar":
        spec["allKeys"] = [k for k in data[0].keys() if k not in ("label",)]
    
    return spec


def build_custom_chart_spec(
    rows: list[dict],
    *,
    chart_type: str,
    x_column: str | None,
    y_column: str | None,
    title: str,
) -> dict | None:
    """Build a chart spec from user-specified parameters."""
    if not rows:
        return None
    
    columns = list(rows[0].keys())
    x_col = x_column if x_column in columns else None
    y_col = y_column if y_column in columns else None
    
    if not x_col or not y_col:
        x_col, y_col = _pick_columns(columns, rows)
    if not y_col:
        return None
    
    data = []
    for row in rows[:100]:
        try:
            val = float(row.get(y_col))
        except (TypeError, ValueError):
            continue
        point = {
            "label": str(row.get(x_col, len(data) + 1))[:60] if x_col else str(len(data) + 1),
            "value": val,
        }
        
        # Additional numeric columns for multi-metric charts
        other_numeric = [c for c in columns if c != y_col and c != x_col and _is_numeric(row.get(c))]
        for i, nc in enumerate(other_numeric[:3]):
            try:
                point[f"value{i+2}"] = float(row.get(nc))
            except (TypeError, ValueError):
                pass
        
        data.append(point)
    
    if not data:
        return None
    
    valid_types = {"bar", "horizontalBar", "line", "area", "pie", "doughnut",
                   "scatter", "bubble", "radar", "histogram", "gauge", "table"}
    ctype = chart_type if chart_type in valid_types else _auto_chart_type(x_col, data)
    
    return {
        "type": ctype,
        "title": title or "Custom chart",
        "xKey": "label",
        "yKey": "value",
        "data": data,
        "colors": CHART_COLORS,
        "meta": {"x_column": x_col, "y_column": y_col, "row_count": len(data)},
    }


def generate_trend_chart_url(df) -> str:
    """QuickChart URL for email embeds."""
    try:
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return ""
        if "date" not in df.columns or "kpi_name" not in df.columns or "value" not in df.columns:
            return ""

        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        recent = df[df["date"] >= (df["date"].max() - pd.Timedelta(days=14))]

        dates = sorted(recent["date"].unique())
        labels = [pd.to_datetime(d).strftime("%b %d") for d in dates]

        datasets = []
        for i, kpi_name in enumerate(recent["kpi_name"].unique()):
            kpi_data = recent[recent["kpi_name"] == kpi_name].sort_values("date")
            values = [round(float(v), 2) for v in kpi_data["value"].tolist()]
            color = CHART_COLORS[i % len(CHART_COLORS)]
            datasets.append({
                "label": _label(kpi_name),
                "data": values,
                "borderColor": color,
                "backgroundColor": f"{color}22",
                "borderWidth": 2,
                "fill": False,
                "pointRadius": 3,
                "tension": 0.4,
            })

        if not datasets:
            return ""

        config = {
            "type": "line",
            "data": {"labels": labels, "datasets": datasets},
            "options": {
                "title": {"display": True, "text": "14-Day KPI Trend"},
                "legend": {"position": "bottom"},
            },
        }
        encoded = urllib.parse.quote(json.dumps(config))
        return f"https://quickchart.io/chart?c={encoded}&w=600&h=280&bkg=white"
    except Exception as e:
        print(f"Chart generation failed: {e}")
        return ""