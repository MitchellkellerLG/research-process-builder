# find hiring activity

surface who a company is currently hiring for — roles, departments, seniority levels, and hiring velocity.

## inputs

- `{{company_name}}` — the company to research
- `{{domain}}` — their website domain
- `{{category}}` — what they do in 2-3 words. required if the company name is a common word or 6 characters or fewer.

## steps

### step 1: general careers search

search: `{{company_name}} {{category}} careers`

extract from results:

- careers page URL (if found)
- every open role mentioned with title and department
- which job boards have listings (Indeed, Glassdoor, LinkedIn, Built In, Wellfound, etc.)
- total number of open positions (if visible)
- any hiring signals (e.g. "now hiring", headcount mentioned in press)
- three sentence summary of what they're hiring for and at what scale

**stop if:** you found a careers page with 10+ roles listed and can identify the top hiring departments. skip to output.

### step 2: ATS board search

search: `{{company_name}} site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com`

this surfaces the actual applicant tracking system where roles are posted with full descriptions. tested Q5/C4 — the most reliable source for specific role titles and departments.

extract from results:

- ATS platform used (greenhouse, lever, ashby, workday, etc.)
- ATS board URL
- every role title visible in results
- group roles by department (engineering, sales, marketing, operations, etc.)
- three sentence summary of hiring focus areas

**stop if:** combined with step 1, you have a clear picture of what departments are hiring and at what seniority level. skip to output.

### step 3: year-filtered hiring activity

search: `{{company_name}} hiring 2026`

extract from results:

- any recent hiring announcements or press mentions of growth
- new roles not found in steps 1-2
- hiring velocity signals (e.g. "hiring 50 engineers", "doubling the team")
- three sentence summary of recent hiring activity

this pattern works well for Tier 1-2 companies but returns generic hiring-trend articles for obscure companies. skip if the company is very small.

### step 4: department-specific deep dive (only if you need detail on a specific department)

search: `{{company_name}} open roles {{department}}`

replace `{{department}}` with the department that has the most open roles from steps 1-2 (e.g. "engineering", "sales", "marketing").

extract from results:

- specific role titles and seniority levels in that department
- any team structure or reporting info visible
- three sentence summary of what they're building in that department

**stop if:** you have enough role detail to understand the company's hiring priorities. skip to output.

### step 5: careers page direct check

search: `site:{{domain}}/careers`

if no results, try: `site:{{domain}} careers OR jobs OR "open positions"`

extract from results:

- careers page URL (definitive)
- company culture info or hiring philosophy if visible
- benefits or perks mentioned
- three sentence summary

### step 6: fallback for obscure companies (only if steps 1-2 returned almost nothing)

search: `{{company_name}} "we're hiring" OR "join our team" OR "open positions"`

extract from results:

- any hiring signals from social media posts, blog posts, or community mentions
- the company may not have a formal careers page — social posts and linkedin are the signal
- three sentence summary

if even this returns nothing, that's the finding. "no active hiring detected" is a signal — the company may be early stage, bootstrapped, or not growing.

## do not search

- `{{company_name}} jobs site:linkedin.com` — returns location-based noise for ambiguous names (e.g. "Clay" returns jobs in Clay, NY and clay modeler positions)
- `{{company_name}} glassdoor salary` — returns salary estimates, not hiring activity
- `{{company_name}} internships` — too narrow unless specifically asked for
- `{{company_name}} remote jobs` — returns aggregator noise, not company-specific data

## output

```
## hiring activity for {{company_name}}

**hiring status:** [actively hiring / selectively hiring / no active hiring detected]
**open roles found:** [number or estimate]
**careers page:** [url or "not found"]
**ats platform:** [greenhouse / lever / ashby / workday / custom / unknown]

**top hiring departments:**
- [department 1] — [X roles] — [example titles: senior software engineer, staff engineer, etc.]
- [department 2] — [X roles] — [example titles]
- [department 3] — [X roles] — [example titles]

**seniority breakdown:** [mostly senior / mix of levels / mostly junior / unclear]

**hiring signals:**
[two sentences. what does the hiring pattern tell you? are they scaling engineering? building out sales? expanding to new markets?]

**sources:** [list of job boards and platforms where listings were found]
```
