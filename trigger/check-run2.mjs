import { config } from "dotenv";
import { resolve } from "path";

config({ path: resolve("../../.env") });

const key = process.env.TRIGGER_SECRET_KEY;
const runId = process.argv[2];

for (const version of ["v2", "v3", "v1"]) {
  const resp = await fetch(`https://api.trigger.dev/api/${version}/runs/${runId}`, {
    headers: { Authorization: `Bearer ${key}` },
  });
  if (resp.ok) {
    const data = await resp.json();
    console.log(`API ${version} works:`);
    console.log("Status:", data.status);
    console.log("Output:", JSON.stringify(data.output ?? data, null, 2).slice(0, 500));
    break;
  } else {
    console.log(`${version}: ${resp.status}`);
  }
}
