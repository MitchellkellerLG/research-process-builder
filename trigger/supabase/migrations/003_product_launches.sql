-- Product launches table
-- Tracks new products and features discovered via Product Hunt and news sources.
-- Dedup on source_url: same launch URL found by multiple pipeline runs = one row.

CREATE TABLE IF NOT EXISTS product_launches (
  id bigint generated always as identity primary key,
  discovered_date date not null,
  company_name text not null,
  company_domain text,
  product_name text not null,
  tagline text,
  launch_type text not null check (launch_type in ('new_product', 'new_feature')),
  is_ai boolean not null default false,
  score integer,
  rank integer,
  launch_count integer,
  maker_website text,
  ph_url text,
  source text not null check (source in ('product_hunt', 'news')),
  source_url text not null,
  source_name text,
  description text,
  categories text[],
  classification_reasoning text,
  linkedin_url text,
  on_product_hunt boolean default false,
  -- Clay enrichment fields
  employee_count integer,
  industry text,
  company_location text,
  company_description text,
  linkedin_followers integer,
  discovered_by_pipeline text,
  pipeline_version text default '1.0-ts',
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(source_url)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_pl_date ON product_launches(discovered_date DESC);
CREATE INDEX IF NOT EXISTS idx_pl_company ON product_launches(company_name);
CREATE INDEX IF NOT EXISTS idx_pl_source ON product_launches(source);
CREATE INDEX IF NOT EXISTS idx_pl_is_ai ON product_launches(is_ai) WHERE is_ai = true;

-- RLS
ALTER TABLE product_launches ENABLE ROW LEVEL SECURITY;
CREATE POLICY "anon_read" ON product_launches FOR SELECT TO anon USING (true);
CREATE POLICY "service_write" ON product_launches FOR ALL TO service_role USING (true);

-- Auto-update trigger (reuse update_updated_at() created in migration 001)
CREATE OR REPLACE TRIGGER set_updated_at
  BEFORE UPDATE ON product_launches
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
