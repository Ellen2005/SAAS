import urllib.parse
import json
import pandas as pd

def generate_trend_chart_url(df: pd.DataFrame) -> str:
    """
    Takes the historical DataFrame, extracts the last 7 days of data,
    and returns a QuickChart.io URL for a line chart representing the primary KPI.
    """
    # Only show the last 7 - 14 days to keep the chart clean
    recent_df = df[df['date'] >= (df['date'].max() - pd.Timedelta(days=14))].copy()
    
    # Get unique dates (formatted)
    dates = sorted(recent_df['date'].unique())
    labels = [pd.to_datetime(d).strftime('%b %d') for d in dates]
    
    datasets = []
    # By requirement we focus on Total Revenue as the primary indicator for the chart
    for kpi_name in recent_df['kpi_name'].unique():
        if kpi_name != "Total Revenue":
            continue
            
        kpi_data = recent_df[recent_df['kpi_name'] == kpi_name].sort_values('date')
        values = kpi_data['value'].tolist()
        
        datasets.append({
            "label": kpi_name,
            "data": values,
            "borderColor": "#10b981", # Emerald green
            "backgroundColor": "rgba(16, 185, 129, 0.1)",
            "borderWidth": 3,
            "fill": True,
            "pointRadius": 4,
            "tension": 0.4
        })

    config = {
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": datasets
        },
        "options": {
            "title": {
                "display": True,
                "text": "14-Day Operations Trend"
            },
            "legend": {"position": "bottom"},
            "scales": {
                "yAxes": [{"ticks": {"beginAtZero": False}}]
            }
        }
    }
    
    # Encode config to URL
    encoded_config = urllib.parse.quote(json.dumps(config))
    return f"https://quickchart.io/chart?c={encoded_config}&w=600&h=300&bkg=white"
