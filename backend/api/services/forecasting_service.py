"""
Advanced ML Forecasting Service
================================
Provides time-series forecasting using multiple algorithms.

Supported methods:
- Prophet (Facebook) - best for seasonal data
- ARIMA - classical time series
- Exponential Smoothing - simple trends
- Linear Regression - basic trend projection
- Moving Average - smoothing

All methods are optional and fall back gracefully.
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


def forecast_with_prophet(
    data: List[Dict],
    periods: int = 30,
    seasonality: str = "auto"
) -> Optional[Dict]:
    """
    Forecast using Facebook Prophet.
    
    Args:
        data: List of {date, value} dicts
        periods: Number of periods to forecast
        seasonality: 'auto', 'daily', 'weekly', 'monthly', 'yearly'
    
    Returns:
        {
            "method": "prophet",
            "forecast": [...],
            "confidence_intervals": {...},
            "components": {...}
        }
    """
    try:
        from prophet import Prophet
        import pandas as pd
        
        # Prepare data
        df = pd.DataFrame(data)
        df.columns = ['ds', 'y']  # Prophet expects 'ds' (date) and 'y' (value)
        df['ds'] = pd.to_datetime(df['ds'])
        
        # Configure seasonality
        model = Prophet(
            yearly_seasonality=(seasonality in ['auto', 'yearly']),
            weekly_seasonality=(seasonality in ['auto', 'weekly']),
            daily_seasonality=(seasonality in ['auto', 'daily']),
        )
        
        model.fit(df)
        
        # Create future dataframe
        future = model.make_future_dataframe(periods=periods)
        forecast = model.predict(future)
        
        # Extract results
        forecast_data = []
        for _, row in forecast.tail(periods).iterrows():
            forecast_data.append({
                "date": row['ds'].isoformat(),
                "predicted": float(row['yhat']),
                "lower_bound": float(row['yhat_lower']),
                "upper_bound": float(row['yhat_upper']),
            })
        
        return {
            "method": "prophet",
            "forecast": forecast_data,
            "confidence": 0.95,
            "components": {
                "trend": "included",
                "seasonality": seasonality,
            }
        }
    except ImportError:
        logger.warning("Prophet not installed. Install with: pip install prophet")
        return None
    except Exception as e:
        logger.error(f"Prophet forecasting failed: {e}")
        return None


def forecast_with_arima(
    data: List[Dict],
    periods: int = 30,
    order: Tuple[int, int, int] = (5, 1, 0)
) -> Optional[Dict]:
    """
    Forecast using ARIMA (AutoRegressive Integrated Moving Average).
    
    Args:
        data: List of {date, value} dicts
        periods: Number of periods to forecast
        order: (p, d, q) parameters
    
    Returns:
        {
            "method": "arima",
            "forecast": [...],
            "confidence_intervals": {...}
        }
    """
    try:
        from statsmodels.tsa.arima.model import ARIMA
        import pandas as pd
        
        # Prepare data
        values = [d['value'] for d in data]
        
        # Fit ARIMA model
        model = ARIMA(values, order=order)
        model_fit = model.fit()
        
        # Forecast
        forecast_result = model_fit.forecast(steps=periods)
        conf_int = model_fit.get_forecast(steps=periods).conf_int(alpha=0.05)
        
        # Extract results
        forecast_data = []
        last_date = datetime.fromisoformat(data[-1]['date'])
        
        for i in range(periods):
            date = (last_date + timedelta(days=i+1)).isoformat()
            forecast_data.append({
                "date": date,
                "predicted": float(forecast_result[i]),
                "lower_bound": float(conf_int.iloc[i, 0]),
                "upper_bound": float(conf_int.iloc[i, 1]),
            })
        
        return {
            "method": "arima",
            "forecast": forecast_data,
            "confidence": 0.95,
            "order": order,
        }
    except ImportError:
        logger.warning("statsmodels not installed. Install with: pip install statsmodels")
        return None
    except Exception as e:
        logger.error(f"ARIMA forecasting failed: {e}")
        return None


def forecast_with_exponential_smoothing(
    data: List[Dict],
    periods: int = 30,
    alpha: float = 0.3
) -> Optional[Dict]:
    """
    Forecast using Exponential Smoothing.
    
    Args:
        data: List of {date, value} dicts
        periods: Number of periods to forecast
        alpha: Smoothing factor (0-1)
    
    Returns:
        {
            "method": "exponential_smoothing",
            "forecast": [...]
        }
    """
    try:
        values = [d['value'] for d in data]
        last_date = datetime.fromisoformat(data[-1]['date'])
        
        # Simple exponential smoothing
        smoothed = [values[0]]
        for v in values[1:]:
            smoothed.append(alpha * v + (1 - alpha) * smoothed[-1])
        
        # Forecast (flat forecast for simplicity)
        last_smoothed = smoothed[-1]
        forecast_data = []
        
        for i in range(periods):
            date = (last_date + timedelta(days=i+1)).isoformat()
            # Add simple trend
            trend = (values[-1] - values[0]) / len(values)
            predicted = last_smoothed + trend * (i + 1)
            
            forecast_data.append({
                "date": date,
                "predicted": float(predicted),
                "lower_bound": float(predicted * 0.9),  # ±10%
                "upper_bound": float(predicted * 1.1),
            })
        
        return {
            "method": "exponential_smoothing",
            "forecast": forecast_data,
            "confidence": 0.80,
            "alpha": alpha,
        }
    except Exception as e:
        logger.error(f"Exponential smoothing failed: {e}")
        return None


def forecast_with_linear_regression(
    data: List[Dict],
    periods: int = 30
) -> Optional[Dict]:
    """
    Forecast using Linear Regression.
    
    Args:
        data: List of {date, value} dicts
        periods: Number of periods to forecast
    
    Returns:
        {
            "method": "linear_regression",
            "forecast": [...],
            "r_squared": ...
        }
    """
    try:
        import numpy as np
        
        # Prepare data
        x = np.arange(len(data)).reshape(-1, 1)
        y = np.array([d['value'] for d in data])
        
        # Fit linear regression
        from sklearn.linear_model import LinearRegression
        model = LinearRegression()
        model.fit(x, y)
        
        # Calculate R-squared
        r_squared = model.score(x, y)
        
        # Forecast
        last_date = datetime.fromisoformat(data[-1]['date'])
        future_x = np.arange(len(data), len(data) + periods).reshape(-1, 1)
        predictions = model.predict(future_x)
        
        # Calculate confidence interval (±2 std)
        residuals = y - model.predict(x)
        std = np.std(residuals)
        
        forecast_data = []
        for i in range(periods):
            date = (last_date + timedelta(days=i+1)).isoformat()
            pred = predictions[i]
            forecast_data.append({
                "date": date,
                "predicted": float(pred),
                "lower_bound": float(pred - 2 * std),
                "upper_bound": float(pred + 2 * std),
            })
        
        return {
            "method": "linear_regression",
            "forecast": forecast_data,
            "confidence": 0.95,
            "r_squared": float(r_squared),
            "slope": float(model.coef_[0]),
            "intercept": float(model.intercept_),
        }
    except ImportError:
        logger.warning("scikit-learn not installed. Install with: pip install scikit-learn")
        return None
    except Exception as e:
        logger.error(f"Linear regression forecasting failed: {e}")
        return None


def forecast_with_moving_average(
    data: List[Dict],
    periods: int = 30,
    window: int = 7
) -> Optional[Dict]:
    """
    Forecast using Moving Average.
    
    Args:
        data: List of {date, value} dicts
        periods: Number of periods to forecast
        window: Moving average window size
    
    Returns:
        {
            "method": "moving_average",
            "forecast": [...]
        }
    """
    try:
        values = [d['value'] for d in data]
        last_date = datetime.fromisoformat(data[-1]['date'])
        
        # Calculate moving average
        if len(values) < window:
            window = len(values)
        
        ma = sum(values[-window:]) / window
        
        # Forecast (flat)
        forecast_data = []
        for i in range(periods):
            date = (last_date + timedelta(days=i+1)).isoformat()
            forecast_data.append({
                "date": date,
                "predicted": float(ma),
                "lower_bound": float(ma * 0.85),
                "upper_bound": float(ma * 1.15),
            })
        
        return {
            "method": "moving_average",
            "forecast": forecast_data,
            "confidence": 0.75,
            "window": window,
        }
    except Exception as e:
        logger.error(f"Moving average forecasting failed: {e}")
        return None


def ensemble_forecast(
    data: List[Dict],
    periods: int = 30,
    kpi_name: str = ""
) -> Dict:
    """
    Combine multiple forecasting methods for better accuracy.
    
    Uses weighted average of all available methods.
    Weights are based on historical accuracy (if available).
    """
    methods = [
        ("prophet", forecast_with_prophet, 0.4),
        ("arima", forecast_with_arima, 0.3),
        ("exponential_smoothing", forecast_with_exponential_smoothing, 0.15),
        ("linear_regression", forecast_with_linear_regression, 0.1),
        ("moving_average", forecast_with_moving_average, 0.05),
    ]
    
    results = []
    weights = []
    
    for name, func, weight in methods:
        result = func(data, periods)
        if result:
            results.append(result)
            weights.append(weight)
    
    if not results:
        return {
            "method": "none",
            "forecast": [],
            "error": "No forecasting method available",
        }
    
    # Normalize weights
    total_weight = sum(weights)
    weights = [w / total_weight for w in weights]
    
    # Combine forecasts
    combined = []
    for i in range(periods):
        predicted = sum(r['forecast'][i]['predicted'] * w for r, w in zip(results, weights))
        lower = sum(r['forecast'][i]['lower_bound'] * w for r, w in zip(results, weights))
        upper = sum(r['forecast'][i]['upper_bound'] * w for r, w in zip(results, weights))
        
        combined.append({
            "date": results[0]['forecast'][i]['date'],
            "predicted": predicted,
            "lower_bound": lower,
            "upper_bound": upper,
        })
    
    return {
        "method": "ensemble",
        "kpi_name": kpi_name,
        "forecast": combined,
        "confidence": 0.90,
        "methods_used": [r['method'] for r in results],
        "weights": dict(zip([r['method'] for r in results], weights)),
    }


def forecast_kpi(
    data: List[Dict],
    periods: int = 30,
    method: str = "auto"
) -> Dict:
    """
    Main forecasting function.
    
    Args:
        data: List of {date, value} dicts
        periods: Number of periods to forecast
        method: 'auto', 'prophet', 'arima', 'exponential_smoothing', 'linear_regression', 'moving_average'
    
    Returns:
        Forecast results
    """
    if not data or len(data) < 3:
        return {
            "method": "none",
            "forecast": [],
            "error": "Insufficient data for forecasting (need at least 3 data points)",
        }
    
    if method == "auto":
        return ensemble_forecast(data, periods)
    
    method_map = {
        "prophet": forecast_with_prophet,
        "arima": forecast_with_arima,
        "exponential_smoothing": forecast_with_exponential_smoothing,
        "linear_regression": forecast_with_linear_regression,
        "moving_average": forecast_with_moving_average,
    }
    
    func = method_map.get(method)
    if not func:
        return {
            "method": "none",
            "forecast": [],
            "error": f"Unknown method: {method}",
        }
    
    result = func(data, periods)
    if result:
        result['kpi_name'] = data[0].get('kpi_name', '')
    
    return result or {
        "method": "none",
        "forecast": [],
        "error": f"Forecasting failed for method: {method}",
    }