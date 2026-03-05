---
name: research-process-builder
description: Build validated web research processes through self-annealing loops. Takes a research goal, generates search steps, tests against sample companies, scores accuracy, and iterates until 90%+. Use when creating new research workflows, building claygent/agent prompts, or systematizing any web research task.
---

# Research Process Builder

Build validated, step-by-step web research processes through iterative testing. Takes any research goal, generates search patterns, tests them against real companies, scores accuracy, and loops until the process hits 90%+ reliability.

This is the factory that produces research agent prompts. The output is a portable .md file with step-by-step instructions that any agent (Claude Code, Clay, custom GPT, browser agent) can follow to reliably surface specific intelligence.

## When To Use

- Building a new research workflow for any topic (company intel, market sizing, hiring signals, tech stack detection)
- Creating claygent or web research agent prompts that need to work reliably
- Systematizing any manual web research you do repeatedly
- Someone asks "how do I research X about companies?"

## When NOT To Use

- Running an existing research process (load the process .md directly)
- One-off research where you just need the answer
- Data enrichment at scale (use a dedicated enrichment tool)

## Example Processes (built with this methodology)

| Process                   | File                            | Steps | Accuracy |
| ------------------------- | ------------------------------- | ----- | -------- |
| Find competitors          | `processes/find-competitors.md` | 8     | 93%      |
| Find reviews              | `processes/find-reviews.md`     | 6     | 95%      |
| Find recent news          | `processes/find-news.md`        | 7     | 90%      |
| Find PR/releases          | `processes/find-pr-releases.md` | 5     | 90%      |
| Find third-party profiles | `processes/find-profiles.md`    | 5     | 100%     |

---

## The Build Loop

### Phase 1: Define the Research Goal

Before generating any patterns, nail down exactly what "success" looks like.

**Step 1: State the goal in one sentence.**

> "Given a company name and domain, find [WHAT] with [ACCURACY TARGET]% reliability."

Examples:

- "Given a company name and domain, find their top 5 competitors with 90%+ reliability."
- "Given a company name and domain, find recent news from the last 6 months with 90%+ reliability."
- "Given a company name and domain, find their tech stack with 85%+ reliability."

**Step 2: Define what a "good result" looks like.**

Write 3-5 bullet points describing what a successful output contains. Be specific.

> For competitors:
>
> - At least 3 named competitors (not just categories)
> - Competitors are in the same market segment (not adjacent industries)
> - At least one source is a structured platform (G2, Capterra, Tracxn)
> - Head-to-head positioning is surfaced (how they differ)

**Step 3: Pick 6-10 sample companies across size tiers.**

You MUST test across company sizes. Patterns that work for SpaceX break for startups.

| Tier             | Description                            | Pick 2-3                                       |
| ---------------- | -------------------------------------- | ---------------------------------------------- |
| Tier 1 (Known)   | Fortune 500, unicorns, household names | SpaceX, Stripe, Salesforce                     |
| Tier 2 (Mid)     | Growth-stage, funded, some press       | Cohere, Harvey AI, Lovable                     |
| Tier 3 (Obscure) | Micro, bootstrapped, early-stage       | Your company, a friend's startup, a niche tool |

**Include at least one company with an ambiguous name** (Clay, Keep, Cursor, Harvey) to stress-test disambiguation.

### Phase 2: Generate Initial Pattern Candidates

Generate 15-20 search pattern candidates. Each pattern is a parameterized search query.

**Pattern anatomy:**

```
[disambiguated_name] competitors
  ^variable             ^fixed search intent
```

**Generation rules:**

1. Start with the obvious: `[name] [goal keyword]` (e.g., `[name] competitors`)
2. Add synonym variants: `[name] alternatives`, `[name] rivals`
3. Add platform-specific: `site:g2.com [name]`, `site:crunchbase.com [name]`
4. Add natural language: `who competes with [name]`, `what is [name] known for`
5. Add category-derived: `best [category] tools 2026`
6. Add year-anchored: `[name] [keyword] 2026`
7. Add domain-anchored: `[domain] [keyword]`
8. Add negation variants: `[name] vs`, `[name] compared to`

**Generate at least 15.** You'll kill half of them. That's the point.

### Phase 3: Test Patterns (The Anneal Loop)

This is where the methodology earns its accuracy. Test every pattern against real companies and score the results.

**For each pattern, test against 3-4 sample companies (mix of tiers).**

Run the search. Score each result on two dimensions:

| Dimension       | Score | Meaning                                                                                      |
| --------------- | ----- | -------------------------------------------------------------------------------------------- |
| Quality (Q)     | 1-5   | How useful/specific are the results? 5 = exactly what we need. 1 = irrelevant noise.         |
| Consistency (C) | 1-5   | Does it work across big AND small companies? 5 = works for all. 1 = only works for one tier. |

**Optional third dimension for time-sensitive goals:**

| Dimension     | Score | Meaning                                                          |
| ------------- | ----- | ---------------------------------------------------------------- |
| Freshness (F) | 1-5   | How recent are the results? 5 = last 3 months. 1 = 3+ years old. |

**Record everything.** For each pattern + company test:

```
Pattern: [name] competitors
Company: Clay (Tier 2, disambiguated as "Clay GTM")
Results: G2 comparison page, CBInsights competitor list, 2 blog roundups
Quality: 5 — Direct competitor names with positioning
Consistency: 4 — Works for known companies, weaker for Tier 3
Verdict: PRIMARY STACK
```

### Phase 4: Score and Classify

After testing all patterns, classify each one:

| Classification | Criteria                          | Action                                      |
| -------------- | --------------------------------- | ------------------------------------------- |
| PRIMARY        | Q >= 4 AND C >= 4                 | Include in the core process                 |
| ENRICHMENT     | Q >= 4 AND C >= 3                 | Include as conditional step (Tier 1-2 only) |
| SITUATIONAL    | Q >= 4 AND C <= 2                 | Include with explicit "when to use" guard   |
| FALLBACK       | Q >= 3, useful when primary fails | Include in Tier 3 fallback section          |
| KILL           | Q <= 2 OR consistently irrelevant | Add to kill list with reason                |

**Calculate stack accuracy:**

```
accuracy = (PRIMARY + ENRICHMENT patterns scoring Q4+C4+) / (total patterns tested) * 100
```

### Phase 5: Iterate Until 90%+

If accuracy < 90%, identify the failure modes:

| Failure Mode                    | Fix                                                             |
| ------------------------------- | --------------------------------------------------------------- |
| Ambiguous name pollution        | Add disambiguation variants (name + category, domain anchor)    |
| Tier 3 companies return nothing | Add fallback patterns (domain search, LinkedIn, hiring signals) |
| Results are stale               | Add year modifiers (2025, 2026)                                 |
| Wrong type of results           | Add more specific intent words, try site: operators             |
| Platform-specific gaps          | Add platform variants (B2B → G2, B2C → Trustpilot)              |

**Generate 5-10 fix patterns targeting the specific failure modes.** Test them the same way. Recalculate accuracy.

**Repeat until all classifications combined yield 90%+ accuracy.**

Typical iterations needed:

- Simple goals (profiles, ratings): 1 iteration
- Medium goals (competitors, reviews): 2 iterations
- Hard goals (news, PR for small companies): 2-3 iterations

### Phase 6: Assemble the Process File

Take the surviving patterns and arrange them into a numbered step sequence.

**Process file structure:**

```markdown
# [Research Goal] Process

**Accuracy:** [X]% validated across [N] companies
**Built:** [date]
**Methodology:** research-process-builder, [N] patterns tested

## Preprocessing

[Disambiguation and tier detection steps]

## Steps

### Step 1: [Most reliable pattern — runs for ALL companies]

**Search:** `[pattern]`
**Extract:** [what to pull from results]
**Quality:** [score] | **Consistency:** [score]

### Step 2: [Second most reliable]

...

### Step 7-8: [Tier 1-2 enrichment — conditional]

**When:** Tier 1-2 only
...

### Step 9-10: [Tier 3 fallbacks — conditional]

**When:** Tier 3 only, primary steps returned thin results
...

## Kill List

- `[pattern]` — [why it fails]

## Output Template

[Structured output the agent should produce]
```

**Ordering rules:**

1. Highest consistency patterns first (they work for everyone)
2. Highest quality patterns second (they give the best results)
3. Conditional/enrichment patterns in the middle
4. Fallback patterns at the end
5. Kill list at the bottom

**Step count target:** 5-8 steps is the sweet spot. Each step should earn its place by improving accuracy. More than 10 means your primary stack is too weak. If you can hit 90%+ in 5 steps, stop there.

---

## Quality Checklist

Before calling a process "done":

- [ ] Tested against 6+ companies across 3 tiers
- [ ] At least one ambiguous-name company tested
- [ ] Stack accuracy >= 90%
- [ ] Kill list includes patterns that LOOK promising but fail (saves future agents from wasting searches)
- [ ] Output template is specific enough that two agents would produce similar reports
- [ ] Each step has explicit "what to extract" instructions
- [ ] Conditional steps have clear "when to run" guards
- [ ] Fallback steps have clear "when to trigger" criteria

---

## Preprocessing (Shared Across All Processes)

Every process built with this methodology should include these two preprocessing steps. They're universal.

### Name Disambiguation

Check if the company name is ambiguous:

- 6 characters or fewer
- Common English word
- Shares name with something famous

If ambiguous: add category qualifier or use domain. If not: use name as-is.

### Company Size Detection

Search: `[name] company overview`

Count third-party profiles in results:

- 5+ profiles → Tier 1 (Known) → full pattern stack
- 2-4 profiles → Tier 2 (Mid) → core stack, skip niche outlets
- 0-1 profiles → Tier 3 (Obscure) → core + fallbacks, thin results are the signal

---

## Worked Example: How "Find Competitors" Was Built

This traces the exact methodology used to build `processes/find-competitors.md`.

**Phase 1 — Goal:** "Given a company name and domain, find their top 5 competitors with 90%+ reliability."

**Phase 2 — 15 candidate patterns generated:**
`[name] competitors`, `[name] alternatives`, `best [category] tools 2026`, `who competes with [name]`, `site:g2.com [name] alternatives`, `[name] vs`, `[name] market landscape`, `[name] competitive intelligence`, `site:crunchbase.com [name] competitors`, `[domain] competitors site:similarweb.com`, `[name] rival companies`, `[name] similar to`, `[category] market map 2026`, `[name] [category] competitors`, `[domain] competitors`

**Phase 3 — Tested across:** SpaceX, Clay, Harvey AI, Cursor, Cohere, Lovable, Keep, Cluely, Hoo.be (11 companies, 3 tiers)

**Phase 4 — Classification:**

- PRIMARY (5): competitors, alternatives, best tools 2026, who competes with, site:g2.com
- ENRICHMENT (2): [name] vs [competitor], market map 2026
- FALLBACK (3): [name] [category] competitors, [domain] competitors, [name] similar to
- KILL (5): market landscape, competitive intelligence, site:crunchbase.com, site:similarweb.com, rival companies

**Initial accuracy:** 71% (5/7 primary+enrichment at Q4+/C4+)

**Phase 5 — Iteration 1:** Added disambiguation variants for Clay, Keep, Harvey. Retested. 6/7 patterns now Q4+/C4+. Accuracy: 86%.

**Phase 5 — Iteration 2:** Added `[name] [category] competitors` as primary for ambiguous names. Retested. 93%.

**Phase 6 — Assembled into 8-step process.** See `processes/find-competitors.md`.
