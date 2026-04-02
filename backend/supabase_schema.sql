-- SAAS-PWA Initial Database Schema für Supabase

-- User Accounts are handled by Supabase Auth (auth.users)

-- 1. Database Connections
CREATE TABLE IF NOT EXISTS public.database_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    db_type VARCHAR(50) NOT NULL, -- mysql, postgresql, sqlite, etc.
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL,
    db_name VARCHAR(255) NOT NULL,
    credentials VARCHAR(512) NOT NULL, -- AES-256 encrypted connection string
    connection_method VARCHAR(50) DEFAULT 'direct',
    connection_options JSONB,
    read_only BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Notification Recipients
CREATE TABLE IF NOT EXISTS public.notification_recipients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    preference VARCHAR(50) DEFAULT 'ALL', -- ALL, ALERTS_ONLY, BRIEF_ONLY
    opted_out BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. KPI Results (Cached for Dashboard Fast Load)
CREATE TABLE IF NOT EXISTS public.kpi_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    kpi_name VARCHAR(100) NOT NULL,
    value NUMERIC(15,2) NOT NULL,
    dod_pct NUMERIC(10,2),
    wow_pct NUMERIC(10,2),
    avg_7d NUMERIC(15,2),
    avg_30d NUMERIC(15,2),
    status VARCHAR(20) DEFAULT 'NORMAL', -- NORMAL, WATCH, WARNING, CRITICAL
    recorded_at DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Anomaly Records
CREATE TABLE IF NOT EXISTS public.anomaly_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    kpi_name VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL, -- WATCH, WARNING, CRITICAL
    deviation NUMERIC(10,2) NOT NULL,
    context JSONB,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Daily Reports (For the email briefing)
CREATE TABLE IF NOT EXISTS public.daily_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    report_date DATE NOT NULL DEFAULT CURRENT_DATE,
    narrative TEXT,
    sent_at TIMESTAMP WITH TIME ZONE
);

-- Row Level Security (RLS) Configuration
-- Ensure users can only access their own data
ALTER TABLE public.database_connections ENABLE ROW LEVEL SECURITY;
CREATE POLICY user_isolation_db_conn ON public.database_connections FOR ALL USING (user_id = auth.uid());

ALTER TABLE public.notification_recipients ENABLE ROW LEVEL SECURITY;
CREATE POLICY user_isolation_notif_rcpt ON public.notification_recipients FOR ALL USING (user_id = auth.uid());

ALTER TABLE public.kpi_results ENABLE ROW LEVEL SECURITY;
CREATE POLICY user_isolation_kpi_results ON public.kpi_results FOR ALL USING (user_id = auth.uid());

ALTER TABLE public.anomaly_records ENABLE ROW LEVEL SECURITY;
CREATE POLICY user_isolation_anomalies ON public.anomaly_records FOR ALL USING (user_id = auth.uid());

ALTER TABLE public.daily_reports ENABLE ROW LEVEL SECURITY;
CREATE POLICY user_isolation_daily_reports ON public.daily_reports FOR ALL USING (user_id = auth.uid());

-- ##############################################################################
-- EXAMPLE SOURCE TABLES (FOR TESTING ETL)
-- In a real scenario, these would live in your department's SQL database.
-- ##############################################################################

CREATE TABLE IF NOT EXISTS public.source_revenue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    amount NUMERIC(15,2) NOT NULL,
    transaction_date TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.source_inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stock_value NUMERIC(15,2) NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.source_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_count INTEGER NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- SEED DATA (OPTIONAL)
-- Uncomment these if you want to populate the source tables with initial data
/*
INSERT INTO public.source_revenue (amount) VALUES (150000.00), (145000.00), (160000.00);
INSERT INTO public.source_inventory (stock_value) VALUES (450000.00), (455000.00);
INSERT INTO public.source_tickets (ticket_count) VALUES (85), (92), (110);
*/

-- 6. User Preferences & Advanced Scheduling
CREATE TABLE IF NOT EXISTS public.user_preferences (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    ai_tone VARCHAR(50) DEFAULT 'insight-driven',
    sync_time VARCHAR(10) DEFAULT '09:00',
    sync_frequency VARCHAR(20) DEFAULT 'daily', -- daily, weekly, monthly, yearly
    yearly_date VARCHAR(10) DEFAULT '01-01', -- MM-DD format
    analysis_instruction TEXT, -- Plain-English focus for AI
    last_sync_status VARCHAR(50) DEFAULT 'IDLE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. Strategic Analysis History
CREATE TABLE IF NOT EXISTS public.analysis_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    instruction TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RLS for new tables
ALTER TABLE public.user_preferences ENABLE ROW LEVEL SECURITY;
CREATE POLICY user_isolation_prefs ON public.user_preferences FOR ALL USING (user_id = auth.uid());

ALTER TABLE public.analysis_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY user_isolation_analysis_hist ON public.analysis_history FOR ALL USING (user_id = auth.uid());
