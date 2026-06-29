"""Test Supabase connectivity and user database connection."""
import os, sys
sys.path.insert(0, os.getcwd())

from backend.api.core.supabase_client import get_supabase

supabase = get_supabase()
print(f"Supabase client created: {type(supabase).__name__}")

# Try to query database_connections
try:
    resp = supabase.table("database_connections").select("*").limit(5).execute()
    if hasattr(resp, "data"):
        print(f"DB connections found: {len(resp.data)}")
        for conn in resp.data:
            print(f"  User: {conn.get('user_id')}, DB Type: {conn.get('db_type')}")
    else:
        print(f"No data attribute in response")
except Exception as e:
    print(f"Supabase query error: {e}")

# Try to find user@cnps.com
try:
    resp = supabase.table("user_roles").select("user_id, role").limit(10).execute()
    if hasattr(resp, "data"):
        print(f"User roles found: {len(resp.data)}")
        for r in resp.data:
            print(f"  User: {r.get('user_id')}, Role: {r.get('role')}")
except Exception as e:
    print(f"User roles query error: {e}")
