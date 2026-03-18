# Search Pattern Optimization Playbook

Auto-accumulated by autocontext_runner.py. Each entry validated by GT score improvement.

## Category Strategies

### leadership_people (GT: 1.000, reliability: YES)
- PROVEN: site:rocketreach.co returns structured people data reliably
- PROVEN: Full name queries outperform abbreviations

### founders_ceo (GT: 0.844, reliability: YES)
- PROVEN: site:crunchbase.com {{company_name}} CEO OR founder — best pattern (0.844)
- PROVEN: "founded by" OR "co-founded" OR "started by" — second best (0.774)
- PROVEN: CEO OR founder site:techcrunch.com OR site:businessinsider.com (0.687)
- FAILED: site:linkedin.com/in — snippets never show names (0.020)
- FAILED: Wikipedia founder queries — too much noise (0.409)

### c_suite_technical (GT: 0.786, reliability: YES)
- PROVEN: "hires" OR "appoints" OR "new" CTO OR CPO — best pattern (0.786)
- PROVEN: "appointed" OR "named" CTO OR CPO OR "Chief Technology" (0.714)
- PROVEN: "CTO" name OR who OR profile (0.714)
- PROVEN: Full title "Chief Technology Officer" queries (0.500)
- FAILED: site:rocketreach.co for tech C-suite (0.071) — RocketReach snippets don't surface names
- FAILED: site:theorg.com (0.143) — limited coverage for smaller companies
- FAILED: site:linkedin.com for C-suite (0.000) — LinkedIn snippets never show names
- LEARNING: "hires/appoints" press language > "appointed/named" language by ~10%

### c_suite_commercial (GT: 0.618, reliability: YES)
- PROVEN: "Chief Marketing Officer" OR "Chief Revenue Officer" OR "Chief Financial Officer" — best (0.618)
- PROVEN: revenue OR marketing leader OR executive profile name (0.484)
- PROVEN: site:rocketreach.co {{company_name}} "Chief Marketing" OR "Chief Revenue" (0.384)
- FAILED: abbreviations (CMO/CRO/CFO) underperform full titles significantly
- FAILED: LinkedIn snippets (0.232)
- LEARNING: Full title strings in quotes vastly outperform abbreviations for C-suite commercial

### funding_financial (GT: 0.688, reliability: YES)
- PROVEN: raises OR raised series OR funding OR "round" million OR billion (0.688)
- PROVEN: {{category}} funding (0.658), simple "funding" query (0.654) — both good
- FAILED: site:crunchbase.com funding URL path (0.339) — paywalled snippets

### pricing_intelligence (GT: 0.655, reliability: YES)
- PROVEN: pricing "$" OR "per month" OR "per seat" OR "per user" (0.655)
- PROVEN: {{company_name}} pricing (0.647) — simple query is nearly as good
- FAILED: site:domain/pricing (0.295) — on-domain pages too specific

### competitor_identification (GT: 0.517, reliability: YES)
- PROVEN: {{company_name}} competitors — simple query is the best (0.517)
- PROVEN: broad alternatives: {{company_name}} {{category}} OR alternatives (0.412)
- FAILED: G2/Capterra site: queries (0.198-0.283)
- FAILED: "vs" + specific competitor names (0.203)
- LEARNING: Simple "competitors" query beats all complex patterns

### company_profile (GT: 0.587, reliability: YES)
- PROVEN: "founded in" OR "headquartered in" company profile overview (0.587)
- PROVEN: {{category}} company "founded" "employees" OR "headquartered" (0.550)
- PROVEN: "founded in" OR "headquartered" OR "employees" plain query (0.475)
- FAILED: site:crunchbase.com (0.069) — paywalled/truncated snippets
- FAILED: site:pitchbook.com (0.130) — same paywall issue
- FAILED: site:domain/about (0.047) — marketing copy, not structured data
- LEARNING: Free-text structured field queries ("founded in", "headquartered") reliably surface Wikipedia/about pages with all 4 GT fields

### partnerships_integrations (GT: 0.270, reliability: PARTIAL)
- PROVEN: site:{{domain}} integrations OR api OR "connect" OR plugins (0.270)
- PROVEN: Zapier OR Slack OR Salesforce OR HubSpot integration (0.224)
- PROVEN: "integrates with" OR "works with" OR "connects to" (0.174)
- FAILED: G2 integrations page (0.044) — irrelevant snippets
- FAILED: Zapier.com site: query (0.148) — Zapier snippets don't list partner names
- LEARNING: On-domain integration pages are the ceiling; third-party sites don't expose partner names in snippets

### tech_stack (GT: 0.269, reliability: PARTIAL)
- PROVEN: jobs requirements Python OR React OR AWS OR Kubernetes (0.269)
- PROVEN: {{company_name}} tech stack — simple query (0.247)
- PROVEN: engineer requirements "experience with" OR "proficiency in" (0.215)
- FAILED: site:stackshare.io (0.125) — limited coverage, snippets truncated
- FAILED: site:builtwith.com (0.139) — same issue
- FAILED: site:back4app.com (0.180) — some coverage but snippets don't list specific tools
- FAILED: HN, engineering blog patterns — too sparse
- LEARNING: Tech stack is fundamentally snippet-limited (~0.27 ceiling). Job postings are the highest-signal source.

### customer_case_studies (GT: 0.234, reliability: PARTIAL)
- PROVEN: "customer spotlight" OR "customer story" OR "case study" {{category}} (0.234)
- PROVEN: site:{{domain}} "case study" OR "customer story" (0.222)
- PROVEN: site:{{domain}} case-study OR customer-story OR success-story (0.214)
- PROVEN: "trusted by" OR "used by" OR "powers" (0.205)
- FAILED: G2 review queries (0.044-0.128) — review snippets don't name customers
- FAILED: ROI-focused queries (0.093) — too generic
- FAILED: ProductHunt (0.100), enterprise mention patterns (0.069-0.142)
- LEARNING: Customer names in 200-char snippets is fundamentally hard (~0.23 ceiling). On-domain case study pages are the ceiling.

## Global Patterns

- **Full title > abbreviation**: "Chief Technology Officer" beats "CTO" by 30-50%
- **Hire/appointment language beats "named/appointed"**: "hires" OR "appoints" > "named" OR "appointed" by ~10%
- **On-domain site: queries for integrations/case studies** — highest signal for on-domain content
- **Aggregator sites almost always disappoint**: Crunchbase, StackShare, PitchBook — paywalled snippets
- **Simple queries often beat complex ones**: "competitors" beats 5-part OR query
- **OR operators are highest-leverage single mutation**
- **Year modifiers improve freshness** for news-like categories (hiring announcements, funding)
- **Disambiguation**: add category for ambiguous names (Clay, Mercury, Grain, Ramp)
- **LinkedIn site: queries = 0.000** for people — snippets never show names
- **site:reddit.com = universally broken**

## Iteration History

- baseline: GT mean 0.3169, best-per-cat 0.493, 342 evaluations, 11 categories
- iter1: GT mean 0.3336 (+0.017), best-per-cat 0.525. Winners: ch1_appoint_tech (c_suite_tech +0.214), ch1_structured (company_profile +0.109), ch1_site_integrations (partnerships +0.028). Pruned 13 dead variants.
- iter2: GT mean 0.3729, best-per-cat 0.539. Winners: ch2_crunchbase_founder (founders +0.070), ch2_zapier_integrations (partnerships +0.044), ch2_site_case_study (case_studies +0.008), ch2_price_numbers (pricing +0.008), ch2_jobs_tech (tech_stack +0.022).
- iter3: GT mean 0.3722, best-per-cat 0.549. Winners: ch3_wiki_about (company_profile +0.075), ch3_rocket_full_title (c_suite_commercial +0.034).
- iter4: GT mean 0.3710, best-per-cat 0.553. Winner: ch4_api_docs (partnerships +0.046).
- iter5: GT mean 0.4351 (aggressive prune), best-per-cat 0.563. Winners: ch5_hires_cto (c_suite_tech +0.072), ch5_about_overview (company_profile +0.037).
- iter6: GT mean 0.4386, best-per-cat 0.572. Winner: ch6_revenue_leader (c_suite_commercial +0.100).
- iter7: GT mean 0.4453, best-per-cat 0.575. Winner: ch7_raises_series (funding +0.030).
- iter8: GT mean 0.4538, best-per-cat 0.587. Winner: ch8_exact_roles (c_suite_commercial +0.134 vs original).
- iter9: GT mean 0.4479, best-per-cat 0.588. Winner: ch9_customer_spotlight (case_studies +0.012).
- iter10: GT mean 0.4479, best-per-cat 0.588. No wins — plateau hit on all 5 targets. Diminishing returns.

## Final State (iter10)
GT mean: 0.4479 (baseline: 0.3169, improvement: +41%)
Best-per-cat mean: 0.588 (baseline: 0.493, improvement: +19%)
Total Serper queries: ~2500 (est. $0.25 of $5 budget)
Plateau: customer_case_studies (0.234), tech_stack (0.269), partnerships_integrations (0.270) — all snippet-limited
