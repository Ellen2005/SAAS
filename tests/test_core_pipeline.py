import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta

import pandas as pd

from backend.api.routers.introspect import _summarize_for_kpi
from backend.api.services.ai_analyst_service import (
    auto_model,
    auto_prepare,
    compute_governance_score,
    generate_augmented_insights,
)
from backend.api.services.etl_service import (
    build_validation_frame,
    detect_anomalies_and_transform,
    finalize_extracted_frame,
)
from backend.api.services.schema_introspector import (
    introspect_sql,
    run_analysis,
    suggest_analyses,
)
from backend.api.services.nlq_service import run_nlq
from backend.api.services.validation_service import run_all_validations


class CorePipelineTests(unittest.TestCase):
    def test_null_and_bad_data_handling_survives_complete_local_pipeline(self):
        today = datetime.utcnow().date()
        rows = []
        for i in range(14):
            rows.append({
                "date": today - timedelta(days=13 - i),
                "kpi_name": "database_metric",
                "value": 100 + i,
                "customer_id": "ACME",
            })
        rows.extend([
            {"date": "not-a-date", "kpi_name": "database_metric", "value": 999},
            {"date": today, "kpi_name": "database_metric", "value": None},
            {"date": today, "kpi_name": None, "value": 50},
        ])

        raw = finalize_extracted_frame(pd.DataFrame(rows))
        self.assertEqual(len(raw), 14)
        self.assertFalse(raw[["date", "kpi_name", "value"]].isnull().any().any())

        validation_frame = build_validation_frame(raw)
        validations = run_all_validations(
            validation_frame,
            [{"global_field_name": "database_metric", "required": True}],
            historical_df=validation_frame.iloc[:-1],
        )
        self.assertEqual({r.check_type for r in validations}, {"schema", "null", "anomaly"})
        self.assertTrue(all(r.status in {"pass", "warning", "fail"} for r in validations))

        kpis, anomalies = detect_anomalies_and_transform(raw)
        self.assertEqual(len(kpis), 1)
        self.assertEqual(kpis[0]["kpi_name"], "database_metric")
        self.assertIsInstance(anomalies, list)

        prepared, prep_actions = auto_prepare(raw[["date", "kpi_name", "value", "customer_id"]])
        self.assertEqual(len(prepared), len(raw))
        self.assertIsInstance(prep_actions, list)

        model = auto_model(prepared)
        self.assertIn("column_roles", model)
        insights = generate_augmented_insights(prepared, kpis, anomalies)
        self.assertIsInstance(insights, list)

        governance = compute_governance_score(prepared, validations, 0, True)
        self.assertGreaterEqual(governance["overall"], 0)
        self.assertLessEqual(governance["overall"], 100)

    def test_sqlite_introspection_analysis_and_kpi_summary(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            conn = sqlite3.connect(path)
            conn.execute(
                "CREATE TABLE contributions (id INTEGER PRIMARY KEY, paid_at TEXT, amount REAL, region TEXT)"
            )
            base = datetime(2026, 1, 1)
            conn.executemany(
                "INSERT INTO contributions (paid_at, amount, region) VALUES (?, ?, ?)",
                [
                    ((base + timedelta(days=i)).date().isoformat(), 100.0 + i, "Centre")
                    for i in range(35)
                ],
            )
            conn.commit()
            conn.close()

            conn_info = {"credentials": f"sqlite:///{path}", "db_type": "sqlite"}
            schema = introspect_sql(conn_info, sample_rows=2, max_tables=10)
            self.assertEqual(schema["kind"], "sql")
            self.assertEqual(schema["table_count"], 1)
            self.assertEqual(schema["tables"][0]["name"], "contributions")

            analyses = suggest_analyses(schema)
            self.assertTrue(any(a["kind"] == "time_series_sum" for a in analyses))
            result = run_analysis(conn_info, next(a for a in analyses if a["kind"] == "time_series_sum"))
            self.assertNotIn("error", result)
            self.assertGreater(len(result["rows"]), 0)

            summary = _summarize_for_kpi(result)
            self.assertIsNotNone(summary)
            value, status = summary
            self.assertGreater(value, 0)
            self.assertEqual(status, "NORMAL")
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    def test_nlq_fallback_chat_queries_connected_database_without_mock_data(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        class Response:
            data = [{"credentials": f"sqlite:///{path}", "db_type": "sqlite", "connection_method": "direct"}]

        class Query:
            def select(self, *args, **kwargs): return self
            def eq(self, *args, **kwargs): return self
            def limit(self, *args, **kwargs): return self
            def execute(self): return Response()

        class Supabase:
            def table(self, name): return Query()

        try:
            conn = sqlite3.connect(path)
            conn.execute("CREATE TABLE rna_sequences (id INTEGER PRIMARY KEY, accession TEXT, sequence TEXT)")
            conn.executemany(
                "INSERT INTO rna_sequences (accession, sequence) VALUES (?, ?)",
                [("RNA001", "AUGC"), ("RNA002", "GGCA")],
            )
            conn.commit()
            conn.close()

            result = run_nlq("user-1", "list all tables", Supabase())
            self.assertIsNone(result.get("error"))
            self.assertIn("sql", result)
            self.assertGreaterEqual(result["row_count"], 1)
            self.assertTrue(any(row.get("table_name") == "rna_sequences" for row in result["rows"]))
            self.assertNotIn("Total Revenue", str(result))
            self.assertNotIn("Support Tickets", str(result))
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    def test_database_overview_pipeline_without_kpi_mappings(self):
        import sqlite3
        from backend.api.services.etl_service import _run_database_overview_pipeline

        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        class MockTable:
            def __init__(self, name, sink):
                self.name = name
                self.sink = sink

            def insert(self, payload):
                self.sink.append((self.name, payload))
                return self

            def execute(self):
                return self

        class MockSupabase:
            def __init__(self):
                self.records = []

            def table(self, name):
                return MockTable(name, self.records)

        try:
            conn = sqlite3.connect(path)
            conn.execute(
                "CREATE TABLE rna_sequences (id INTEGER PRIMARY KEY, accession TEXT, sequence TEXT)"
            )
            conn.execute(
                "INSERT INTO rna_sequences (accession, sequence) VALUES (?, ?)"
                , ("RNA001", "AUGC")
            )
            conn.commit()
            conn.close()

            supabase = MockSupabase()
            conn_info = {"credentials": f"sqlite:///{path}", "db_type": "sqlite"}
            result = _run_database_overview_pipeline("user-42", supabase, conn_info, department_id="dept-1")
            self.assertEqual(result.get("status"), "success")
            self.assertGreaterEqual(result.get("kpis"), 1)
            self.assertTrue(any(name == "kpi_results" for name, _ in supabase.records))
            self.assertTrue(any(name == "daily_reports" for name, _ in supabase.records))
            self.assertTrue(any("rna_sequences" in str(payload) for _, payload in supabase.records))
        finally:
            try:
                os.remove(path)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
