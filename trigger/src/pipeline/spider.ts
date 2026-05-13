const FIRECRAWL_API_KEY = process.env.FIRECRAWL_API_KEY ?? "";
const FC_BASE = "https://api.firecrawl.dev/v1";

interface FetchOptions {
  renderJs?: boolean;   // kept for call-site compat — FC handles JS natively, ignored
  waitForSecs?: number; // kept for compat — ignored
}

async function firecrawlFetch(url: string, timeoutMs: number): Promise<string | null> {
  const resp = await fetch(`${FC_BASE}/scrape`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${FIRECRAWL_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      url,
      formats: ["markdown"],
      onlyMainContent: true,
    }),
    signal: AbortSignal.timeout(timeoutMs),
  });

  if (!resp.ok) return null;

  const data = await resp.json() as { success: boolean; data?: { markdown?: string } };
  if (!data.success) return null;

  const content = data.data?.markdown ?? "";
  return content.length > 200 ? content.slice(0, 15_000) : null;
}

export async function fetchUrl(url: string, options?: FetchOptions): Promise<string | null> {
  if (FIRECRAWL_API_KEY) {
    try {
      const result = await firecrawlFetch(url, 30_000);
      if (result) return result;
    } catch { /* first attempt failed */ }

    try {
      const result = await firecrawlFetch(url, 60_000);
      if (result) return result;
    } catch { /* retry failed */ }
  }

  // Direct fetch fallback (no key or FC failed)
  try {
    const resp = await fetch(url, {
      headers: { "User-Agent": "Mozilla/5.0 (compatible; LeadGrow/1.0)" },
      signal: AbortSignal.timeout(15_000),
    });
    if (resp.ok) {
      const text = await resp.text();
      if (text.length > 200) return text.slice(0, 15_000);
    }
  } catch { /* all methods failed */ }

  return null;
}
