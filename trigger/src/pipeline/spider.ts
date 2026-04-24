const SPIDER_API_KEY = process.env.SPIDER_API_KEY ?? "";

async function spiderFetch(url: string, timeoutMs: number): Promise<string | null> {
  const resp = await fetch("https://api.spider.cloud/crawl", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${SPIDER_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ url, limit: 1, return_format: "markdown" }),
    signal: AbortSignal.timeout(timeoutMs),
  });

  if (!resp.ok) return null;

  const data = await resp.json();
  let content = "";
  if (Array.isArray(data) && data.length > 0) {
    content = data[0]?.content ?? "";
  } else if (data && typeof data === "object") {
    content = (data as Record<string, string>).content ?? "";
  }
  return content.length > 200 ? content.slice(0, 15_000) : null;
}

export async function fetchUrl(url: string): Promise<string | null> {
  if (SPIDER_API_KEY) {
    try {
      const result = await spiderFetch(url, 20_000);
      if (result) return result;
    } catch { /* first attempt failed */ }

    try {
      const result = await spiderFetch(url, 45_000);
      if (result) return result;
    } catch { /* retry failed */ }
  }

  try {
    const resp = await fetch(url, {
      headers: { "User-Agent": "Mozilla/5.0 (compatible; LeadGrow/1.0)" },
      signal: AbortSignal.timeout(15_000),
    });
    if (resp.ok) {
      const text = await resp.text();
      if (text.length > 200) {
        return text.slice(0, 15_000);
      }
    }
  } catch { /* all methods failed */ }

  return null;
}
