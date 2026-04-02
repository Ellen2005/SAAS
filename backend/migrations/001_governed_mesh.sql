-- =============================================================================
-- SAAS Governed Mesh Migration
-- Phase 1: New tables, schema alterations, RLS policies, bootstrap
-- Run this in Supabase SQL Editor (Dashboard > SQL Editor)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. DEPARTMENTS
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.departments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    instance_url VARCHAR(500),
    api_key VARCHAR(256),
    template_id UUID,
    instance_template_id UUID,
    heartbeat_schedule VARCHAR(20) DEFAULT 'daily',  -- daily, weekly, monthly
    heartbeat_time VARCHAR(10) DEFAULT '06:00',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- 2. USER ROLES
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    department_id UUID REFERENCES public.departments(id) ON DELETE SET NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'viewer',  -- admin, manager, viewer
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, department_id)
);

-- -----------------------------------------------------------------------------
-- 3. SEMANTIC TEMPLATES
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.semantic_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add FK from departments to semantic_templates now that it exists
ALTER TABLE public.departments
    ADD CONSTRAINT fk_departments_template
    FOREIGN KEY (template_id) REFERENCES public.semantic_templates(id) ON DELETE SET NULL;

-- -----------------------------------------------------------------------------
-- 4. SEMANTIC FIELDS (global field definitions within a template)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.semantic_fields (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID NOT NULL REFERENCES public.semantic_templates(id) ON DELETE CASCADE,
    global_field_name VARCHAR(100) NOT NULL,
    data_type VARCHAR(50) NOT NULL,  -- currency, string, date, percent, integer, float
    required BOOLEAN DEFAULT false,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- 5. FIELD MAPPINGS (user's local columns → global fields)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.field_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    template_field_id UUID NOT NULL REFERENCES public.semantic_fields(id) ON DELETE CASCADE,
    local_column_name VARCHAR(200) NOT NULL,
    transformation_rule JSONB,  -- e.g., {"type": "multiply", "factor": 100}
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, template_field_id)
);

-- -----------------------------------------------------------------------------
-- 6. VALIDATION LOGS
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.validation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    department_id UUID REFERENCES public.departments(id) ON DELETE SET NULL,
    check_type VARCHAR(50) NOT NULL,   -- schema, null, anomaly
    status VARCHAR(20) NOT NULL,       -- pass, warning, fail
    message TEXT,
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- 7. INSTANCE TEMPLATES
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.instance_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    config JSONB NOT NULL,
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE table_schema = 'public'
          AND table_name = 'departments'
          AND constraint_name = 'fk_departments_instance_template'
    ) THEN
        ALTER TABLE public.departments
            ADD CONSTRAINT fk_departments_instance_template
            FOREIGN KEY (instance_template_id) REFERENCES public.instance_templates(id) ON DELETE SET NULL;
    END IF;
END $$;

-- -----------------------------------------------------------------------------
-- 8. COMBINED REPORTS (admin-level aggregated reports)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.combined_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_date DATE NOT NULL DEFAULT CURRENT_DATE,
    department_breakdown JSONB,
    combined_kpis JSONB,
    narrative TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- 9. SOURCE LINEAGE RECORDS
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.source_lineage_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_source_id UUID NOT NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    department_id UUID REFERENCES public.departments(id) ON DELETE SET NULL,
    kpi_name VARCHAR(100) NOT NULL,
    source_record_id VARCHAR(128),
    record_label VARCHAR(255),
    record_date DATE,
    record_value NUMERIC(15,2),
    raw_payload JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- SCHEMA ALTERATIONS TO EXISTING TABLES
-- =============================================================================

ALTER TABLE public.kpi_results ADD COLUMN IF NOT EXISTS department_id UUID REFERENCES public.departments(id);
ALTER TABLE public.kpi_results ADD COLUMN IF NOT EXISTS source_id UUID;
ALTER TABLE public.kpi_results ADD COLUMN IF NOT EXISTS source_record_count INTEGER;

ALTER TABLE public.anomaly_records ADD COLUMN IF NOT EXISTS department_id UUID REFERENCES public.departments(id);

ALTER TABLE public.daily_reports ADD COLUMN IF NOT EXISTS department_id UUID REFERENCES public.departments(id);
ALTER TABLE public.database_connections ADD COLUMN IF NOT EXISTS connection_method VARCHAR(50) DEFAULT 'direct';
ALTER TABLE public.database_connections ADD COLUMN IF NOT EXISTS connection_options JSONB;

-- =============================================================================
-- RLS POLICIES
-- =============================================================================

-- Enable RLS on all new tables
ALTER TABLE public.departments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.semantic_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.semantic_fields ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.field_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.validation_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.instance_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.combined_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.source_lineage_records ENABLE ROW LEVEL SECURITY;

-- Drop existing per-user isolation policies on modified tables
DROP POLICY IF EXISTS user_isolation_kpi_results ON public.kpi_results;
DROP POLICY IF EXISTS user_isolation_anomalies ON public.anomaly_records;
DROP POLICY IF EXISTS user_isolation_daily_reports ON public.daily_reports;

-- -----------------------------------------------------------------------------
-- DEPARTMENTS: Admins see all, managers/viewers see own
-- -----------------------------------------------------------------------------
CREATE POLICY departments_admin_all ON public.departments
    FOR ALL USING (
        EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
    );

CREATE POLICY departments_manager_select ON public.departments
    FOR SELECT USING (
        id IN (SELECT department_id FROM public.user_roles WHERE user_id = auth.uid())
    );

-- -----------------------------------------------------------------------------
-- USER ROLES: Admins see all, users see own
-- -----------------------------------------------------------------------------
CREATE POLICY user_roles_admin_all ON public.user_roles
    FOR ALL USING (
        EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
    );

CREATE POLICY user_roles_self_select ON public.user_roles
    FOR SELECT USING (user_id = auth.uid());

-- -----------------------------------------------------------------------------
-- SEMANTIC TEMPLATES: Everyone can read, admins can write
-- -----------------------------------------------------------------------------
CREATE POLICY semantic_templates_read_all ON public.semantic_templates
    FOR SELECT USING (true);

CREATE POLICY semantic_templates_admin_write ON public.semantic_templates
    FOR INSERT WITH CHECK (
        EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
    );

CREATE POLICY semantic_templates_admin_update ON public.semantic_templates
    FOR UPDATE USING (
        EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
    );

CREATE POLICY semantic_templates_admin_delete ON public.semantic_templates
    FOR DELETE USING (
        EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
    );

-- -----------------------------------------------------------------------------
-- SEMANTIC FIELDS: Everyone can read, admins can write
-- -----------------------------------------------------------------------------
CREATE POLICY semantic_fields_read_all ON public.semantic_fields
    FOR SELECT USING (true);

CREATE POLICY semantic_fields_admin_write ON public.semantic_fields
    FOR INSERT WITH CHECK (
        EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
    );

CREATE POLICY semantic_fields_admin_update ON public.semantic_fields
    FOR UPDATE USING (
        EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
    );

CREATE POLICY semantic_fields_admin_delete ON public.semantic_fields
    FOR DELETE USING (
        EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
    );

-- -----------------------------------------------------------------------------
-- FIELD MAPPINGS: Users manage own, admins see all
-- -----------------------------------------------------------------------------
CREATE POLICY field_mappings_self ON public.field_mappings
    FOR ALL USING (user_id = auth.uid());

CREATE POLICY field_mappings_admin_select ON public.field_mappings
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
    );

-- -----------------------------------------------------------------------------
-- VALIDATION LOGS: Users see own, admins see all
-- -----------------------------------------------------------------------------
CREATE POLICY validation_logs_self ON public.validation_logs
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY validation_logs_admin_all ON public.validation_logs
    FOR ALL USING (
        EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
    );

-- Managers can insert their own validation logs
CREATE POLICY validation_logs_insert ON public.validation_logs
    FOR INSERT WITH CHECK (user_id = auth.uid());

-- -----------------------------------------------------------------------------
-- INSTANCE TEMPLATES: Everyone can read, admins can write
-- -----------------------------------------------------------------------------
CREATE POLICY instance_templates_read_all ON public.instance_templates
    FOR SELECT USING (true);

CREATE POLICY instance_templates_admin_write ON public.instance_templates
    FOR INSERT WITH CHECK (
        EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
    );

CREATE POLICY instance_templates_admin_update ON public.instance_templates
    FOR UPDATE USING (
        EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
    );

CREATE POLICY instance_templates_admin_delete ON public.instance_templates
    FOR DELETE USING (
        EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
    );

-- -----------------------------------------------------------------------------
-- COMBINED REPORTS: Admins only
-- -----------------------------------------------------------------------------
CREATE POLICY combined_reports_admin ON public.combined_reports
    FOR ALL USING (
        EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
    );

-- -----------------------------------------------------------------------------
-- SOURCE LINEAGE RECORDS: Admins see all, department users see own department
-- -----------------------------------------------------------------------------
CREATE POLICY source_lineage_admin_all ON public.source_lineage_records
    FOR ALL USING (
        EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
    );

CREATE POLICY source_lineage_department_select ON public.source_lineage_records
    FOR SELECT USING (
        department_id IN (SELECT department_id FROM public.user_roles WHERE user_id = auth.uid())
        OR user_id = auth.uid()
    );

CREATE POLICY source_lineage_insert ON public.source_lineage_records
    FOR INSERT WITH CHECK (user_id = auth.uid());

-- -----------------------------------------------------------------------------
-- KPI RESULTS: Dept-aware policies replacing per-user isolation
-- -----------------------------------------------------------------------------
CREATE POLICY kpi_results_admin_all ON public.kpi_results
    FOR ALL USING (
        EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
    );

CREATE POLICY kpi_results_dept_select ON public.kpi_results
    FOR SELECT USING (
        department_id IN (SELECT department_id FROM public.user_roles WHERE user_id = auth.uid())
        OR user_id = auth.uid()  -- backward compat: users can still see their own
    );

CREATE POLICY kpi_results_dept_insert ON public.kpi_results
    FOR INSERT WITH CHECK (
        department_id IN (SELECT department_id FROM public.user_roles WHERE user_id = auth.uid())
        OR user_id = auth.uid()
    );

-- -----------------------------------------------------------------------------
-- ANOMALY RECORDS: Dept-aware policies
-- -----------------------------------------------------------------------------
CREATE POLICY anomaly_records_admin_all ON public.anomaly_records
    FOR ALL USING (
        EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
    );

CREATE POLICY anomaly_records_dept_select ON public.anomaly_records
    FOR SELECT USING (
        department_id IN (SELECT department_id FROM public.user_roles WHERE user_id = auth.uid())
        OR user_id = auth.uid()
    );

CREATE POLICY anomaly_records_dept_insert ON public.anomaly_records
    FOR INSERT WITH CHECK (
        department_id IN (SELECT department_id FROM public.user_roles WHERE user_id = auth.uid())
        OR user_id = auth.uid()
    );

-- -----------------------------------------------------------------------------
-- DAILY REPORTS: Dept-aware policies
-- -----------------------------------------------------------------------------
CREATE POLICY daily_reports_admin_all ON public.daily_reports
    FOR ALL USING (
        EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
    );

CREATE POLICY daily_reports_dept_select ON public.daily_reports
    FOR SELECT USING (
        department_id IN (SELECT department_id FROM public.user_roles WHERE user_id = auth.uid())
        OR user_id = auth.uid()
    );

CREATE POLICY daily_reports_dept_insert ON public.daily_reports
    FOR INSERT WITH CHECK (
        department_id IN (SELECT department_id FROM public.user_roles WHERE user_id = auth.uid())
        OR user_id = auth.uid()
    );

-- Re-create per-user policies for tables that were NOT modified (unchanged from original)
-- database_connections, notification_recipients, user_preferences, analysis_history
-- These keep their original user_isolation_* policies (already exist)

-- =============================================================================
-- SEED: Default department + default semantic template
-- =============================================================================

-- Create a default department for existing users
INSERT INTO public.departments (name, description)
VALUES ('General', 'Default department for existing users')
ON CONFLICT (name) DO NOTHING;

-- Create a default semantic template with standard KPI fields
INSERT INTO public.semantic_templates (name, description)
VALUES ('Standard Analytics KPIs', 'Default template with common business KPI fields')
ON CONFLICT DO NOTHING;

INSERT INTO public.instance_templates (name, config)
VALUES (
    'Standard Department Instance',
    '{
        "sync_default": {"frequency": "weekly", "time": "06:00"},
        "ai_tone": "insight-driven",
        "validation_rules": {"null_threshold": 0.1, "anomaly_threshold": 0.5, "critical_anomaly_zscore": 3.0},
        "email_recipients": [],
        "base_definitions": "STANDARD METRIC DEFINITIONS: Net Revenue = Gross Revenue minus Returns and Discounts. Customer Count = unique active accounts. Gross Margin = (Revenue - COGS) / Revenue.",
        "base_prompt": "You are a business analyst for {company_name}. Always use these definitions: {definitions}\\nTone: {user_tone}\\nFocus: {user_instruction}\\nData: {kpis}\\nAnomalies: {anomalies}"
    }'::jsonb
)
ON CONFLICT DO NOTHING;

-- Populate default template fields (only if template was just created)
DO $$
DECLARE
    tpl_id UUID;
BEGIN
    SELECT id INTO tpl_id FROM public.semantic_templates WHERE name = 'Standard Analytics KPIs' LIMIT 1;
    
    IF tpl_id IS NOT NULL THEN
        INSERT INTO public.semantic_fields (template_id, global_field_name, data_type, required, description)
        VALUES
            (tpl_id, 'net_revenue', 'currency', true, 'Net revenue after returns and discounts'),
            (tpl_id, 'customer_id', 'string', true, 'Unique customer identifier'),
            (tpl_id, 'report_date', 'date', true, 'Date of the reported metric'),
            (tpl_id, 'gross_margin', 'percent', false, 'Gross profit margin percentage'),
            (tpl_id, 'operating_cost', 'currency', false, 'Total operating expenses'),
            (tpl_id, 'inventory_value', 'currency', false, 'Current inventory valuation'),
            (tpl_id, 'support_tickets', 'integer', false, 'Number of open or resolved support tickets')
        ON CONFLICT DO NOTHING;
    END IF;
END $$;

-- Link default department to default template
UPDATE public.departments
SET
    template_id = COALESCE(
        template_id,
        (SELECT id FROM public.semantic_templates WHERE name = 'Standard Analytics KPIs' LIMIT 1)
    ),
    instance_template_id = COALESCE(
        instance_template_id,
        (SELECT id FROM public.instance_templates WHERE name = 'Standard Department Instance' LIMIT 1)
    )
WHERE name = 'General';

-- =============================================================================
-- BOOTSTRAP FUNCTION: Run once to make your first admin
-- Usage: SELECT bootstrap_admin('your-email@company.com');
-- =============================================================================
CREATE OR REPLACE FUNCTION bootstrap_admin(admin_email TEXT)
RETURNS TEXT AS $$
DECLARE
    admin_uid UUID;
    default_dept_id UUID;
BEGIN
    -- Find user by email
    SELECT id INTO admin_uid FROM auth.users WHERE email = admin_email LIMIT 1;
    
    IF admin_uid IS NULL THEN
        RETURN 'ERROR: No user found with email ' || admin_email || '. Please sign up first.';
    END IF;
    
    -- Get default department
    SELECT id INTO default_dept_id FROM public.departments WHERE name = 'General' LIMIT 1;
    
    -- Insert admin role (no department needed for admin)
    INSERT INTO public.user_roles (user_id, department_id, role)
    VALUES (admin_uid, NULL, 'admin')
    ON CONFLICT (user_id, department_id) DO UPDATE SET role = 'admin';
    
    RETURN 'SUCCESS: ' || admin_email || ' is now an admin.';
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- HELPER: Assign existing users to default department as managers
-- Run this ONCE after migration if you have existing users
-- =============================================================================
CREATE OR REPLACE FUNCTION assign_existing_users_to_default()
RETURNS TEXT AS $$
DECLARE
    default_dept_id UUID;
    user_rec RECORD;
    assign_count INTEGER := 0;
BEGIN
    SELECT id INTO default_dept_id FROM public.departments WHERE name = 'General' LIMIT 1;
    
    IF default_dept_id IS NULL THEN
        RETURN 'ERROR: Default department not found.';
    END IF;
    
    -- For each auth user that has no role entry yet
    FOR user_rec IN
        SELECT au.id FROM auth.users au
        WHERE NOT EXISTS (
            SELECT 1 FROM public.user_roles ur WHERE ur.user_id = au.id
        )
    LOOP
        INSERT INTO public.user_roles (user_id, department_id, role)
        VALUES (user_rec.id, default_dept_id, 'manager')
        ON CONFLICT DO NOTHING;
        
        assign_count := assign_count + 1;
    END LOOP;
    
    RETURN 'SUCCESS: Assigned ' || assign_count || ' existing users to General department as managers.';
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- MIGRATION COMPLETE
-- Next steps:
-- 1. Run: SELECT bootstrap_admin('your-email@company.com');
-- 2. Run: SELECT assign_existing_users_to_default();  (if you have existing users)
-- 3. Proceed to backend Phase 2 implementation
-- =============================================================================
