# Clay Callback Routing via Trigger.dev Waitpoints

Confirmed working 2026-05-06. Full loop tested: game signals pipeline → Clay → Worker → token complete.

## Architecture

```
Trigger.dev task
  │
  ├─ wait.createToken({ timeout: "2m" })  → token.id = "waitpoint_xxx"
  │
  ├─ POST to Clay webhook
  │    body: {
  │      _callback_id: token.id,
  │      _callback_url: "https://clay-game-callback.leadgrowai.workers.dev/{token.id}",
  │      "Company Name": ...,
  │      ...
  │    }
  │
  ├─ wait.forToken(token)  ← task suspends here
  │
  │  [Clay runs enrichment, then POSTs result to _callback_url]
  │
  └─ Cloudflare Worker receives POST at /{token.id}
       → calls Trigger.dev /api/v1/waitpoints/tokens/{token.id}/complete
       → task resumes with enrichment data
```

## Code Pattern (TypeScript / Trigger.dev SDK)

```typescript
import { wait } from "@trigger.dev/sdk";

const CLAY_WEBHOOK_URL = process.env.CLAY_GAME_SIGNALS_WEBHOOK ?? "";
const CLAY_CALLBACK_URL =
  process.env.CLAY_GAME_SIGNALS_CALLBACK_URL ??
  "https://clay-game-callback.leadgrowai.workers.dev";

async function sendToClay(companyName: string, domain: string) {
  const token = await wait.createToken({ timeout: "2m" });

  const resp = await fetch(CLAY_WEBHOOK_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      _callback_id: token.id,
      _callback_url: `${CLAY_CALLBACK_URL}/${token.id}`,
      "Company Name": companyName,
      "Company Website": domain,
    }),
    signal: AbortSignal.timeout(10_000),
  });

  if (!resp.ok) {
    logger.warn(`Clay push failed: ${resp.status}`);
    return null;
  }

  const result = await wait.forToken<Record<string, unknown>>(token).catch(() => null);
  if (result?.ok) {
    return result.output; // enrichment data
  }
  return null; // timeout
}
```

## Clay Table Setup

In your Clay table, add these two columns on the incoming webhook row:
- `_callback_id` — the waitpoint token ID
- `_callback_url` — the full Worker URL with token in path

At the end of the table (after all enrichment steps), add a **Webhook** action:
- URL: `{{_callback_url}}`
- Method: POST
- Body: all enriched columns as JSON (include `_callback_id` in the body)

## Cloudflare Worker

Single worker (`cloudflare/clay-game-callback/`) handles all pipelines — it's token-agnostic.
Deployed at: `https://clay-game-callback.leadgrowai.workers.dev`

Worker logic:
1. Reads token from URL path (`/{token.id}`) or body `_callback_id`
2. POSTs `{ data: body }` to `https://api.trigger.dev/api/v1/waitpoints/tokens/{token}/complete`
3. Returns 200 to Clay

Worker needs one secret: `TRIGGER_API_KEY` (set in Cloudflare dashboard).

## Env Vars per Pipeline

| Pipeline       | Webhook env var                  | Callback env var                        | Fallback                                           |
|----------------|----------------------------------|-----------------------------------------|----------------------------------------------------|
| Game signals   | `CLAY_GAME_SIGNALS_WEBHOOK`      | `CLAY_GAME_SIGNALS_CALLBACK_URL`        | `https://clay-game-callback.leadgrowai.workers.dev` |
| Product Hunt   | `CLAY_COMPANY_ENRICH_WEBHOOK`    | `CLAY_COMPANY_ENRICH_CALLBACK_URL`      | `https://clay-game-callback.leadgrowai.workers.dev` |

Both pipelines share the same Cloudflare Worker — no separate worker needed per pipeline.

## Adding Clay to a New Pipeline

1. Add env vars to `trigger/.env` and Trigger.dev dashboard
2. Copy the code pattern above, change env var names
3. Always hardcode the fallback callback URL — don't leave it as `?? ""`
4. In Clay: wire `_callback_url` webhook action as the last step
5. Test locally with `scripts/test_clay_callback.py` pattern before deploying
