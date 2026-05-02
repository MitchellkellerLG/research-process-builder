import type { ExtractedData, RoundConfig } from "./types.js";

export interface SemanticValidationResult {
  correctCompanyName: string;
  correctDomain: string;
  status: "Correct" | "Wrong" | "Unclear";
  reason: string;
}

const OPENAI_API_KEY = process.env.OPENAI_API_KEY ?? "";

export async function extractWithOpenAI(
  articleText: string,
  companyHint: string,
  amountHint: string,
  config: RoundConfig
): Promise<ExtractedData | null> {
  if (!OPENAI_API_KEY) return null;

  const prompt = config.extractionPrompt
    .replace("{{companyHint}}", companyHint)
    .replace("{{amountHint}}", amountHint)
    .replace("{{articleText}}", articleText.slice(0, 8000));

  const messages = [
    {
      role: "system" as const,
      content:
        "You extract structured funding data from articles. Return valid JSON only, no markdown fences, no explanation.",
    },
    {
      role: "user" as const,
      content: prompt,
    },
  ];

  try {
    const resp = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${OPENAI_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "gpt-4.1-mini",
        temperature: 0,
        max_tokens: 500,
        messages,
      }),
      signal: AbortSignal.timeout(30_000),
    });

    if (!resp.ok) return null;

    const data = (await resp.json()) as {
      choices: { message: { content: string } }[];
    };

    let content = data.choices[0]?.message?.content?.trim() ?? "";
    if (content.startsWith("```")) {
      content = content.replace(/^```(?:json)?\s*/, "").replace(/\s*```$/, "");
    }

    return JSON.parse(content) as ExtractedData;
  } catch {
    return null;
  }
}

const SEMANTIC_VALIDATION_SYSTEM = `You are a company domain verification agent. You are given a CANDIDATE domain to verify — it may be correct or wrong. Your job: find the TRUE domain, then compare.

Step 1 — Find the true domain from the article:
  a) Is the company name a markdown hyperlink like [Company](https://example.com)?
     YES → that hyperlinked URL is the true domain. Stop here.
  b) Is there a URL in the article that belongs to the company itself (not a news site, not social media)?
     YES → that is the true domain.
  c) Neither → the article does not contain a verifiable domain.

Step 2 — Validate the CANDIDATE domain from the article context:
  A candidate is VALID only if ALL of these hold:
  - Belongs to the company that raised funding (not a news site, CDN, investor, or social platform)
  - Product/service described on that site matches the article
  - Industry matches
  - Geography matches (if stated)
  NEVER accept a news/media domain as the company's domain.

Step 3 — Set status:
  - If true domain found AND it EXACTLY matches the candidate → status = "Correct"
  - If true domain found AND it DIFFERS from the candidate → status = "Wrong", set correctDomain
  - If no true domain found in article AND candidate passes Step 2 validation → status = "Correct"
  - If no true domain found AND candidate fails validation → status = "Unclear"
  - If you cannot confidently determine anything → status = "Unclear", DO NOT GUESS

Rules:
  - NEVER guess a domain not explicitly in the article
  - NEVER default to company-name.com as a guess
  - News/media sites (techcrunch.com, finsmes.com, etc.) are NEVER the company domain

Output ONLY valid JSON:
{"correctCompanyName": "", "correctDomain": "", "status": "Correct / Wrong / Unclear", "reason": ""}

reason: max 2 short sentences explaining your decision.`;

function normalizeDomain(raw: string): string {
  return raw
    .replace(/^https?:\/\//, "")
    .replace(/^www\./, "")
    .split("/")[0]
    .toLowerCase()
    .trim();
}

export async function validateDomainSemantic(
  sourceUrl: string,
  companyName: string,
  domain: string,
  rawArticleText: string
): Promise<SemanticValidationResult> {
  const fallback: SemanticValidationResult = {
    correctCompanyName: companyName,
    correctDomain: domain,
    status: "Unclear",
    reason: "validation skipped",
  };

  if (!OPENAI_API_KEY || !rawArticleText) return fallback;

  const userMsg = [
    `source_url: ${sourceUrl}`,
    `company_name: ${companyName}`,
    `domain: ${domain}`,
    "",
    `Article text:\n${rawArticleText.slice(0, 8000)}`,
  ].join("\n");

  try {
    const resp = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${OPENAI_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "gpt-4.1-mini",
        temperature: 0,
        max_tokens: 200,
        messages: [
          { role: "system", content: SEMANTIC_VALIDATION_SYSTEM },
          { role: "user", content: userMsg },
        ],
      }),
      signal: AbortSignal.timeout(25_000),
    });

    if (!resp.ok) return fallback;

    const data = (await resp.json()) as { choices: { message: { content: string } }[] };
    const content = data.choices[0]?.message?.content?.trim() ?? "";
    const jsonMatch = content.match(/\{[\s\S]*\}/);
    if (!jsonMatch) return fallback;

    const parsed = JSON.parse(jsonMatch[0]) as SemanticValidationResult;
    if (parsed.correctDomain) {
      parsed.correctDomain = normalizeDomain(parsed.correctDomain);
    }
    return parsed;
  } catch {
    return fallback;
  }
}
