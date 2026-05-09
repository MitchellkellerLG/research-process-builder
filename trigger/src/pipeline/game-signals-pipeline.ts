import { logger, wait } from "@trigger.dev/sdk";
import { searchSerper } from "./serper.js";

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
const CLAY_WEBHOOK_URL = process.env.CLAY_GAME_SIGNALS_WEBHOOK ?? "";
const CLAY_CALLBACK_URL = process.env.CLAY_GAME_SIGNALS_CALLBACK_URL ?? "https://clay-game-callback.leadgrowai.workers.dev";

const TABLE = "game_signals";

interface QueryDef {
  id: string;
  label: string;
  q: string;
  num: number;
}

export interface GameSignalRecord {
  signal_type: "game_announcement" | "studio_funding";
  developer: string | null;
  developer_domain: string | null;
  publisher: string | null;
  publisher_domain: string | null;
  game_title: string | null;
  funding_amount: string | null;
  genre: string | null;
  platform: string | null;
  article_date: string | null;
  source_url: string;
  summary: string | null;
  date_detected: string;
}

const SYSTEM_PROMPT = `You classify gaming search results as signal or noise, then extract structured data.

SIGNAL TYPES:
- "game_announcement": pre-release game reveal or announcement. Must be a brand-new original game not yet released.
  INCLUDE: action RPG, MMORPG, soulslike, open-world RPG, hack & slash, fighting, third-person story shooter, monster hunting genres
  EXCLUDE: DLC, expansions, patches, reviews of released games, forum speculation with no source, sports games, puzzle/casual mobile, remasters, remakes, ports, definitive editions, anniversary editions, enhanced editions, collections of existing games
- "studio_funding": a game studio raised a funding round
  INCLUDE: any disclosed investment in a game development studio
  EXCLUDE: sports betting companies (FanDuel, DraftKings), game retailers (GameStop), government grants, crowdfunding under $500K

If neither applies: "noise"

For signals, extract:
- developer: the studio making the game (game_announcement) or receiving funding (studio_funding)
- developer_domain: developer's website if mentioned (e.g. "rebelwolves.com"), else null
- publisher: publishing company if different from developer, else null
- publisher_domain: publisher's website if mentioned, else null
- game_title: game name for game_announcement, null or "undisclosed" for studio_funding with no named game
- funding_amount: e.g. "$5.7M", "€2.1M", null for game_announcement
- genre: one of: Action RPG | MMORPG | Soulslike | Open-World | Hack & Slash | Fighting | Third-Person Shooter | Monster Hunting | Other | null
- platform: comma-separated from: PC, PS5, Xbox Series X, Switch, Mobile — null if not stated
- article_date: publication date in YYYY-MM-DD if detectable, else null
- summary: 1-2 sentences. Be specific.

Return JSON only:
{"classification":"game_announcement"|"studio_funding"|"noise","developer":string|null,"developer_domain":string|null,"publisher":string|null,"publisher_domain":string|null,"game_title":string|null,"funding_amount":string|null,"genre":string|null,"platform":string|null,"article_date":string|null,"summary":string|null}`;

const STREAM_A_IDS = new Set(["A1","A2","A3","A4","A5","A6","A7","A8","A9"]);

const QUERIES: QueryDef[] = [
  { id: "A1", label: "Gaming press — reveal/announce", q: '"game reveal" OR "new game announced" OR "reveal trailer" site:ign.com OR site:eurogamer.net OR site:gamespot.com OR site:gamerant.com', num: 20 },
  { id: "A2", label: "VGC + GI.biz — reveal/announce", q: '"game reveal" OR "game announced" site:videogameschronicle.com OR site:gamesindustry.biz', num: 20 },
  { id: "A3", label: "Animation-heavy genres announced", q: '"action RPG" OR "open world RPG" OR "MMORPG" OR "soulslike" game announced OR reveal 2026', num: 20 },
  { id: "A4", label: "Major franchise signals", q: '"God of War" OR "Monster Hunter" OR "Witcher" OR "Cyberpunk" OR "GTA" sequel OR "new game" OR announced', num: 20 },
  { id: "A5", label: "Press wire — video game announce", q: 'site:businesswire.com OR site:prnewswire.com "video game" announce OR reveal OR "new title"', num: 15 },
  { id: "A6", label: "Gaming events — reveals", q: '"Summer Game Fest" OR "State of Play" OR "Xbox Showcase" OR "Nintendo Direct" reveal game', num: 20 },
  { id: "A7", label: "AAA engine signal", q: '"Unreal Engine 5" OR "RE Engine" OR "Decima Engine" game announced OR reveal OR trailer', num: 20 },
  { id: "A8", label: "Gematsu — Japanese studio announcements", q: 'site:gematsu.com announced OR reveal OR trailer 2026', num: 20 },
  { id: "A9", label: "Polygon — game reveals", q: 'site:polygon.com "announced" OR "reveal trailer" game 2026', num: 20 },
  { id: "B1", label: "Broad game studio funding", q: '"game studio" raises OR raised OR funding OR investment million 2026', num: 20 },
  { id: "B2", label: "Game studio round types", q: '"game developer" OR "game development studio" "Series A" OR "Series B" OR seed OR funding', num: 20 },
  { id: "B3", label: "Vertical press — GI.biz + GamesBeat", q: "site:gamesindustry.biz OR site:venturebeat.com funding investment raised game studio", num: 20 },
  { id: "B4", label: "Press wire — game studio funding", q: 'site:businesswire.com OR site:prnewswire.com "game studio" OR "game developer" OR "gaming company" raises OR funding OR investment', num: 15 },
  { id: "B5", label: "Pocket Gamer Biz — mobile gaming funding", q: "site:pocketgamer.biz funding investment raised million", num: 10 },
  { id: "B6", label: "Crunchbase News — gaming funding", q: 'site:crunchbase.com/news "game" OR "gaming" funding 2026', num: 10 },
  { id: "B7", label: "Console/PC game studio raises — broad", q: '"video game" OR "console game" studio raises OR secured OR "closed a" million funding', num: 20 },
];

async function classifyResult(
  title: string,
  url: string,
  snippet: string,
  queryId: string
): Promise<GameSignalRecord | null> {
  if (!OPENAI_API_KEY) throw new Error("OPENAI_API_KEY not set");

  const streamContext = STREAM_A_IDS.has(queryId)
    ? "Stream A (game announcements)"
    : "Stream B (studio funding)";

  const resp = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: { Authorization: `Bearer ${OPENAI_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "gpt-4o-mini",
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user", content: `Title: ${title}\nURL: ${url}\nSnippet: ${snippet}\nQuery context: ${streamContext}` },
      ],
      response_format: { type: "json_object" },
      temperature: 0,
    }),
    signal: AbortSignal.timeout(30_000),
  });

  if (!resp.ok) throw new Error(`OpenAI ${resp.status}: ${await resp.text()}`);

  const data = await resp.json() as { choices: { message: { content: string } }[] };
  const result = JSON.parse(data.choices[0].message.content);

  if (result.classification === "noise") return null;

  const today = new Date().toISOString().split("T")[0];
  return {
    signal_type: result.classification,
    developer: result.developer ?? null,
    developer_domain: result.developer_domain ?? null,
    publisher: result.publisher ?? null,
    publisher_domain: result.publisher_domain ?? null,
    game_title: result.game_title ?? null,
    funding_amount: result.funding_amount ?? null,
    genre: result.genre ?? null,
    platform: result.platform ?? null,
    article_date: result.article_date ?? null,
    source_url: url,
    summary: (result.summary ?? "").slice(0, 500),
    date_detected: today,
  };
}

function dedup(signals: GameSignalRecord[]): GameSignalRecord[] {
  const seenUrls = new Set<string>();
  const seenEntities = new Set<string>();
  const out: GameSignalRecord[] = [];
  for (const s of signals) {
    if (seenUrls.has(s.source_url)) continue;
    seenUrls.add(s.source_url);

    let key: string | null = null;
    if (s.signal_type === "game_announcement") {
      const t = (s.game_title ?? "").toLowerCase().trim();
      key = t && t !== "undisclosed" ? t : null;
    } else {
      const d = (s.developer ?? "").toLowerCase();
      key = d ? `${d}|${s.funding_amount ?? ""}` : null;
    }

    if (key && seenEntities.has(key)) continue;
    if (key) seenEntities.add(key);
    out.push(s);
  }
  return out;
}

async function seenRecently(signal: GameSignalRecord, lookbackDays = 30): Promise<boolean> {
  if (!SUPABASE_URL || !SUPABASE_KEY) return false;

  const since = new Date();
  since.setDate(since.getDate() - lookbackDays);
  const sinceStr = since.toISOString().split("T")[0];

  const h = { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}` };

  try {
    let url: string;
    if (signal.signal_type === "game_announcement" && signal.game_title && signal.game_title !== "undisclosed") {
      url = `${SUPABASE_URL}/rest/v1/${TABLE}?signal_type=eq.game_announcement&game_title=eq.${encodeURIComponent(signal.game_title)}&date_detected=gte.${sinceStr}&select=id&limit=1`;
    } else if (signal.signal_type === "studio_funding" && signal.developer && signal.funding_amount) {
      url = `${SUPABASE_URL}/rest/v1/${TABLE}?signal_type=eq.studio_funding&developer=eq.${encodeURIComponent(signal.developer)}&funding_amount=eq.${encodeURIComponent(signal.funding_amount)}&date_detected=gte.${sinceStr}&select=id&limit=1`;
    } else {
      return false;
    }
    const resp = await fetch(url, { headers: h, signal: AbortSignal.timeout(10_000) });
    if (!resp.ok) return false;
    const rows = await resp.json() as unknown[];
    return rows.length > 0;
  } catch {
    return false;
  }
}

async function pushToSupabase(signals: GameSignalRecord[]): Promise<number> {
  if (!SUPABASE_URL || !SUPABASE_KEY) return 0;

  const h = {
    apikey: SUPABASE_KEY,
    Authorization: `Bearer ${SUPABASE_KEY}`,
    "Content-Type": "application/json",
    Prefer: "resolution=merge-duplicates",
  };

  let upserted = 0;
  for (const row of signals) {
    const seen = await seenRecently(row);
    if (seen) {
      logger.info(`Cross-run dedup skip: ${row.game_title ?? row.developer}`);
      continue;
    }
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

async function pushToClay(signals: GameSignalRecord[]): Promise<number> {
  if (!CLAY_WEBHOOK_URL) return 0;

  const enrichable = signals.filter((s) => s.developer);
  if (enrichable.length === 0) return 0;

  // Create all tokens and fire all webhooks in parallel
  const pending = await Promise.all(
    enrichable.map(async (s) => {
      try {
        const token = await wait.createToken({ timeout: "5m" });
        const resp = await fetch(CLAY_WEBHOOK_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            _callback_id: token.id,
            _callback_url: `${CLAY_CALLBACK_URL}/${token.id}`,
            "Company Name": s.developer,
            "Company Website": s.developer_domain ?? "",
            signal_type: s.signal_type,
            game_title: s.game_title ?? "",
            source_url: s.source_url,
            date_detected: s.date_detected,
          }),
          signal: AbortSignal.timeout(10_000),
        });
        if (!resp.ok) {
          logger.warn(`Clay push failed for ${s.developer}: ${resp.status}`);
          return null;
        }
        return { signal: s, token };
      } catch (e) {
        logger.warn(`Clay push error for ${s.developer}: ${e instanceof Error ? e.message : String(e)}`);
        return null;
      }
    })
  );

  const fired = pending.filter(Boolean).length;
  logger.info(`Clay: fired ${fired}/${enrichable.length} webhooks — waiting for all callbacks in parallel`);

  // Wait for all tokens simultaneously
  await Promise.all(
    pending.map(async (p) => {
      if (!p) return;
      const result = await wait.forToken<Record<string, unknown>>(p.token).catch(() => null);
      if (result?.ok) {
        logger.info(`Clay enrichment received: ${p.signal.developer}`, { enrichment: result.output });
      } else {
        logger.warn(`Clay enrichment timeout: ${p.signal.developer}`);
      }
    })
  );

  return fired;
}

export interface GameSignalsPipelineResult {
  date: string;
  signalCount: number;
  announcements: number;
  fundings: number;
  rawResults: number;
  durationMs: number;
}

export async function runGameSignalsPipeline(opts: {
  tbs: string;
  date: string;
  dryRun: boolean;
}): Promise<GameSignalsPipelineResult> {
  const start = Date.now();
  logger.info("Game signals pipeline starting", opts);

  // Stage 1: search
  logger.info("Stage 1: Discovery");
  const rawItems: { queryId: string; title: string; url: string; snippet: string }[] = [];
  await Promise.all(
    QUERIES.map(async (q) => {
      try {
        const items = await searchSerper(q.q, q.num, opts.tbs);
        for (const item of items) {
          if (item.link) {
            rawItems.push({ queryId: q.id, title: item.title ?? "", url: item.link, snippet: (item.snippet ?? "").slice(0, 300) });
          }
        }
      } catch (e) {
        logger.warn(`Query ${q.id} failed: ${e instanceof Error ? e.message : String(e)}`);
      }
    })
  );

  // URL dedup before GPT calls
  const seenUrls = new Set<string>();
  const unique = rawItems.filter((r) => {
    if (seenUrls.has(r.url)) return false;
    seenUrls.add(r.url);
    return true;
  });
  logger.info(`Stage 1 complete: ${rawItems.length} raw → ${unique.length} unique`);

  // Stage 2: classify
  logger.info("Stage 2: Classify");
  const signals: GameSignalRecord[] = [];
  let noiseCount = 0;

  // Sequential to avoid OpenAI rate limits
  for (const item of unique) {
    try {
      const signal = await classifyResult(item.title, item.url, item.snippet, item.queryId);
      if (signal) {
        signals.push(signal);
      } else {
        noiseCount++;
      }
    } catch (e) {
      logger.warn(`Classify error for ${item.url}: ${e instanceof Error ? e.message : String(e)}`);
      noiseCount++;
    }
  }

  const deduped = dedup(signals);
  const announcements = deduped.filter((s) => s.signal_type === "game_announcement").length;
  const fundings = deduped.filter((s) => s.signal_type === "studio_funding").length;
  logger.info(`Stage 2 complete: ${deduped.length} signals (${announcements} announces, ${fundings} fundings), ${noiseCount} noise`);

  // Stage 3: output
  if (opts.dryRun) {
    logger.info("Dry run — skipping Supabase + Clay");
  } else {
    const upserted = await pushToSupabase(deduped);
    logger.info(`Supabase: ${upserted}/${deduped.length} upserted to ${TABLE}`);
    const clayFired = await pushToClay(deduped);
    logger.info(`Clay: ${clayFired} developer enrichment requests fired`);
  }

  return {
    date: opts.date,
    signalCount: deduped.length,
    announcements,
    fundings,
    rawResults: unique.length,
    durationMs: Date.now() - start,
  };
}
