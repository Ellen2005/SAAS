from supabase import create_client
import requests, json, time

url = 'https://jtbyxbdkhmbzivzuaekz.supabase.co'
key = 'sb_publishable_IgihMlgZs_uK-MHkMn9Vcg_NFo1BPQn'
client = create_client(url, key)
resp = client.auth.sign_in_with_password({'email': 'user@cnps.com', 'password': 'tests2'})
token = resp.session.access_token
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
print('Login OK')

tests = [
    ('TC-002', 'Show payment status breakdown from contributions table. Group by payment_status and show count, total amount, and average amount.'),
    ('TC-003', 'Show monthly contribution trend for the last 12 months. Display month, transaction count, total collected, and average contribution per month.'),
    ('TC-005', 'Analyze pension disbursement by region for the last 12 months. Show total beneficiaries, total disbursed, average pension, and average processing days per region.'),
    ('TC-006', 'Analyze workplace accidents by severity and region for the last 12 months. Show claim count, average claim amount, average processing days, and total claimed.'),
    ('TC-007', 'Provide employer sector health overview. Show employer count, total contributions, average contribution, overdue count, and overdue percentage per sector.'),
    ('TC-008', 'Show regional office budget vs staffing. Display code, name, region, staff count, budget allocated, and budget per staff ratio.'),
    ('TC-009', 'Analyze late payment fees by region. Show late payment count, total fees collected, average fee, and max fee per region.'),
    ('TC-010', 'Provide executive KPI summary including: total contributions YTD, active employers count, pension disbursed YTD, pending accident claims, and total late fees collected.'),
    ('TC-011', 'Show monthly new employer registration trend for the last 24 months. Display month, new employer count, and average employee count.'),
]

for tc_id, goal in tests:
    print(f'\n--- {tc_id} ---')
    start = time.time()
    try:
        r = requests.post('http://localhost:8000/api/analysis/run', json={'goal_text': goal, 'goal_type': 'natural_language'}, headers=headers, timeout=180)
        elapsed = time.time() - start
        if r.status_code == 200:
            data = r.json()
            status_val = data.get('status', 'unknown')
            rows = data.get('rows', [])
            chart = data.get('chart', {})
            chart_type = chart.get('type', 'N/A')
            chart_len = len(chart.get('data', []))
            sql = data.get('sql', '')
            print(f'  Status: {status_val} | Time: {elapsed:.1f}s | Rows: {len(rows)} | Chart: {chart_type} ({chart_len} pts)')
            print(f'  SQL: {sql[:200] if sql else "None"}')
            if rows:
                print(f'  Columns: {list(rows[0].keys())}')
                for i, row in enumerate(rows[:2]):
                    print(f'    Row {i+1}: {row}')
        else:
            print(f'  ERROR {r.status_code}: {r.text[:300]}')
    except Exception as e:
        elapsed = time.time() - start
        print(f'  EXCEPTION after {elapsed:.1f}s: {e}')
