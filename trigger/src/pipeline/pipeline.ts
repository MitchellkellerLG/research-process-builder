import { logger } from "@trigger.dev/sdk";
import type {
  Candidate,
  EnrichedRecord,
  PipelineConfig,
  PipelineResult,
  RoundConfig,
} from "./types.js";
import { runDiscovery } from "./serper.js";
import { fetchUrl } from "./spider.js";
import { extractWithOpenAI } from "./openai.js";
import { scoreAndFilter } from "./filters.js";
import { isSupabaseConfigured, checkTable, pushToSupabase } from "./supabase.js";
import { pushToWebhook } from "./webhook.js";
import { lookupDomainMultiSignal } from "./domain-lookup.js";

const SUSPECT_DOMAIN_PATTERNS = [
  /newswire|businesswire|prnewswire|einpresswire|globenewswire/i,
  /techcrunch|thesaasnews|finsmes|alleywatch|vcnewsdaily/i,
  /yahoo|reuters|bloomberg|forbes|fortune|cnbc|wsj/i,
  /linkedin|crunchbase|pitchbook|wikipedia|facebook/i,
  /eu-startups|tech\.eu|venturebeat|siliconangle/i,
  /finanzwire|therecursive|netinfluencer|biospace/i,
  /kitsapsun|cincinnati|bandt\.com/i,
  /googletagmanager|googleapis|gstatic|cloudfront|cloudflare/i,
  /wistia|cision|adobedtm|doubleclick|googlesyndication/i,
  /cdn\.|analytics\.|tracker\.|pixel\.|tag\./i,
  /fonts\.|static\.|assets\.|media\.|images\./i,
  /licdn|fbcdn|twimg|ytimg|akamai/i,
  /gravatar|wordpress\.com|wp\.com|disqus/i,
  /newrelic|segment\.io|mixpanel|hotjar|intercom/i,
  /yoast|schema\.org|w3\.org/i,
];

function isExtractedDomainSuspect(domain: string, sourceUrl: string): boolean {
  if (SUSPECT_DOMAIN_PATTERNS.some(p => p.test(domain))) return true;
  try {
    const sourceDomain = new URL(sourceUrl).hostname.replace(/^www\./, "");
    if (domain === sourceDomain) return true;
  } catch { /* ignore */ }
  return false;
}

function extractDomainFromArticle(articleText: string, companyName: string, sourceUrl: string): string | null {
  const sourceDomain = (() => {
    try { return new URL(sourceUrl).hostname.replace(/^www\./, ""); }
    catch { return ""; }
  })();

  const normCompany = companyName.toLowerCase().replace(/[^a-z0-9]/g, "");

  const patterns = [
    /(?:visit|learn more|more (?:info|information|at)|about us|website)\s*(?:at\s*)?[:.]?\s*(?:https?:\/\/)?(?:www\.)?([a-z0-9][-a-z0-9]*\.[a-z]{2,}(?:\.[a-z]{2,})?)/gi,
    /(?:https?:\/\/)?(?:www\.)?([a-z0-9][-a-z0-9]*\.(?:com|io|ai|co|dev|app|tech|health|bio))\b/gi,
    /[\w.+-]+@([a-z0-9][-a-z0-9]*\.[a-z]{2,}(?:\.[a-z]{2,})?)/gi,
  ];

  const candidates = new Map<string, number>();

  for (const pattern of patterns) {
    let match;
    while ((match = pattern.exec(articleText)) !== null) {
      const domain = match[1].toLowerCase().replace(/^www\./, "");
      if (isExtractedDomainSuspect(domain, sourceUrl)) continue;
      if (domain === sourceDomain) continue;
      if (domain.length < 4) continue;

      const normDomain = domain.split(".")[0].replace(/[^a-z0-9]/g, "");
      let score = candidates.get(domain) ?? 0;

      if (normDomain.includes(normCompany) || normCompany.includes(normDomain)) {
        score += 10;
      }
      score += 1;
      candidates.set(domain, score);
    }
  }

  if (candidates.size === 0) return null;

  const sorted = [...candidates.entries()].sort((a, b) => b[1] - a[1]);
  const [bestDomain, bestScore] = sorted[0];

  if (bestScore >= 10) return bestDomain;
  if (sorted.length === 1 && bestScore >= 2) return bestDomain;

  return null;
}

function extractContextClues(
  extracted: { round_reasoning?: string; lead_investors?: string } | null,
  articleTitle: string
): { industry?: string; productOrService?: string } {
  const clues: { industry?: string; productOrService?: string } = {};

  const reasoning = extracted?.round_reasoning ?? "";
  const combined = `${articleTitle} ${reasoning}`;

  const industryPatterns = [
    /\b(AI|artificial intelligence|machine learning|ML)\b/i,
    /\b(fintech|financial technology|payments|banking)\b/i,
    /\b(healthtech|healthcare|medical|biotech|pharma)\b/i,
    /\b(SaaS|software|platform|cloud)\b/i,
    /\b(cybersecurity|security|infosec)\b/i,
    /\b(e-commerce|ecommerce|retail|marketplace)\b/i,
    /\b(robotics|autonomous|automation)\b/i,
    /\b(climate|cleantech|energy|sustainability)\b/i,
    /\b(edtech|education|learning)\b/i,
    /\b(proptech|real estate)\b/i,
  ];

  for (const pattern of industryPatterns) {
    const match = combined.match(pattern);
    if (match) {
      clues.industry = match[0];
      break;
    }
  }

  return clues;
}

function buildEnrichedRecord(
  company: Candidate,
  extracted: { company_name?: string; company_domain?: string; amount_raised?: string; lead_investors?: string; round_reasoning?: string } | null,
  domain: string,
  sourceUrl: string,
  roundLabel: string,
  articleText: string | null,
  pipelineId: string
): EnrichedRecord {
  return {
    company_name: extracted?.company_name ?? company.company_name,
    company_domain: domain,
    amount_raised: extracted?.amount_raised ?? company.amount ?? "",
    round_type: company.round_type ?? roundLabel,
    source_url: sourceUrl,
    lead_investors: extracted?.lead_investors ?? "not_stated",
    round_reasoning: extracted?.round_reasoning ?? "not_stated",
    article_text: articleText,
    source_count: company.sources.length,
    score: company.best_score,
    discovered_by: [...new Set(company.sources.map((s) => s.query_source))].join(","),
    discovered_by_pipeline: pipelineId,
  };
}

function buildSkipEnrichRecord(company: Candidate, roundLabel: string, pipelineId: string): EnrichedRecord {
  return {
    company_name: company.company_name,
    company_domain: "not_enriched",
    amount_raised: company.amount ?? "",
    round_type: company.round_type ?? roundLabel,
    source_url: company.best_source_url,
    lead_investors: "not_enriched",
    round_reasoning: "not_enriched",
    article_text: null,
    source_count: company.sources.length,
    score: company.best_score,
    discovered_by: [...new Set(company.sources.map((s) => s.query_source))].join(","),
    discovered_by_pipeline: pipelineId,
  };
}

async function enrichCompanies(
  companies: Candidate[],
  maxEnrich: number,
  roundConfig: RoundConfig,
  pipelineId: string
): Promise<EnrichedRecord[]> {
  const enriched: EnrichedRecord[] = [];
  const toProcess = companies.slice(0, maxEnrich);

  for (let i = 0; i < toProcess.length; i++) {
    const company = toProcess[i];
    logger.info(`Enriching ${i + 1}/${toProcess.length}: ${company.company_name}`);

    let articleText: string | null = null;
    let sourceUrl = company.best_source_url;

    if (sourceUrl) {
      articleText = await fetchUrl(sourceUrl);
      if (!articleText) {
        for (const src of company.sources) {
          if (src.url !== sourceUrl) {
            articleText = await fetchUrl(src.url);
            if (articleText) {
              sourceUrl = src.url;
              break;
            }
          }
        }
      }
    }

    let extracted = null;
    if (articleText) {
      extracted = await extractWithOpenAI(
        articleText,
        company.company_name,
        company.amount ?? "",
        roundConfig
      );
      if (extracted?.company_name === roundConfig.notRoundSentinel) {
        logger.info(`Filtered post-extraction: ${company.company_name}`);
        continue;
      }
    }

    let domain = "not_found";
    let domainSource = "not_found";

    // Step 1: Extract domain directly from PR article text (cheapest, most reliable)
    if (articleText) {
      const articleDomain = extractDomainFromArticle(articleText, company.company_name, sourceUrl);
      if (articleDomain) {
        domain = articleDomain;
        domainSource = "article_text_extract";
        logger.info(`Domain from article text: ${domain}`);
      }
    }

    // Step 2: Trust GPT extraction if article text extraction missed it
    if (domain === "not_found") {
      const extractedDomain = extracted?.company_domain?.replace(/^www\./, "");
      if (extractedDomain && extractedDomain !== "not_stated" && !isExtractedDomainSuspect(extractedDomain, sourceUrl)) {
        domain = extractedDomain;
        domainSource = "gpt_extraction";
        logger.info(`Domain from GPT extraction: ${domain}`);
      }
    }

    // Step 3: Search-based lookup as last resort
    if (domain === "not_found") {
      const clues = extractContextClues(extracted, company.sources[0]?.title ?? "");
      logger.info(`Domain lookup with clues: ${JSON.stringify(clues)}`);
      const result = await lookupDomainMultiSignal(company.company_name, clues, sourceUrl);
      domain = result.domain;
      domainSource = result.source;
      logger.info(`Domain found: ${result.domain} (${result.confidence}, ${result.evidence})`);
    }

    logger.info(`Domain resolved: ${domain} via ${domainSource}`);

    const record = buildEnrichedRecord(company, extracted, domain, sourceUrl, roundConfig.roundLabel, articleText, pipelineId);
    enriched.push(record);

    logger.info(`Enriched: ${record.company_name} | ${record.company_domain} | ${record.amount_raised}`);
  }

  return enriched;
}

export async function runFundingPipeline(
  config: PipelineConfig
): Promise<PipelineResult> {
  const start = Date.now();
  const rc = config.roundConfig;

  logger.info(`${rc.roundLabel} pipeline starting`, {
    date: config.date,
    tbs: config.tbs,
    skipEnrich: config.skipEnrich,
    roundType: rc.roundType,
  });

  logger.info("Stage 1: Discovery");
  const rawResults = await runDiscovery(rc.queries, config.tbs);
  logger.info(`Stage 1 complete: ${rawResults.length} raw results`);

  logger.info("Stage 2: Score & Filter");
  const scored = scoreAndFilter(rawResults, rc);
  logger.info(
    `Stage 2 complete: ${scored.stats.company_count} companies (filtered ${scored.stats.filtered_count})`
  );

  let enriched: EnrichedRecord[];
  if (config.skipEnrich) {
    logger.info("Stage 3: Skipped (skipEnrich)");
    enriched = scored.companies.map((c) => buildSkipEnrichRecord(c, rc.roundLabel, config.pipelineId));
  } else {
    logger.info(`Stage 3: Enrich (max ${config.maxEnrich})`);
    enriched = await enrichCompanies(scored.companies, config.maxEnrich, rc, config.pipelineId);
    logger.info(`Stage 3 complete: ${enriched.length} enriched`);
  }

  logger.info("Stage 4: Output");

  if (isSupabaseConfigured()) {
    const tableExists = await checkTable(rc.supabaseTable);
    if (tableExists) {
      const upserted = await pushToSupabase(enriched, config.date, rc.supabaseTable);
      logger.info(`Supabase: ${upserted}/${enriched.length} upserted to ${rc.supabaseTable}`);
    } else {
      logger.warn(`Supabase table ${rc.supabaseTable} not found`);
    }
  }

  const webhookSent = await pushToWebhook(enriched, config.date, rc.webhookUrl, rc.webhookAuthToken);
  if (webhookSent > 0) {
    logger.info(`Webhook: ${webhookSent}/${enriched.length} sent`);
  }

  const durationMs = Date.now() - start;

  logger.info(`${rc.roundLabel} pipeline complete`, {
    companies: enriched.length,
    durationMs,
  });

  return {
    date: config.date,
    companyCount: enriched.length,
    companies: enriched,
    stats: {
      rawResults: rawResults.length,
      candidatesAfterFilter: scored.stats.company_count,
      enrichedCount: enriched.length,
      durationMs,
    },
  };
}
