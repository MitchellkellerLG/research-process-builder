# find competitors

find the direct competitors of a company and explain why each one competes.

## inputs

- `{{company_name}}` — the company to research
- `{{domain}}` — their website domain (e.g. clay.com)
- `{{category}}` — what they do in 2-3 words (e.g. "GTM data enrichment", "legal AI"). required if the company name is a common word or 6 characters or fewer.

## steps

### step 1: the company's own competitive positioning

search: `site:{{domain}} alternatives OR competitors OR "vs" OR "compared to"`

extract from results:

- any "alternatives to" or "vs" pages the company publishes
- competitors they name directly (this is the highest-signal source — companies know their own market)
- how they position themselves against each competitor
- one sentence on what each named competitor does

if no results, try: `site:{{domain}} compare`

companies that publish comparison pages are telling you exactly who they compete with. this is more reliable than any third-party list.

**stop if:** you found 3+ competitors named by the company itself with clear positioning. skip to output.

### step 2: direct competitor search

search: `{{company_name}} {{category}} competitors`

extract from results:

- every company named as a competitor
- which source mentioned them (G2, blog, Tracxn, etc.)
- one sentence on what each competitor does

**stop if:** combined with step 1, you have 5+ competitors from structured sources. skip to output.

### step 3: alternatives search

search: `{{company_name}} {{category}} alternatives`

extract from results:

- any new companies not found in previous steps
- note which platform listed them (Capterra, Product Hunt, "alternatives to" blogs)

**stop if:** you now have 5+ unique competitors with clear positioning. skip to output.

### step 4: category market map

search: `best {{category}} tools 2026`

extract from results:

- full list of tools mentioned in the category
- how each is positioned relative to `{{company_name}}`
- any market segments or subcategories identified

### step 5: G2 structured data (software companies only)

search: `site:g2.com {{company_name}} alternatives`

extract from results:

- G2 alternative listings with ratings
- category ranking if visible

skip this step if `{{company_name}}` is not a software company.

### step 6: head-to-head positioning

search: `{{company_name}} vs {{top_competitor_from_above}}`

extract from results:

- how the two companies differ (pricing, features, ideal customer)
- which one wins in which scenario
- three sentence summary of the competitive dynamic

**stop if:** you have clear positioning context for the top 3 competitors. skip to output.

### step 7: practitioner opinions

search: `who competes with {{company_name}} {{category}}`

extract from results:

- competitors mentioned by actual users (forums, reddit-synthesis articles, blog comments)
- any competitors the structured platforms missed

### step 8: domain-anchored fallback (use only if steps 2-3 returned noise from an ambiguous name)

search: `{{domain}} competitors`

extract from results:

- competitors identified via domain matching (unambiguous, zero noise)

## do not search

- `{{company_name}} market landscape` — returns industry research papers, not competitors
- `{{company_name}} competitive intelligence` — returns CI vendor marketing
- `site:crunchbase.com {{company_name}} competitors` — description matching is inaccurate
- `{{domain}} competitors site:similarweb.com` — traffic-based, identifies audience sites not competitors

## output

```
## competitors for {{company_name}}

**top competitors:** [competitor a], [competitor b], [competitor c]

**why these three:**
- [competitor a] — [one sentence on why they compete directly. what do they share? where do they differ?]
- [competitor b] — [one sentence on why they compete directly]
- [competitor c] — [one sentence on why they compete directly]

**also mentioned:** [competitor d], [competitor e], [etc.] — [one sentence on why these are secondary/adjacent competitors]

**how {{company_name}} is positioned:**
[three sentences max. what's their angle vs the field? where do they win? where are they weaker?]

**sources:** [list of platforms/articles that provided competitor data]
```
