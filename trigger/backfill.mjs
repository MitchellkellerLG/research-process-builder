import { config } from "dotenv";
import { resolve } from "path";

config({ path: resolve("../../.env") });

const triggerKey = process.env.TRIGGER_SECRET_KEY;
const dates = process.argv.slice(2);

if (dates.length === 0) {
  console.log("Usage: node backfill.mjs 2026-05-04 2026-05-05 ...");
  process.exit(1);
}

for (const date of dates) {
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
  if (resp.ok) {
    console.log(`${date} → run_id: ${data.id}`);
  } else {
    console.log(`${date} → ERROR: ${JSON.stringify(data)}`);
  }
}
