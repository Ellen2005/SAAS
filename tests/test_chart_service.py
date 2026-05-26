import unittest

from backend.api.services.chart_service import build_chart_from_rows, build_kpi_snapshot_chart


class ChartServiceTests(unittest.TestCase):
    def test_kpi_snapshot_chart(self):
        spec = build_kpi_snapshot_chart([
            {"kpi_name": "Payment · contributions", "value": 1200, "status": "NORMAL"},
            {"kpi_name": "Claim throughput", "value": 45, "status": "WARNING"},
        ])
        self.assertEqual(spec["type"], "bar")
        self.assertEqual(len(spec["data"]), 2)

    def test_nlq_bar_chart_from_rows(self):
        rows = [
            {"month": "2026-01", "total": 10},
            {"month": "2026-02", "total": 20},
        ]
        spec = build_chart_from_rows(rows, ["month", "total"], title="Test")
        self.assertIn(spec["type"], {"bar", "line"})
        self.assertGreaterEqual(len(spec["data"]), 2)


if __name__ == "__main__":
    unittest.main()
