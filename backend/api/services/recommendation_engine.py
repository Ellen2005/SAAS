"""
Recommendation Engine
=====================
Generates prioritized business recommendations after every analysis.
Each recommendation includes priority, impact, risk, and actionable steps.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)
UTC = timezone.utc


class RecommendationEngine:
    """Generates prioritized business recommendations."""

    async def generate(
        self,
        analysis_results: dict,
        context: Optional[dict] = None,
    ) -> dict:
        """
        Generate recommendations from analysis results.
        
        Args:
            analysis_results: Dict with kpis, anomalies, trends, stats
            context: Department, period, user info
        
        Returns:
            {recommendations: [...], total_generated: N, context: {...}}
        """
        context = context or {}
        recommendations = []

        # Analyze KPIs
        for kpi in analysis_results.get("kpis", []):
            rec = self._analyze_kpi_for_recommendation(kpi)
            if rec:
                recommendations.append(rec)

        # Analyze anomalies
        for anomaly in analysis_results.get("anomalies", []):
            rec = self._analyze_anomaly_for_recommendation(anomaly)
            if rec:
                recommendations.append(rec)

        # Analyze trends
        for trend in analysis_results.get("trends", []):
            rec = self._analyze_trend_for_recommendation(trend)
            if rec:
                recommendations.append(rec)

        # Analyze governance scores
        governance = analysis_results.get("governance", {})
        if governance:
            rec = self._analyze_governance_for_recommendation(governance)
            if rec:
                recommendations.append(rec)

        # Sort by priority score (highest first)
        recommendations.sort(key=lambda x: x.get("priority_score", 0), reverse=True)

        return {
            "recommendations": recommendations[:10],
            "total_generated": len(recommendations),
            "context": {
                "department": context.get("department"),
                "period": context.get("period"),
                "generated_at": datetime.now(UTC).isoformat(),
            },
        }

    def _analyze_kpi_for_recommendation(self, kpi: dict) -> Optional[dict]:
        """Generate recommendation from a KPI."""
        try:
            delta = float(kpi.get("delta", 0) or 0)
        except (ValueError, TypeError):
            return None

        if abs(delta) < 5:
            return None

        label = kpi.get("label") or kpi.get("kpi_name", "KPI")
        if isinstance(label, str):
            label = label.replace("_", " ").title()

        if delta < -10:
            return {
                "priority": "HIGH",
                "priority_score": 0.9,
                "category": "performance",
                "title": f"Address decline in {label}",
                "reason": f"{label} declined by {abs(delta):.1f}%",
                "expected_impact": "Reverse negative trend",
                "estimated_risk": "Medium - continued decline possible",
                "business_value": "Prevents further deterioration",
                "suggested_actions": [
                    f"Investigate root cause of {label} decline",
                    "Review recent changes affecting this metric",
                    "Consider corrective actions",
                ],
            }
        elif delta > 15:
            return {
                "priority": "MEDIUM",
                "priority_score": 0.6,
                "category": "opportunity",
                "title": f"Leverage growth in {label}",
                "reason": f"{label} grew by {delta:.1f}%",
                "expected_impact": "Sustain positive momentum",
                "estimated_risk": "Low - growth is positive",
                "business_value": "Capitalizes on successful trends",
                "suggested_actions": [
                    "Document what drove the improvement",
                    "Consider scaling successful strategies",
                ],
            }
        return None

    def _analyze_anomaly_for_recommendation(self, anomaly: dict) -> Optional[dict]:
        """Generate recommendation from an anomaly."""
        severity = anomaly.get("severity", "low")
        if severity not in ("high", "critical", "medium", "warning"):
            return None

        anom_type = anomaly.get("type", "unknown")
        kpi_name = anomaly.get("kpi_name", "Unknown")
        if isinstance(kpi_name, str):
            kpi_name = kpi_name.replace("_", " ").title()

        if severity in ("high", "critical"):
            return {
                "priority": "CRITICAL",
                "priority_score": 0.95,
                "category": "risk",
                "title": f"Investigate critical anomaly: {kpi_name}",
                "reason": anomaly.get("context", {}).get("reason", f"Anomaly detected: {anom_type}"),
                "expected_impact": "Prevent potential losses",
                "estimated_risk": "High - unaddressed anomalies can escalate",
                "business_value": "Risk mitigation",
                "suggested_actions": [
                    "Immediate investigation required",
                    "Verify data accuracy",
                    "Implement corrective measures",
                ],
            }
        elif severity in ("medium", "warning"):
            return {
                "priority": "MEDIUM",
                "priority_score": 0.7,
                "category": "investigation",
                "title": f"Review anomaly: {kpi_name}",
                "reason": anomaly.get("context", {}).get("reason", "Anomaly detected"),
                "expected_impact": "Early detection prevents escalation",
                "estimated_risk": "Low-Medium",
                "business_value": "Proactive monitoring",
                "suggested_actions": [
                    "Review within 24 hours",
                    "Check for data entry errors",
                ],
            }
        return None

    def _analyze_trend_for_recommendation(self, trend: dict) -> Optional[dict]:
        """Generate recommendation from a trend."""
        direction = trend.get("direction", "stable")
        if direction == "stable":
            return None

        metric = trend.get("metric") or trend.get("kpi_name", "Unknown")
        if isinstance(metric, str):
            metric = metric.replace("_", " ").title()

        if direction == "declining":
            return {
                "priority": "MEDIUM",
                "priority_score": 0.7,
                "category": "trend",
                "title": f"Address declining trend: {metric}",
                "reason": trend.get("description", "Declining trend detected"),
                "expected_impact": "Reverse negative trajectory",
                "estimated_risk": "Medium - trends tend to persist",
                "business_value": "Early intervention prevents larger issues",
                "suggested_actions": trend.get("suggested_actions", [
                    "Analyze contributing factors",
                    "Review historical patterns",
                ]),
            }
        elif direction == "increasing":
            return {
                "priority": "LOW",
                "priority_score": 0.4,
                "category": "opportunity",
                "title": f"Capitalize on upward trend: {metric}",
                "reason": trend.get("description", "Upward trend detected"),
                "expected_impact": "Sustain positive momentum",
                "estimated_risk": "Low",
                "business_value": "Reinforce successful patterns",
                "suggested_actions": [
                    "Document contributing factors",
                    "Consider scaling related strategies",
                ],
            }
        return None

    def _analyze_governance_for_recommendation(self, governance: dict) -> Optional[dict]:
        """Generate recommendation from governance scores."""
        grade = governance.get("grade", "A")
        if grade in ("A", "B"):
            return None

        score = governance.get("score", 100)
        dimensions = governance.get("dimensions", {})
        weakest = min(dimensions.items(), key=lambda x: x[1]) if dimensions else None

        return {
            "priority": "HIGH" if grade in ("D", "F") else "MEDIUM",
            "priority_score": 0.8 if grade in ("D", "F") else 0.65,
            "category": "improvement",
            "title": f"Improve data governance (Grade: {grade})",
            "reason": f"Overall governance score: {score}/100",
            "expected_impact": "Improved data quality and AI accuracy",
            "estimated_risk": "Medium - poor governance affects all AI outputs",
            "business_value": "Better decision-making through better data",
            "suggested_actions": [
                f"Focus on weakest dimension: {weakest[0]} ({weakest[1]}%)" if weakest
                else "Review all governance dimensions",
                "Implement data quality improvement plan",
                "Schedule regular governance reviews",
            ],
        }
