"""
Statistical Engine for AI Data Analyst
========================================
Provides a comprehensive statistical toolkit for the AI Analyst.

Capabilities:
  - Descriptive Statistics (mean, median, mode, variance, std)
  - Diagnostic Analysis (correlation, regression, root cause)
  - Predictive Analysis (trend projection, forecasting)
  - Prescriptive Analysis (recommendations, risk detection)
  - Formula Generation (human-readable formulas for all calculations)

All methods return standardized results with:
  - method: name of statistical method used
  - formula: human-readable formula
  - result: computed value(s)
  - interpretation: plain-language meaning
"""

import math
import statistics
from collections import Counter
from typing import Optional


# ─── Descriptive Statistics ─────────────────────────────────────────────────

def compute_mean(values: list) -> dict:
    """Compute arithmetic mean."""
    if not values:
        return {"method": "Mean", "formula": "μ = Σx / n", "result": 0, "interpretation": "No data available"}
    n = len(values)
    result = sum(values) / n
    return {
        "method": "Mean (Moyenne)",
        "formula": "μ = Σx / n",
        "result": round(result, 4),
        "interpretation": f"La valeur moyenne est de {result:,.2f} sur {n} observations.",
    }


def compute_median(values: list) -> dict:
    """Compute median (50th percentile)."""
    if not values:
        return {"method": "Median", "formula": "Median = middle value", "result": 0, "interpretation": "No data"}
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n % 2 == 0:
        result = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
    else:
        result = sorted_vals[n // 2]
    return {
        "method": "Median",
        "formula": "Median = central value of sorted data",
        "result": round(result, 4),
        "interpretation": f"50% of values are below {result:,.2f} and 50% are above.",
    }


def compute_mode(values: list) -> dict:
    """Compute mode (most frequent value)."""
    if not values:
        return {"method": "Mode", "formula": "Mode = most frequent value", "result": None, "interpretation": "No data"}
    counter = Counter(values)
    most_common = counter.most_common(1)
    if most_common:
        result, count = most_common[0]
        return {
            "method": "Mode",
            "formula": "Mode = most frequent value",
            "result": round(result, 4) if isinstance(result, float) else result,
            "interpretation": f"The most frequent value is {result:,.2f} (appeared {count} times).",
        }
    return {"method": "Mode", "formula": "Mode = most frequent value", "result": None, "interpretation": "No dominant value detected."}


def compute_variance(values: list, population: bool = True) -> dict:
    """Compute variance."""
    if len(values) < 2:
        return {"method": "Variance", "formula": "σ² = Σ(x - μ)² / n", "result": 0, "interpretation": "Insufficient data"}
    n = len(values)
    mean = sum(values) / n
    result = sum((x - mean) ** 2 for x in values) / (n if population else n - 1)
    label = "population" if population else "sample"
    return {
        "method": f"Variance ({label})",
        "formula": "σ² = Σ(x - μ)² / n" if population else "s² = Σ(x - x̄)² / (n-1)",
        "result": round(result, 4),
        "interpretation": f"Variance measures data spread around the mean ({result:,.2f}). High variance indicates high dispersion.",
    }


def compute_std_dev(values: list, population: bool = True) -> dict:
    """Compute standard deviation."""
    var_result = compute_variance(values, population)
    result = math.sqrt(var_result["result"]) if var_result["result"] > 0 else 0
    return {
        "method": "Standard Deviation",
        "formula": "σ = √σ²" if population else "s = √s²",
        "result": round(result, 4),
        "interpretation": f"The standard deviation is {result:,.2f}. Approximately 68% of data falls within ±{result:,.2f} of the mean.",
    }


def compute_quartiles(values: list) -> dict:
    """Compute Q1, Q2 (median), Q3, IQR."""
    if len(values) < 4:
        return {"method": "Quartiles", "formula": "Q1, Q2, Q3, IQR", "result": {}, "interpretation": "Insufficient data"}
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    
    def percentile(data, p):
        k = (len(data) - 1) * p / 100
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return data[int(k)]
        return data[f] * (c - k) + data[c] * (k - f)
    
    q1 = percentile(sorted_vals, 25)
    q2 = percentile(sorted_vals, 50)
    q3 = percentile(sorted_vals, 75)
    iqr = q3 - q1
    
    return {
        "method": "Quartiles",
        "formula": "Q1 (25th), Q2 (50th), Q3 (75th), IQR = Q3 - Q1",
        "result": {"Q1": round(q1, 2), "Q2 (Median)": round(q2, 2), "Q3": round(q3, 2), "IQR": round(iqr, 2)},
        "interpretation": f"Q1={q1:,.2f}, Median={q2:,.2f}, Q3={q3:,.2f}. The interquartile range (IQR) is {iqr:,.2f}.",
    }


def compute_percentiles(values: list, percentiles: list = None) -> dict:
    """Compute specified percentiles."""
    if not values or not percentiles:
        percentiles = [10, 25, 50, 75, 90]
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    
    results = {}
    for p in percentiles:
        k = (n - 1) * p / 100
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            results[f"P{p}"] = round(sorted_vals[int(k)], 2)
        else:
            results[f"P{p}"] = round(sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f), 2)
    
    return {
        "method": "Percentiles (Percentiles)",
        "formula": "Pk = valeur au rang k%",
        "result": results,
        "interpretation": f"Distribution des valeurs du percentile 10 ({results.get('P10', 'N/A')}) au percentile 90 ({results.get('P90', 'N/A')}).",
    }


# ─── Diagnostic Statistics ─────────────────────────────────────────────────

def compute_correlation(x_values: list, y_values: list) -> dict:
    """Compute Pearson correlation coefficient between two series."""
    if len(x_values) < 3 or len(y_values) < 3:
        return {"method": "Correlation", "formula": "r = covariance(x,y) / (σx × σy)", "result": 0, "interpretation": "Insufficient data"}
    
    n = min(len(x_values), len(y_values))
    x, y = x_values[:n], y_values[:n]
    
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    
    covariance = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y)) / n
    std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x) / n)
    std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y) / n)
    
    if std_x == 0 or std_y == 0:
        return {"method": "Correlation", "formula": "r = covariance(x,y) / (σx × σy)", "result": 0, "interpretation": "No variation detected"}
    
    r = covariance / (std_x * std_y)
    
    # Interpretation
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
        "formula": "r = Σ((xi - x̄)(yi - ȳ)) / √(Σ(xi - x̄)² × Σ(yi - ȳ)²)",
        "result": round(r, 4),
        "interpretation": f"{strength.title()} {direction} correlation (r={r:.3f}). {'When X increases, Y increases.' if r > 0 else 'When X increases, Y decreases.'}",
    }


def compute_linear_regression(x_values: list, y_values: list) -> dict:
    """Compute linear regression: y = ax + b."""
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
    
    # R-squared
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
        "interpretation": f"Equation: y = {a:.4f}x + {b:.2f}. R² = {r_squared:.3f}. {'The model explains the variance well.' if r_squared > 0.7 else 'The model explains the variance moderately.'}",
    }


# ─── Outlier Detection ─────────────────────────────────────────────────────

def detect_outliers_zscore(values: list, threshold: float = 2.5) -> dict:
    """Detect outliers using Z-score method."""
    if len(values) < 3:
        return {"method": "Z-Score Outlier Detection", "formula": "|z| > threshold", "result": [], "interpretation": "Insufficient data"}
    
    n = len(values)
    mean = sum(values) / n
    std = math.sqrt(sum((x - mean) ** 2 for x in values) / n)
    
    if std == 0:
        return {"method": "Z-Score Outlier Detection", "formula": "|z| > threshold", "result": [], "interpretation": "No variation in data"}
    
    outliers = []
    for i, val in enumerate(values):
        z = abs(val - mean) / std
        if z > threshold:
            outliers.append({"index": i, "value": round(val, 2), "z_score": round(z, 2)})
    
    return {
        "method": "Outlier Detection (Z-Score)",
        "formula": "z = |x - μ| / σ, threshold = {threshold}".format(threshold=threshold),
        "result": {"outliers": outliers, "count": len(outliers), "threshold": threshold},
        "interpretation": f"{len(outliers)} outlier(s) detected out of {n} (z>{threshold}).",
    }


def detect_outliers_iqr(values: list) -> dict:
    """Detect outliers using IQR method."""
    if len(values) < 4:
        return {"method": "IQR Outlier Detection", "formula": "Q1 - 1.5×IQR, Q3 + 1.5×IQR", "result": [], "interpretation": "Insufficient data"}
    
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    
    def percentile(data, p):
        k = (len(data) - 1) * p / 100
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return data[int(k)]
        return data[f] * (c - k) + data[c] * (k - f)
    
    q1 = percentile(sorted_vals, 25)
    q3 = percentile(sorted_vals, 75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    
    outliers = [{"value": round(v, 2)} for v in values if v < lower_bound or v > upper_bound]
    
    return {
        "method": "IQR Outlier Detection",
        "formula": "Lower bound = Q1 - 1.5×IQR, Upper bound = Q3 + 1.5×IQR",
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


# ─── Formula Generator ─────────────────────────────────────────────────────

FORMULA_CATALOG = {
    "sum": "SUM = Σx",
    "count": "COUNT = number of observations",
    "average": "AVERAGE = Σx / n",
    "growth": "GROWTH = ((Current_Value - Previous_Value) / Previous_Value) × 100",
    "revenue": "REVENUE = Quantity × Price",
    "profit": "PROFIT = Revenue - Cost",
    "rate": "RATE = (Part / Total) × 100",
    "ratio": "RATIO = Value1 / Value2",
    "retention": "RETENTION = (End_Customers / Start_Customers) × 100",
    "variance": "VARIANCE = Actual_Value - Budget",
    "attainment": "ATTAINMENT = (Achieved / Target) × 100",
    "yoy": "Year-over-Year Growth = ((Year_N - Year_N-1) / Year_N-1) × 100",
    "dod": "Day-over-Day Change = ((Today - Yesterday) / Yesterday) × 100",
    "wow": "Week-over-Week Change = ((This_Week - Last_Week) / Last_Week) × 100",
    "mom": "Month-over-Month Change = ((This_Month - Last_Month) / Last_Month) × 100",
}


def get_formula(formula_key: str) -> str:
    """Get a human-readable formula by key."""
    return FORMULA_CATALOG.get(formula_key.lower(), f"Custom formula: {formula_key}")


def explain_formula(metric_name: str, operation: str, values: list = None) -> str:
    """Generate a human-readable formula explanation."""
    if operation == "sum":
        return f"{metric_name} = Sum of all values (cumulative total)"
    elif operation == "average":
        return f"{metric_name} = Sum of values / {len(values) if values else 'n'} (arithmetic mean)"
    elif operation == "growth":
        return f"Growth of {metric_name} = ((Current Period - Previous Period) / Previous Period) × 100"
    elif operation == "percentage":
        return f"{metric_name} = (Part / Total) × 100"
    elif operation == "correlation":
        return f"Correlation = Covariance(X,Y) / (StdDev(X) × StdDev(Y))"
    return get_formula(operation)


# ─── Complete Statistical Analysis ─────────────────────────────────────────

def run_full_statistical_analysis(values: list, label: str = "Dataset") -> dict:
    """Run all statistical methods on a dataset and return comprehensive results."""
    if not values:
        return {"error": "No data provided", "label": label}
    
    clean_vals = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    
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
            "zscore": detect_outliers_zscore(clean_vals),
            "iqr": detect_outliers_iqr(clean_vals),
        },
    }
    
    # Generate summary
    mean_val = desc_stats["sum"] / n if n > 0 else 0
    std_val = math.sqrt(sum((x - mean_val) ** 2 for x in clean_vals) / n) if n > 0 else 0
    
    if n >= 3:
        results["confidence_interval_95"] = {
            "method": "95% Confidence Interval",
            "formula": "IC = μ ± 1.96 × (σ / √n)",
            "result": {
                "lower": round(mean_val - 1.96 * std_val / math.sqrt(n), 2),
                "upper": round(mean_val + 1.96 * std_val / math.sqrt(n), 2),
                "mean": round(mean_val, 2),
                "margin": round(1.96 * std_val / math.sqrt(n), 2),
            },
            "interpretation": f"We are 95% confident that the true mean lies between {mean_val - 1.96 * std_val / math.sqrt(n):,.2f} and {mean_val + 1.96 * std_val / math.sqrt(n):,.2f}.",
        }
    
    return results