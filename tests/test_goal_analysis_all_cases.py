"""
Comprehensive test for AI Analyst Goal Analysis.
Tests all 11 TC cases against the running backend.
Authenticates as user@cnps.com and calls the /api/analysis/run endpoint.
"""
import json
import sys
import time
import requests

BASE_URL = "http://localhost:8000"
EMAIL = "user@cnps.com"
PASSWORD = "tests2"


def login():
    """Authenticate with Supabase and get access token."""
    from supabase import create_client
    url = "https://jtbyxbdkhmbzivzuaekz.supabase.co"
    key = "sb_publishable_IgihMlgZs_uK-MHkMn9Vcg_NFo1BPQn"
    client = create_client(url, key)
    resp = client.auth.sign_in_with_password({"email": EMAIL, "password": PASSWORD})
    token = resp.session.access_token
    print(f"Logged in as {EMAIL}, token: {token[:30]}...")
    return token


def run_analysis(token, goal_text, test_id, description):
    """Call the analysis API and return results."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"goal_text": goal_text, "goal_type": "natural_language"}
    
    print(f"\n{'='*70}")
    print(f"  {test_id} — {description}")
    print(f"{'='*70}")
    print(f"  Goal: {goal_text}")
    
    start = time.time()
    try:
        resp = requests.post(f"{BASE_URL}/api/analysis/run", json=payload, headers=headers, timeout=120)
        elapsed = time.time() - start
        print(f"  Status: {resp.status_code} | Time: {elapsed:.1f}s")
        
        if resp.status_code != 200:
            print(f"  ERROR: {resp.text[:500]}")
            return None
        
        data = resp.json()
        status = data.get("status", "unknown")
        print(f"  Analysis status: {status}")
        
        # Print SQL
        sql = data.get("sql")
        if sql:
            print(f"  Generated SQL:\n    {sql[:500]}")
        else:
            print(f"  No SQL generated")
        
        # Print chart info
        chart = data.get("chart", {})
        chart_type = chart.get("type", "N/A")
        chart_data = chart.get("data", [])
        print(f"  Chart type: {chart_type} | Data points: {len(chart_data)}")
        
        # Print rows count
        rows = data.get("rows", [])
        print(f"  Rows returned: {len(rows)}")
        
        # Print columns
        if rows:
            cols = list(rows[0].keys()) if isinstance(rows[0], dict) else []
            print(f"  Columns: {cols}")
            # Print first 3 rows
            for i, row in enumerate(rows[:3]):
                print(f"    Row {i+1}: {row}")
        
        # Print metrics/explanation
        metrics = data.get("metrics", {})
        explanation = metrics.get("explanation", {})
        if explanation:
            print(f"  What this means: {explanation.get('what_this_means', 'N/A')[:200]}")
        
        summary = data.get("summary", "")
        print(f"  Summary: {summary[:200] if summary else 'N/A'}")
        
        return data
    except requests.exceptions.Timeout:
        print(f"  TIMEOUT after 120s")
        return None
    except Exception as e:
        print(f"  EXCEPTION: {e}")
        return None


def test_nlq_direct(token, question, test_id):
    """Test via the NLQ endpoint directly."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    print(f"\n{'='*70}")
    print(f"  {test_id} — NLQ Direct Test")
    print(f"{'='*70}")
    print(f"  Question: {question}")
    
    start = time.time()
    try:
        resp = requests.post(f"{BASE_URL}/api/nlq", json={"question": question}, headers=headers, timeout=120)
        elapsed = time.time() - start
        print(f"  Status: {resp.status_code} | Time: {elapsed:.1f}s")
        
        if resp.status_code != 200:
            print(f"  ERROR: {resp.text[:500]}")
            return None
        
        data = resp.json()
        sql = data.get("sql")
        rows = data.get("rows", [])
        chart = data.get("chart", {})
        
        print(f"  SQL: {sql[:500] if sql else 'None'}")
        print(f"  Rows: {len(rows)}")
        print(f"  Chart type: {chart.get('type', 'N/A') if chart else 'None'}")
        
        if rows:
            cols = list(rows[0].keys()) if isinstance(rows[0], dict) else []
            print(f"  Columns: {cols}")
            for i, row in enumerate(rows[:3]):
                print(f"    Row {i+1}: {row}")
        
        return data
    except Exception as e:
        print(f"  EXCEPTION: {e}")
        return None


def main():
    print("=" * 70)
    print("  AI ANALYST — COMPREHENSIVE GOAL ANALYSIS TEST")
    print("  Testing 11 CNPS Test Cases")
    print("=" * 70)
    
    # Login
    try:
        token = login()
    except Exception as e:
        print(f"Login failed: {e}")
        sys.exit(1)
    
    results = {}
    
    # ── TC-001: Contribution Collection by Region ──
    results["TC-001"] = run_analysis(
        token,
        "Analyze contribution collection by region for the last 6 months. "
        "Show total employers, total collected, average contribution, and transaction count per region.",
        "TC-001",
        "Contribution Collection by Region"
    )
    
    # ── TC-002: Payment Status Breakdown ──
    results["TC-002"] = run_analysis(
        token,
        "Show payment status breakdown from contributions table. "
        "Group by payment_status and show count, total amount, and average amount.",
        "TC-002",
        "Payment Status Breakdown"
    )
    
    # ── TC-003: Monthly Contribution Trend ──
    results["TC-003"] = run_analysis(
        token,
        "Show monthly contribution trend for the last 12 months. "
        "Display month, transaction count, total collected, and average contribution per month.",
        "TC-003",
        "Monthly Contribution Trend"
    )
    
    # ── TC-004: Employer Delinquency Analysis ──
    results["TC-004"] = run_analysis(
        token,
        "Analyze employer delinquency. Show employer code, company name, sector, region, "
        "last payment date, days since last payment, unpaid count, and total owed for delinquent employers.",
        "TC-004",
        "Employer Delinquency Analysis"
    )
    
    # ── TC-005: Pension Disbursement by Region ──
    results["TC-005"] = run_analysis(
        token,
        "Analyze pension disbursement by region for the last 12 months. "
        "Show total beneficiaries, total disbursed, average pension, and average processing days per region.",
        "TC-005",
        "Pension Disbursement by Region"
    )
    
    # ── TC-006: Workplace Accidents by Severity ──
    results["TC-006"] = run_analysis(
        token,
        "Analyze workplace accidents by severity and region for the last 12 months. "
        "Show claim count, average claim amount, average processing days, and total claimed.",
        "TC-006",
        "Workplace Accidents by Severity"
    )
    
    # ── TC-007: Employer Sector Health Overview ──
    results["TC-007"] = run_analysis(
        token,
        "Provide employer sector health overview. Show employer count, total contributions, "
        "average contribution, overdue count, and overdue percentage per sector.",
        "TC-007",
        "Employer Sector Health Overview"
    )
    
    # ── TC-008: Regional Office Budget vs Staffing ──
    results["TC-008"] = run_analysis(
        token,
        "Show regional office budget vs staffing. Display code, name, region, "
        "staff count, budget allocated, and budget per staff ratio.",
        "TC-008",
        "Regional Office Budget vs Staffing"
    )
    
    # ── TC-009: Late Payment Fee Analysis ──
    results["TC-009"] = run_analysis(
        token,
        "Analyze late payment fees by region. Show late payment count, "
        "total fees collected, average fee, and max fee per region.",
        "TC-009",
        "Late Payment Fee Analysis"
    )
    
    # ── TC-010: Executive KPI Summary ──
    results["TC-010"] = run_analysis(
        token,
        "Provide executive KPI summary including: total contributions YTD, "
        "active employers count, pension disbursed YTD, pending accident claims, "
        "and total late fees collected.",
        "TC-010",
        "Executive KPI Summary"
    )
    
    # ── TC-011: Monthly New Employers Trend ──
    results["TC-011"] = run_analysis(
        token,
        "Show monthly new employer registration trend for the last 24 months. "
        "Display month, new employer count, and average employee count.",
        "TC-011",
        "Monthly New Employers Trend"
    )
    
    # ── Summary ──
    print("\n" + "=" * 70)
    print("  TEST SUMMARY")
    print("=" * 70)
    
    passed = 0
    failed = 0
    for tc_id, result in results.items():
        if result and result.get("status") == "completed" and result.get("rows"):
            status = "PASS"
            passed += 1
        elif result and result.get("rows"):
            status = "PARTIAL"
            passed += 1
        else:
            status = "FAIL"
            failed += 1
        rows_count = len(result.get("rows", [])) if result else 0
        chart_type = result.get("chart", {}).get("type", "N/A") if result else "N/A"
        print(f"  {tc_id}: {status} | Rows: {rows_count} | Chart: {chart_type}")
    
    print(f"\n  Total: {passed + failed} | Passed: {passed} | Failed: {failed}")
    print("=" * 70)
    
    # Save full results to JSON
    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nFull results saved to test_results.json")


if __name__ == "__main__":
    main()
