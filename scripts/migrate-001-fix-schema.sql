-- Migration 001: Fix schema defaults and constraints
-- Run this against live Supabase via SQL Editor

-- 1. Fix round_type default (was 'Series A', should be 'Unknown')
ALTER TABLE funding_discoveries ALTER COLUMN round_type SET DEFAULT 'Unknown';

-- 2. Add unique constraint on source_url (required for TS pipeline on_conflict=source_url)
-- First check for duplicate source_urls that would block constraint creation
-- SELECT source_url, count(*) FROM funding_discoveries GROUP BY source_url HAVING count(*) > 1;
ALTER TABLE funding_discoveries ADD CONSTRAINT funding_discoveries_source_url_key UNIQUE (source_url);

-- 3. Fix existing rows that got wrong round_type from old default
-- These Python-inserted rows have round_type='Series A' but might be other rounds
-- Only update rows where round_type was clearly set by the default (pipeline_version='1.0')
-- Manual audit recommended before running:
-- SELECT company_name, round_type, amount_raised, source_url FROM funding_discoveries WHERE pipeline_version = '1.0';

-- 4. Update pipeline_version default for clarity
ALTER TABLE funding_discoveries ALTER COLUMN pipeline_version SET DEFAULT '1.0-ts';
