#!/usr/bin/env python3
"""Test Oracle SQL queries from ORACLE_DEMO_SQL_TESTS.md via API"""
import urllib.request
import json

# Login token for user@cnps.com
TOKEN = 'eyJhbGciOiJFUzI1NiIsImtpZCI6IjZkY2QxMzY2LTg3MGUtNDk0Mi1hYzBlLTZiMTQ0ZDdjMzU1NSIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL2p0Ynl4YmRraG1ieml2enVhZWt6LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI5ODYyMjIyYi03YjM1LTQ5NzAtOTZiZC02NTViNzg5YTk1ODUiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzgyNzM3MDUzLCJpYXQiOjE3ODI3MzM0NTMsImVtYWlsIjoidXNlckBjbnBzLmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWxfdmVyaWZpZWQiOnRydWV9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzgyNzIxNjc2fV0sInNlc3Npb25faWQiOiIxNjFjODUxYi1lYTdkLTQwYjMtYjg1Mi1jMjY5Mzg0MmNjMDkiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.s3UuwH0XoKf9NEATzZQZXYvaQNNSHgMqNxWYVIrRey6qT_YnHbN4cDrug0aeegugICo6hEu_XQ9bR-nFDdDo-Q'
HEADERS = {
    'Authorization': f'Bearer {TOKEN}',
    'Content-Type': 'application/json'
}

def test_chart(name, sql, chart_type='bar'):
    print(f'=== {name} ===')
    payload = json.dumps({
        'instruction': name,
        'sql': sql,
        'chart_type': chart_type
    }).encode()
    
    req = urllib.request.Request(
        'http://localhost:8000/api/charts/custom',
        data=payload,
        headers=HEADERS,
        method='POST'
    )
    
    try:
        r = urllib.request.urlopen(req, timeout=30)
        data = json.loads(r.read())
        status = r.status
        rows = data.get('row_count', 0)
        chart = data.get('chart', {})
        chart_type_result = chart.get('type', 'none')
        print(f'  Status: {status} | Rows: {rows} | Chart: {chart_type_result}')
        if status == 200 and rows > 0:
            print(f'  ✓ PASSED')
        else:
            print(f'  ✗ FAILED')
    except urllib.error.HTTPError as e:
        print(f'  HTTP Error: {e.code} {e.read().decode()[:120]}')
        print(f'  ✗ FAILED')
    except Exception as e:
        print(f'  Error: {e}')
        print(f'  ✗ FAILED')
    print()

# Run Oracle SQL tests from ORACLE_DEMO_SQL_TESTS.md
tests = [
    ('TC-001: Contribution Collection by Region', '''
SELECT r.name AS region_name,
       COUNT(DISTINCT e.employer_id) AS total_employers,
       SUM(c.contribution_amount) AS total_collected,
       ROUND(AVG(c.contribution_amount), 2) AS avg_contribution,
       COUNT(c.contribution_id) AS transaction_count
FROM contributions c
JOIN employers e ON c.employer_id = e.employer_id
JOIN regional_offices r ON c.regional_code = r.code
WHERE c.contribution_date >= ADD_MONTHS(SYSDATE, -6)
GROUP BY r.name
ORDER BY total_collected DESC
'''.strip()),

    ('TC-002: Payment Status Breakdown', '''
SELECT payment_status,
       COUNT(*) AS count,
       SUM(contribution_amount) AS total_amount,
       ROUND(AVG(contribution_amount), 2) AS avg_amount
FROM contributions
GROUP BY payment_status
ORDER BY count DESC
'''.strip()),

    ('TC-003: Monthly Contribution Trend', '''
SELECT TO_CHAR(contribution_date, 'YYYY-MM') AS month,
       COUNT(*) AS transaction_count,
       SUM(contribution_amount) AS total_collected,
       ROUND(AVG(contribution_amount), 2) AS avg_contribution
FROM contributions
WHERE contribution_date >= ADD_MONTHS(SYSDATE, -12)
GROUP BY TO_CHAR(contribution_date, 'YYYY-MM')
ORDER BY month
'''.strip()),

    ('TC-010: Executive KPI Summary', '''
SELECT 'Total Contributions (YTD)' AS kpi_name,
       TO_CHAR(SUM(contribution_amount), 'FML999G999G999') AS kpi_value
FROM contributions
WHERE contribution_date >= TRUNC(SYSDATE, 'YEAR')
UNION ALL
SELECT 'Active Employers', TO_CHAR(COUNT(*), 'FM999G999')
FROM employers WHERE status IN ('active', 'suspended')
UNION ALL
SELECT 'Pension Disbursed (YTD)', TO_CHAR(SUM(pension_amount), 'FML999G999G999')
FROM pension_payments
WHERE payment_date >= TRUNC(SYSDATE, 'YEAR')
UNION ALL
SELECT 'Pending Accident Claims', TO_CHAR(COUNT(*), 'FM999')
FROM workplace_accidents WHERE claim_status IN ('pending', 'under-investigation')
UNION ALL
SELECT 'Total Late Fees Collected', TO_CHAR(SUM(late_fee), 'FML999G999G999')
FROM contributions WHERE late_fee > 0
'''.strip()),
]

print('Testing Oracle SQL queries via /api/charts/custom endpoint')
print('=' * 60)
print()

passed = 0
failed = 0

for name, sql in tests:
    test_chart(name, sql)
    # Count will be updated by test_chart

print()
print('=' * 60)
print('Testing complete!')