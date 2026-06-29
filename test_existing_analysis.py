"""Inspect existing analysis runs to verify they contain proper output."""
import os, sys, json
sys.path.insert(0, os.getcwd())

from backend.api.core.supabase_client import get_supabase

supabase = get_supabase()

# Get analysis runs for all users
resp = supabase.table("analysis_runs").select("*").order("created_at", desc=True).limit(10).execute()

if hasattr(resp, "data") and resp.data:
    print(f"Found {len(resp.data)} analysis runs:\n")
    for run in resp.data:
        print(f"=== Run {run.get('id')} ===")
        print(f"  User: {run.get('user_id')}")
        print(f"  Goal: {run.get('goal_text', '')[:100]}")
        print(f"  Status: {run.get('status')}")
        print(f"  Type: {run.get('goal_type')}")
        
        plan = run.get("plan_json")
        if plan and isinstance(plan, dict):
            print(f"  SQL generated: {'Yes' if plan.get('sql') else 'No'}")
            if plan.get("sql"):
                print(f"    SQL (first 100): {plan['sql'][:100]}...")
            print(f"  Chart type: {plan.get('chart_type')}")
            print(f"  Summary hint: {plan.get('summary_hint', '')[:80]}")
        elif plan and isinstance(plan, str):
            print(f"  Plan (string): {plan[:100]}...")
        else:
            print(f"  Plan: {plan}")
        
        chart = run.get("chart_json")
        if chart and isinstance(chart, dict):
            print(f"  Chart: type={chart.get('type')}, data_len={len(chart.get('data', []))}")
            if chart.get("data"):
                print(f"    First data: {chart['data'][0]}")
        elif chart and isinstance(chart, str):
            print(f"  Chart (string): {chart[:100]}...")
        else:
            print(f"  Chart: {chart}")
        
        metrics = run.get("metrics_json")
        if metrics and isinstance(metrics, dict):
            print(f"  Metrics: row_count={metrics.get('row_count')}, columns={metrics.get('columns')}")
            if "explanation" in metrics:
                expl = metrics["explanation"]
                print(f"  Explanation: {expl.get('what_this_means', '')[:100]}")
        elif metrics and isinstance(metrics, str):
            print(f"  Metrics (string): {metrics[:100]}...")
        
        error = run.get("error_message")
        if error:
            print(f"  ERROR: {error[:200]}")
        
        result_summary = run.get("result_summary", "")
        if result_summary:
            print(f"  Summary: {result_summary[:100]}")
        print()
else:
    print("No analysis runs found")

# Check presets
print("\n=== Analysis Presets ===")
resp = supabase.table("cnps_analysis_presets").select("*").execute()
if hasattr(resp, "data") and resp.data:
    for p in resp.data:
        print(f"  {p.get('slug')}: {p.get('title_en')} | goal: {p.get('default_goal_text', '')[:80]}")
