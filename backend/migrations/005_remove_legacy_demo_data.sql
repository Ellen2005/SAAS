-- =============================================================================
-- Remove legacy demo analytics rows
--
-- Safe cleanup for deployments that previously generated the old demo
-- revenue/inventory/support-ticket fallback data. This does not remove rows
-- produced from connected database overview syncs because those carry a
-- source_id and use "Table rows: ..." KPI names.
-- =============================================================================

DELETE FROM public.kpi_results
WHERE source_id IS NULL
  AND kpi_name IN (
    'net_revenue',
    'inventory_value',
    'support_tickets',
    'Total Revenue',
    'Inventory Value',
    'Support Tickets'
  );

DELETE FROM public.anomaly_records
WHERE kpi_name IN (
    'net_revenue',
    'inventory_value',
    'support_tickets',
    'Total Revenue',
    'Inventory Value',
    'Support Tickets'
  )
  AND (
    context::text ILIKE '%same-weekday average%'
    OR context::text ILIKE '%190000%'
    OR context::text ILIKE '%150.00%'
  );

DELETE FROM public.daily_reports
WHERE narrative ILIKE '%Net Revenue is 190,000%'
  AND narrative ILIKE '%Inventory Value%'
  AND narrative ILIKE '%Support Tickets%';

DELETE FROM public.validation_logs
WHERE (
    message ILIKE '%inventory_value%'
    OR message ILIKE '%net_revenue%'
    OR message ILIKE '%support_tickets%'
    OR message ILIKE '%Inventory Value%'
    OR message ILIKE '%Total Revenue%'
    OR message ILIKE '%Support Tickets%'
  )
  AND message ILIKE '%Month-over-month change exceeds%';
