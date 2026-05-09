import { logger } from "@trigger.dev/sdk";
import { searchSerper } from "./serper.js";
import type { ProductLaunchRaw, ProductLaunchPipelineResult } from "./product-launch-types.js";

const OPENAI_API_KEY = process.env.OPENAI_API_KEY ?? "";
const SUPABASE_URL = (() => {
  const url = process.env.SUPABASE_PROJECT_URL ?? process.env.SUPABASE_URL ?? "";
  return url.startsWith("http") ? url : "";
})();
const SUPABASE_KEY =
  process.env.SUPABASE_KEY ??
  process.env.SUPABASE_SERVICE_ROLE_KEY ??
  process.env.SUPABASE_ANON_KEY ??
  "";

const FETCH_HEADERS = { "User-Agent": "Mozilla/5.0 (compatible; LeadGrow/1.0)" };
const TABLE = "product_launches";

// ---------------------------------------------------------------------------
// Serper supplement queries (Stage 1B)
// ---------------------------------------------------------------------------

interface SerperQuery {
  id: string;
  desc: string;
  query: string;
  num: number;
}

const SERPER_QUERIES: SerperQuery[] = [
  {
    id: "q_tc",
    desc: "TechCrunch launches",
    query: 'site:techcrunch.com "launches" OR "announces" OR "introduces" OR "debuts"',
    num: 20,
  },
  {
    id: "q_vb",
    desc: "VentureBeat launches",
    query: "site:venturebeat.com launches OR announces product",
    num: 15,
  },
  {
    id: "q_verge",
    desc: "The Verge launches",
    query: 'site:theverge.com "launches" OR "announces" product',
    num: 15,
  },
  {
    id: "q_wire",
    desc: "Press wire launches",
    query: '"now available" OR "product launch" site:businesswire.com OR site:prnewswire.com',
    num: 10,
  },
];

// ---------------------------------------------------------------------------
// HTML parsing utilities (regex-based, no cheerio)
// ---------------------------------------------------------------------------

// TC article URLs match: https://techcrunch.com/YYYY/MM/DD/slug/
const TC_ARTICLE_RE = /https:\/\/techcrunch\.com\/\d{4}\/\d{2}\/\d{2}\/[^/"]+\/?/g;

function parseTCArticles(html: string): Array<{ title: string; url: string }> {
  const results: Array<{ title: string; url: string }> = [];
  const seen = new Set<string>();

  // Find all <a href="https://techcrunch.com/YYYY/MM/DD/slug/">TITLE</a>
  // We scan for anchor tags and check the href pattern
  const anchorRe = /<a\s+[^>]*href="(https:\/\/techcrunch\.com\/\d{4}\/\d{2}\/\d{2}\/[^"]+)"[^>]*>([^<]{20,})<\/a>/gi;
  let match: RegExpExecArray | null;
  while ((match = anchorRe.exec(html)) !== null) {
    const url = match[1].split("?")[0].replace(/\/$/, "") + "/";
    const title = match[2].replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").trim();
    if (!seen.has(url) && title.length > 20) {
      seen.add(url);
      results.push({ url, title });
    }
  }

  return results;
}

// HN titleline spans: <span class="titleline"><a href="URL">TITLE</a>
function parseHNItems(html: string): Array<{ title: string; url: string }> {
  const results: Array<{ title: string; url: string }> = [];
  const titlelineRe = /<span[^>]+class="titleline"[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>([^<]+)<\/a>/gi;
  let match: RegExpExecArray | null;
  while ((match = titlelineRe.exec(html)) !== null) {
    const url = match[1].trim();
    const title = match[2].replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").trim();
    if (url && title) {
      results.push({ url, title });
    }
  }
  return results;
}

function domainFromUrl(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

// ---------------------------------------------------------------------------
// Stage 1A: Direct source fetches
// ---------------------------------------------------------------------------

async function fetchTCDatePage(dateStr: string): Promise<ProductLaunchRaw[]> {
  const [year, month, day] = dateStr.split("-");
  const url = `https://techcrunch.com/${year}/${month}/${day}/`;
  try {
    const resp = await fetch(url, {
      headers: FETCH_HEADERS,
      signal: AbortSignal.timeout(20_000),
    });
    if (!resp.ok) {
      logger.warn(`TC ${dateStr}: HTTP ${resp.status}`);
      return [];
    }
    const html = await resp.text();
    const articles = parseTCArticles(html);
    logger.info(`TC ${dateStr}: ${articles.length} articles`);
    return articles.map((a) => ({
      title: a.title,
      source_url: a.url,
      source_domain: "techcrunch.com",
      snippet: "",
      query_source: `tc_direct_${dateStr}`,
    }));
  } catch (err) {
    logger.warn(`TC ${dateStr}: ${err instanceof Error ? err.message : String(err)}`);
    return [];
  }
}

async function fetchHNShowPage(): Promise<ProductLaunchRaw[]> {
  const url = "https://news.ycombinator.com/show";
  try {
    const resp = await fetch(url, {
      headers: FETCH_HEADERS,
      signal: AbortSignal.timeout(20_000),
    });
    if (!resp.ok) {
      logger.warn(`HN Show: HTTP ${resp.status}`);
      return [];
    }
    const html = await resp.text();
    const items = parseHNItems(html);
    logger.info(`HN Show: ${items.length} items`);
    return items.map((it) => ({
      title: it.title,
      source_url: it.url,
      source_domain: domainFromUrl(it.url) || "news.ycombinator.com",
      snippet: "",
      query_source: "hn_show",
    }));
  } catch (err) {
    logger.warn(`HN Show: ${err instanceof Error ? err.message : String(err)}`);
    return [];
  }
}

async function fetchHNFrontPage(dateStr: string): Promise<ProductLaunchRaw[]> {
  const url = `https://news.ycombinator.com/front?day=${dateStr}`;
  try {
    const resp = await fetch(url, {
      headers: FETCH_HEADERS,
      signal: AbortSignal.timeout(20_000),
    });
    if (!resp.ok) {
      logger.warn(`HN front ${dateStr}: HTTP ${resp.status}`);
      return [];
    }
    const html = await resp.text();
    const items = parseHNItems(html);
    logger.info(`HN front ${dateStr}: ${items.length} items`);
    return items.map((it) => ({
      title: it.title,
      source_url: it.url,
      source_domain: domainFromUrl(it.url) || "news.ycombinator.com",
      snippet: "",
      query_source: `hn_front_${dateStr}`,
    }));
  } catch (err) {
    logger.warn(`HN front ${dateStr}: ${err instanceof Error ? err.message : String(err)}`);
    return [];
  }
}

async function runDirectFetches(dateStr: string): Promise<ProductLaunchRaw[]> {
  const yesterday = new Date(dateStr);
  yesterday.setDate(yesterday.getDate() - 1);
  const yesterdayStr = yesterday.toISOString().split("T")[0];

  const [tc1, tc2, hnShow, hnFront] = await Promise.all([
    fetchTCDatePage(dateStr),
    fetchTCDatePage(yesterdayStr),
    fetchHNShowPage(),
    fetchHNFrontPage(dateStr),
  ]);

  const all = [...tc1, ...tc2, ...hnShow, ...hnFront];
  logger.info(`Stage 1A direct fetches: ${all.length} raw items`);
  return all;
}

// ---------------------------------------------------------------------------
// Stage 1B: Serper supplement
// ---------------------------------------------------------------------------

async function runSerperQueries(tbs: string): Promise<ProductLaunchRaw[]> {
  const results = await Promise.allSettled(
    SERPER_QUERIES.map(async (q) => {
      const items = await searchSerper(q.query, q.num, tbs);
      logger.info(`Serper [${q.id}] ${q.desc}: ${items.length} results`);
      return items.map((item) => {
        const url = (item as { link?: string; title?: string; snippet?: string }).link ?? "";
        return {
          title: (item as { title?: string }).title ?? "",
          source_url: url,
          source_domain: domainFromUrl(url),
          snippet: ((item as { snippet?: string }).snippet ?? "").slice(0, 300),
          query_source: q.id,
        } as ProductLaunchRaw;
      });
    })
  );

  const all: ProductLaunchRaw[] = [];
  for (const r of results) {
    if (r.status === "fulfilled") all.push(...r.value);
  }
  logger.info(`Stage 1B Serper: ${all.length} raw items`);
  return all;
}

// ---------------------------------------------------------------------------
// Stage 2: Classify & filter via GPT-4o-mini
// ---------------------------------------------------------------------------

const CLASSIFY_SYSTEM = "You classify news articles as product launches. Output strict JSON only.";

const CLASSIFY_USER_TEMPLATE = `You are given a list of news article titles (and optional snippets) from tech press and Hacker News.

For each item, classify whether it is a PRODUCT LAUNCH or feature announcement.

KEEP (is_launch=true) if:
- Article is about a new product, new feature, new version, or open-source project released for the first time
- Company is real and identifiable
- "Show HN: ..." posts that introduce something new
- Company launches a new service, platform, or initiative (e.g. "Amazon opens logistics network" = new_product)
- Company launches a joint venture or new business unit focused on a product/service
- Company adds new AI tools or features to an existing product

DISCARD (is_launch=false) if:
- Product review (product existed before, this tests/reviews it)
- Funding announcement ONLY (Series A/B/C) -- funding pipeline handles those. But if an article is PRIMARILY about a new product/service and mentions funding secondarily, KEEP it.
- Job posting, acquisition (unless acquiring to launch new product), market analysis, opinion, roundup
- Listicle ("best AI tools 2026")
- Court cases, lawsuits, regulatory actions
- Earnings reports, stock news, market commentary

COMPANY NAME EXTRACTION RULES:
- For "Show HN: ProductName" titles: the company name is the product name or the maker. NEVER return "Show HN" as company_name.
- For "Show HN: ProductName -- description" titles: extract ProductName as both company_name and product_name.
- If title mentions a well-known company (Amazon, DoorDash, Anthropic, OpenAI, etc.), use that as company_name.
- If title says "X launches Y" or "X announces Y", X is the company, Y is the product.
- Never return "Unknown" as company_name -- extract the best guess from the title.

For each KEPT item, also classify:
- launch_type: "new_product" (brand new thing, new service, new platform, new JV) or "new_feature" (extends existing product)
- is_ai: true if the product is AI-powered or AI-related. Flag true if title or snippet contains ANY of:
  "AI", "artificial intelligence", "LLM", "GPT", "Claude", "neural", "embeddings", "fine-tun",
  "machine learning", "ML", "agentic", "MCP" (Model Context Protocol), "RAG", "vector",
  "diffusion", "generative", "copilot", "AI-powered", "AI-native", "AI-driven",
  "context for agents", "context layer for agents", "AI agents", "software agents",
  "dashboard for agents", "tool for agents", "built for agents".
  CRITICAL RULE: If the product NAME contains "Agents" or "Agent" (e.g. "Airbyte Agents",
  "AI Agents", "Agent SDK") it is ALWAYS is_ai=true -- software agents are AI systems.
  Also flag true if the product description implies AI automation (e.g. "turns notes into
  visual mind maps" = auto-generation by AI, "context for agents across data sources" = AI agent
  infrastructure). Flag false only if there is no AI signal at all.
- company_name: the company behind the product (see extraction rules above)
- product_name: the product, service, or feature being launched

Return STRICT JSON:
{
  "results": [
    {
      "idx": 1,
      "is_launch": true,
      "launch_type": "new_product",
      "is_ai": false,
      "company_name": "Acme Corp",
      "product_name": "Acme Widget"
    },
    {
      "idx": 2,
      "is_launch": false,
      "reason": "product review"
    }
  ]
}

Items:
{items}`;

const SKIP_URL_RE = /techcrunch\.com\/tag\/|techcrunch\.com\/author\/|techcrunch\.com\/category\/|\/page\/\d+/;

interface RawItemWithIdx extends ProductLaunchRaw {
  idx: number;
}

interface ClassifiedLaunch extends RawItemWithIdx {
  is_launch: true;
  launch_type: "new_product" | "new_feature";
  is_ai: boolean;
  company_name: string;
  product_name: string;
  idx: number;
}

async function classifyBatch(items: RawItemWithIdx[]): Promise<ClassifiedLaunch[]> {
  if (!OPENAI_API_KEY) {
    logger.warn("OPENAI_API_KEY missing -- classify skipped");
    return [];
  }

  const BATCH_SIZE = 30;
  const resultsMap = new Map<number, ClassifiedLaunch>();

  for (let start = 0; start < items.length; start += BATCH_SIZE) {
    const batch = items.slice(start, start + BATCH_SIZE);
    const lines = batch.map((it, localI) => {
      const title = (it.title ?? "").replace(/\n/g, " ").trim();
      const snippet = (it.snippet ?? "").replace(/\n/g, " ").trim().slice(0, 200);
      let line = `[${localI + 1}] TITLE: ${title}`;
      if (snippet) line += ` | SNIPPET: ${snippet}`;
      return line;
    });

    const userMsg = CLASSIFY_USER_TEMPLATE.replace("{items}", lines.join("\n"));

    try {
      const resp = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${OPENAI_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: "gpt-4o-mini",
          temperature: 0,
          response_format: { type: "json_object" },
          max_tokens: 3000,
          messages: [
            { role: "system", content: CLASSIFY_SYSTEM },
            { role: "user", content: userMsg },
          ],
        }),
        signal: AbortSignal.timeout(60_000),
      });

      if (!resp.ok) {
        logger.warn(`GPT classify batch failed: HTTP ${resp.status}`);
        continue;
      }

      const data = (await resp.json()) as { choices: { message: { content: string } }[] };
      const body = JSON.parse(data.choices[0]?.message?.content ?? "{}") as {
        results?: Array<{
          idx: number;
          is_launch: boolean;
          launch_type?: "new_product" | "new_feature";
          is_ai?: boolean;
          company_name?: string;
          product_name?: string;
        }>;
      };

      for (const r of body.results ?? []) {
        const localIdx = r.idx;
        if (!localIdx || localIdx < 1 || localIdx > batch.length) continue;
        if (!r.is_launch) continue;
        const globalIdx = batch[localIdx - 1].idx;
        const raw = batch[localIdx - 1];
        resultsMap.set(globalIdx, {
          ...raw,
          is_launch: true,
          launch_type: r.launch_type ?? "new_product",
          is_ai: r.is_ai ?? false,
          company_name: r.company_name ?? raw.source_domain,
          product_name: r.product_name ?? raw.title.slice(0, 60),
          idx: globalIdx,
        });
      }
    } catch (err) {
      logger.warn(`GPT classify batch error: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  return [...resultsMap.values()];
}

const SOURCE_RANK: Record<string, number> = {
  "techcrunch.com": 2,
  "venturebeat.com": 3,
  "theverge.com": 3,
  "businesswire.com": 4,
  "prnewswire.com": 4,
  "news.ycombinator.com": 5,
};

function normalizeKey(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]/g, "");
}

function sourceRank(item: ClassifiedLaunch): number {
  const domain = item.source_domain ?? "";
  if (domain in SOURCE_RANK) return SOURCE_RANK[domain];
  if (domain && !domain.includes("ycombinator")) return 1; // own domain = best
  return 6;
}

function dedupLaunches(launches: ClassifiedLaunch[]): ClassifiedLaunch[] {
  const groups = new Map<string, ClassifiedLaunch[]>();
  for (const item of launches) {
    const key = `${normalizeKey(item.company_name)}|${normalizeKey(item.product_name)}`;
    const group = groups.get(key) ?? [];
    group.push(item);
    groups.set(key, group);
  }

  const out: ClassifiedLaunch[] = [];
  for (const group of groups.values()) {
    const best = group.reduce((a, b) => (sourceRank(a) <= sourceRank(b) ? a : b));
    out.push(best);
  }
  return out;
}

async function runClassify(rawResults: ProductLaunchRaw[]): Promise<ClassifiedLaunch[]> {
  // Dedup by URL and strip pagination/tag pages
  const seenUrls = new Set<string>();
  const filtered: RawItemWithIdx[] = [];
  let skippedPages = 0;

  for (let i = 0; i < rawResults.length; i++) {
    const r = rawResults[i];
    const url = r.source_url ?? "";
    if (seenUrls.has(url)) continue;
    seenUrls.add(url);
    if (url && SKIP_URL_RE.test(url)) {
      skippedPages++;
      continue;
    }
    filtered.push({ ...r, idx: i });
  }

  logger.info(`Stage 2 input: ${rawResults.length} raw -> ${filtered.length} after dedup+filter (${skippedPages} pagination skipped)`);

  const launches = await classifyBatch(filtered);
  logger.info(`GPT classified ${launches.length} launches from ${filtered.length} items`);

  const deduped = dedupLaunches(launches);
  logger.info(`After company dedup: ${deduped.length} launches`);

  return deduped;
}

// ---------------------------------------------------------------------------
// Stage 3: Push to Supabase
// ---------------------------------------------------------------------------

interface ProductLaunchRow {
  discovered_date: string;
  company_name: string;
  product_name: string;
  launch_type: string;
  is_ai: boolean;
  source: "news";
  source_url: string;
  source_domain: string;
  query_source: string;
  snippet: string | null;
  pipeline_version: string;
}

function toRow(launch: ClassifiedLaunch, dateStr: string): ProductLaunchRow {
  return {
    discovered_date: dateStr,
    company_name: launch.company_name,
    product_name: launch.product_name,
    launch_type: launch.launch_type,
    is_ai: launch.is_ai,
    source: "news",
    source_url: launch.source_url,
    source_domain: launch.source_domain,
    query_source: launch.query_source,
    snippet: launch.snippet || null,
    pipeline_version: "1.0-ts",
  };
}

async function pushToSupabase(launches: ClassifiedLaunch[], dateStr: string): Promise<number> {
  if (!SUPABASE_URL || !SUPABASE_KEY) {
    logger.warn("Supabase not configured -- skipping push");
    return 0;
  }

  const h = {
    apikey: SUPABASE_KEY,
    Authorization: `Bearer ${SUPABASE_KEY}`,
    "Content-Type": "application/json",
    Prefer: "resolution=merge-duplicates",
  };

  let upserted = 0;
  for (const launch of launches) {
    const row = toRow(launch, dateStr);
    try {
      const resp = await fetch(`${SUPABASE_URL}/rest/v1/${TABLE}?on_conflict=source_url`, {
        method: "POST",
        headers: h,
        body: JSON.stringify([row]),
        signal: AbortSignal.timeout(15_000),
      });
      if (resp.ok) {
        upserted++;
      } else {
        const err = await resp.text().catch(() => "");
        logger.error(`Supabase upsert failed: ${resp.status} ${err.slice(0, 200)}`);
      }
    } catch (err) {
      logger.error(`Supabase upsert error: ${err instanceof Error ? err.message : String(err)}`);
    }
  }
  return upserted;
}

// ---------------------------------------------------------------------------
// Public entrypoint
// ---------------------------------------------------------------------------

export async function runNewsLaunchPipeline(options: {
  date: string;
  tbs?: string;
  skipSerper?: boolean;
  dryRun?: boolean;
}): Promise<ProductLaunchPipelineResult> {
  const { date, tbs = "qdr:d", skipSerper = false, dryRun = false } = options;
  const startMs = Date.now();

  logger.info("News launch pipeline starting", { date, tbs, skipSerper, dryRun });

  if (dryRun) {
    logger.info("[DRY] Stage 1A: TC today, TC yesterday, HN Show, HN front");
    if (!skipSerper) {
      for (const q of SERPER_QUERIES) {
        logger.info(`[DRY] Serper [${q.id}] ${q.desc} (num=${q.num})`);
      }
    }
    return {
      date,
      source: "news",
      launchCount: 0,
      stats: { rawResults: 0, afterClassify: 0, durationMs: Date.now() - startMs },
    };
  }

  // Stage 1A: Direct fetches
  const direct = await runDirectFetches(date);

  // Stage 1B: Serper supplement
  const serper = skipSerper ? [] : await runSerperQueries(tbs);

  const rawResults = [...direct, ...serper];
  logger.info(`Stage 1 total: ${rawResults.length} raw items (${direct.length} direct + ${serper.length} Serper)`);

  // Stage 2: Classify
  const launches = await runClassify(rawResults);

  // Stage 3: Push to Supabase
  const pushed = await pushToSupabase(launches, date);
  logger.info(`Stage 3: pushed ${pushed} rows to ${TABLE}`);

  const durationMs = Date.now() - startMs;
  logger.info("News launch pipeline complete", { launchCount: launches.length, pushed, durationMs });

  return {
    date,
    source: "news",
    launchCount: launches.length,
    stats: {
      rawResults: rawResults.length,
      afterClassify: launches.length,
      durationMs,
    },
  };
}
