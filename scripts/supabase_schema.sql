-- Funding Discoveries — Unified Supabase Schema
-- All funding sources (Serper pipeline, raisingfi, future) share this table.
-- Filter by round_type, discovered_by, or discovered_by_pipeline for source-specific views.

create table if not exists funding_discoveries (
  id bigint generated always as identity primary key,
  discovered_date date not null,
  company_name text,
  company_domain text,
  amount_raised text,
  round_type text default 'Unknown',
  source_url text,
  lead_investors text,
  round_reasoning text,
  article_text text,
  discovered_by text,
  discovered_by_pipeline text,
  industry text,
  location text,
  source_count integer default 1,
  score integer default 0,
  pipeline_version text default '1.0',
  created_at timestamptz default now(),
  updated_at timestamptz default now(),

  unique (company_name, discovered_date),
  unique (source_url)
);

create index if not exists idx_funding_date on funding_discoveries (discovered_date desc);
create index if not exists idx_funding_company on funding_discoveries (company_name);
create index if not exists idx_funding_domain on funding_discoveries (company_domain);
create index if not exists idx_funding_round_type on funding_discoveries (round_type);
create index if not exists idx_funding_discovered_by on funding_discoveries (discovered_by_pipeline);
