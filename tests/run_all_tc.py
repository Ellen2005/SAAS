"""
Run all 11 TC test cases against the analysis API.
"""
from supabase import create_client
import requests, json, time

url = 'https://jtbyxbdkhmbzivzuaekz.supabase.co'
key = 'sb_publishable_IgihMlgZs_uK-MHkMn9Vcg_NFo1BPQn'
client = create_client(url, key)
resp = client.auth.sign_in_with_password({'email': 'user@cnps.com', 'password': 'tests2'})
token = resp.session.access_token
print('Login OK')

headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

TEST_CASES = [
    ("TC-001", "Contribution Collection by Region",
     "Analyze contribution collection by region for the last 6 months. Show total employers, total collected, average contribution, and transaction count per region."),
    ("TC-002", "Payment Status Breakdown",
     "Show payment status breakdown from contributions table. Group by payment_status and show count, total amount, and average amount."),
    ("TC-003", "Monthly Contribution Trend",
     "Show monthly contribution trend for the last 12 months. Display month, transaction count, total collected, and average contribution per month."),
    ("TC-004", "Employer Delinquency Analysis",
     "Analyze employer delinquency. Show employer code, company name, sector, region, last payment date, days since last payment, unpaid count, and total owed for delinquent employers."),
    ("TC-005", "Pension Disbursement by Region",
     "Analyze pension disbursement by region for the last 12 months. Show total beneficiaries, total disbursed, average pension, and average processing days per region."),
    ("TC-006", "Workplace Accidents by Severity",
     "Analyze workplace accidents by severity and region for the last 12 months. Show claim count, average claim amount, average processing days, and total claimed."),
    ("TC-007", "Employer Sector Health Overview",
     "Provide employer sector health overview. Show employer count, total contributions, average contribution, overdue count, and overdue percentage per sector."),
    ("TC-008", "Regional Office Budget vs Staffing",
     "Show regional office budget vs staffing. Display code, name, region, staff count, budget allocated, and budget per staff ratio."),
    ("TC-009", "Late Payment Fee Analysis",
     "Analyze late payment fees by region. Show late payment count, total fees collected, average fee, and max fee per region."),
    ("TC-010", "Executive KPI Summary",
     "Provide executive KPI summary including: total contributions YTD, active employers count, pension disbursed YTD, pending accident claims, and total late fees collected."),
    ("TC-011", "Monthly New Employers Trend",
     "Show monthly new employer registration trend for the last 24 months. Display month, new employer count, and average employee count."),
]

results = {}
for tc_id, desc, goal in TEST_CASES:
    print(f"\n{'='*60}")
    print(f"  {tc_id} — {desc}")
    print(f"{'='*60}")
    start = time.time()
    try:
        r = requests.post('http://localhost:8000/api/analysis/run', 
            json={'goal_text': goal, 'goal_type': 'natural_language'},
            headers=headers, timeout=180)
        elapsed = time.time() - start
        if r.status_code == 200:
            data = r.json()
            status = data.get('status')
            sql = data.get('sql', '')
            rows = data.get('rows', [])
            chart = data.get('chart', {})
            print(f"  Status: {status} | Time: {elapsed:.1f}s | Rows: {len(rows)} | Chart: {chart.get('type', 'N/A')}")
            print(f"  SQL: {sql[:200] if sql else 'None'}")
            if rows and isinstance(rows[0], dict):
                print(f"  Columns: {list(rows[0].keys())}")
                for i, row in enumerate(rows[:2]):
                    print(f"    Row {i+1}: {row}")
            results[tc_id] = {"status": status, "rows": len(rows), "chart": chart.get('type', 'N/A'), "sql": sql[:300] if sql else None}
        else:
            print(f"  ERROR {r.status_code}: {r.text[:300]}")
            results[tc_id] = {"status": "error", "error": r.text[:200]}
    except Exception as e:
        elapsed = time.time() - start
        print(f"  EXCEPTION after {elapsed:.1f}s: {e}")
        results[tc_id] = {"status": "exception", "error": str(e)[:200]}

print(f"\n\n{'='*60}")
print("  FINAL SUMMARY")
print(f"{'='*60}")
passed = sum(1 for v in results.values() if v.get('status') == 'completed' and v.get('rows', 0) > 0)
total = len(TEST_CASES)
for tc_id, r in results.items():
    s = r.get('status', 'unknown')
    rows = r.get('rows', 0)
    chart = r.get('chart', 'N/A')
    marker = 'PASS' if s == 'completed' and rows > 0 else 'FAIL'
    print(f"  {tc_id}: [{marker}] status={s} rows={rows} chart={chart}")
print(f"\n  {passed}/{total} passed")
