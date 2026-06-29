"""Test that analysis engine now uses proper chart type detection."""
import sys, os
sys.path.insert(0, os.getcwd())
os.environ["TESTING"] = "True"

from backend.api.services.analysis_engine import _build_chart
from sqlalchemy import create_engine, text

DB_URL = "sqlite:///cnps_realistic_demo.db"
engine = create_engine(DB_URL)

with engine.connect() as conn:
    # Time series -> should be line
    rows = [dict(r._mapping) for r in conn.execute(text("""
        SELECT strftime('%Y-%m', contribution_date) AS month,
               SUM(contribution_amount) AS total
        FROM contributions GROUP BY month ORDER BY month LIMIT 12
    """))]
    chart = _build_chart(rows, {"summary_hint": "Monthly Trend"})
    print(f"Time series -> {chart['type']} (expected: line or area) [{'PASS' if chart['type'] in ('line', 'area') else 'FAIL'}]")

    # Categorical (<=12) -> should be bar
    rows = [dict(r._mapping) for r in conn.execute(text("""
        SELECT r.name, SUM(c.contribution_amount) AS total
        FROM contributions c JOIN regional_offices r ON c.regional_code = r.code
        GROUP BY r.name ORDER BY total DESC
    """))]
    chart = _build_chart(rows, {"summary_hint": "By Region"})
    print(f"Categorical (10) -> {chart['type']} (expected: bar or hbar) [{'PASS' if chart['type'] in ('bar', 'horizontalBar') else 'FAIL'}]")

    # Distribution (<=5) -> should be pie
    rows = [dict(r._mapping) for r in conn.execute(text("""
        SELECT payment_status, COUNT(*) AS cnt
        FROM contributions GROUP BY payment_status
    """))]
    chart = _build_chart(rows, {"summary_hint": "Payment Status"})
    print(f"Distribution (4) -> {chart['type']} (expected: pie) [{'PASS' if chart['type'] == 'pie' else 'FAIL'}]")

    # Single row -> gauge
    rows = [dict(r._mapping) for r in conn.execute(text("SELECT SUM(contribution_amount) AS total FROM contributions"))]
    chart = _build_chart(rows, {"summary_hint": "Total"})
    print(f"Single KPI -> {chart['type']} (expected: gauge) [{'PASS' if chart['type'] == 'gauge' else 'FAIL'}]")

print("\nAll chart detection tests complete!")
