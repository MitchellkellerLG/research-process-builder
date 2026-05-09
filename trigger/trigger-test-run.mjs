import { config } from "dotenv";
import { resolve } from "path";

config({ path: resolve("../../.env") });

const key = process.env.TRIGGER_SECRET_KEY;
const taskId = "product-launches-ph-daily";
const date = process.argv[2] ?? "2026-05-04";

console.log(`Triggering ${taskId} for date ${date}...`);

const resp = await fetch(`https://api.trigger.dev/api/v1/tasks/${taskId}/trigger`, {
  method: "POST",
  headers: {
    Authorization: `Bearer ${key}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    payload: { date },
  }),
});

const data = await resp.json();
if (!resp.ok) {
  console.error("Error:", resp.status, JSON.stringify(data, null, 2));
  process.exit(1);
}

console.log("Run triggered!");
console.log("Run ID:", data.id);
console.log("Dashboard:", `https://cloud.trigger.dev/orgs/leadgrow-289d/projects/series-a-monitoring-6fK0/runs/${data.id}`);
