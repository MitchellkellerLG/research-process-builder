# Handoff: Company Name via Domain Normalization

## Problem
`company_name` == `product_name` for most PH products. GPT can't separate them from leaderboard data alone.

Examples of bad data currently in Supabase:
- company_name: "Kilo Code v7 for VS Code" (should be: Kilo Code)
- company_name: "Shadow 2.0" (should be: Shadow Labs)
- company_name: "Lingo.dev v1" (should be: Lingo.dev)
- company_name: "Lovie Formation - Incorporation MCP" (should be: Lovie)

## Solution
Use `maker_website` domain as a strong hint for company name. Domain = canonical company identity without version noise.

## File to Edit
`C:\Users\mitch\Everything_CC\research-process-builder\trigger\src\pipeline\product-launches-ph.ts`

## Implementation Steps

### Step 1: Add domain normalization helper (after `parseJsonResponse`)

```ts
function domainToCompanyHint(makerWebsite: string | null): string | null {
  if (!makerWebsite) return null;
  try {
    const hostname = new URL(makerWebsite).hostname.toLowerCase();
    // Strip www and app subdomains, keep meaningful subdomains (e.g. app.rudel.ai → rudel)
    const parts = hostname.split(".");
    // Remove TLD (last part) and common subdomains
    const filtered = parts.filter((p, i) => {
      if (i === parts.length - 1) return false; // TLD
      if (p === "www" || p === "app" || p === "get" || p === "try" || p === "use") return false;
      return true;
    });
    if (filtered.length === 0) return null;
    // Use first meaningful segment
    const slug = filtered[0];
    // Ignore generic domains that don't represent the company
    const generic = new Set(["github", "google", "apple", "microsoft", "openai", "anthropic", "solana", "notion", "vercel", "netlify"]);
    if (generic.has(slug)) return null;
    // Convert slug to title case, splitting on hyphens and camelCase boundaries
    return slug
      .replace(/-/g, " ")
      .replace(/([a-z])([A-Z])/g, "$1 $2")
      .replace(/\b\w/g, (c) => c.toUpperCase());
  } catch {
    return null;
  }
}
```

### Step 2: Compute hint after Stage 1b and attach to products

After the Stage 1b + 1c blocks (around line 320), add:

```ts
// Compute domain-based company name hints
for (const product of filtered) {
  if (!product.company_name && product.maker_website) {
    const hint = domainToCompanyHint(product.maker_website);
    if (hint) product.company_name = hint;
  }
}
```

This handles the simple case cheaply — no GPT needed for straightforward domains.

### Step 3: Pass hint into Stage 2 GPT prompt for hard cases

In `stage2Classify`, update `productLines` to include the domain hint:

```ts
const productLines = products.map((p) => {
  const cats = (p.categories ?? []).join(", ");
  const domainHint = domainToCompanyHint(p.maker_website ?? null);
  const hintStr = domainHint ? ` | domain_hint=${domainHint}` : "";
  return `rank=${p.rank} | product_name=${p.product_name} | company_name_hint=${p.company_name ?? "unknown"}${hintStr} | tagline=${p.tagline ?? ""} | categories=${cats}`;
});
```

Update GPT classification prompt to also return `company_name`:

```
For each product, also determine:
4. company_name: the organization behind this product. Use domain_hint as a strong signal.
   Strip version suffixes (v1, v2, 2.0, v7), descriptors (for VS Code, - Incorporation MCP),
   and dates from the product_name to get the company name.
   If domain_hint is provided and plausible, prefer it over a raw product_name.
   Examples: "Kilo Code v7 for VS Code" + domain_hint=Kilo Code → "Kilo Code"
             "Shadow 2.0" + domain_hint=Shadow Labs → "Shadow Labs"
             "Lingo.dev v1" + no hint → "Lingo.dev"
```

Update return schema:
```
Return: {"classifications": [{"rank": <int>, "product_name": "<str>", "company_name": "<str>",
"launch_type": "new_product|new_feature", "is_ai": true|false, "classification_reasoning": "<str>"}]}
```

Update the merge step after GPT call to also pick up `company_name`:
```ts
const classified: ClassifiedProduct[] = products.map((p) => {
  const cls = clsByRank.get(p.rank);
  return {
    ...p,
    company_name: cls?.company_name ?? p.company_name ?? null,
    launch_type: ...,
    ...
  };
});
```

## Testing
Deploy and trigger: `node deploy-and-run.mjs 2026-05-04`

Verify in website API:
```
curl -sL "https://www.leadgrow.ai/api/signals/product-launches?limit=20"
```

Check that `company_name` != `product_name` for versioned products.

Ground truth checks (from May 4):
- Codex Pets → company: OpenAI
- Kilo Code v7 for VS Code → company: Kilo Code
- Shadow 2.0 → company: Shadow Labs

## Context
- Pipeline: `research-process-builder/trigger/src/pipeline/product-launches-ph.ts`
- Deploy script: `research-process-builder/trigger/deploy-and-run.mjs`
- Backfill script: `research-process-builder/trigger/backfill.mjs`
- TriggerDev project: `proj_vvsvdbeeoiaausrkdiqp`
- Dashboard: https://cloud.trigger.dev/orgs/leadgrow-289d/projects/series-a-monitoring-6fK0
- Website API: https://www.leadgrow.ai/api/signals/product-launches
- Supabase table: `product_launches` (RLS: anon can read+write, service_role can read+write)
- Deploy command: `cd research-process-builder/trigger && node deploy-and-run.mjs <date>`
