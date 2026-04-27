import type { RoundConfig } from "./types.js";

function buildExtractionPrompt(roundLabel: string, sentinel: string): string {
  return `Extract ${roundLabel} funding data from this article.

Company hint: {{companyHint}}
Amount hint: {{amountHint}}

Article:
{{articleText}}

Return exactly this JSON:
{"company_name": "...", "company_domain": "...", "amount_raised": "...", "lead_investors": "...", "round_reasoning": "...", "industry": "...", "location": "..."}

Rules:
- company_name = the company that RAISED money (NOT the investor/VC)
- company_domain = their official website domain (e.g. mosaic.pe, zenskar.com). Look carefully in: the "About [Company]" section near the bottom, "Learn more at" or "visit" links, contact email addresses (press@mosaic.pe → mosaic.pe), and any inline URLs. PR articles almost always contain this. Do NOT return the PR wire domain (prnewswire.com, businesswire.com). "not_stated" ONLY if truly absent after checking all sections
- amount_raised = exact amount with currency symbol (e.g. "$15M", "EUR10M", "KRW 90B")
- lead_investors = who led the round, comma-separated. "not_stated" if unknown
- round_reasoning = why they raised / what funds are for, 1-2 sentences. "not_stated" if unknown
- industry = primary industry/vertical (e.g. "AI", "fintech", "healthtech", "cybersecurity", "SaaS"). "not_stated" if unclear
- location = company HQ city and country (e.g. "San Francisco, US", "London, UK", "Tel Aviv, Israel"). "not_stated" if unknown
- If this is NOT actually a ${roundLabel} funding announcement, set company_name to "${sentinel}"`;
}

export const SERIES_A_CONFIG: RoundConfig = {
  roundType: "series_a",
  roundLabel: "Series A",
  roundPattern: /\bSeries\s+A\b/i,
  nonRoundPattern:
    /\b(Series\s+[B-Z]|Pre-Seed|pre-seed|Pre-IPO|IPO|Debt|Grant|acquisition|acquires|acquired|merger|SPAC|refinanc)\b/i,
  softNonPattern: /\b(Seed|Growth)\b/i,
  noisePatterns:
    /(?:Series A activity|weekly recap|funding recap|venture market|job search|quarterly.*dividend|financial results|earnings|stock|preferred stock|broadband|announces common|\bTag\b\s*[-|]|\bTag\s*$)/i,
  notRoundSentinel: "NOT_SERIES_A",
  queries: [
    { id: "q3", query: "site:thesaasnews.com Series A", num: 30, desc: "TheSaaSNews" },
    { id: "q4", query: "site:finsmes.com Series A", num: 30, desc: "FinSMEs" },
    { id: "q5", query: "site:alleywatch.com funding report", num: 10, desc: "AlleyWatch" },
    { id: "q9", query: "site:vcnewsdaily.com Series A", num: 10, desc: "VCNewsDaily" },
    { id: "q10", query: "site:infotechlead.com venture capital funding", num: 10, desc: "InfotechLead" },
    { id: "q1", query: '"Series A" raises OR raised OR funding OR round million', num: 30, desc: "broad sweep" },
    { id: "q2", query: '"Series A" announces OR secures OR closes OR completes funding', num: 20, desc: "announcement language" },
    { id: "q6", query: '"Series A" site:businesswire.com OR site:prnewswire.com OR site:einpresswire.com', num: 10, desc: "press wires" },
    { id: "q7", query: '"led the round" OR "led the Series A" OR "led a" Series A investment startup', num: 20, desc: "VC language" },
    { id: "q8", query: '"Series A" startup funding site:eu-startups.com OR site:tech.eu OR site:techround.co.uk', num: 10, desc: "European" },
  ],
  supabaseTable: "funding_discoveries",
  webhookUrl:
    "https://api.clay.com/v3/sources/webhook/pull-in-data-from-a-webhook-d1b53ce2-fe64-40e4-a86c-faef265c5a63",
  webhookAuthToken: "0be318b702699f40b68f",
  extractionPrompt: buildExtractionPrompt("Series A", "NOT_SERIES_A"),
};

export const SERIES_B_CONFIG: RoundConfig = {
  roundType: "series_b",
  roundLabel: "Series B",
  roundPattern: /\bSeries\s+B\b/i,
  nonRoundPattern:
    /\b(Series\s+[CDEFG-Z]|Series\s+A(?!\s*-?\s*B)|Pre-Seed|pre-seed|Seed\s+round|IPO|Debt|Grant|acquisition|acquires|acquired|merger|SPAC|refinanc)\b/i,
  softNonPattern: /\b(Pre-Series|Bridge)\b/i,
  noisePatterns:
    /(?:Series B activity|weekly recap|funding recap|venture market|job search|quarterly.*dividend|financial results|earnings|stock|preferred stock|broadband|announces common|\bTag\b\s*[-|]|\bTag\s*$)/i,
  notRoundSentinel: "NOT_SERIES_B",
  queries: [
    { id: "bq1", query: '"Series B" raises OR raised OR funding OR round million', num: 30, desc: "broad sweep" },
    { id: "bq2", query: '"Series B" announces OR secures OR closes OR completes funding', num: 20, desc: "announcement language" },
    { id: "bq3", query: "site:thesaasnews.com Series B", num: 30, desc: "TheSaaSNews" },
    { id: "bq4", query: "site:finsmes.com Series B", num: 30, desc: "FinSMEs" },
    { id: "bq5", query: '"Series B" site:businesswire.com OR site:prnewswire.com OR site:einpresswire.com', num: 10, desc: "press wires" },
    { id: "bq6", query: '"Series B" growth round OR expansion capital startup', num: 20, desc: "growth language" },
    { id: "bq7", query: '"led the Series B" OR "led a Series B" investment', num: 20, desc: "VC language" },
    { id: "bq8", query: '"Series B" startup funding site:eu-startups.com OR site:tech.eu OR site:techround.co.uk', num: 10, desc: "European" },
  ],
  supabaseTable: "funding_discoveries",
  webhookUrl:
    "https://api.clay.com/v3/sources/webhook/pull-in-data-from-a-webhook-d1b53ce2-fe64-40e4-a86c-faef265c5a63",
  webhookAuthToken: "0be318b702699f40b68f",
  extractionPrompt: buildExtractionPrompt("Series B", "NOT_SERIES_B"),
};

export const SERIES_C_CONFIG: RoundConfig = {
  roundType: "series_c",
  roundLabel: "Series C",
  roundPattern: /\bSeries\s+C\b/i,
  nonRoundPattern:
    /\b(Series\s+[DEFG-Z]|Series\s+[AB](?!\s*-?\s*C)|Pre-Seed|pre-seed|Seed\s+round|IPO|Debt|Grant|acquisition|acquires|acquired|merger|SPAC|refinanc)\b/i,
  softNonPattern: /\b(Pre-Series|Bridge)\b/i,
  noisePatterns:
    /(?:Series C activity|weekly recap|funding recap|venture market|job search|quarterly.*dividend|financial results|earnings|stock|preferred stock|broadband|announces common|\bTag\b\s*[-|]|\bTag\s*$)/i,
  notRoundSentinel: "NOT_SERIES_C",
  queries: [
    { id: "cq1", query: '"Series C" raises OR raised OR funding OR round million', num: 30, desc: "broad sweep" },
    { id: "cq2", query: '"Series C" announces OR secures OR closes OR completes funding', num: 20, desc: "announcement language" },
    { id: "cq3", query: "site:thesaasnews.com Series C", num: 30, desc: "TheSaaSNews" },
    { id: "cq4", query: "site:finsmes.com Series C", num: 30, desc: "FinSMEs" },
    { id: "cq5", query: '"Series C" site:businesswire.com OR site:prnewswire.com OR site:einpresswire.com', num: 10, desc: "press wires" },
    { id: "cq6", query: '"Series C" scaling OR expansion OR "late stage" startup', num: 20, desc: "late-stage language" },
    { id: "cq7", query: '"led the Series C" OR "led a Series C" investment', num: 20, desc: "VC language" },
    { id: "cq8", query: '"Series C" startup funding site:eu-startups.com OR site:tech.eu OR site:techround.co.uk', num: 10, desc: "European" },
  ],
  supabaseTable: "funding_discoveries",
  webhookUrl:
    "https://api.clay.com/v3/sources/webhook/pull-in-data-from-a-webhook-d1b53ce2-fe64-40e4-a86c-faef265c5a63",
  webhookAuthToken: "0be318b702699f40b68f",
  extractionPrompt: buildExtractionPrompt("Series C", "NOT_SERIES_C"),
};
