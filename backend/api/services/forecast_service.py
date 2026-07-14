import logging
import math
from datetime import datetime, timezone, timedelta
UTC = timezone.utc

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _fallback_forecast(kpi_df: pd.DataFrame, periods: int = 7) -> list:
    """
    Simple moving-average + linear-trend forecast when Prophet is unavailable.
    Uses the last 14 data points (or all if fewer) to project forward with
    a confidence band derived from recent volatility.
    """
    vals = kpi_df["value"].astype(float).tolist()
    if len(vals) < 2:
        return []

    recent = vals[-14:] if len(vals) >= 14 else vals
    n = len(recent)

    # Simple linear regression on recent window
    x = np.arange(n, dtype=float)
    y = np.array(recent, dtype=float)
    x_mean = x.mean()
    y_mean = y.mean()
    ss_xy = ((x - x_mean) * (y - y_mean)).sum()
    ss_xx = ((x - x_mean) ** 2).sum()
    slope = ss_xy / ss_xx if ss_xx != 0 else 0
    intercept = y_mean - slope * x_mean

    # Recent volatility for confidence band
    if n >= 3:
        residuals = y - (slope * x + intercept)
        volatility = float(np.std(residuals))
    else:
        volatility = float(np.std(y)) * 0.2 if len(y) > 1 else abs(y_mean) * 0.05

    # Generate forecast dates
    last_date = pd.to_datetime(kpi_df["date"].iloc[-1])
    forecasts = []
    for i in range(1, periods + 1):
        future_date = last_date + timedelta(days=i)
        predicted = slope * (n + i - 1) + intercept
        band = volatility * (1 + 0.15 * i)  # widen slightly over time
        forecasts.append({
            "forecast_date": future_date.date().isoformat(),
            "predicted_value": round(float(predicted), 2),
            "lower_bound": round(float(predicted - 1.65 * band), 2),
            "upper_bound": round(float(predicted + 1.65 * band), 2),
        })
    return forecasts


def _prophet_forecast(kpi_df: pd.DataFrame, periods: int = 7) -> list:
    """Prophet-based forecast. Returns empty list if Prophet unavailable."""
    try:
        from prophet import Prophet
    except (ImportError, Exception) as e:
        logger.warning(f"Prophet unavailable ({e}), will use fallback.")
        return []

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

    future = model.make_future_dataframe(periods=periods)
    forecast = model.predict(future)

    future_rows = forecast.tail(periods)
    results = []
    for _, row in future_rows.iterrows():
        results.append({
            "forecast_date": row["ds"].date().isoformat(),
            "predicted_value": round(float(row["yhat"]), 2),
            "lower_bound": round(float(row["yhat_lower"]), 2),
            "upper_bound": round(float(row["yhat_upper"]), 2),
        })
    return results


def generate_forecasts(df: pd.DataFrame) -> list:
    """
    Generate 7-day ahead forecasts for each KPI.
    Uses Prophet when available; falls back to linear-trend extrapolation.
    Returns a list of forecast dicts ready for Supabase insertion.
    """
    if df.empty or "kpi_name" not in df.columns or "date" not in df.columns:
        return []

    forecasts = []
    for kpi_name in df["kpi_name"].unique():
        kpi_df = df[df["kpi_name"] == kpi_name].sort_values("date").copy()
        kpi_df = kpi_df.dropna(subset=["date", "value"])

        # Need at least 3 data points for any meaningful forecast
        if len(kpi_df) < 3:
            continue

        try:
            # Try Prophet first, fall back to linear trend
            result = _prophet_forecast(kpi_df)
            if not result:
                result = _fallback_forecast(kpi_df)

            for entry in result:
                entry["kpi_name"] = kpi_name
                entry["generated_at"] = datetime.now(UTC).isoformat()
            forecasts.extend(result)
        except Exception as e:
            logger.error(f"Forecast failed for {kpi_name}: {e}")
            # Even on error, try fallback
            try:
                result = _fallback_forecast(kpi_df)
                for entry in result:
                    entry["kpi_name"] = kpi_name
                    entry["generated_at"] = datetime.now(UTC).isoformat()
                forecasts.extend(result)
            except Exception:
                pass

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
        _cleanup_old_forecasts(supabase, user_id)
    except Exception as e:
        logger.error(f"Failed to store forecasts: {e}")


def _cleanup_old_forecasts(supabase, user_id: str, max_age_days: int = 60):
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
        supabase.table("kpi_forecasts").delete().eq("user_id", user_id).lt("generated_at", cutoff).execute()
    except Exception as e:
        logger.warning(f"Forecast cleanup failed: {e}")
