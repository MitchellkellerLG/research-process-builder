import type { ExtractedData, RoundConfig } from "./types.js";

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
        model: "gpt-4o-mini",
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
