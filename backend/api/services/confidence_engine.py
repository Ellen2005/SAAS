"""
Confidence Engine
=================
Calculates confidence scores for AI responses based on multiple signals.
Every AI answer must include a calculated confidence score — never hardcoded.
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ConfidenceEngine:
    """Calculates confidence scores for AI responses."""

    def __init__(self, db=None):
        self.db = db

    async def calculate(
        self,
        response: dict,
        context: dict,
        data_stats: Optional[dict] = None,
    ) -> dict:
        """
        Calculate comprehensive confidence score.
        
        Returns:
            {
                "score": 0.0-1.0,
                "grade": "A"-"F",
                "factors": {...},
                "evidence": [...],
                "data_freshness": ...,
                "affected_records": ...,
                "reasoning_summary": "..."
            }
        """
        factors = {}

        # Factor 1: Data Completeness (weight: 0.25)
        completeness = 0.7
        if data_stats:
            completeness = data_stats.get("completeness", 0.7)
        factors["data_completeness"] = {
            "score": completeness,
            "weight": 0.25,
            "evidence": f"{completeness * 100:.0f}% of fields populated",
        }

        # Factor 2: Data Freshness (weight: 0.15)
        freshness = 0.8
        days_old = 0
        if data_stats:
            freshness = data_stats.get("freshness", 0.8)
            days_old = data_stats.get("days_old", 0)
        factors["data_freshness"] = {
            "score": freshness,
            "weight": 0.15,
            "evidence": f"Last updated {days_old} days ago" if days_old else "Recently updated",
        }

        # Factor 3: Source Record Count (weight: 0.15)
        record_count = context.get("record_count", 0)
        if record_count > 10000:
            sample_score = 0.98
        elif record_count > 1000:
            sample_score = 0.95
        elif record_count > 100:
            sample_score = 0.8
        elif record_count > 10:
            sample_score = 0.6
        else:
            sample_score = 0.4
        factors["sample_size"] = {
            "score": sample_score,
            "weight": 0.15,
            "evidence": f"Based on {record_count:,} records" if record_count else "No record count available",
        }

        # Factor 4: Response Specificity (weight: 0.20)
        content = ""
        if isinstance(response, dict):
            content = response.get("content", "")
            if not content:
                resp_choices = response.get("raw_response", {}).get("choices", [])
                if resp_choices:
                    content = resp_choices[0].get("message", {}).get("content", "")
        specificity = self._measure_specificity(content)
        factors["response_specificity"] = {
            "score": specificity,
            "weight": 0.20,
            "evidence": "Response contains specific data points" if specificity > 0.7
            else "Response is more general",
        }

        # Factor 5: Model Confidence (weight: 0.15)
        model = context.get("model", "")
        if "70b" in model:
            model_conf = 0.95
        elif "8b" in model or "mixtral" in model:
            model_conf = 0.85
        else:
            model_conf = 0.7
        factors["model_confidence"] = {
            "score": model_conf,
            "weight": 0.15,
            "evidence": f"Model: {model}" if model else "Model unknown",
        }

        # Factor 6: Semantic Consistency (weight: 0.10)
        semantic_score = self._check_semantic_consistency(content, context)
        factors["semantic_consistency"] = {
            "score": semantic_score,
            "weight": 0.10,
            "evidence": "Response aligns with business terminology" if semantic_score > 0.7
            else "Limited business terminology alignment",
        }

        # Weighted average
        total_score = sum(f["score"] * f["weight"] for f in factors.values())
        total_score = min(max(total_score, 0.0), 1.0)

        return {
            "score": round(total_score, 3),
            "grade": self._score_to_grade(total_score),
            "factors": factors,
            "evidence": self._compile_evidence(factors),
            "data_freshness": data_stats.get("last_updated") if data_stats else None,
            "affected_records": record_count,
            "reasoning_summary": self._generate_reasoning(factors, total_score),
        }

    def _measure_specificity(self, text: str) -> float:
        """Measure how specific/data-driven a response is."""
        if not text:
            return 0.5
        numbers = len(re.findall(r"\d+\.?\d*%?", text))
        has_comparison = any(
            w in text.lower()
            for w in ["increase", "decrease", "higher", "lower", "vs", "compared"]
        )
        has_date = bool(re.search(r"\d{4}-\d{2}-\d{2}", text))
        has_percentage = "%" in text
        score = 0.5
        score += min(numbers * 0.03, 0.2)
        score += 0.15 if has_comparison else 0
        score += 0.1 if has_date else 0
        score += 0.1 if has_percentage else 0
        return min(score, 1.0)

    def _check_semantic_consistency(self, content: str, context: dict) -> float:
        """Check if response uses consistent business terminology."""
        business_terms = context.get("business_terms", [])
        if not business_terms or not content:
            return 0.8
        found = sum(1 for t in business_terms if t.lower() in content.lower())
        return min(0.5 + (found / len(business_terms)) * 0.5, 1.0)

    def _score_to_grade(self, score: float) -> str:
        if score >= 0.9:
            return "A"
        if score >= 0.8:
            return "B"
        if score >= 0.7:
            return "C"
        if score >= 0.6:
            return "D"
        return "F"

    def _compile_evidence(self, factors: dict) -> list:
        return [f"{k}: {v['evidence']}" for k, v in factors.items()]

    def _generate_reasoning(self, factors: dict, total: float) -> str:
        if total >= 0.85:
            return "High confidence: strong data foundation and specific response"
        if total >= 0.7:
            return "Moderate confidence: adequate data support with specific findings"
        if total >= 0.5:
            return "Lower confidence: limited data or general response"
        return "Low confidence: significant gaps in data or reasoning"
