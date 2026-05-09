import { config } from "dotenv";
import { resolve } from "path";

config({ path: resolve("../../.env") });

const triggerKey = process.env.TRIGGER_SECRET_KEY;
const projectRef = "proj_vvsvdbeeoiaausrkdiqp";

const resp = await fetch(
  `https://api.trigger.dev/api/v1/projects/${projectRef}/envvars/prod`,
  { headers: { Authorization: `Bearer ${triggerKey}` } }
);

const data = await resp.json();
console.log("Status:", resp.status);
console.log("All cloud env var names:");
const vars = data.environmentVariables ?? data.data ?? data ?? [];
for (const v of vars) {
  console.log(" -", v.name ?? v.key ?? JSON.stringify(v));
}
