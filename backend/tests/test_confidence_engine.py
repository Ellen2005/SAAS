import pytest
import asyncio
from api.services.confidence_engine import ConfidenceEngine


class TestConfidenceEngine:
    def setup_method(self):
        self.engine = ConfidenceEngine()

    def test_confidence_grade_mapping(self):
        test_cases = [
            (0.95, "A"),
            (0.85, "B"),
            (0.75, "C"),
            (0.65, "D"),
            (0.5, "F"),
        ]
        for score_val, expected_grade in test_cases:
            grade = self.engine._score_to_grade(score_val)
            assert grade == expected_grade

    def test_confidence_calculation(self):
        result = asyncio.run(self.engine.calculate(
            response={"content": "Revenue increased 15% to $2.3M in Q1 2024"},
            context={"record_count": 5000, "model": "llama-3.3-70b-versatile"},
            data_stats={"completeness": 0.9, "freshness": 0.85, "days_old": 1},
        ))
        assert 0.0 <= result["score"] <= 1.0
        assert "grade" in result
        assert "factors" in result

    def test_confidence_factors(self):
        result = asyncio.run(self.engine.calculate(
            response={"content": "Test analysis with 42 data points"},
            context={"record_count": 100},
            data_stats={"completeness": 0.8},
        ))
        expected_factors = [
            "data_completeness", "data_freshness", "sample_size",
            "response_specificity", "model_confidence", "semantic_consistency",
        ]
        for factor in expected_factors:
            assert factor in result["factors"]
