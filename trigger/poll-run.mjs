import { config } from "dotenv";
import { resolve } from "path";

config({ path: resolve("../../.env") });

const key = process.env.TRIGGER_SECRET_KEY;
const runId = process.argv[2];
const intervalMs = 20000;
const maxWaitMs = 600000;

const start = Date.now();

async function check() {
  const resp = await fetch(`https://api.trigger.dev/api/v3/runs/${runId}`, {
    headers: { Authorization: `Bearer ${key}` },
  });
  return resp.ok ? resp.json() : null;
}

while (Date.now() - start < maxWaitMs) {
  const data = await check();
  if (!data) { console.log("API error"); break; }

  const elapsed = Math.round((Date.now() - start) / 1000);
  console.log(`[${elapsed}s] Status: ${data.status} | cost: ${data.costInCents}¢`);

  if (data.isCompleted) {
    console.log("\nDone!");
    console.log("Output:", JSON.stringify(data.output, null, 2));
    if (data.error) console.log("Error:", JSON.stringify(data.error, null, 2));
    break;
  }

  await new Promise(r => setTimeout(r, intervalMs));
}
