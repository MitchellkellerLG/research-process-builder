# Handoff: Website Signal Subpages — 2026-05-06

## Task

Add two new GTM signal subpages to the LeadGrow website, matching the existing `/gtm-signals` (funding) page pattern. Wire them into home page notification toasts (stack 3 high) and re-introduce the blinking green "live" indicator in the header.

---

## New Pages

### 1. Product Launch Signals — `/gtm-signals/product-launches`

**SEO Title:** `Product Launch Signals — Daily Product Hunt & New Product Alerts | LeadGrow`

**H1:** `Product Launch Signals`

**Tagline:** `New products and features launching daily — spotted before your competitors notice.`

**Data source:** Supabase `product_launches` table

**Key columns for table:** discovered_date, company_name, product_name, tagline, rank, score, launch_type (new_product / new_feature), is_ai, maker_website, categories, employee_count, industry

**Filters needed:** launch_type (new_product / new_feature / all), is_ai (true / false / all), recency (7d / 30d / all), sort by score/rank/date

### 2. Game Industry Signals — `/gtm-signals/game-signals`

**SEO Title:** `Game Industry Signals — New Game Announcements & Studio Funding | LeadGrow`

**H1:** `Game Industry Signals`

**Tagline:** `Game studio funding rounds and major title announcements — fresh intel, daily.`

**Data source:** Supabase `game_signals` table

**Key columns for table:** date_detected, signal_type (announcement / funding), developer, game_title, publisher, funding_amount, genre, platform, developer_domain, summary, source_url

**Filters needed:** signal_type (announcement / funding / all), recency (7d / 30d / all), sort by date/funding_amount

---

## Implementation Pattern — Copy from Funding Signals

All three signal pages share identical architecture. Clone and adapt:

| Existing (funding) | New page needs |
|---------------------|----------------|
| `src/app/gtm-signals/page.tsx` | Keep as-is — this is funding. Create `gtm-signals/product-launches/page.tsx` and `gtm-signals/game-signals/page.tsx` |
| `src/components/ui/FundingTable.tsx` | Create `ProductLaunchTable.tsx` and `GameSignalTable.tsx` — same paginated, filterable pattern |
| `src/app/api/signals/funding/route.ts` | Create `api/signals/product-launches/route.ts` and `api/signals/game-signals/route.ts` |
| `src/lib/supabase.ts` (FundingDiscovery type) | Add `ProductLaunch` and `GameSignal` interfaces |
| Email gate (15 rows free → subscribe) | Same pattern on both new pages |

---

## Home Page: Signal Toast Stack (3 high)

### Current state
- `FundingToast.tsx` — single toast, bottom-right, rotates through funding signals
- Shows after 3s delay, cycles every 6s
- Green pinging dot + "Live Signal" label

### Target state
- Stack 3 toasts vertically (bottom-right):
  1. **Funding signal** (existing) — amber/gold accent
  2. **Product launch signal** — blue accent  
  3. **Game signal** — green accent
- Each toast smaller than current (compact mode)
- Each cycles through its own signal type independently
- Stagger appearance: 3s → 5s → 7s
- All dismissable independently
- Clicking a toast navigates to its signal page

### Implementation
- Refactor `FundingToast.tsx` → generic `SignalToast.tsx` that accepts: signalType, accent color, API endpoint, display formatter
- Render 3 instances in layout with vertical stack offset
- Each instance fetches its own `/api/signals/[type]?limit=50`

---

## Header: Green Blinking Circle

### Current state
- `TopBar.tsx` line ~198: static green dot (6px, `#22c55e`) next to "GTM Signals" nav link
- Only shows when `item.live === true`
- **NOT blinking** — just a static circle

### Target state
- Animate with CSS pulse/blink (match the `FundingToast` ping animation: `@keyframes lg-toast-ping`)
- Keep on "GTM Signals" nav item
- Add dropdown or sub-nav linking to all 3 signal pages:
  - Funding Signals
  - Product Launch Signals  
  - Game Industry Signals

---

## Whiteboard Sketches

Create an on-brand whiteboard-style sketch for each new page (placed in hero section like existing pages use). Use components from `src/components/ds/whiteboard-kit.tsx`:

- `WbArrowCurved`, `WbArrowHooked`, `WbArrowForked`
- `WbHandPointing`, `WbHandThumbsUp`
- Hand-drawn style SVGs, cream/amber/ink palette

### Product Launches sketch concept
- Rocket or launch icon (hand-drawn SVG)
- Arrow from "Product Hunt" → "Your Inbox" flow
- Annotation: "spotted in < 24h"

### Game Signals sketch concept  
- Game controller or joystick icon (hand-drawn SVG)
- Forked arrow: one path → "Funding" one path → "Announcements"
- Annotation: "before the press release hits"

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `C:\Users\mitch\Everything_CC\website\src\app\gtm-signals\page.tsx` | Existing funding page (clone pattern) |
| `C:\Users\mitch\Everything_CC\website\src\components\ui\FundingTable.tsx` | Table component (clone for each type) |
| `C:\Users\mitch\Everything_CC\website\src\components\ui\FundingToast.tsx` | Toast notification (refactor to generic) |
| `C:\Users\mitch\Everything_CC\website\src\components\layout\TopBar.tsx` | Header nav with green dot |
| `C:\Users\mitch\Everything_CC\website\src\app\api\signals\funding\route.ts` | API route (clone for each type) |
| `C:\Users\mitch\Everything_CC\website\src\lib\supabase.ts` | Supabase client + types |
| `C:\Users\mitch\Everything_CC\website\src\components\ds\whiteboard-kit.tsx` | Whiteboard SVG components |
| `C:\Users\mitch\Everything_CC\website\src\app\api\signals\subscribe\route.ts` | Email gate subscribe endpoint |

## Supabase Tables

| Table | Pipeline | Status |
|-------|----------|--------|
| `funding_discoveries` | `series_a_pipeline.py` | Production, 88% GT hit rate |
| `product_launches` | `trigger/src/pipeline/product-launches-ph.ts` | Deployed v20260506.20, daily 9AM ET |
| `game_signals` | `trigger/src/pipeline/game-signals-pipeline.ts` | Deployed v20260506.20, weekly |

## Env Vars (website `.env.local`)

Already has Supabase service role key for funding. Same key reads all 3 tables — no new env vars needed.

---

## Build Order

1. Supabase types + API routes (2 new routes)
2. Table components (2 new, cloned from FundingTable)
3. Signal subpages (2 new page.tsx files with hero + sketch + table + CTA)
4. Refactor FundingToast → SignalToast (generic, 3 instances)
5. TopBar: animate green dot + add signal sub-nav dropdown
6. Whiteboard sketches (2 hand-drawn SVG compositions)
7. Test on dev → deploy
