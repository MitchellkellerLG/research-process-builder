# Handoff: Semantic Domain Validation — Trigger Pipeline

## What was done

### Python pipeline (COMPLETE, committed to master)
- `scripts/pipeline_base.py` — added `validate_domain_semantic()` method + wired into `enrich_companies()`
- `scripts/test_semantic_validation.py` — 5/5 tests passing
- Commit: `0d8a38c`

### Trigger.dev pipeline (IN PROGRESS, NOT committed)
- `trigger/src/pipeline/openai.ts` — added `SemanticValidationResult` interface + `validateDomainSemantic()` function at bottom of file. **Done.**
- `trigger/src/pipeline/pipeline.ts` — **NOT YET UPDATED.** Needs wiring.

## What still needs to happen

### 1. Wire `validateDomainSemantic` into `pipeline.ts`

In `enrichOneCompany()` (line ~254), after domain is resolved and before `buildEnrichedRecord`, add:

```typescript
// After: domain = result.domain; domainSource = result.source;
// Before: logger.info(...)

if (domain !== "not_found" && articleText) {
  const vresult = await validateDomainSemantic(sourceUrl, company.company_name, domain, articleText);
  const vstatus = vresult.status;

  if (vstatus === "Wrong") {
    const corrected = vresult.correctDomain?.trim() ?? "";
    if (corrected && corrected !== "not_found" && corrected !== "not_stated" && !isDomainBlocked(corrected)) {
      logger.info(`Semantic: corrected ${domain} -> ${corrected} (${vresult.reason})`);
      domain = corrected;
      domainSource = "semantic_validation";
      if (vresult.correctCompanyName && vresult.correctCompanyName !== company.company_name) {
        company = { ...company, company_name: vresult.correctCompanyName };
      }
    } else {
      logger.info(`Semantic: rejected ${domain}, no valid correction (${vresult.reason})`);
      domain = "not_found";
      domainSource = "semantic_rejected";
    }
  } else if (vstatus === "Unclear") {
    logger.info(`Semantic: unclear (${vresult.reason}) — demoting confidence`);
    company = { ...company, confidence: "low" };
  } else {
    logger.info(`Semantic: correct`);
  }
}
```

### 2. Add import to `pipeline.ts`

Change the existing openai import line from:
```typescript
import { extractWithOpenAI } from "./openai.js";
```
to:
```typescript
import { extractWithOpenAI, validateDomainSemantic } from "./openai.js";
```

### 3. TypeScript check + deploy

```bash
cd trigger
npm run build   # or bunx tsc --noEmit
```

Then push to Trigger.dev (check CLAUDE.md or existing deploy SOP for exact command).

## Key files

| File | Status |
|------|--------|
| `scripts/pipeline_base.py` | Done, committed |
| `scripts/test_semantic_validation.py` | Done, committed |
| `trigger/src/pipeline/openai.ts` | Done, NOT committed |
| `trigger/src/pipeline/pipeline.ts` | Needs wiring (see above) |

## How it works (both pipelines)

After domain resolution waterfall (article regex → GPT extract → Serper agent):
- `Wrong` + valid correction → replaces domain, passes through blocked-domain check
- `Wrong` + no valid correction → marks domain as `not_found`
- `Unclear` → demotes company confidence to `low` (review queue only, skipped from Supabase)
- `Correct` → passes through unchanged

Key: uses **raw** article text so markdown hyperlinks like `[Company](https://co.io)` are visible to the LLM — hyperlinked company name = strongest signal for correct domain.

## Model used
- Python: `gpt-4o-mini`
- Trigger: `gpt-4.1-mini` (matches rest of trigger pipeline)
