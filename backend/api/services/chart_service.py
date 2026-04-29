import urllib.parse
import json
import pandas as pd


def generate_trend_chart_url(df) -> str:
    """
    Generates a QuickChart.io URL for a KPI trend line chart.
    Returns empty string if df is empty or missing required columns.
    """
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
        colors = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6"]
        for i, kpi_name in enumerate(recent["kpi_name"].unique()):
            kpi_data = recent[recent["kpi_name"] == kpi_name].sort_values("date")
            values = [round(float(v), 2) for v in kpi_data["value"].tolist()]
            color = colors[i % len(colors)]
            datasets.append({
                "label": str(kpi_name).replace("_", " ").title(),
                "data": values,
                "borderColor": color,
                "backgroundColor": color.replace("#", "rgba(") + ",0.08)",
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
                "scales": {"yAxes": [{"ticks": {"beginAtZero": False}}]},
            },
        }

        encoded = urllib.parse.quote(json.dumps(config))
        return f"https://quickchart.io/chart?c={encoded}&w=600&h=280&bkg=white"
    except Exception as e:
        print(f"Chart generation failed: {e}")
        return ""
