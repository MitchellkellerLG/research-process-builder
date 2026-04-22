import type { EnrichedRecord } from "./types.js";

const SUPABASE_URL = (() => {
  const url =
    process.env.SUPABASE_PROJECT_URL ?? process.env.SUPABASE_URL ?? "";
  return url.startsWith("http") ? url : "";
})();

const SUPABASE_KEY =
  process.env.SUPABASE_KEY ??
  process.env.SUPABASE_SERVICE_ROLE_KEY ??
  process.env.SUPABASE_ANON_KEY ??
  "";

function headers(prefer?: string): Record<string, string> {
  const h: Record<string, string> = {
    apikey: SUPABASE_KEY,
    Authorization: `Bearer ${SUPABASE_KEY}`,
    "Content-Type": "application/json",
  };
  if (prefer) h["Prefer"] = prefer;
  return h;
}

export function isSupabaseConfigured(): boolean {
  return Boolean(SUPABASE_URL && SUPABASE_KEY);
}

export async function checkTable(tableName: string): Promise<boolean> {
  if (!SUPABASE_URL) return false;
  try {
    const resp = await fetch(
      `${SUPABASE_URL}/rest/v1/${tableName}?limit=1`,
      { headers: headers(), signal: AbortSignal.timeout(10_000) }
    );
    return resp.status === 200;
  } catch {
    return false;
  }
}

function toRow(record: EnrichedRecord, dateStr: string) {
  return {
    discovered_date: dateStr,
    company_name: record.company_name,
    company_domain: record.company_domain,
    amount_raised: record.amount_raised,
    round_type: record.round_type,
    source_url: record.source_url,
    lead_investors: record.lead_investors,
    round_reasoning: record.round_reasoning,
    article_text: record.article_text,
    discovered_by_pipeline: record.discovered_by_pipeline,
    source_count: record.source_count,
    score: record.score,
    pipeline_version: "1.0-ts",
  };
}

export async function pushToSupabase(
  enriched: EnrichedRecord[],
  dateStr: string,
  tableName: string
): Promise<number> {
  if (!SUPABASE_URL || !SUPABASE_KEY) return 0;

  const seen = new Set<string>();
  const rows = enriched
    .map((r) => toRow(r, dateStr))
    .filter((row) => {
      if (seen.has(row.source_url)) return false;
      seen.add(row.source_url);
      return true;
    });

  let upserted = 0;
  for (const row of rows) {
    try {
      const existing = await fetch(
        `${SUPABASE_URL}/rest/v1/${tableName}?source_url=eq.${encodeURIComponent(row.source_url)}&select=score,discovered_by_pipeline`,
        { headers: headers(), signal: AbortSignal.timeout(10_000) }
      );

      if (existing.ok) {
        const data = await existing.json();
        if (Array.isArray(data) && data.length > 0) {
          const prev = data[0];
          if (row.score <= (prev.score ?? 0)) {
            const pipelines = new Set(
              (prev.discovered_by_pipeline ?? "").split(",").filter(Boolean)
            );
            pipelines.add(row.discovered_by_pipeline);
            await fetch(
              `${SUPABASE_URL}/rest/v1/${tableName}?source_url=eq.${encodeURIComponent(row.source_url)}`,
              {
                method: "PATCH",
                headers: headers(),
                body: JSON.stringify({ discovered_by_pipeline: [...pipelines].join(",") }),
                signal: AbortSignal.timeout(10_000),
              }
            );
            upserted++;
            continue;
          }
          row.discovered_by_pipeline = [
            ...new Set(
              [...(prev.discovered_by_pipeline ?? "").split(",").filter(Boolean), row.discovered_by_pipeline]
            ),
          ].join(",");
        }
      }

      const resp = await fetch(
        `${SUPABASE_URL}/rest/v1/${tableName}?on_conflict=source_url`,
        {
          method: "POST",
          headers: headers("resolution=merge-duplicates"),
          body: JSON.stringify([row]),
          signal: AbortSignal.timeout(15_000),
        }
      );
      if (resp.ok) upserted++;
    } catch {
      // continue with next row
    }
  }

  return upserted;
}
