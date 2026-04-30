import logging
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)


def generate_forecasts(df: pd.DataFrame) -> list:
    """
    Generate 7-day ahead forecasts for each KPI using Prophet.
    Returns a list of forecast dicts ready for Supabase insertion.
    Falls back gracefully if Prophet is unavailable or data is insufficient.
    """
    try:
        from prophet import Prophet
    except ImportError:
        logger.warning("Prophet not installed — skipping forecasting.")
        return []

    forecasts = []

    for kpi_name in df["kpi_name"].unique():
        kpi_df = df[df["kpi_name"] == kpi_name].sort_values("date").copy()

        # Prophet requires at least 2 data points; realistically needs 10+ for useful forecasts
        if len(kpi_df) < 10:
            continue

        try:
            prophet_df = kpi_df[["date", "value"]].rename(columns={"date": "ds", "value": "y"})
            prophet_df["ds"] = pd.to_datetime(prophet_df["ds"])

            model = Prophet(
                interval_width=0.80,
                daily_seasonality=False,
                weekly_seasonality=True,
                yearly_seasonality=False,
                changepoint_prior_scale=0.05,
            )
            model.fit(prophet_df)

            future = model.make_future_dataframe(periods=7)
            forecast = model.predict(future)

            # Only return the 7 future rows
            future_rows = forecast.tail(7)
            for _, row in future_rows.iterrows():
                forecasts.append({
                    "kpi_name": kpi_name,
                    "forecast_date": row["ds"].date().isoformat(),
                    "predicted_value": round(float(row["yhat"]), 2),
                    "lower_bound": round(float(row["yhat_lower"]), 2),
                    "upper_bound": round(float(row["yhat_upper"]), 2),
                    "generated_at": datetime.utcnow().isoformat(),
                })
        except Exception as e:
            logger.error(f"Forecast failed for {kpi_name}: {e}")
            continue

    return forecasts


def store_forecasts(supabase, user_id: str, department_id, forecasts: list):
    """Persist forecast results to the kpi_forecasts table."""
    if not forecasts:
        return
    for f in forecasts:
        f["user_id"] = user_id
        f["department_id"] = department_id
    try:
        supabase.table("kpi_forecasts").insert(forecasts).execute()
    except Exception as e:
        logger.error(f"Failed to store forecasts: {e}")
