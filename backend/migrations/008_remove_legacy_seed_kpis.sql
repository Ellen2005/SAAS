-- Migration 008: Remove legacy seed/demo KPI rows that have no source_id
-- These are leftover from the original seed data (net_revenue, inventory_value, support_tickets)
-- and do not belong to any real sync batch.

DELETE FROM kpi_results
WHERE source_id IS NULL
  AND kpi_name IN (
    'net_revenue', 'inventory_value', 'support_tickets',
    'Total Revenue', 'Inventory Value', 'Support Tickets'
  );

DELETE FROM anomaly_records
WHERE kpi_name IN (
    'net_revenue', 'inventory_value', 'support_tickets',
    'Total Revenue', 'Inventory Value', 'Support Tickets'
  );

-- Remove demo reports that contain the legacy narrative markers
DELETE FROM daily_reports
WHERE narrative LIKE '%Net Revenue is 190,000%'
   OR narrative LIKE '%Support Tickets is 150%';
