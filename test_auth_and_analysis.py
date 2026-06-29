"""Test authentication and goal analysis API end-to-end."""
import os, sys, json
sys.path.insert(0, os.getcwd())

from backend.api.core.supabase_client import get_supabase
from backend.api.services.analysis_engine import run_analysis, list_presets

supabase = get_supabase()

# Find user@cnps.com in Supabase auth
try:
    resp = supabase.auth.admin.list_users()
    for user in resp.users:
        email = getattr(user, "email", None) or user.get("email", "")
        if "cnps" in str(email).lower():
            print(f"Found user: {email} (id: {user.id})")
except Exception as e:
    print(f"Could not list users: {e}")
    print("Trying with known user IDs from database_connections...")

# Check the database connections in detail
resp = supabase.table("database_connections").select("*").limit(5).execute()
for conn in resp.data:
    print(f"\nConnection for user {conn.get('user_id')}:")
    print(f"  DB Type: {conn.get('db_type')}")
    print(f"  Connection method: {conn.get('connection_method')}")
    creds = conn.get("credentials", "")
    if creds:
        print(f"  Credentials (first 80 chars): {str(creds)[:80]}...")
    
    # Also check KPI results for this user
    kpi_resp = supabase.table("kpi_results").select("*").eq("user_id", conn["user_id"]).limit(3).execute()
    if hasattr(kpi_resp, "data") and kpi_resp.data:
        print(f"  Has KPI results: {len(kpi_resp.data)}")
    
    # Check analysis runs
    run_resp = supabase.table("analysis_runs").select("*").eq("user_id", conn["user_id"]).limit(3).execute()
    if hasattr(run_resp, "data") and run_resp.data:
        print(f"  Has analysis runs: {len(run_resp.data)}")
        for run in run_resp.data:
            print(f"    Goal: {run.get('goal_text', '')[:60]} | Status: {run.get('status')}")

# Check presets
try:
    presets = list_presets(supabase, "en")
    print(f"\nAnalysis presets: {len(presets)}")
    for p in presets:
        print(f"  {p.get('slug')}: {p.get('title')} ({p.get('category')})")
except Exception as e:
    print(f"Error listing presets: {e}")
