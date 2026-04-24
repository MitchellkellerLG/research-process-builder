import type { QueryDef, RawResult } from "./types.js";

const SERPER_API_KEY = process.env.SERPER_API_KEY ?? "";
const SERPER_URL = "https://google.serper.dev/search";

interface SerperOrganic {
  title?: string;
  link?: string;
  snippet?: string;
}

export async function searchSerper(
  query: string,
  num: number,
  tbs: string
): Promise<SerperOrganic[]> {
  const resp = await fetch(SERPER_URL, {
    method: "POST",
    headers: {
      "X-API-KEY": SERPER_API_KEY,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ q: query, num, tbs }),
  });

  if (!resp.ok) {
    throw new Error(`Serper ${resp.status}: ${await resp.text()}`);
  }

  const data = (await resp.json()) as { organic?: SerperOrganic[] };
  return data.organic ?? [];
}

export async function runSingleQuery(
  qdef: QueryDef,
  tbs: string
): Promise<{ queryId: string; desc: string; results: RawResult[]; error?: string }> {
  try {
    const items = await searchSerper(qdef.query, qdef.num, tbs);

    const results: RawResult[] = items.map((item) => {
      const link = item.link ?? "";
      const domain = link.includes("://") ? new URL(link).hostname : "";
      return {
        company_name_raw: "",
        amount_raw: "",
        round_type_raw: "",
        source_url: link,
        source_domain: domain,
        snippet: (item.snippet ?? "").slice(0, 300),
        title: item.title ?? "",
        query_source: qdef.id,
      };
    });

    return { queryId: qdef.id, desc: qdef.desc, results };
  } catch (e) {
    return {
      queryId: qdef.id,
      desc: qdef.desc,
      results: [],
      error: e instanceof Error ? e.message : String(e),
    };
  }
}

export async function runDiscovery(
  queries: QueryDef[],
  tbs: string
): Promise<RawResult[]> {
  const results = await Promise.all(
    queries.map((q) => runSingleQuery(q, tbs))
  );

  const allResults: RawResult[] = [];
  for (const r of results) {
    allResults.push(...r.results);
  }

  return allResults;
}
