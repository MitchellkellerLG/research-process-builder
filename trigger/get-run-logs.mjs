import { config } from "dotenv";
import { resolve } from "path";

config({ path: resolve("../../.env") });

const triggerKey = process.env.TRIGGER_SECRET_KEY;
const runId = process.argv[2];

const resp = await fetch(
  `https://api.trigger.dev/api/v3/runs/${runId}/logs`,
  { headers: { Authorization: `Bearer ${triggerKey}` } }
);

console.log("Status:", resp.status);
if (!resp.ok) {
  console.log(await resp.text());
  process.exit(1);
}

const text = await resp.text();
// Try to parse as NDJSON
const lines = text.trim().split("\n");
for (const line of lines) {
  try {
    const entry = JSON.parse(line);
    const msg = entry.message ?? entry.msg ?? JSON.stringify(entry);
    const level = entry.level ?? entry.severity ?? "";
    const attrs = entry.properties ?? entry.attributes ?? {};
    console.log(`[${level}] ${msg}`, Object.keys(attrs).length ? JSON.stringify(attrs) : "");
  } catch {
    console.log(line);
  }
}
