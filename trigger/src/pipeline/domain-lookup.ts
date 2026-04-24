import { searchSerper } from "./serper.js";

const DISQUALIFIED_DOMAINS = new Set([
  "linkedin.com",
  "crunchbase.com",
  "wikipedia.org",
  "twitter.com",
  "x.com",
  "facebook.com",
  "bloomberg.com",
  "pitchbook.com",
  "glassdoor.com",
  "indeed.com",
  "ycombinator.com",
  "github.com",
  "youtube.com",
  "instagram.com",
  "tiktok.com",
  "reddit.com",
  "medium.com",
  "substack.com",
  "angel.co",
  "wellfound.com",
  "g2.com",
  "capterra.com",
  "trustpilot.com",
  "apple.com",
  "play.google.com",
  "apps.apple.com",
]);

const NEWS_AND_MEDIA_DOMAINS = new Set([
  "techcrunch.com",
  "thesaasnews.com",
  "finsmes.com",
  "businesswire.com",
  "prnewswire.com",
  "einpresswire.com",
  "globenewswire.com",
  "yahoo.com",
  "finance.yahoo.com",
  "reuters.com",
  "bloomberg.com",
  "eu-startups.com",
  "tech.eu",
  "venturebeat.com",
  "siliconangle.com",
  "alleywatch.com",
  "vcnewsdaily.com",
  "infotechlead.com",
  "therecursive.com",
  "finanzwire.com",
  "biospace.com",
  "fiercebiotech.com",
  "digitaltoday.co.kr",
  "netinfluencer.com",
  "bandt.com.au",
  "kitsapsun.com",
  "cincinnati.com",
  "thequantuminsider.com",
  "techround.co.uk",
  "pulse2.com",
  "ventureburn.com",
  "techstartups.com",
  "startupnews.fyi",
  "wired.com",
  "theverge.com",
  "arstechnica.com",
  "zdnet.com",
  "cnet.com",
  "forbes.com",
  "fortune.com",
  "cnbc.com",
  "axios.com",
  "inc.com",
  "fastcompany.com",
  "businessinsider.com",
  "insider.com",
  "wsj.com",
  "nytimes.com",
  "theinformation.com",
  "sifted.eu",
  "dealstreetasia.com",
  "techinasia.com",
  "krasia.com",
  "inc42.com",
  "yourstory.com",
  "entrackr.com",
  "contxto.com",
  "labsnews.com",
  "startupdaily.net",
  "uktech.news",
  "eu-startups.com",
  "silicon.co.uk",
  "techfundingnews.com",
  "fundingpost.com",
  "crunchbase.com",
  "pitchbook.com",
  "cbinsights.com",
  "news.google.com",
  "google.com",
  "bing.com",
  "finance.biggo.com",
  "gobiernu.cw",
  "chosun.com",
  "biz.chosun.com",
  "chosun.co.kr",
  "hankyung.com",
  "mk.co.kr",
  "sedaily.com",
  "edaily.co.kr",
  "etnews.com",
  "zdnet.co.kr",
  "bloter.net",
  "platum.kr",
  "thebell.co.kr",
  "dealsite.co.kr",
  "f6s.com",
  "startupranking.com",
  "startupblink.com",
  "tracxn.com",
  "owler.com",
  "zoominfo.com",
  "dnb.com",
  "apollo.io",
]);

interface DomainCandidate {
  domain: string;
  score: number;
  appearances: number;
  evidence: string[];
}

function isDomainDisqualified(domain: string): boolean {
  const clean = domain.replace(/^www\./, "");
  for (const d of DISQUALIFIED_DOMAINS) {
    if (clean === d || clean.endsWith(`.${d}`)) return true;
  }
  return false;
}

function isDomainNews(domain: string): boolean {
  const clean = domain.replace(/^www\./, "");
  for (const d of NEWS_AND_MEDIA_DOMAINS) {
    if (clean === d || clean.endsWith(`.${d}`)) return true;
  }
  return false;
}

function isDomainSuspectByTLD(domain: string): boolean {
  const clean = domain.replace(/^www\./, "").toLowerCase();
  const parts = clean.split(".");
  if (parts.length < 2) return false;

  // Check all TLD segments for institutional patterns
  // Handles: .edu, .edu.au, .ac.uk, .ac.kr, .gov, .gov.uk, .go.kr, .mil, .mil.us
  for (let i = 1; i < parts.length; i++) {
    const segment = parts[i];
    if (
      segment === "edu" ||
      segment === "ac" ||
      segment === "gov" ||
      segment === "go" ||
      segment === "mil"
    ) {
      return true;
    }
  }
  return false;
}

export function isDomainBlocked(domain: string): boolean {
  return isDomainDisqualified(domain) || isDomainNews(domain) || isDomainSuspectByTLD(domain);
}

function normalizeForComparison(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]/g, "");
}

function extractCompanyNames(companyName: string): string[] {
  const names: string[] = [];
  const dbaMatch = companyName.match(/\bdba\s+([^)]+)/i);
  if (dbaMatch) {
    names.push(dbaMatch[1].replace(/[™®©]/g, "").trim());
  }
  names.push(companyName.replace(/\s*\(.*?\)\s*/g, "").trim());
  names.push(companyName);
  return [...new Set(names.map(n => normalizeForComparison(n)).filter(n => n.length >= 3))];
}

function domainContainsCompanyName(domain: string, companyName: string): boolean {
  const normDomain = normalizeForComparison(domain.split(".")[0]);
  const names = extractCompanyNames(companyName);
  return names.some(n => normDomain.includes(n) || n.includes(normDomain));
}

function extractDomainFromText(text: string): string[] {
  const domainPattern = /\b([a-z0-9][-a-z0-9]*\.(?:com|io|ai|co|org|net|dev|app|tech|health|bio|xyz|gg|so|cc|me))\b/gi;
  const matches = text.match(domainPattern) ?? [];
  return [...new Set(matches.map(m => m.toLowerCase()))];
}

export interface DomainResult {
  domain: string;
  confidence: "high" | "medium" | "low";
  source: "article_extract" | "search_validated" | "search_only" | "crunchbase_signal";
  evidence: string;
}

export interface ContextClues {
  industry?: string;
  productOrService?: string;
  location?: string;
  founderName?: string;
}

export async function lookupDomainMultiSignal(
  companyName: string,
  clues: ContextClues,
  sourceUrl?: string
): Promise<DomainResult> {
  const sourceDomain = sourceUrl
    ? new URL(sourceUrl).hostname.replace(/^www\./, "")
    : "";

  const candidates = new Map<string, DomainCandidate>();

  function addCandidate(domain: string, title: string, snippet: string, searchLabel: string) {
    if (isDomainBlocked(domain)) return;
    if (sourceDomain && domain === sourceDomain) return;

    const existing = candidates.get(domain);
    if (existing) {
      existing.appearances++;
      existing.score += 2;
      existing.evidence.push(searchLabel);
    } else {
      let score = 0;
      if (domainContainsCompanyName(domain, companyName)) score += 5;
      if (title.toLowerCase().includes(companyName.toLowerCase())) score += 2;
      if (snippet.toLowerCase().includes(companyName.toLowerCase())) score += 1;
      if (/\.(com|io|ai|co)$/.test(domain)) score += 1;
      candidates.set(domain, {
        domain,
        score,
        appearances: 1,
        evidence: [searchLabel],
      });
    }
  }

  const searches: { query: string; label: string; extractFromSnippet?: boolean }[] = [];

  searches.push({
    query: `"${companyName}" startup website`,
    label: "quoted+startup",
  });

  searches.push({
    query: `site:crunchbase.com "${companyName}"`,
    label: "crunchbase",
    extractFromSnippet: true,
  });

  const industryTerm = clues.industry || clues.productOrService || "";
  if (industryTerm) {
    searches.push({
      query: `"${companyName}" ${industryTerm} official site`,
      label: "industry+site",
    });
  }

  searches.push({
    query: `"${companyName}" company -site:linkedin.com -site:crunchbase.com`,
    label: "direct-company",
  });

  if (clues.founderName) {
    searches.push({
      query: `"${clues.founderName}" "${companyName}" website`,
      label: "founder+company",
    });
  }

  for (const s of searches) {
    try {
      const items = await searchSerper(s.query, 5, "");
      for (const item of items) {
        const link = item.link ?? "";
        if (!link.includes("://")) continue;

        const domain = new URL(link).hostname.replace(/^www\./, "");
        const snippet = item.snippet ?? "";
        const title = item.title ?? "";

        if (s.extractFromSnippet) {
          const domainsInSnippet = extractDomainFromText(snippet);
          for (const d of domainsInSnippet) {
            if (!isDomainBlocked(d) && d !== sourceDomain) {
              const nameMatch = domainContainsCompanyName(d, companyName);
              const existing = candidates.get(d);
              if (existing) {
                existing.appearances++;
                existing.score += 3;
                existing.evidence.push("crunchbase_snippet");
              } else {
                candidates.set(d, {
                  domain: d,
                  score: nameMatch ? 8 : 4,
                  appearances: 1,
                  evidence: ["crunchbase_snippet"],
                });
              }
            }
          }
        }

        addCandidate(domain, title, snippet, s.label);
      }
    } catch {
      // continue
    }
  }

  if (candidates.size === 0) {
    return {
      domain: "not_found",
      confidence: "low",
      source: "search_only",
      evidence: `${searches.length} searches returned no valid candidates`,
    };
  }

  const sorted = [...candidates.values()].sort((a, b) => b.score - a.score);
  const best = sorted[0];
  const second = sorted[1];

  let confidence: "high" | "medium" | "low";
  if (best.score >= 8 && domainContainsCompanyName(best.domain, companyName)) {
    confidence = "high";
  } else if (best.appearances >= 2 || best.score >= 5) {
    confidence = "medium";
  } else {
    confidence = "low";
  }

  if (second && best.score - second.score <= 2) {
    confidence = confidence === "high" ? "medium" : "low";
  }

  const source = best.evidence.includes("crunchbase_snippet")
    ? "crunchbase_signal" as const
    : "search_validated" as const;

  return {
    domain: best.domain,
    confidence,
    source,
    evidence: `score=${best.score}, ${best.appearances} appearances [${best.evidence.join(", ")}]`,
  };
}
