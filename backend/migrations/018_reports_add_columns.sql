-- Migration 018: Add missing columns to reports table
-- report_id: stable external identifier used by professional report service
-- excel_path: path to generated Excel file
-- updated_at: for narrative edit tracking
BEGIN;

ALTER TABLE reports
    ADD COLUMN IF NOT EXISTS report_id TEXT,
    ADD COLUMN IF NOT EXISTS excel_path TEXT,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

-- Backfill report_id from id for existing rows
UPDATE reports SET report_id = id::TEXT WHERE report_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_reports_report_id ON reports(report_id);

COMMIT;
