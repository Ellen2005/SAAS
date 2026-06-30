"""Quick test of dialect sanitization and imports."""
import sys
sys.path.insert(0, "backend")

from api.services.nlq_service import _sanitize_sql_for_dialect, _oracle_to_sqlite_strftime

# Test TO_CHAR helper
print("=== TO_CHAR Helper ===")
print(_oracle_to_sqlite_strftime("hire_date", "YYYY-MM"))
print(_oracle_to_sqlite_strftime("created_at", "YYYY-MM-DD"))

# Test Oracle sanitization
print("\n=== Oracle Sanitization ===")
oracle_sql = "SELECT TRUNC(hire_date, 'MM') FROM employees WHERE hire_date >= DATE_TRUNC('month', SYSDATE) FETCH FIRST 10 ROWS ONLY;"
result = _sanitize_sql_for_dialect(oracle_sql, "oracle")
print(f"Input:  {oracle_sql}")
print(f"Output: {result}")

# Test SQLite sanitization
print("\n=== SQLite Sanitization ===")
sqlite_sql = "SELECT TO_CHAR(hire_date, 'YYYY-MM') FROM employees WHERE hire_date >= SYSDATE LIMIT 10"
result = _sanitize_sql_for_dialect(sqlite_sql, "sqlite")
print(f"Input:  {sqlite_sql}")
print(f"Output: {result}")

# Test analysis_engine import
print("\n=== Analysis Engine Import ===")
from api.services.analysis_engine import _plan_analysis_goal
print("OK: analysis_engine imports work")

print("\n=== All tests passed ===")
