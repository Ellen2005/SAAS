"""Chart specification builders for Recharts on the frontend."""
from __future__ import annotations

import json
import urllib.parse
from typing import Any

import pandas as pd

CHART_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444", "#06b6d4", "#ec4899"]


def _label(name: str) -> str:
    return str(name).replace("_", " ").strip()


def build_kpi_snapshot_chart(kpis: list[dict]) -> dict | None:
    """Horizontal bar chart of current KPI values on the dashboard."""
    if not kpis:
        return None
    rows = sorted(kpis, key=lambda k: float(k.get("value") or 0), reverse=True)[:12]
    return {
        "type": "bar",
        "layout": "vertical",
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


def _pick_columns(columns: list[str], rows: list[dict]) -> tuple[str | None, str | None]:
    if not columns or not rows:
        return None, None
    lower = {c: c.lower() for c in columns}
    numeric_cols = []
    for col in columns:
        sample = rows[0].get(col)
        if isinstance(sample, (int, float)) and not isinstance(sample, bool):
            numeric_cols.append(col)
            continue
        try:
            float(sample)
            numeric_cols.append(col)
        except (TypeError, ValueError):
            pass
    date_hints = ("date", "time", "at", "day", "month", "year")
    x_col = next((c for c in columns if any(h in lower[c] for h in date_hints)), None)
    y_col = numeric_cols[0] if numeric_cols else None
    if not x_col and len(columns) >= 2:
        x_col = columns[0]
    if not y_col and len(columns) >= 2:
        y_col = columns[1] if columns[1] != x_col else (columns[2] if len(columns) > 2 else None)
    return x_col, y_col


def build_chart_from_rows(
    rows: list[dict],
    columns: list[str] | None = None,
    *,
    chart_type: str = "auto",
    title: str = "Query result",
) -> dict | None:
    if not rows:
        return None
    columns = columns or list(rows[0].keys())
    x_col, y_col = _pick_columns(columns, rows)
    if not y_col:
        return {
            "type": "table_only",
            "title": title,
            "message": "No numeric column detected for charting.",
        }

    ctype = chart_type.lower().strip() if chart_type else "auto"
    if ctype == "auto":
        ctype = "line" if x_col and any(h in (x_col or "").lower() for h in ("date", "time", "at")) else "bar"

    data = []
    for row in rows[:50]:
        point = {"label": str(row.get(x_col, ""))[:40] if x_col else str(len(data) + 1)}
        try:
            point["value"] = float(row.get(y_col))
        except (TypeError, ValueError):
            continue
        data.append(point)
    if not data:
        return None

    return {
        "type": ctype if ctype in {"bar", "line", "pie", "area"} else "bar",
        "title": title,
        "xKey": "label",
        "yKey": "value",
        "data": data,
        "colors": CHART_COLORS,
        "meta": {"x_column": x_col, "y_column": y_col},
    }


def build_custom_chart_spec(
    rows: list[dict],
    *,
    chart_type: str,
    x_column: str | None,
    y_column: str | None,
    title: str,
) -> dict | None:
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
        data.append({
            "label": str(row.get(x_col, len(data) + 1))[:60] if x_col else str(len(data) + 1),
            "value": val,
        })
    if not data:
        return None
    ctype = chart_type if chart_type in {"bar", "line", "pie", "area"} else "bar"
    return {
        "type": ctype,
        "title": title or "Custom chart",
        "xKey": "label",
        "yKey": "value",
        "data": data,
        "colors": CHART_COLORS,
        "meta": {"x_column": x_col, "y_column": y_col},
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
