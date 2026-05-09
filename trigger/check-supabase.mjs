import { config } from "dotenv";
import { resolve } from "path";

config({ path: resolve("../../.env") });

const url = process.env.SUPABASE_PROJECT_URL ?? process.env.SUPABASE_URL ?? "";
const key = process.env.SUPABASE_KEY ?? process.env.SUPABASE_SERVICE_ROLE_KEY ?? process.env.SUPABASE_ANON_KEY ?? "";

console.log("SUPABASE_PROJECT_URL:", url ? url.slice(0, 40) + "..." : "MISSING");
console.log("SUPABASE_KEY:", key ? key.slice(0, 20) + "..." : "MISSING");

if (!url || !key) {
  console.log("\nMissing Supabase vars — stage3 will silently skip.");
  process.exit(1);
}

// Test a simple count query
const resp = await fetch(`${url}/rest/v1/product_launches?select=count`, {
  headers: {
    apikey: key,
    Authorization: `Bearer ${key}`,
    "Content-Type": "application/json",
    Prefer: "count=exact",
  },
});

console.log("\nSupabase response status:", resp.status);
console.log("Row count header:", resp.headers.get("content-range"));
const body = await resp.text();
console.log("Body:", body.slice(0, 200));
