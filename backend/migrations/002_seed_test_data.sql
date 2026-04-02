-- =============================================================================
-- Seed Test Data
-- Run AFTER 001_governed_mesh.sql has been applied
-- Run in Supabase SQL Editor
-- =============================================================================

-- 1. Seed source tables with test data for ETL
INSERT INTO public.source_revenue (amount, transaction_date) VALUES
    (150000.00, NOW() - INTERVAL '7 days'),
    (145000.00, NOW() - INTERVAL '6 days'),
    (160000.00, NOW() - INTERVAL '5 days'),
    (155000.00, NOW() - INTERVAL '4 days'),
    (170000.00, NOW() - INTERVAL '3 days'),
    (165000.00, NOW() - INTERVAL '2 days'),
    (175000.00, NOW() - INTERVAL '1 day'),
    (180000.00, NOW());

INSERT INTO public.source_inventory (stock_value, recorded_at) VALUES
    (450000.00, NOW() - INTERVAL '7 days'),
    (455000.00, NOW() - INTERVAL '6 days'),
    (448000.00, NOW() - INTERVAL '5 days'),
    (460000.00, NOW() - INTERVAL '4 days'),
    (470000.00, NOW() - INTERVAL '3 days'),
    (465000.00, NOW() - INTERVAL '2 days'),
    (475000.00, NOW() - INTERVAL '1 day'),
    (480000.00, NOW());

INSERT INTO public.source_tickets (ticket_count, recorded_at) VALUES
    (85, NOW() - INTERVAL '7 days'),
    (92, NOW() - INTERVAL '6 days'),
    (78, NOW() - INTERVAL '5 days'),
    (110, NOW() - INTERVAL '4 days'),
    (95, NOW() - INTERVAL '3 days'),
    (88, NOW() - INTERVAL '2 days'),
    (102, NOW() - INTERVAL '1 day'),
    (97, NOW());

-- 2. Seed sample KPI results (so the dashboard has data to show)
-- Replace 'YOUR_USER_ID' with your actual auth user id after running bootstrap_admin
-- You can get it with: SELECT id FROM auth.users WHERE email = 'your-email@company.com';

-- 3. Seed sample validation logs
-- These will appear in the Dashboard validation warnings section
-- Uncomment and replace YOUR_USER_ID after bootstrapping:

/*
INSERT INTO public.validation_logs (user_id, department_id, check_type, status, message, details) VALUES
    ('YOUR_USER_ID', NULL, 'schema', 'pass', 'All required columns present', '{"columns_checked": 12}'),
    ('YOUR_USER_ID', NULL, 'null', 'warning', '3 null values found in source_revenue.amount', '{"null_count": 3, "table": "source_revenue"}'),
    ('YOUR_USER_ID', NULL, 'anomaly', 'pass', 'No anomalies detected in latest batch', '{"records_checked": 48}');
*/
