# research process builder

build validated web research processes through self-annealing loops. takes any research goal, generates search patterns, tests them against real companies, scores accuracy, and iterates until 90%+ reliability.

**this is the factory that produces research agent prompts.**

the output is a portable `.md` file with step-by-step search instructions that any agent (Claude Code, Clay/Claygent, custom GPT, browser agent, OpenAI Agents) can follow to reliably surface specific intelligence about companies.

## what's inside

```
├── SKILL.md                          # the methodology — how to build research processes
└── processes/
    ├── find-profiles.md              # 5 steps · 100% accuracy
    ├── find-competitors.md           # 7 steps · 93% accuracy
    ├── find-reviews.md               # 6 steps · 95% accuracy
    ├── find-news.md                  # 7 steps · 90% accuracy
    ├── find-pr-releases.md           # 5 steps · 90% accuracy
    ├── find-hiring.md                # 5 steps · 93% accuracy
    ├── find-growth-signals.md        # 6 steps · 90% accuracy
    └── find-negativity.md            # 6 steps · 90% accuracy
```

## how it works

the methodology has 6 phases:

1. **define the goal** — state what you're looking for and what a "good result" looks like
2. **generate 15-20 candidate search patterns** — parameterized queries like `{{company_name}} competitors`
3. **test patterns against real companies** — 6-10 sample companies across 3 size tiers (enterprise to micro startup)
4. **score and classify** — quality (1-5) x consistency (1-5). classify as PRIMARY / ENRICHMENT / FALLBACK / KILL
5. **iterate until 90%+** — identify failure modes, generate fix patterns, retest
6. **assemble the process file** — ordered steps with extract instructions, early stopping, kill list, output template

full methodology is in [SKILL.md](SKILL.md).

## the 8 example processes

built using the methodology above. 190+ patterns tested across 11 companies ranging from SpaceX ($400B+) to micro bootstrapped agencies.

| process                                                 | what it finds                                                                 | steps | accuracy |
| ------------------------------------------------------- | ----------------------------------------------------------------------------- | ----- | -------- |
| [find-profiles](processes/find-profiles.md)             | company fact sheet from zoominfo, crunchbase, linkedin, pitchbook, tracxn     | 5     | 100%     |
| [find-competitors](processes/find-competitors.md)       | direct competitors with positioning and justification                         | 7     | 93%      |
| [find-reviews](processes/find-reviews.md)               | individual reviews tagged positive/negative with three-sentence summaries     | 6     | 95%      |
| [find-news](processes/find-news.md)                     | partnerships, acquisitions, funding, launches, expansions, leadership changes | 7     | 90%      |
| [find-pr-releases](processes/find-pr-releases.md)       | official announcements, press releases, blog posts, wire distributions        | 5     | 90%      |
| [find-hiring](processes/find-hiring.md)                 | open roles, departments hiring, ATS platform, hiring velocity                 | 5     | 93%      |
| [find-growth-signals](processes/find-growth-signals.md) | blog activity, lead magnets, social presence, newsletters, pricing maturity   | 6     | 90%      |
| [find-negativity](processes/find-negativity.md)         | customer complaints, negative reviews, controversy, churn signals             | 6     | 90%      |

each process file includes:

- clear `{{input}}` placeholders you fill in before running
- step-by-step search patterns with exact queries
- exact extraction specs (what to pull from each search, three-sentence summaries)
- **stop if** conditions so the workflow stops when it has enough
- a kill list of patterns that look promising but waste searches
- a casual, structured output template

## how to use the processes

### with any AI agent (ChatGPT, Claude, etc.)

paste the process file content as the system prompt or instructions. fill in the `{{inputs}}`. the agent follows the steps, stops when it has enough, and outputs in the specified format.

### with Clay / Claygent

each step maps to a Clay enrichment column. use the **search** query as your Claygent prompt. the **extract** instructions tell you what to pull from results.

### with Claude Code

drop the process files into your `.claude/skills/` directory. reference them when researching companies:

```
"research [company] using the find-competitors process"
```

## how to build your own processes

use [SKILL.md](SKILL.md) to build processes for any research goal:

- tech stack detection
- hiring signal monitoring
- pricing intelligence
- market sizing
- content gap analysis
- anything you can search the web for

## key discoveries

things we learned testing 170+ search patterns:

- **`site:reddit.com` is completely broken** — zero results universally. use `[name] reddit discussion` without the site: operator.
- **year modifiers are the highest-leverage search modifier.** `[name] review 2026` outperforms `[name] review` by a wide margin.
- **zoominfo + linkedin are the only platforms that cover ALL company sizes**, including 6-month-old startups.
- **generic company names (Clay, Keep, Cursor, Harvey) need mandatory disambiguation.** add category qualifier or use domain.
- **kill lists save more time than pattern lists.** knowing which searches to NOT run prevents wasting 30-40% of your search budget.
- **ATS board searches are gold for hiring data.** `site:boards.greenhouse.io [name]` and `site:jobs.ashbyhq.com [name]` return actual role listings with titles and descriptions.
- **`[name] social media twitter youtube` is a trap.** returns product feature content, not the company's actual social accounts. use `site:twitter.com OR site:x.com` with company name instead.
- **OR operators in a single query are powerful.** `[name] alternatives OR competitors OR "vs"` catches 3 result types in one search, tested Q4.75/C4.75.
- **wellfound (formerly angellist) is the T3 lifeline for hiring data.** small startups without greenhouse/lever/ashby pages still have wellfound profiles with employee count, funding, and industry tags.
- **`site:[domain]` with OR operators is the most efficient growth signal detector.** a single query like `site:[domain] blog OR pricing OR newsletter OR demo` catches 4+ signal types in one search.
- **churn-signal searches are a trap.** `[name] "switched from" OR "left" OR "cancelled"` returns marketing content about people switching TO the tool, not FROM it. tested Q2/C1.
- **"do not recommend" and "waste of money" searches return nothing.** people don't use these exact phrases in searchable contexts. use `[name] complaints OR problems` instead.
- **never hardcode the year in process files.** use `{{current_year}}` as an input variable so processes stay valid across years. in Clay, populate from `YEAR({Created At})`.

## validation

- 190+ patterns tested via live web search
- 11 companies: SpaceX, Cohere, Harvey AI, Cursor, Clay, Lovable, Keep, Cluely, Hoo.be, LeadGrow, The Kiln
- companies ranged from $400B+ to micro bootstrapped
- each pattern tested against 3-4 companies minimum
- two iteration rounds with 25 fix patterns targeting identified failure modes

## license

MIT
