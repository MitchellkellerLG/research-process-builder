# Research Prompt — Autoresearch Loop

Karpathy-style optimization loop for search patterns. You are the agent.
Fixed infrastructure: `pattern_tester.py` + `gt_evaluator.py`. You mutate `master_test_config.json`.

## Loop Protocol

```
1. Save baseline:     py scripts/autoresearch.py --save-baseline
2. Read GT report:    py scripts/validate.py --score
3. Identify the 3 worst-performing categories (lowest GT avg)
4. For each, propose 2-3 new query variant templates
5. Add variants to scripts/master_test_config.json
6. Run targeted test:  py scripts/pattern_tester.py --category [CATEGORY]
7. Evaluate:           py scripts/autoresearch.py --compare
8. Keep variants that improved GT score. Revert the rest.
9. If any category improved >0.05: save new baseline, go to step 2
10. Stop when no improvement or budget exhausted
```

## Budget

- Max 50 Serper queries per iteration (~$0.005)
- Use `--category` and `--company` flags to limit scope
- Total budget per session: $0.50 (5,000 queries)

## Current Category Reliability (from GT layer)

| Category | GT Score | Snippet Extractable? |
|----------|----------|---------------------|
| leadership_people | 1.000 | YES — names in snippets |
| funding_financial | 0.656 | YES — money amounts detectable |
| pricing_intelligence | 0.492 | YES — pricing keywords work |
| founders_ceo | 0.433 | YES — names found ~43% |
| competitor_identification | 0.355 | PARTIAL — names appear ~35% |
| customer_case_studies | 0.262 | PARTIAL — customer names ~26% |
| c_suite_technical | 0.229 | PARTIAL — CTO names hard to find |
| c_suite_commercial | 0.216 | PARTIAL — CFO/CMO names hard |
| company_profile | 0.206 | PARTIAL — keyword overlap helps |
| tech_stack | 0.165 | NO — need page visits |
| partnerships_integrations | 0.149 | NO — need page visits |

## Mutation Strategies

### For PARTIAL categories (target: >0.4 GT)

1. **More specific queries**: "Stripe CTO name 2024" > "Stripe leadership team"
2. **Data platform targeting**: "Stripe CTO site:linkedin.com OR site:crunchbase.com"
3. **Role-specific queries**: "Stripe Chief Technology Officer" (full title, not abbreviation)
4. **Year anchoring**: Add `{{current_year}}` to catch recent appointments

### For NO categories (target: >0.3 GT)

1. **Aggregator sites**: "Stripe tech stack site:stackshare.io OR site:builtwith.com"
2. **Community signals**: "Stripe engineering blog technology" (tech stack from blog)
3. **Marketplace/directory**: "Stripe integrations marketplace" (partnerships)
4. **Comparison sites**: "Stripe vs alternative" (partnerships from comparison pages)

### What makes a GOOD pattern

- Specific: targets the exact data type (names, amounts, quotes)
- Uses quotes for exact phrases: `"case study"` not `case study`
- Uses OR for synonyms: `case study OR customer story OR success story`
- Site operators for high-signal domains
- Includes result-type hints that surface the right page format

### What makes a BAD pattern

- Too generic: "Stripe information" (returns homepage)
- Too narrow: forces exact format that may not exist
- Redundant: same signal as an existing variant
- Expensive: queries that return mostly irrelevant results

## Template Variables

Available in master_test_config.json templates:
- `{{company_name}}` — company name
- `{{domain}}` — company domain
- `{{category}}` — company industry category
- `{{current_year}}` — current year
- `{{role_title}}` — role title for people searches

## Commands Reference

```bash
# Measurement
py scripts/validate.py --score                          # GT accuracy report
py scripts/validate.py --calibrate                      # correlation analysis
py scripts/gt_evaluator.py --category X --json          # raw evaluation data

# Baseline management
py scripts/autoresearch.py --save-baseline [name]       # snapshot scores
py scripts/autoresearch.py --compare [name]             # diff vs baseline
py scripts/autoresearch.py --history                    # trend over time

# Pattern testing (costs Serper credits)
py scripts/pattern_tester.py --category X               # test one category
py scripts/pattern_tester.py --category X --company Y   # test one combo
py scripts/pattern_tester.py --dry-run                  # preview queries

# Analysis
py scripts/tier_analysis.py                             # category classification
py scripts/pattern_tester.py --report                   # full pattern report
```

## Rules

1. Never modify `gt_evaluator.py` or `validate.py` (fixed infrastructure)
2. Never modify ground truth files (verified facts are immutable)
3. Only modify `master_test_config.json` (the patterns)
4. Always save baseline before mutating
5. Always compare after testing — revert if no improvement
6. Track iterations: name baselines sequentially (iter-1, iter-2, ...)
