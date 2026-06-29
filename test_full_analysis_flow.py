"""Full end-to-end test of goal analysis using the working user connection."""
import os, sys, json
sys.path.insert(0, os.getcwd())

from backend.api.core.supabase_client import get_supabase
from backend.api.services.analysis_engine import run_analysis, list_presets

supabase = get_supabase()

# Use the user that has working analysis (5a4166a7-bc77-4244-aef9-b4edcc6a120c)
USER_ID = "5a4166a7-bc77-4244-aef9-b4edcc6a120c"

# Test 1: Run goal analysis with a preset
print("=" * 70)
print("TEST 1: Run analysis with 'contributions-monitoring' preset")
print("=" * 70)
result = run_analysis(
    user_id=USER_ID,
    goal_text="",
    goal_type="natural_language",
    preset_slug="contributions-monitoring",
    supabase=supabase,
)
if result.get("status") == "completed":
    print(f"  Status: {result['status']}")
    print(f"  SQL: {result.get('sql', 'N/A')[:120]}...")
    print(f"  Chart type: {result.get('chart', {}).get('type')}")
    print(f"  Rows: {result.get('metrics', {}).get('row_count')}")
    expl = result.get("metrics", {}).get("explanation", {})
    if expl:
        print(f"  Explanation: {expl.get('what_this_means', '')[:100]}")
        print(f"  Assumptions: {expl.get('assumptions', [])}")
        print(f"  Limitations: {expl.get('limitations', [])[:2]}")
        print(f"  Recommendations: {expl.get('recommended_actions', [])[:2]}")
    print(f"  Summary: {result.get('summary', '')[:100]}")
else:
    print(f"  FAILED: {result.get('error', 'Unknown error')}")
print()

# Test 2: Run analysis with natural language
print("=" * 70)
print("TEST 2: Run analysis with natural language goal")
print("=" * 70)
result2 = run_analysis(
    user_id=USER_ID,
    goal_text="Show contribution collection rates by region for last 6 months",
    goal_type="natural_language",
    supabase=supabase,
)
if result2.get("status") == "completed":
    print(f"  Status: {result2['status']}")
    print(f"  SQL: {result2.get('sql', 'N/A')[:120]}...")
    print(f"  Chart type: {result2.get('chart', {}).get('type')}")
    print(f"  Rows: {result2.get('metrics', {}).get('row_count')}")
    expl2 = result2.get("metrics", {}).get("explanation", {})
    if expl2:
        print(f"  Explanation: {expl2.get('what_this_means', '')[:100]}")
else:
    print(f"  FAILED: {result2.get('error', 'Unknown error')}")
print()

# Test 3: Run analysis with pension preset
print("=" * 70)
print("TEST 3: Run analysis with 'pension-analytics' preset")
print("=" * 70)
result3 = run_analysis(
    user_id=USER_ID,
    goal_text="",
    goal_type="natural_language",
    preset_slug="pension-analytics",
    supabase=supabase,
)
if result3.get("status") == "completed":
    print(f"  Status: {result3['status']}")
    print(f"  SQL: {result3.get('sql', 'N/A')[:120]}...")
    print(f"  Chart type: {result3.get('chart', {}).get('type')}")
    print(f"  Rows: {result3.get('metrics', {}).get('row_count')}")
else:
    print(f"  FAILED: {result3.get('error', 'Unknown error')}")
print()

# Test 4: Run analysis with 'employer-compliance' preset
print("=" * 70)
print("TEST 4: Run analysis with 'employer-compliance' preset")
print("=" * 70)
result4 = run_analysis(
    user_id=USER_ID,
    goal_text="",
    goal_type="natural_language",
    preset_slug="employer-compliance",
    supabase=supabase,
)
if result4.get("status") == "completed":
    print(f"  Status: {result4['status']}")
    print(f"  SQL: {result4.get('sql', 'N/A')[:120]}...")
    print(f"  Chart type: {result4.get('chart', {}).get('type')}")
    print(f"  Rows: {result4.get('metrics', {}).get('row_count')}")
else:
    print(f"  FAILED: {result4.get('error', 'Unknown error')}")
print()

# Test 5: Test what happens with the realistic demo database
print("=" * 70)
print("TEST 5: Check KPI results for this user")
print("=" * 70)
kpi_resp = supabase.table("kpi_results").select("*").eq("user_id", USER_ID).order("recorded_at", desc=True).limit(5).execute()
if hasattr(kpi_resp, "data") and kpi_resp.data:
    for kpi in kpi_resp.data:
        print(f"  KPI: {kpi.get('kpi_name')} = {kpi.get('value')} ({kpi.get('status')})")
print()

# Test 6: Verify chart building works for different data shapes
print("=" * 70)
print("TEST 6: Verify chart output structure")
print("=" * 70)
chart = result.get("chart", {})
print(f"  Chart keys: {list(chart.keys())}")
print(f"  Chart type: {chart.get('type')}")
if chart.get("data"):
    print(f"  Data sample: {json.dumps(chart['data'][0], indent=2)}")
print()

# Test 7: Try with formula
print("=" * 70)
print("TEST 7: Run analysis with formula")
print("=" * 70)
result5 = run_analysis(
    user_id=USER_ID,
    goal_text="Analyze overdue payment ratio",
    goal_type="formula",
    formula="overdue_count / total_count * 100",
    supabase=supabase,
)
if result5.get("status") == "completed":
    print(f"  Status: {result5['status']}")
    print(f"  SQL: {result5.get('sql', 'N/A')[:120]}...")
elif result5.get("status") == "failed":
    print(f"  Status: {result5['status']} (expected, formula requires specific columns)")
    print(f"  Error: {result5.get('error', '')[:200]}")
print()

print("=" * 70)
print("FULL ANALYSIS TEST COMPLETE")
print("=" * 70)
