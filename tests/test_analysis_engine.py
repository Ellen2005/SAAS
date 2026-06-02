"""Tests for CNPS goal-driven analysis engine."""
import unittest

from backend.api.services.analysis_engine import validate_formula, _rule_based_sql, _build_chart


class TestAnalysisEngine(unittest.TestCase):


    def test_validate_formula_accepts_simple_ratio(self):
        result = validate_formula("total_paid / total_expected")
        self.assertTrue(result["valid"])

    def test_validate_formula_rejects_semicolon(self):
        result = validate_formula("1; DROP TABLE contributions")
        self.assertFalse(result["valid"])

    def test_rule_based_sql_contributions(self):
        sql = _rule_based_sql("regional contribution share by region", "sqlite")
        self.assertIsNotNone(sql)
        self.assertIn("regional_code", sql.lower())

    def test_build_chart_empty(self):
        chart = _build_chart([], {"chart_type": "bar"})
        self.assertEqual(chart["type"], "table")

    def test_build_chart_with_rows(self):
        rows = [{"region": "DOU", "total": 1000}, {"region": "YAO", "total": 800}]
        chart = _build_chart(rows, {"chart_type": "bar", "x_column": "region", "y_column": "total"})
        self.assertEqual(len(chart["data"]), 2)


if __name__ == "__main__":
    unittest.main()
