"""
Statistical Analysis Engine
Provides real statistical methods: regression, correlation, forecasting,
hypothesis testing, time series decomposition, outlier detection.
Used by analysis_engine.py and the professional report service.
"""

import logging
import math
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import numpy as np
    import pandas as pd
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    logger.warning("scipy not available — statistical methods limited")


# ── Correlation Analysis ─────────────────────────────────────────────────────

def compute_correlation_matrix(df: pd.DataFrame, method: str = "pearson") -> Dict[str, Any]:
    """Compute pairwise correlation matrix for all numeric columns."""
    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.shape[1] < 2:
        return {"matrix": {}, "strong_pairs": [], "method": method}

    corr = numeric_df.corr(method=method)
    matrix = corr.to_dict()
    strong_pairs = []
    cols = list(corr.columns)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            r = corr.iloc[i, j]
            if abs(r) >= 0.7:
                strong_pairs.append({
                    "var1": cols[i], "var2": cols[j],
                    "r": round(float(r), 4),
                    "strength": "strong" if abs(r) >= 0.9 else "moderate-strong",
                    "direction": "positive" if r > 0 else "negative",
                })
    strong_pairs.sort(key=lambda x: abs(x["r"]), reverse=True)
    return {"matrix": matrix, "strong_pairs": strong_pairs, "method": method}


# ── Linear Regression ───────────────────────────────────────────────────────

def linear_regression(x: list, y: list) -> Dict[str, Any]:
    """Simple linear regression: y = a + b*x. Returns slope, intercept, R², p-value."""
    if not HAS_SCIPY or len(x) < 3:
        return {"error": "Need scipy and at least 3 data points"}
    x_arr = np.array([float(v) for v in x if v is not None])
    y_arr = np.array([float(v) for v in y if v is not None])
    min_len = min(len(x_arr), len(y_arr))
    x_arr, y_arr = x_arr[:min_len], y_arr[:min_len]
    slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(x_arr, y_arr)
    return {
        "slope": round(float(slope), 6),
        "intercept": round(float(intercept), 6),
        "r_squared": round(float(r_value ** 2), 6),
        "r": round(float(r_value), 6),
        "p_value": round(float(p_value), 8),
        "std_error": round(float(std_err), 6),
        "significant": float(p_value) < 0.05,
        "trend": "increasing" if slope > 0 else "decreasing" if slope < 0 else "flat",
        "forecast_next": round(float(intercept + slope * (min_len)), 4),
    }


def multiple_regression(df: pd.DataFrame, y_col: str, x_cols: List[str]) -> Dict[str, Any]:
    """Multiple linear regression: y = b0 + b1*x1 + b2*x2 + ..."""
    if not HAS_SCIPY:
        return {"error": "scipy required"}
    from sklearn.linear_model import LinearRegression
    data = df[[y_col] + x_cols].dropna()
    if len(data) < len(x_cols) + 2:
        return {"error": f"Need at least {len(x_cols) + 2} rows"}
    X = data[x_cols].values
    y = data[y_col].values
    model = LinearRegression().fit(X, y)
    r2 = model.score(X, y)
    coefs = dict(zip(x_cols, [round(float(c), 6) for c in model.coef_]))
    return {
        "intercept": round(float(model.intercept_), 6),
        "coefficients": coefs,
        "r_squared": round(r2, 6),
        "adj_r_squared": round(1 - (1 - r2) * (len(data) - 1) / (len(data) - len(x_cols) - 1), 6),
        "n_observations": len(data),
    }


# ── Time Series Forecasting ─────────────────────────────────────────────────

def forecast_linear_trend(values: List[float], periods: int = 6) -> Dict[str, Any]:
    """Forecast using linear regression trend line."""
    if not HAS_SCIPY or len(values) < 3:
        return {"error": "Need scipy and at least 3 data points"}
    x = list(range(len(values)))
    slope, intercept, r_value, p_value, _ = scipy_stats.linregress(x, values)
    forecasts = [round(float(intercept + slope * (len(values) + i)), 4) for i in range(periods)]
    residuals = [v - (intercept + slope * i) for i, v in enumerate(values)]
    rmse = math.sqrt(sum(r ** 2 for r in residuals) / len(residuals))
    return {
        "method": "linear_trend",
        "forecasts": forecasts,
        "trend_slope": round(float(slope), 6),
        "r_squared": round(float(r_value ** 2), 6),
        "rmse": round(rmse, 4),
        "confidence": "high" if r_value ** 2 > 0.7 else "medium" if r_value ** 2 > 0.4 else "low",
    }


def forecast_moving_average(values: List[float], window: int = 3, periods: int = 6) -> Dict[str, Any]:
    """Forecast using simple moving average."""
    if len(values) < window:
        return {"error": f"Need at least {window} data points"}
    recent = values[-window:]
    avg = sum(recent) / len(recent)
    std = math.sqrt(sum((v - avg) ** 2 for v in recent) / len(recent))
    forecasts = [round(avg + std * 0.1 * i, 4) for i in range(periods)]
    return {
        "method": "moving_average",
        "window": window,
        "forecasts": forecasts,
        "current_avg": round(avg, 4),
        "std_dev": round(std, 4),
    }


def forecast_exponential_smoothing(values: List[float], alpha: float = 0.3, periods: int = 6) -> Dict[str, Any]:
    """Simple exponential smoothing forecast."""
    if not values:
        return {"error": "No data"}
    smoothed = [values[0]]
    for v in values[1:]:
        smoothed.append(round(alpha * v + (1 - alpha) * smoothed[-1], 4))
    last = smoothed[-1]
    trend = (smoothed[-1] - smoothed[-max(3, len(smoothed))]) / max(1, min(3, len(smoothed) - 1))
    forecasts = [round(last + trend * (i + 1), 4) for i in range(periods)]
    return {
        "method": "exponential_smoothing",
        "alpha": alpha,
        "forecasts": forecasts,
        "last_smoothed": last,
        "trend_per_period": round(trend, 4),
    }


# ── Hypothesis Testing ──────────────────────────────────────────────────────

def t_test_two_samples(group1: List[float], group2: List[float]) -> Dict[str, Any]:
    """Two-sample t-test (Welch's). Tests if means are significantly different."""
    if not HAS_SCIPY or len(group1) < 2 or len(group2) < 2:
        return {"error": "Need scipy and at least 2 samples per group"}
    g1 = [float(v) for v in group1 if v is not None]
    g2 = [float(v) for v in group2 if v is not None]
    t_stat, p_value = scipy_stats.ttest_ind(g1, g2, equal_var=False)
    return {
        "test": "welch_t_test",
        "t_statistic": round(float(t_stat), 6),
        "p_value": round(float(p_value), 8),
        "significant_at_005": float(p_value) < 0.05,
        "significant_at_001": float(p_value) < 0.01,
        "group1_mean": round(float(np.mean(g1)), 4),
        "group2_mean": round(float(np.mean(g2)), 4),
        "group1_n": len(g1),
        "group2_n": len(g2),
        "effect_size_cohens_d": round(float((np.mean(g1) - np.mean(g2)) / np.sqrt((np.std(g1)**2 + np.std(g2)**2) / 2)), 4) if (np.std(g1) > 0 or np.std(g2) > 0) else 0,
    }


def one_way_anova(groups: List[List[float]]) -> Dict[str, Any]:
    """One-way ANOVA: tests if group means are significantly different."""
    if not HAS_SCIPY or len(groups) < 2:
        return {"error": "Need scipy and at least 2 groups"}
    cleaned = [[float(v) for v in g if v is not None] for g in groups]
    cleaned = [g for g in cleaned if len(g) >= 2]
    if len(cleaned) < 2:
        return {"error": "Need at least 2 groups with 2+ values each"}
    f_stat, p_value = scipy_stats.f_oneway(*cleaned)
    return {
        "test": "one_way_anova",
        "f_statistic": round(float(f_stat), 6),
        "p_value": round(float(p_value), 8),
        "significant_at_005": float(p_value) < 0.05,
        "n_groups": len(cleaned),
        "group_means": [round(float(np.mean(g)), 4) for g in cleaned],
    }


# ── Outlier Detection ───────────────────────────────────────────────────────

def detect_outliers_iqr(values: List[float], factor: float = 1.5) -> Dict[str, Any]:
    """Detect outliers using IQR method."""
    arr = np.array([float(v) for v in values if v is not None])
    if len(arr) < 4:
        return {"outliers": [], "n_outliers": 0, "method": "IQR"}
    q1, q3 = np.percentile(arr, [25, 75])
    iqr = q3 - q1
    lower, upper = q1 - factor * iqr, q3 + factor * iqr
    outlier_mask = (arr < lower) | (arr > upper)
    return {
        "outliers": [round(float(v), 4) for v in arr[outlier_mask]],
        "outlier_indices": [int(i) for i in np.where(outlier_mask)[0]],
        "n_outliers": int(outlier_mask.sum()),
        "pct_outliers": round(float(outlier_mask.sum() / len(arr) * 100), 2),
        "iqr": round(float(iqr), 4),
        "lower_bound": round(float(lower), 4),
        "upper_bound": round(float(upper), 4),
        "method": "IQR",
    }


def detect_outliers_zscore(values: List[float], threshold: float = 3.0) -> Dict[str, Any]:
    """Detect outliers using Z-score method."""
    arr = np.array([float(v) for v in values if v is not None])
    if len(arr) < 3:
        return {"outliers": [], "n_outliers": 0, "method": "zscore"}
    z_scores = np.abs(scipy_stats.zscore(arr)) if HAS_SCIPY else np.abs((arr - np.mean(arr)) / (np.std(arr) + 1e-10))
    mask = z_scores > threshold
    return {
        "outliers": [round(float(v), 4) for v in arr[mask]],
        "n_outliers": int(mask.sum()),
        "pct_outliers": round(float(mask.sum() / len(arr) * 100), 2),
        "max_zscore": round(float(z_scores.max()), 4),
        "method": "zscore",
        "threshold": threshold,
    }


# ── Descriptive Statistics ──────────────────────────────────────────────────

def comprehensive_stats(values: List[float]) -> Dict[str, Any]:
    """Full descriptive statistics beyond basic min/max/avg."""
    arr = np.array([float(v) for v in values if v is not None])
    if len(arr) == 0:
        return {}
    percentiles = np.percentile(arr, [5, 10, 25, 50, 75, 90, 95])
    return {
        "n": len(arr),
        "mean": round(float(np.mean(arr)), 4),
        "median": round(float(np.median(arr)), 4),
        "std_dev": round(float(np.std(arr, ddof=1)), 4) if len(arr) > 1 else 0,
        "variance": round(float(np.var(arr, ddof=1)), 4) if len(arr) > 1 else 0,
        "min": round(float(np.min(arr)), 4),
        "max": round(float(np.max(arr)), 4),
        "range": round(float(np.ptp(arr)), 4),
        "skewness": round(float(scipy_stats.skew(arr)), 4) if HAS_SCIPY else None,
        "kurtosis": round(float(scipy_stats.kurtosis(arr)), 4) if HAS_SCIPY else None,
        "iqr": round(float(percentiles[3] - percentiles[1]), 4),
        "percentiles": {
            "p5": round(float(percentiles[0]), 4),
            "p10": round(float(percentiles[1]), 4),
            "p25": round(float(percentiles[2]), 4),
            "p50": round(float(percentiles[3]), 4),
            "p75": round(float(percentiles[4]), 4),
            "p90": round(float(percentiles[5]), 4),
            "p95": round(float(percentiles[6]), 4),
        },
        "cv": round(float(np.std(arr, ddof=1) / np.mean(arr) * 100), 2) if np.mean(arr) != 0 else None,
        "coefficient_of_variation_pct": round(float(np.std(arr, ddof=1) / np.mean(arr) * 100), 2) if np.mean(arr) != 0 and len(arr) > 1 else None,
    }


# ── Time Series Decomposition ───────────────────────────────────────────────

def decompose_trend(values: List[float], period: int = 7) -> Dict[str, Any]:
    """Simple trend decomposition: trend + seasonal + residual."""
    arr = np.array(values, dtype=float)
    n = len(arr)
    if n < period * 2:
        return {"error": f"Need at least {period * 2} data points for decomposition"}

    # Centered moving average for trend
    half = period // 2
    trend = np.full(n, np.nan)
    for i in range(half, n - half):
        trend[i] = np.mean(arr[i - half: i + half + 1])

    # Detrend
    detrended = arr - trend

    # Seasonal component (average of each position in period)
    seasonal = np.zeros(period)
    for j in range(period):
        vals = [detrended[i] for i in range(j, n, period) if not np.isnan(detrended[i])]
        seasonal[j] = np.mean(vals) if vals else 0
    seasonal = seasonal - np.mean(seasonal)

    # Repeat seasonal pattern
    seasonal_full = np.tile(seasonal, n // period + 1)[:n]

    # Residual
    residual = arr - trend - seasonal_full

    return {
        "trend": [round(float(v), 4) if not np.isnan(v) else None for v in trend],
        "seasonal_pattern": [round(float(v), 4) for v in seasonal],
        "residual": [round(float(v), 4) if not np.isnan(v) else None for v in residual],
        "period": period,
        "has_trend": bool(np.nanstd(trend) > np.std(arr) * 0.1),
        "has_seasonality": bool(np.std(seasonal) > np.std(arr) * 0.1),
    }


# ── Comprehensive Analysis Runner ───────────────────────────────────────────

def run_full_analysis(df: pd.DataFrame, goal_text: str = "") -> Dict[str, Any]:
    """Run comprehensive statistical analysis on a DataFrame. Returns structured results."""
    results: Dict[str, Any] = {"descriptive": {}, "correlations": [], "outliers": [], "forecasts": [], "tests": []}

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    # 1. Descriptive stats for all numeric columns
    for col in numeric_cols:
        vals = df[col].dropna().tolist()
        if len(vals) >= 3:
            results["descriptive"][col] = comprehensive_stats(vals)

    # 2. Correlation matrix
    if len(numeric_cols) >= 2:
        try:
            corr_result = compute_correlation_matrix(df)
            results["correlations"] = corr_result.get("strong_pairs", [])
        except Exception as e:
            logger.warning(f"Correlation failed: {e}")

    # 3. Outlier detection per column
    for col in numeric_cols:
        vals = df[col].dropna().tolist()
        if len(vals) >= 4:
            outlier_info = detect_outliers_iqr(vals)
            if outlier_info.get("n_outliers", 0) > 0:
                outlier_info["column"] = col
                results["outliers"].append(outlier_info)

    # 4. Trend/forecast for time-ordered numeric columns
    for col in numeric_cols[:3]:
        vals = df[col].dropna().tolist()
        if len(vals) >= 5:
            forecast = forecast_linear_trend(vals, periods=min(6, max(2, len(vals) // 3)))
            if "error" not in forecast:
                forecast["column"] = col
                results["forecasts"].append(forecast)

    return results
