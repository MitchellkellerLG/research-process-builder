import { config } from "dotenv";
import { resolve } from "path";

config({ path: resolve("../../.env") });

const url = process.env.SUPABASE_PROJECT_URL ?? process.env.SUPABASE_URL ?? "";
const key =
  process.env.SUPABASE_KEY ??
  process.env.SUPABASE_SERVICE_ROLE_KEY ??
  process.env.SUPABASE_ANON_KEY ??
  "";

console.log("URL:", url.slice(0, 40));
console.log("Key prefix:", key.slice(0, 20));

// Test row matching exactly what toSupabaseRow produces
const row = {
  discovered_date: "2026-05-07",
  company_name: "Test Company",
  product_name: "Test Product",
  tagline: "A test tagline",
  rank: 99,
  score: 42,
  ph_url: "https://www.producthunt.com/posts/test-product-99",
  categories: ["AI", "Developer Tools"],
  maker_website: "https://example.com",
  linkedin_url: null,
  launch_type: "new_product",
  is_ai: true,
  launch_count: 1,
  classification_reasoning: "Test row",
  source: "product_hunt",
  source_url: "https://www.producthunt.com/posts/test-product-99",
};

const resp = await fetch(
  `${url}/rest/v1/product_launches?on_conflict=source_url`,
  {
    method: "POST",
    headers: {
      apikey: key,
      Authorization: `Bearer ${key}`,
      "Content-Type": "application/json",
      Prefer: "resolution=merge-duplicates",
    },
    body: JSON.stringify([row]),
  }
);

console.log("\nStatus:", resp.status);
const body = await resp.text();
console.log("Response:", body.slice(0, 500));
