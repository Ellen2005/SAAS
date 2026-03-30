import pandas as pd
import numpy as np
from datetime import datetime, timezone
import uuid

from sqlalchemy import create_engine
import os

def extract_from_source(user_id: str, db_connection_info: dict) -> pd.DataFrame:
    """
    Extracts the last 30 days of KPI data from the provided database connection.
    If MOCK_DATA is True or connection fails, it falls back to mock data.
    """
    mock_flag = os.getenv("MOCK_DATA", "False").lower() == "true"
    
    # Use connection string from db_connection_info if available (prioritize user settings)
    db_url = db_connection_info.get("credentials") if db_connection_info else os.getenv("DATABASE_URL")
    
    if not mock_flag and db_url:
        try:
            # Clean up URL for logging (hide password)
            safe_url = db_url.split('@')[-1] if '@' in db_url else "external source"
            print(f"[{datetime.now().isoformat()}] Fetching real data for user {user_id} from {safe_url}...")
            
            engine = create_engine(db_url)
            
            # Query real data for the 3 KPIs from the source tables
            revenue_query = "SELECT transaction_date as date, 'Total Revenue' as kpi_name, amount as value FROM public.source_revenue WHERE transaction_date > NOW() - INTERVAL '30 days'"
            inventory_query = "SELECT recorded_at as date, 'Inventory Value' as kpi_name, stock_value as value FROM public.source_inventory WHERE recorded_at > NOW() - INTERVAL '30 days'"
            tickets_query = "SELECT recorded_at as date, 'Support Tickets' as kpi_name, ticket_count as value FROM public.source_tickets WHERE recorded_at > NOW() - INTERVAL '30 days'"
            
            with engine.connect() as conn:
                df_rev = pd.read_sql(revenue_query, conn)
                df_inv = pd.read_sql(inventory_query, conn)
                df_tic = pd.read_sql(tickets_query, conn)
                
            combined_df = pd.concat([df_rev, df_inv, df_tic])
            
            if not combined_df.empty:
                return combined_df
            else:
                print(f"[{datetime.now().isoformat()}] User {user_id} source database is empty. Falling back to mock data.")
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Extraction Error for user {user_id}: {e}. Falling back to mock data.")

    # FALLBACK MOCK DATA GENERATION
    # Create 30 days of mock historical data for 3 KPIs
    dates = pd.date_range(end=pd.Timestamp.today(), periods=30)
    
    data = []
    # Total Revenue (Trend: Generally stable, but let's spike the last day to trigger anomaly)
    base_revenue = 135000
    for i, d in enumerate(dates):
        val = 190000 if i == 29 else base_revenue + np.random.normal(0, 5000)
        data.append({"date": d, "kpi_name": "Total Revenue", "value": val})
        
    # inventory Value
    base_inventory = 450000
    for i, d in enumerate(dates):
        val = base_inventory + np.random.normal(0, 8000)
        data.append({"date": d, "kpi_name": "Inventory Value", "value": val})
        
    # Support Tickets
    base_tickets = 89
    for i, d in enumerate(dates):
        val = 150 if i == 29 else max(10, int(base_tickets + np.random.normal(0, 15)))
        data.append({"date": d, "kpi_name": "Support Tickets", "value": val})
        
    return pd.DataFrame(data)

def detect_anomalies_and_transform(df: pd.DataFrame):
    """
    Compares the most recent data point against the 30-day mean/std deviation.
    Flags as anomaly if it's > 1.5 std dev away.
    """
    kpis = []
    anomalies = []
    
    # Process each KPI
    for kpi_name in df['kpi_name'].unique():
        kpi_df = df[df['kpi_name'] == kpi_name].sort_values('date')
        
        # Historical (excluding today)
        historical = kpi_df.iloc[:-1]
        today = kpi_df.iloc[-1]
        
        mean_30d = historical['value'].mean()
        std_30d = historical['value'].std()
        
        # Calculate 7-day average
        avg_7d = historical.tail(7)['value'].mean()
        
        # Calculate DoD and WoW
        yesterday_val = historical.iloc[-1]['value']
        last_week_val = historical.iloc[-7]['value']
        
        dod_pct = ((today['value'] - yesterday_val) / yesterday_val) * 100 if yesterday_val else 0
        wow_pct = ((today['value'] - last_week_val) / last_week_val) * 100 if last_week_val else 0
        
        current_val = today['value']
        
        # Anomaly Detection (Standard Deviations)
        z_score = abs(current_val - mean_30d) / std_30d if std_30d > 0 else 0
        
        status = "NORMAL"
        if z_score > 2.5:
            status = "CRITICAL"
            anomalies.append({
                "id": str(uuid.uuid4()),
                "kpi_name": kpi_name,
                "severity": "CRITICAL",
                "deviation": round(z_score, 2),
                "context": {"reason": f"Value {current_val:.2f} is exceptionally far from the 30-day average of {mean_30d:.2f}"},
                "detected_at": datetime.now(timezone.utc).isoformat()
            })
        elif z_score > 1.5:
            status = "WARNING"
            anomalies.append({
                "id": str(uuid.uuid4()),
                "kpi_name": kpi_name,
                "severity": "WARNING",
                "deviation": round(z_score, 2),
                "context": {"reason": f"Value {current_val:.2f} is notable compared to the average of {mean_30d:.2f}"},
                "detected_at": datetime.now(timezone.utc).isoformat()
            })
            
        kpis.append({
            "id": str(uuid.uuid4()),
            "kpi_name": kpi_name,
            "value": current_val,
            "dod_pct": round(dod_pct, 2),
            "wow_pct": round(wow_pct, 2),
            "avg_7d": round(avg_7d, 2),
            "status": status,
            "recorded_at": today['date'].isoformat()
        })
        
    return kpis, anomalies

def run_user_etl_pipeline(user_id: str):
    """
    Main orchestrator for a single user's ETL execution.
    """
    print(f"[{datetime.now().isoformat()}] Starting ETL for user {user_id}...")
    
    from ..core.supabase_client import get_supabase
    supabase = get_supabase()

    # 1. Fetch user's specific database connection from Supabase
    conn_response = supabase.table('database_connections').select("*").eq("user_id", user_id).execute()
    db_connection_info = {}
    if hasattr(conn_response, 'data') and conn_response.data:
        db_connection_info = conn_response.data[0]
        print(f"[{datetime.now().isoformat()}] Using saved connection for user {user_id}.")
    else:
        print(f"[{datetime.now().isoformat()}] No saved connection found for user {user_id}. Using system environment defaults.")

    # 2. Extract
    df = extract_from_source(user_id, db_connection_info)
    print(f"[{datetime.now().isoformat()}] Extraction complete. {len(df)} records retrieved.")
    
    # 3. Transform & Anomaly Detection
    kpis, anomalies = detect_anomalies_and_transform(df)
    
    # Ensure user_id is set on all records
    for k in kpis: k['user_id'] = user_id
    for a in anomalies: a['user_id'] = user_id

    print(f"[{datetime.now().isoformat()}] Transformation complete. Generated {len(kpis)} KPIs and {len(anomalies)} anomalies.")
    
    # 4. Load
    # Insert new results
    supabase.table('kpi_results').insert(kpis).execute()
    if anomalies:
        supabase.table('anomaly_records').insert(anomalies).execute()
        
    print(f"[{datetime.now().isoformat()}] Data loaded to Supabase successfully for user {user_id}.")
    
    # 5. Trigger Narrative & Email Briefings
    from .narrative_service import generate_live_narrative
    from .email_service import send_automated_briefing
    
    print(f"[{datetime.now().isoformat()}] Generating AI Narrative...")
    narrative_text = generate_live_narrative(kpis, anomalies)
    
    # Record the report in Supabase
    report_data = {
        "user_id": user_id,
        "narrative": narrative_text,
        "report_date": datetime.now().date().isoformat()
    }
    supabase.table('daily_reports').insert(report_data).execute()

    # In a real environment, query DB for user notification preferences.
    # For now, we simulate finding an email associated with the user.
    mock_email = "department.user@example.com"
    send_automated_briefing(mock_email, kpis, anomalies, narrative_text, df)
    
    return {"status": "success", "user_id": user_id, "kpis": len(kpis), "anomalies": len(anomalies)}
