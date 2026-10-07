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


# ═══════════════════════════════════════════════════════════════════════════════
# Legacy compatibility API — used by ai_analyst_service.py and routers/analyst.py
# These preserve the original result shape: {"method":..., "formula":..., "result":...}
# ═══════════════════════════════════════════════════════════════════════════════

import math as _math
from collections import Counter as _Counter


def compute_mean(values: list) -> dict:
    if not values:
        return {"method": "Mean", "formula": "mean = sum(x) / n", "result": 0, "interpretation": "No data available"}
    result = sum(values) / len(values)
    return {
        "method": "Mean (Moyenne)",
        "formula": "mean = sum(x) / n",
        "result": round(result, 4),
        "interpretation": f"La valeur moyenne est de {result:,.2f} sur {len(values)} observations.",
    }


def compute_median(values: list) -> dict:
    if not values:
        return {"method": "Median", "formula": "median = middle value", "result": 0, "interpretation": "No data"}
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    result = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2 if n % 2 == 0 else sorted_vals[n // 2]
    return {
        "method": "Median",
        "formula": "median = central value of sorted data",
        "result": round(result, 4),
        "interpretation": f"50% of values are below {result:,.2f} and 50% are above.",
    }


def compute_mode(values: list) -> dict:
    if not values:
        return {"method": "Mode", "formula": "mode = most frequent value", "result": None, "interpretation": "No data"}
    most_common = _Counter(values).most_common(1)
    if most_common:
        result, count = most_common[0]
        return {
            "method": "Mode",
            "formula": "mode = most frequent value",
            "result": round(result, 4) if isinstance(result, float) else result,
            "interpretation": f"The most frequent value is {result:,.2f} (appeared {count} times).",
        }
    return {"method": "Mode", "formula": "mode = most frequent value", "result": None, "interpretation": "No dominant value detected."}


def compute_variance(values: list, population: bool = True) -> dict:
    if len(values) < 2:
        return {"method": "Variance", "formula": "var = sum((x - mean)^2) / n", "result": 0, "interpretation": "Insufficient data"}
    n = len(values)
    mean = sum(values) / n
    result = sum((x - mean) ** 2 for x in values) / (n if population else n - 1)
    label = "population" if population else "sample"
    return {
        "method": f"Variance ({label})",
        "formula": "var = sum((x - mean)^2) / n" if population else "s^2 = sum((x - xbar)^2) / (n-1)",
        "result": round(result, 4),
        "interpretation": f"Variance measures data spread around the mean ({result:,.2f}). High variance indicates high dispersion.",
    }


def compute_std_dev(values: list, population: bool = True) -> dict:
    var_result = compute_variance(values, population)
    result = _math.sqrt(var_result["result"]) if var_result["result"] > 0 else 0
    return {
        "method": "Standard Deviation",
        "formula": "sd = sqrt(variance)",
        "result": round(result, 4),
        "interpretation": f"The standard deviation is {result:,.2f}. Approximately 68% of data falls within +/-{result:,.2f} of the mean.",
    }


def _percentile(data: list, p: float) -> float:
    k = (len(data) - 1) * p / 100
    f = _math.floor(k)
    c = _math.ceil(k)
    if f == c:
        return data[int(k)]
    return data[f] * (c - k) + data[c] * (k - f)


def compute_quartiles(values: list) -> dict:
    if len(values) < 4:
        return {"method": "Quartiles", "formula": "Q1, Q2, Q3, IQR", "result": {}, "interpretation": "Insufficient data"}
    sorted_vals = sorted(values)
    q1 = _percentile(sorted_vals, 25)
    q2 = _percentile(sorted_vals, 50)
    q3 = _percentile(sorted_vals, 75)
    iqr = q3 - q1
    return {
        "method": "Quartiles",
        "formula": "Q1 (25th), Q2 (50th), Q3 (75th), IQR = Q3 - Q1",
        "result": {"Q1": round(q1, 2), "Q2 (Median)": round(q2, 2), "Q3": round(q3, 2), "IQR": round(iqr, 2)},
        "interpretation": f"Q1={q1:,.2f}, Median={q2:,.2f}, Q3={q3:,.2f}. The interquartile range (IQR) is {iqr:,.2f}.",
    }


def compute_percentiles(values: list, percentiles: list = None) -> dict:
    if not values or not percentiles:
        percentiles = [10, 25, 50, 75, 90]
    sorted_vals = sorted(values)
    results = {}
    for p in percentiles:
        results[f"P{p}"] = round(_percentile(sorted_vals, p), 2)
    return {
        "method": "Percentiles",
        "formula": "Pk = value at rank k%",
        "result": results,
        "interpretation": f"Distribution from percentile 10 ({results.get('P10', 'N/A')}) to percentile 90 ({results.get('P90', 'N/A')}).",
    }


def compute_correlation(x_values: list, y_values: list) -> dict:
    if len(x_values) < 3 or len(y_values) < 3:
        return {"method": "Correlation", "formula": "r = covariance(x,y) / (sd_x * sd_y)", "result": 0, "interpretation": "Insufficient data"}
    n = min(len(x_values), len(y_values))
    x, y = x_values[:n], y_values[:n]
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    covariance = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y)) / n
    std_x = _math.sqrt(sum((xi - mean_x) ** 2 for xi in x) / n)
    std_y = _math.sqrt(sum((yi - mean_y) ** 2 for yi in y) / n)
    if std_x == 0 or std_y == 0:
        return {"method": "Correlation", "formula": "r = covariance(x,y) / (sd_x * sd_y)", "result": 0, "interpretation": "No variation detected"}
    r = covariance / (std_x * std_y)
    if abs(r) > 0.8:
        strength = "very strong"
    elif abs(r) > 0.6:
        strength = "strong"
    elif abs(r) > 0.4:
        strength = "moderate"
    elif abs(r) > 0.2:
        strength = "weak"
    else:
        strength = "very weak"
    direction = "positive" if r > 0 else "negative"
    return {
        "method": "Pearson Correlation",
        "formula": "r = sum((xi - xbar)(yi - ybar)) / sqrt(sum(xi - xbar)^2 * sum(yi - ybar)^2)",
        "result": round(r, 4),
        "interpretation": f"{strength.title()} {direction} correlation (r={r:.3f}). {'When X increases, Y increases.' if r > 0 else 'When X increases, Y decreases.'}",
    }


def compute_linear_regression(x_values: list, y_values: list) -> dict:
    if len(x_values) < 3:
        return {"method": "Linear Regression", "formula": "y = ax + b", "result": {}, "interpretation": "Insufficient data"}
    n = min(len(x_values), len(y_values))
    x, y = x_values[:n], y_values[:n]
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    denominator = sum((xi - mean_x) ** 2 for xi in x)
    a = numerator / denominator if denominator != 0 else 0
    b = mean_y - a * mean_x
    y_pred = [a * xi + b for xi in x]
    ss_res = sum((yi - ypi) ** 2 for yi, ypi in zip(y, y_pred))
    ss_tot = sum((yi - mean_y) ** 2 for yi in y)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
    return {
        "method": "Linear Regression",
        "formula": "y = ax + b, where a = slope, b = intercept",
        "result": {
            "slope (a)": round(a, 4),
            "intercept (b)": round(b, 2),
            "r_squared": round(r_squared, 4),
            "equation": f"y = {a:.4f}x + {b:.2f}",
        },
        "interpretation": f"Equation: y = {a:.4f}x + {b:.2f}. R^2 = {r_squared:.3f}. {'The model explains the variance well.' if r_squared > 0.7 else 'The model explains the variance moderately.'}",
    }


FORMULA_CATALOG = {
    "sum": "SUM = sum of all values",
    "count": "COUNT = number of observations",
    "average": "AVERAGE = sum(x) / n",
    "mean": "MEAN = sum(x) / n",
    "median": "MEDIAN = middle value of sorted data (50th percentile)",
    "mode": "MODE = most frequently occurring value",
    "std": "STANDARD DEVIATION = sqrt(sum((x - mean)^2) / (n - 1))",
    "std_dev": "STANDARD DEVIATION = sqrt(sum((x - mean)^2) / (n - 1))",
    "standard deviation": "STANDARD DEVIATION = sqrt(sum((x - mean)^2) / (n - 1))",
    "percentile": "PERCENTILE = value below which a given percentage of observations fall",
    "correlation": "CORRELATION = Covariance(X,Y) / (StdDev(X) * StdDev(Y))",
    "regression": "LINEAR REGRESSION = y = slope*x + intercept",
    "trend": "TREND = direction and rate of change over time (linear fit)",
    "forecast": "FORECAST = extrapolation of the fitted trend to future periods",
    "zscore": "Z-SCORE = (x - mean) / standard_deviation",
    "outlier": "OUTLIER = observation with z-score beyond threshold or outside Q1-1.5*IQR, Q3+1.5*IQR",
    "confidence interval": "CONFIDENCE INTERVAL = mean +/- 1.96 * (sd / sqrt(n))",
    "hypothesis test": "HYPOTHESIS TEST = compare observed statistic against null distribution (p-value)",
    "growth": "GROWTH = ((Current_Value - Previous_Value) / Previous_Value) * 100",
    "revenue": "REVENUE = Quantity * Price",
    "profit": "PROFIT = Revenue - Cost",
    "rate": "RATE = (Part / Total) * 100",
    "ratio": "RATIO = Value1 / Value2",
    "retention": "RETENTION = (End_Customers / Start_Customers) * 100",
    "variance": "VARIANCE = sum((x - mean)^2) / (n - 1)  [statistical]  |  Actual_Value - Budget  [budget variance]",
    "attainment": "ATTAINMENT = (Achieved / Target) * 100",
    "yoy": "Year-over-Year Growth = ((Year_N - Year_N-1) / Year_N-1) * 100",
    "dod": "Day-over-Day Change = ((Today - Yesterday) / Yesterday) * 100",
    "wow": "Week-over-Week Change = ((This_Week - Last_Week) / Last_Week) * 100",
    "mom": "Month-over-Month Change = ((This_Month - Last_Month) / Last_Month) * 100",
}


def get_formula(formula_key: str) -> str:
    key = str(formula_key).lower().strip()
    if key in FORMULA_CATALOG:
        return FORMULA_CATALOG[key]
    aliases = {"avg": "average", "sd": "std", "sigma": "std", "pct": "rate",
               "linear regression": "regression", "linreg": "regression"}
    if key in aliases:
        return FORMULA_CATALOG[aliases[key]]
    return f"Custom formula: {formula_key}"


def explain_formula(metric_name: str, operation: str, values: list = None) -> str:
    if operation == "sum":
        return f"{metric_name} = Sum of all values (cumulative total)"
    elif operation in ("average", "mean"):
        return f"{metric_name} = Sum of values / {len(values) if values else 'n'} (arithmetic mean)"
    elif operation == "median":
        return f"{metric_name} = Median of values (middle value of sorted data)"
    elif operation in ("std", "std_dev", "standard deviation"):
        return f"{metric_name} = Square root of variance (spread of data around the mean)"
    elif operation == "variance":
        return f"{metric_name} = Average of squared deviations from the mean"
    elif operation == "growth":
        return f"Growth of {metric_name} = ((Current Period - Previous Period) / Previous Period) * 100"
    elif operation == "percentage":
        return f"{metric_name} = (Part / Total) * 100"
    elif operation == "correlation":
        return "Correlation = Covariance(X,Y) / (StdDev(X) * StdDev(Y))"
    elif operation == "regression":
        return "Linear Regression: y = slope*x + intercept (best-fit line minimizing squared errors)"
    return get_formula(operation)


def _legacy_outliers_zscore(values: list, threshold: float = 2.5) -> dict:
    if len(values) < 3:
        return {"method": "Z-Score Outlier Detection", "formula": "|z| > threshold", "result": [], "interpretation": "Insufficient data"}
    n = len(values)
    mean = sum(values) / n
    std = _math.sqrt(sum((x - mean) ** 2 for x in values) / n)
    if std == 0:
        return {"method": "Z-Score Outlier Detection", "formula": "|z| > threshold", "result": [], "interpretation": "No variation in data"}
    outliers = []
    for i, val in enumerate(values):
        z = abs(val - mean) / std
        if z > threshold:
            outliers.append({"index": i, "value": round(val, 2), "z_score": round(z, 2)})
    return {
        "method": "Outlier Detection (Z-Score)",
        "formula": f"z = |x - mean| / sd, threshold = {threshold}",
        "result": {"outliers": outliers, "count": len(outliers), "threshold": threshold},
        "interpretation": f"{len(outliers)} outlier(s) detected out of {n} (z>{threshold}).",
    }


def _legacy_outliers_iqr(values: list) -> dict:
    if len(values) < 4:
        return {"method": "IQR Outlier Detection", "formula": "Q1 - 1.5*IQR, Q3 + 1.5*IQR", "result": [], "interpretation": "Insufficient data"}
    sorted_vals = sorted(values)
    q1 = _percentile(sorted_vals, 25)
    q3 = _percentile(sorted_vals, 75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    outliers = [{"value": round(v, 2)} for v in values if v < lower_bound or v > upper_bound]
    return {
        "method": "IQR Outlier Detection",
        "formula": "Lower bound = Q1 - 1.5*IQR, Upper bound = Q3 + 1.5*IQR",
        "result": {
            "outliers": outliers,
            "count": len(outliers),
            "lower_bound": round(lower_bound, 2),
            "upper_bound": round(upper_bound, 2),
            "q1": round(q1, 2),
            "q3": round(q3, 2),
            "iqr": round(iqr, 2),
        },
        "interpretation": f"{len(outliers)} outlier(s) outside [{lower_bound:,.2f}, {upper_bound:,.2f}].",
    }


def run_full_statistical_analysis(values: list, label: str = "Dataset") -> dict:
    """Run all statistical methods on a dataset and return comprehensive legacy-shaped results."""
    if not values:
        return {"error": "No data provided", "label": label}

    clean_vals = [v for v in values if v is not None and not (isinstance(v, float) and _math.isnan(v))]
    if not clean_vals:
        return {"error": "No valid numeric data", "label": label}

    n = len(clean_vals)
    desc_stats = {
        "count": n,
        "min": round(min(clean_vals), 2),
        "max": round(max(clean_vals), 2),
        "sum": round(sum(clean_vals), 2),
        "range": round(max(clean_vals) - min(clean_vals), 2),
    }

    results = {
        "label": label,
        "observations": n,
        "descriptive": {
            **desc_stats,
            "mean": compute_mean(clean_vals),
            "median": compute_median(clean_vals),
            "mode": compute_mode(clean_vals),
            "variance": compute_variance(clean_vals),
            "std_dev": compute_std_dev(clean_vals),
            "quartiles": compute_quartiles(clean_vals),
        },
        "outliers": {
            "zscore": _legacy_outliers_zscore(clean_vals),
            "iqr": _legacy_outliers_iqr(clean_vals),
        },
    }

    mean_val = desc_stats["sum"] / n
    std_val = _math.sqrt(sum((x - mean_val) ** 2 for x in clean_vals) / n)

    if n >= 3:
        margin = 1.96 * std_val / _math.sqrt(n)
        results["confidence_interval_95"] = {
            "method": "95% Confidence Interval",
            "formula": "CI = mean +/- 1.96 * (sd / sqrt(n))",
            "result": {
                "lower": round(mean_val - margin, 2),
                "upper": round(mean_val + margin, 2),
                "mean": round(mean_val, 2),
                "margin": round(margin, 2),
            },
            "interpretation": f"We are 95% confident that the true mean lies between {mean_val - margin:,.2f} and {mean_val + margin:,.2f}.",
        }

    return results
