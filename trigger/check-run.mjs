import { config } from "dotenv";
import { resolve } from "path";

config({ path: resolve("../../.env") });

const key = process.env.TRIGGER_SECRET_KEY;
const runId = process.argv[2];

const resp = await fetch(`https://api.trigger.dev/api/v1/runs/${runId}`, {
  headers: { Authorization: `Bearer ${key}` },
});

const data = await resp.json();
console.log("Status:", data.status);
console.log("Created:", data.createdAt);
console.log("Started:", data.startedAt);
console.log("Finished:", data.finishedAt);
if (data.output) console.log("Output:", JSON.stringify(data.output, null, 2));
if (data.error) console.log("Error:", JSON.stringify(data.error, null, 2));
