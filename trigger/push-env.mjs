import { config } from "dotenv";
import { resolve } from "path";

config({ path: resolve("../../.env") });

const triggerKey = process.env.TRIGGER_SECRET_KEY;
const projectRef = "proj_vvsvdbeeoiaausrkdiqp";

// Resolve the right Supabase service role key from local env
const supabaseServiceKey =
  process.env.SUPABASE_KEY ??
  process.env.SUPABASE_SERVICE_ROLE_KEY ??
  null;

// Resolve Clay webhook — cloud has CLAY_GAME_SIGNALS_WEBHOOK which pipeline already reads
// But CLAY_COMPANY_ENRICH_WEBHOOK is the primary. Check if it exists locally.
const clayWebhook = process.env.CLAY_COMPANY_ENRICH_WEBHOOK ?? null;
const clayCallback = process.env.CLAY_COMPANY_ENRICH_CALLBACK_URL ?? null;

console.log("supabaseServiceKey found:", !!supabaseServiceKey);
console.log("clayWebhook found:", !!clayWebhook, clayWebhook ? "(local)" : "(will use CLAY_GAME_SIGNALS_WEBHOOK fallback)");

async function setVar(name, value) {
  if (!value) { console.log(`SKIP ${name} — not found locally`); return; }
  const resp = await fetch(
    `https://api.trigger.dev/api/v1/projects/${projectRef}/envvars/prod/${name}`,
    {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${triggerKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ value }),
    }
  );
  console.log(`${name}: ${resp.status} ${resp.ok ? "OK" : await resp.text()}`);
}

// Push service role key so writes work
await setVar("SUPABASE_SERVICE_ROLE_KEY", supabaseServiceKey);
// Push Clay vars if we have them locally
await setVar("CLAY_COMPANY_ENRICH_WEBHOOK", clayWebhook);
await setVar("CLAY_COMPANY_ENRICH_CALLBACK_URL", clayCallback);
