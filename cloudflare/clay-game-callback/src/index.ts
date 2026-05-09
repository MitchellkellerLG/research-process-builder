export interface Env {
  TRIGGER_API_KEY: string;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (request.method !== "POST") {
      return new Response("Method not allowed", { status: 405 });
    }

    let body: Record<string, unknown>;
    try {
      body = await request.json() as Record<string, unknown>;
    } catch {
      return new Response("Invalid JSON", { status: 400 });
    }

    // Token can come from URL path (/TOKEN) or body (_callback_id)
    const urlToken = new URL(request.url).pathname.replace(/^\//, '').trim();
    const token = (urlToken || body._callback_id || body.callback_id) as string | undefined;
    if (!token) {
      return new Response("Missing token (path or _callback_id)", { status: 400 });
    }

    if (!env.TRIGGER_API_KEY) {
      return new Response("Server misconfigured: missing TRIGGER_API_KEY", { status: 500 });
    }

    console.log(`Clay callback received for token ${token}:`, JSON.stringify(body));

    const resp = await fetch(
      `https://api.trigger.dev/api/v1/waitpoints/tokens/${token}/complete`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${env.TRIGGER_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ data: body }),
      }
    );

    if (!resp.ok) {
      const err = await resp.text();
      console.error(`Trigger.dev complete failed: ${resp.status} ${err}`);
      return new Response(`Trigger.dev error: ${resp.status}`, { status: 502 });
    }

    return new Response("OK", { status: 200 });
  },
};
