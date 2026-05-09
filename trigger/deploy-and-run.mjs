import { config } from "dotenv";
import { resolve } from "path";
import { execSync } from "child_process";

config({ path: resolve("../../.env") });

const date = process.argv[2] ?? "2026-05-06";
const triggerKey = process.env.TRIGGER_SECRET_KEY;

console.log("Deploying...");
try {
  const out = execSync("npx trigger.dev@latest deploy", {
    env: process.env,
    timeout: 120000,
    encoding: "utf8",
    stdio: ["pipe", "pipe", "pipe"],
  });
  console.log(out.slice(-500));
} catch (e) {
  console.log("Deploy stdout:", e.stdout?.slice(-1000));
  console.log("Deploy stderr:", e.stderr?.slice(-500));
  process.exit(1);
}

console.log(`\nTriggering run for date: ${date}`);
const resp = await fetch(
  `https://api.trigger.dev/api/v1/tasks/product-launches-ph-daily/trigger`,
  {
    method: "POST",
    headers: {
      Authorization: `Bearer ${triggerKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ payload: { date } }),
  }
);

const data = await resp.json();
if (!resp.ok) {
  console.error("Trigger error:", JSON.stringify(data));
  process.exit(1);
}

console.log("Run ID:", data.id);
console.log("Dashboard:", `https://cloud.trigger.dev/orgs/leadgrow-289d/projects/series-a-monitoring-6fK0/runs/${data.id}`);
