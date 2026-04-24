-- Unified funding_discoveries table
-- Replaces per-round tables (series_a_discoveries, series_b_discoveries, series_c_discoveries)
-- Append-only: each pipeline discovery = new row. Same company from different articles = separate rows.
-- Dedup on source_url: same article found by multiple pipelines = one row, best score wins.

-- Rename existing table to preserve data
ALTER TABLE IF EXISTS series_a_discoveries RENAME TO series_a_discoveries_archive;

CREATE TABLE IF NOT EXISTS funding_discoveries (
  id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  company_name    text NOT NULL,
  company_domain  text,
  round_type      text NOT NULL,
  amount_raised   text,
  lead_investors  text,
  round_reasoning text,
  source_url      text NOT NULL,
  article_text    text,
  discovered_date date NOT NULL DEFAULT CURRENT_DATE,
  discovered_by_pipeline text NOT NULL,
  source_count    integer DEFAULT 1,
  score           real DEFAULT 0,
  pipeline_version text DEFAULT '1.0-ts',
  created_at      timestamptz DEFAULT now(),
  updated_at      timestamptz DEFAULT now(),

  CONSTRAINT uq_source_url UNIQUE (source_url)
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_fd_company_name ON funding_discoveries (company_name);
CREATE INDEX IF NOT EXISTS idx_fd_round_type ON funding_discoveries (round_type);
CREATE INDEX IF NOT EXISTS idx_fd_discovered_date ON funding_discoveries (discovered_date DESC);
CREATE INDEX IF NOT EXISTS idx_fd_score ON funding_discoveries (score DESC);
CREATE INDEX IF NOT EXISTS idx_fd_company_round ON funding_discoveries (company_name, round_type);

-- Auto-update updated_at on upsert
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_fd_updated_at
  BEFORE UPDATE ON funding_discoveries
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();

-- Migrate existing Series A data into unified table
INSERT INTO funding_discoveries (
  company_name, company_domain, round_type, amount_raised,
  lead_investors, round_reasoning, source_url, discovered_date,
  discovered_by_pipeline, source_count, score, pipeline_version, created_at
)
SELECT
  company_name, company_domain, round_type, amount_raised,
  lead_investors, round_reasoning, source_url, discovered_date,
  COALESCE(discovered_by, 'series_a_daily') AS discovered_by_pipeline,
  source_count, score, pipeline_version, COALESCE(created_at, now())
FROM series_a_discoveries_archive
ON CONFLICT (source_url) DO NOTHING;

-- Enable RLS
ALTER TABLE funding_discoveries ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anon read" ON funding_discoveries
  FOR SELECT USING (true);

CREATE POLICY "Allow service write" ON funding_discoveries
  FOR ALL USING (auth.role() = 'service_role');
