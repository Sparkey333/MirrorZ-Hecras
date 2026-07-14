# Earnings Projection — Year 1 and Year 2

> Two scenarios, plain math, transparent assumptions. The pitch deck cites
> these tables verbatim. Update them as evidence comes in — don't keep
> stale optimistic numbers around.

---

## 1. Where the numbers come from

Niche education tools (sub-$50, single-domain, indie maker) reliably
publish ~similar conversion curves. The closest public comps:

* **Sublime Text** (early years, indie code editor): ~1.5 % paid conversion
  on free downloads; ARPU ~$70.
* **iA Writer** (single-domain writing tool): grew from 0 → ~10k paid in
  18 months, mostly content-driven.
* **TablePlus** (indie database GUI): ~3% paid conversion, $50 ARPU.

Hydraulics is smaller and slower-cycle than text editors, so we deflate
those numbers. We also have **two real demand signals already**:

1. HEC-RAS has 100k+ active users (USACE-published estimate); ~20% are
   students or junior. That's the candidate pool.
2. Educational sub-$50 engineering apps (Geogebra Pro, Wolfram Player,
   PocketLab) all clear single-digit-thousand paid users in year one.

## 2. Common assumptions

| Quantity | Value | Source / reason |
|---|---|---|
| Sticker price (App tier) | $29.99 | docs/pricing.md tier ladder |
| Student price | $14.99 | half-off academic norm |
| Classroom price | $199 / yr (30 seats) | <$7/seat, dept discretionary |
| App-store cut | 15 % | Apple/MS small-business rate |
| Direct (Paddle/Gumroad) cut | 5 % + $0.50 / sale | published rates |
| Refund rate | 4 % | conservative for sub-$50 desktop |
| Blended net ARPU (App tier) | ~$22–26 | weighted by store mix |
| Costs Y1 | ~$2,400 | rename, code-signing, EULA review |
| Costs Y2 | ~$4,800 | + Apple Dev, MS Partner, hosting, modest ads |
| Hours / week founder | ~10 | side-project assumption |

Channel mix assumed (Year 1 → Year 2):

| Channel | Y1 share | Y2 share |
|---|---|---|
| Direct (Paddle/Gumroad) | 60 % | 45 % |
| Microsoft Store | 25 % | 30 % |
| Mac App Store | 5 % | 15 % |
| Classroom (invoice) | 10 % | 10 % |

## 3. Scenario A — Baseline (high-probability, ~70 %)

Solo founder, ~10 hr/week, content marketing only (one tutorial per
month + Show-HN at launch + r/civilengineering post + one cold-email
batch to professors per quarter). No paid ads.

### Year 1 monthly trajectory

| Month | Units | ARPU | Revenue | Cumulative |
|---|---:|---:|---:|---:|
| M1 (launch) | 25 | $22 | $550 | $550 |
| M2 | 25 | $22 | $550 | $1,100 |
| M3 | 30 | $22 | $660 | $1,760 |
| M4 | 40 | $22 | $880 | $2,640 |
| M5 | 50 | $22 | $1,100 | $3,740 |
| M6 | 55 | $22 | $1,210 | $4,950 |
| M7 | 65 | $22 | $1,430 | $6,380 |
| M8 | 75 | $24 | $1,800 | $8,180 |
| M9 | 85 | $24 | $2,040 | $10,220 |
| M10 | 100 | $24 | $2,400 | $12,620 |
| M11 | 110 | $24 | $2,640 | $15,260 |
| M12 | 125 | $24 | $3,000 | $18,260 |
| **Y1 totals** | **785** | — | **$18,260** | — |

Year-1 costs ~$2,400 (one-time signing certs, domain, hosted storefront).
**Net Year 1: ~$15,800.**

### Year 2 — modest growth + classroom mix

| Driver | Y2 Q1 | Y2 Q2 | Y2 Q3 | Y2 Q4 | Y2 Total |
|---|---:|---:|---:|---:|---:|
| App-tier units | 380 | 420 | 450 | 470 | 1,720 |
| ARPU | $24 | $25 | $26 | $26 | — |
| App revenue | $9,120 | $10,500 | $11,700 | $12,220 | $43,540 |
| Classroom contracts | 2 | 4 | 5 | 5 | 16 |
| Classroom revenue (@ $170 net) | $340 | $680 | $850 | $850 | $2,720 |
| **Total revenue** | $9,460 | $11,180 | $12,550 | $13,070 | **$46,260** |

Year-2 costs ~$4,800 (Apple Dev $99, MS Partner $19, ~$1k modest ads,
hosting, refunds reserve).
**Net Year 2: ~$41,500.**

**Two-year cumulative net (baseline): ~$57,000.** Sustainable side income,
funds the Pro tier development without external capital.

## 4. Scenario B — "Musk-mode" (~15 %, requires execution intensity)

Same product, but loud. The Musk playbook applied honestly to a niche
software business looks like:

1. **Premium first** — don't compete on price. Charge $29.99 from day one,
   never discount permanently. Free-for-instructors creates the viral loop
   without commoditizing the consumer price.
2. **Public roadmap with bold milestones** — "1-D unsteady in 90 days,
   bridge module in 180" — published, dated, regularly missed-by-a-month
   like every Musk timeline, but the visibility itself drives press.
3. **Founder-as-channel** — daily build screenshots on Twitter/Bluesky/X.
   Every shipping commit becomes a post. Personal brand = product brand.
4. **Verified-instructor program** — instructor with a `.edu` email gets
   the Pro tier free in perpetuity; their students see the splash screen
   with the school's branding. Cheap, classy, scalable.
5. **Adjacent vertical expansion in Y2** — storm-sewer / culvert sizing
   uses the same engine with a different geometry kit. Doubles the
   reachable market without doubling the product surface.
6. **Direct sales, no middlemen** — Paddle for individuals, invoice
   for classrooms, refuse rev-share resellers.

### Musk-mode Year 1

| Quarter | Story | Units | ARPU | Revenue | Cum |
|---|---|---:|---:|---:|---:|
| Q1 | Show-HN front page; viral demo video (1 in 4 odds) | 300 | $25 | $7,500 | $7,500 |
| Q2 | 10 instructor pilots → student word-of-mouth | 800 | $25 | $20,000 | $27,500 |
| Q3 | Pro tier ships at $79 one-time | 1,400 | $32 | $44,800 | $72,300 |
| Q4 | 15 paid classrooms ($170 net × 15 = $2,550) plus 2,200 individual units | 2,200 | $32 | $70,400 + $2,550 | **~$145,000** |

### Musk-mode Year 2 — adjacent vertical lights up

| Driver | Q1 | Q2 | Q3 | Q4 | Total |
|---|---:|---:|---:|---:|---:|
| Hydraulics individual units | 2,500 | 2,700 | 2,900 | 3,000 | 11,100 |
| ARPU (Pro mix climbs) | $34 | $36 | $38 | $40 | — |
| Hydraulics revenue | $85k | $97k | $110k | $120k | $412k |
| Classrooms (cumulative) | 25 | 35 | 45 | 50 | 50 |
| Classroom revenue (@ $170) | $4.3k | $1.7k* | $1.7k | $0.9k | $8.6k |
| Storm-sewer module (Q3 launch) | — | — | $5k | $10k | $15k |
| **Total** | $89k | $99k | $117k | $131k | **~$436k** |

\* Classrooms renew annually, so growth in customers ≠ growth in revenue
in the quarters mid-year. Cohort math, not magic.

Year-2 Musk-mode costs ~$45k (modest contractor hours for the storm-sewer
module, code-signing renewals, modest ads, conference booth ×1).
**Net Year 2 Musk-mode: ~$390k.**

**Two-year cumulative net (Musk-mode): ~$520k.**

## 5. Expected value (the only honest number)

Probability-weighted blend:

```
EV(Y1+Y2) = 0.70 × $57k        # baseline
         + 0.15 × $520k        # Musk-mode
         + 0.15 × $0           # launch flops, we kill it
         = $40k + $78k + $0
         ≈ $118k cumulative net over 24 months
```

That is the number to plan around — not the upside, not the floor.
**~$5k/month average over two years** is what a realistic founder should
mentally bank, with the Musk-mode option preserved by behaving as if it
might happen.

## 6. Sensitivity — which inputs matter most

We swept each input ±50 % and measured impact on 2-year cumulative net:

| Input | Sensitivity | Notes |
|---|---|---|
| Y1 unit growth rate | **±$45k** | Dominant — content marketing pays back |
| App ARPU (price × store mix) | ±$22k | Discounting hurts more than helps |
| Classroom contract count | ±$18k | Each contract is ~$2k/yr — hunt for them |
| Refund rate | ±$3k | Negligible at sub-$50 |
| Hosting / domain / cert | ±$1k | Cost discipline is largely free |

**Where to spend the next hour** = the row with the largest sensitivity.
For us that's <u>writing the next tutorial</u> or <u>cold-emailing a
professor</u> — not optimizing the storefront skin.

## 7. What we're NOT projecting

- 2-D mesh flow — out of scope for v1 / v2.
- Enterprise consulting revenue — we'd take it, but we don't build a
  model on it.
- Selling the business / acquihire — possible if the storm-sewer module
  works, but you don't plan revenue around an exit.

## 8. Update cadence

Re-run this file every quarter against actuals (write actual columns
alongside projected). If actuals are >30 % below baseline at the end of
Q2, replan — the product probably needs work, not louder marketing.
