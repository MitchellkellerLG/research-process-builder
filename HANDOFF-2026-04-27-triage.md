# GT Validation Triage — 2026-04-27

Two conflicts surfaced by `gt_validation.py --sample 2` on 2026-04-27. Investigated by scraping each source URL + verifying domains.

---

## Mosaic — 3 dup rows, all same $18M Series A

All three Supabase rows describe the **same funding event**: Mosaic, AI-driven deal modeling platform for private equity, $18M Series A led by Radical Ventures. Confirmed by reading all 3 source URLs.

| id | stored domain | source | actual company at that domain | verdict |
|---|---|---|---|---|
| 18 | mosaicco.com | ventureburn.com/mosaic-raises-18m | **The Mosaic Company** (NYSE-listed potash/phosphate mining giant — wrong company entirely) | DELETE |
| 145 | mosaic.pe | linkedin grishinrobotics post | **Mosaic — The Future of Deals Analysis. AI Deal Modeling Platform** (matches article) | KEEP (canonical) |
| 142 | mosaic.ai | vcnewsdaily.com/mosaic-ai/... | **mosaic.ai = AI Recruiting & HR Q&A** (different company despite slug match) | DELETE |

**Root cause of the dup:** cross-day dedup did not merge id=18 (Apr 22) with id=145 / id=142 (Apr 25) because each row resolved to a different domain. `match_existing_company` checks domain-exact OR fuzzy name; with same name "Mosaic" it should have merged on the name path. Likely the merge logic didn't run on id=18 (Apr 22 was before commit `a181137` that added cross-day dedup), and on Apr 25 the same-batch insertion of id=145 + id=142 happened in one push so neither saw the other.

**Verified domain candidates** (scraped 2026-04-27):
- `mosaic.pe` — "The Future of Deals Analysis. World's Leading AI Deal Modeling Platform" ✓
- `mosaic.ai` — AI Recruiting / HR Q&A ✗
- `mosaicco.com` — The Mosaic Company (potash mining) ✗
- `mosaic.tech` — redirects to HiBob FP&A ✗
- `getmosaic.com` — parked / lander ✗

**Action required:** DELETE rows 18 and 142 in Supabase. Keep 145. Add `Mosaic → mosaic.pe` to KNOWN_GOOD (already there per handoff). Sources and source_count from id=18 + id=142 should ideally be merged into 145 to preserve the multi-source signal — see proposed SQL below.

---

## Kajaani — likely bad extraction

| id | stored domain | source | amount | round | verdict |
|---|---|---|---|---|---|
| 141 | iiwari.com | instagram.com/p/DXg9AJAiB47/ | "€1.7 billion" | Series C | INVESTIGATE |

**Why suspicious:**
- Source is an Instagram post (no scrapeable body)
- Amount "€1.7 billion" Series C is implausible for Iiwari (a small Finnish indoor positioning company in Kajaani — this is a $5-20M-stage company, not a multi-billion-EUR Series C)
- The "1.7 billion" pattern matches **Ricerca** (Japanese AI co that raised 1.7B JPY ≈ $11M) — see stage1-2026-04-26.json idx=1 ("AI Market Watch's Post" snippet truncated). Looks like Stage 2 mis-extracted "Kajaani" as the company name from an article that was actually about Ricerca, OR the row predates the v004 anneal.

**Proposed action:** DELETE row 141. The domain mapping `Kajaani → iiwari.com` is preserved separately in `BAD_DOMAIN_CASES` in `eval_pipeline.py`, so the GT signal is not lost. If the row turns out to be a real Iiwari Series C (low likelihood), it can be re-ingested when the actual article surfaces.

---

## Proposed cleanup SQL

```sql
-- Mosaic dedup: merge sources from 18 + 142 into 145, then delete dups.
-- (run only after confirming with the team — destructive)

-- Increment source_count + raise score on the canonical row.
UPDATE funding_discoveries
   SET source_count = (
         SELECT COALESCE(SUM(source_count), 0)
           FROM funding_discoveries WHERE id IN (18, 142, 145)
       )
 WHERE id = 145;

DELETE FROM funding_discoveries WHERE id IN (18, 142);

-- Kajaani: outright delete (likely bad extraction)
DELETE FROM funding_discoveries WHERE id = 141;
```

After running, re-trigger `gt_validation.py --reset-conflicts` to re-verify and clear the conflict state.

---

## Bug surfaced for follow-up

`match_existing_company` in `domain_resolver.py` should merge same-name rows even when domains differ, IF one of the domains is in BLOCKED_DOMAINS or a known-bad mapping. Current behavior: id=18 (mosaicco.com — a real domain not in the blocklist, but for the wrong company) survived without merging because cross-day dedup wasn't running yet. New rows on the same day with the same name SHOULD have merged via the name-similarity path.

Worth a one-line audit pass to confirm `match_existing_company` is being invoked on every push, and that the recent-window fetch isn't silently returning empty.

---

## Cost of this triage

- Spider scrapes (5 candidate domains + 4 source URLs): ~$0.005
- Domain agent (1 call): ~$0.02
- Total: ~$0.025
