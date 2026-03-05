# Research Process Builder

Build validated web research processes through self-annealing loops. Takes any research goal, generates search patterns, tests them against real companies, scores accuracy, and iterates until 90%+ reliability.

**This is the factory that produces research agent prompts.**

The output is a portable `.md` file with 10-12 numbered steps that any agent (Claude Code, Clay, custom GPT, browser agent) can follow to reliably surface specific intelligence about companies.

## What's Inside

```
├── SKILL.md                          # The methodology — how to build research processes
└── processes/
    ├── find-profiles.md              # 10 steps · 100% accuracy
    ├── find-competitors.md           # 12 steps · 93% accuracy
    ├── find-reviews.md               # 12 steps · 95% accuracy
    ├── find-news.md                  # 12 steps · 90% accuracy
    └── find-pr-releases.md           # 10 steps · 90% accuracy
```

## How It Works

The methodology has 6 phases:

1. **Define the goal** — State what you're looking for and what a "good result" looks like
2. **Generate 15-20 candidate search patterns** — Parameterized queries like `[company_name] competitors`
3. **Test patterns against real companies** — 6-10 sample companies across 3 size tiers (enterprise → micro startup)
4. **Score and classify** — Quality (1-5) × Consistency (1-5). Classify as PRIMARY / ENRICHMENT / FALLBACK / KILL
5. **Iterate until 90%+** — Identify failure modes, generate fix patterns, retest
6. **Assemble the process file** — Ordered steps with extract instructions, kill list, output template

Full methodology is in [SKILL.md](SKILL.md).

## The 5 Example Processes

These were built using the methodology above. 138 patterns tested across 11 companies ranging from SpaceX ($400B+) to micro bootstrapped agencies.

| Process                                              | What It Finds                                                                 | Steps | Accuracy |
| ---------------------------------------------------- | ----------------------------------------------------------------------------- | ----- | -------- |
| [find-profiles.md](processes/find-profiles.md)       | Company fact sheet from ZoomInfo, Crunchbase, LinkedIn, PitchBook, Tracxn     | 10    | 100%     |
| [find-competitors.md](processes/find-competitors.md) | Direct competitors with positioning context                                   | 12    | 93%      |
| [find-reviews.md](processes/find-reviews.md)         | Customer sentiment, pain points, employee health, platform ratings            | 12    | 95%      |
| [find-news.md](processes/find-news.md)               | Partnerships, acquisitions, funding, launches, expansions, leadership changes | 12    | 90%      |
| [find-pr-releases.md](processes/find-pr-releases.md) | Official announcements, press releases, blog posts, wire distributions        | 10    | 90%      |

Each process file includes:

- Step-by-step search patterns with exact queries
- What to extract from each search
- Quality and consistency scores
- Conditional routing based on company size (Tier 1/2/3)
- A kill list of patterns that look promising but waste searches
- A structured output template

## How to Use the Processes

### With Claude Code

Drop the process files into your `.claude/skills/` directory. Reference them when researching companies:

```
"Research [company] using the find-competitors process"
```

### With Clay / Claygent

Each step maps to a Clay enrichment column. Use the **Search** query as your Claygent prompt. The **Extract** instructions tell you what to pull from results.

### With Any AI Agent

The processes are plain markdown. Any agent that can run web searches can follow the steps. Feed the process file as context and provide a company name + domain.

## How to Build Your Own Processes

Use [SKILL.md](SKILL.md) to build processes for any research goal:

- Tech stack detection
- Hiring signal monitoring
- Pricing intelligence
- Market sizing
- Content gap analysis
- Anything you can search the web for

The methodology works for any repeatable web research task, not just company intelligence.

## Key Discoveries

Things we learned testing 138 search patterns:

- **`site:reddit.com` is completely broken** — zero results universally. Use `[name] reddit discussion` without the site: operator instead.
- **Year modifiers are the highest-leverage search modifier.** `[name] review 2026` outperforms `[name] review` by a wide margin.
- **ZoomInfo + LinkedIn are the only platforms that cover ALL company sizes**, including 6-month-old startups that Crunchbase and PitchBook haven't indexed.
- **Generic company names (Clay, Keep, Cursor, Harvey) require mandatory disambiguation.** Add category qualifier or use domain as anchor.
- **Company size tiering (Tier 1/2/3) changes which patterns work.** Patterns validated for SpaceX fail for micro startups. Always test across size tiers.
- **Kill lists save more time than pattern lists.** Knowing which searches to NOT run prevents wasting 30-40% of your search budget.

## Validation Methodology

- 138 patterns tested via live web search
- 11 companies: SpaceX, Cohere, Harvey AI, Cursor, Clay, Lovable, Keep, Cluely, Hoo.be, LeadGrow, The Kiln
- Companies ranged from $400B+ valuations to micro bootstrapped
- Each pattern tested against 3-4 companies minimum
- Scoring: Quality (1-5) × Consistency (1-5), optional Freshness (1-5) for news
- Two iteration rounds with 25 fix patterns targeting identified failure modes

## License

MIT
