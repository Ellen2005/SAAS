"""
Explainability Engine (XAI)
============================
Generates human-readable explanations for AI decisions.
Every recommendation or anomaly detection must come with an explanation.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ExplainabilityEngine:
    """Generates explanations for AI outputs."""

    async def explain_kpi(self, kpi_data: dict, context: Optional[dict] = None) -> dict:
        """Explain a KPI value and its drivers."""
        context = context or {}
        return {
            "feature_importance": self._compute_feature_importance(kpi_data),
            "reasoning": self._generate_reasoning(kpi_data),
            "business_explanation": self._business_explanation(kpi_data),
            "natural_language": self._nl_explanation(kpi_data),
            "source_lineage": self._trace_lineage(kpi_data, context),
            "decision_trace": self._build_decision_trace(kpi_data, context),
        }

    async def explain_anomaly(self, anomaly_data: dict, context: Optional[dict] = None) -> dict:
        """Explain why an anomaly was detected."""
        context = context or {}
        return {
            "anomaly_type": anomaly_data.get("type", "unknown"),
            "expected_range": anomaly_data.get("expected"),
            "actual_value": anomaly_data.get("actual"),
            "deviation": anomaly_data.get("deviation"),
            "possible_causes": self._identify_causes(anomaly_data, context),
            "confidence": anomaly_data.get("confidence", 0.5),
            "recommended_action": self._suggest_action(anomaly_data),
        }

    async def explain_forecast(self, forecast_data: dict, context: Optional[dict] = None) -> dict:
        """Explain a forecast result."""
        context = context or {}
        return {
            "trend_direction": forecast_data.get("trend", "stable"),
            "confidence_interval": forecast_data.get("confidence_interval"),
            "key_drivers": forecast_data.get("drivers", []),
            "risks": forecast_data.get("risks", []),
            "business_explanation": self._forecast_explanation(forecast_data),
        }

    def _compute_feature_importance(self, data: dict) -> list:
        """Compute which features contributed most to the value."""
        features = []
        if "delta" in data and data["delta"] is not None:
            features.append({
                "name": "Period-over-period change",
                "impact": abs(float(data["delta"])),
                "direction": "positive" if data["delta"] > 0 else "negative",
            })
        if "components" in data:
            for comp in data["components"]:
                features.append({
                    "name": comp.get("name", "Unknown"),
                    "impact": abs(comp.get("impact", 0)),
                    "direction": "positive" if comp.get("impact", 0) > 0 else "negative",
                })
        if "contributors" in data:
            for contrib in data["contributors"]:
                features.append({
                    "name": contrib.get("name", "Unknown"),
                    "impact": abs(contrib.get("value", 0)),
                    "direction": "positive" if contrib.get("value", 0) > 0 else "negative",
                })
        return sorted(features, key=lambda x: x["impact"], reverse=True)

    def _generate_reasoning(self, data: dict) -> list:
        """Generate reasoning chain."""
        steps = []
        if "source" in data:
            steps.append(f"Data sourced from {data['source']}")
        if "calculation" in data:
            steps.append(f"Calculated using {data['calculation']}")
        if "period" in data:
            steps.append(f"For period: {data['period']}")
        if "aggregation" in data:
            steps.append(f"Aggregation method: {data['aggregation']}")
        return steps

    def _business_explanation(self, data: dict) -> str:
        """Generate business-friendly explanation."""
        label = data.get("label") or data.get("kpi_name", "This metric")
        if isinstance(label, str):
            label = label.replace("_", " ").title()
        value = data.get("value", "N/A")
        delta = data.get("delta")
        try:
            delta = float(delta) if delta is not None else None
        except (ValueError, TypeError):
            delta = None

        if delta is not None and delta > 0:
            return f"{label} is {value}, which is an improvement of {abs(delta):.1f}%"
        elif delta is not None and delta < 0:
            return f"{label} is {value}, which is a decline of {abs(delta):.1f}%"
        return f"{label} is currently at {value}"

    def _nl_explanation(self, data: dict) -> str:
        """Generate natural language explanation."""
        return self._business_explanation(data)

    def _trace_lineage(self, data: dict, context: dict) -> dict:
        """Trace data lineage."""
        return {
            "source_table": context.get("source_table", data.get("source_table", "unknown")),
            "source_column": context.get("source_column", data.get("source_column", "unknown")),
            "transformations": context.get("transformations", []),
            "aggregation": context.get("aggregation", "none"),
            "filters_applied": context.get("filters", []),
        }

    def _build_decision_trace(self, data: dict, context: dict) -> dict:
        """Build complete decision trace."""
        return {
            "inputs": context.get("inputs", {}),
            "model": context.get("model", "unknown"),
            "parameters": context.get("parameters", {}),
            "intermediate_results": context.get("intermediates", []),
            "final_output": {k: v for k, v in data.items() if not k.startswith("_")},
        }

    def _identify_causes(self, anomaly: dict, context: dict) -> list:
        """Identify possible causes of an anomaly."""
        causes = []
        anom_type = anomaly.get("type", "")
        if anom_type == "spike" or anom_type == "high":
            causes.append("Unusual surge in activity")
            causes.append("Data entry error possible")
            causes.append("Seasonal pattern")
        elif anom_type == "drop" or anom_type == "low":
            causes.append("Activity reduction")
            causes.append("System outage possible")
            causes.append("Holiday or weekend effect")
        else:
            causes.append("Pattern deviation detected")
        return causes

    def _suggest_action(self, anomaly: dict) -> str:
        """Suggest action for an anomaly."""
        severity = anomaly.get("severity", "low")
        if severity == "high" or severity == "critical":
            return "Immediate investigation recommended"
        elif severity == "medium" or severity == "warning":
            return "Review within 24 hours"
        return "Monitor for recurrence"

    def _forecast_explanation(self, forecast: dict) -> str:
        """Generate business explanation for a forecast."""
        trend = forecast.get("trend", "stable")
        if trend == "increasing":
            return "Forecast shows an upward trend. Consider capacity planning."
        elif trend == "decreasing":
            return "Forecast shows a downward trend. Investigate root causes."
        return "Forecast shows stable performance."
