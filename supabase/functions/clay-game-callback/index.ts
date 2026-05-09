// Clay enrichment callback receiver.
// Clay POSTs enriched data here; we complete the Trigger.dev token so the
// game-signals pipeline task resumes with the enrichment payload.
const TRIGGER_API_KEY = Deno.env.get("TRIGGER_API_KEY") ?? "";
const TRIGGER_API_BASE = "https://api.trigger.dev/api/v1";

Deno.serve(async (req) => {
  if (req.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }

  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return new Response("Invalid JSON", { status: 400 });
  }

  const token = body._callback_id as string | undefined;
  if (!token) {
    return new Response("Missing _callback_id", { status: 400 });
  }

  if (!TRIGGER_API_KEY) {
    console.error("TRIGGER_API_KEY not set");
    return new Response("Server misconfigured", { status: 500 });
  }

  // Complete the Trigger.dev manual waitpoint so the pipeline task resumes.
  const completeResp = await fetch(
    `${TRIGGER_API_BASE}/waitpoints/tokens/${token}/complete`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${TRIGGER_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ data: body }),
    }
  );

  if (!completeResp.ok) {
    const err = await completeResp.text();
    console.error(`Trigger.dev complete failed: ${completeResp.status} ${err}`);
    return new Response(`Trigger.dev error: ${completeResp.status}`, { status: 502 });
  }

  return new Response("OK", { status: 200 });
});
