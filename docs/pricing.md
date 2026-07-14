# Pricing & Go-to-Market Strategy

How to sell an educational hydraulics app **fairly** — to students, teachers,
and engineers — and why specific dollar amounts were chosen.

---

## 1. The market gap (why "app store hydraulics" is genuinely open space)

| Existing option | Price | Gap it leaves |
|---|---|---|
| HEC-RAS itself | Free (US Gov) | Steep learning curve, Windows-only, zero guided learning |
| Commercial wrappers (CivilGEO, Krey, etc.) | $1,500–$8,000/seat | Priced for firms, not learners |
| Textbooks + YouTube | $50–150 | Not interactive, no feedback loop |
| University lab software | site licenses | Unavailable after graduation |

**Nobody sells a $30 "learn open-channel hydraulics by doing" desktop app
with a built-in companion/tutor.** That is the position to occupy: priced
like a good textbook chapter, not like engineering software. The buyer is a
*student, professor, or junior engineer* — not a firm's procurement office.

> Validation note: "unique to today's market" is true **for the niche**, but
> the niche is small. Realistic ceiling is thousands of users, not millions —
> price and effort should match that. This is a sustainable-side-project
> business, potentially a nice consulting funnel, not a venture-scale one.

---

## 2. Recommended model: Free core + paid app ("open core, polished shell")

Keep the **engine (this repo) MIT-licensed and free forever**. Sell the
*packaged convenience*: signed installers, the companion content, updates,
and support. This is the proven model for dev tools (e.g., free CLI + paid
app), and it fits an educational mission: nobody is ever locked out of the
math — they can always build from source.

### Tier table — the actual numbers

| Tier | Price | What's included | Rationale |
|---|---|---|---|
| **Source** | Free (MIT) | Everything in this repo, build it yourself | Trust, education mission, marketing |
| **App** (one-time) | **$29.99** | Signed installers, all 1.x updates, examples library | Textbook-chapter price; impulse-buy range for engineers; above $9.99 "toy" signal |
| **App — student/educator** | **$14.99** | Same, verified via .edu mail or GitHub Education | Half price is the expected academic norm |
| **Classroom license** | **$199/yr** | 30 seats, gradebook-friendly exercise packs, priority email | ≈ $6.60/seat — under any department's no-approval-needed threshold |
| **Pro** (later, v2+) | **$79 one-time or $39/yr** | Batch automation UI (controller.py), report export, mixed-flow when built | Only ship when the features exist; don't pre-sell |

### Why one-time instead of subscription for individuals?

* The app has **no server costs** — charging monthly for static software
  erodes trust with exactly the audience (students) we court.
* "Pay once, free updates within major version, paid upgrade at 2.0"
  (the classic *Sketch/Affinity* model) is widely perceived as the fairest
  structure in 2026 and consistently outperforms subscriptions for tools
  under $50.
* The classroom tier *is* annual, because that matches how institutions
  budget — fairness means matching the buyer's mental model, not one rule.

### Price-point psychology, briefly

* **$29.99** sits in the "serious tool, trivial expense" band: above the
  $0.99–9.99 mobile-junk signal, below the $49+ "needs justification" line.
* **App store fee math:** Apple/Microsoft take 15 % (small-business
  programs) → ~$25.49 net. Direct sales via Paddle/Gumroad take ~5 % +
  fees → ~$28. Keep the same *customer* price everywhere; treat the store
  cut as a customer-acquisition cost.
* Launch discount (20 %, two weeks) beats a permanently lower price — it
  creates urgency without anchoring low.

---

## 3. Models considered and rejected

| Model | Why not |
|---|---|
| Fully free + donations | Hydraulics niche too small for donation volume |
| Subscription-only | Hostile to students; no recurring cost to justify it |
| Freemium with crippled solver | Poisons the educational mission; bad reviews |
| $199+ pro pricing | That market already belongs to certified commercial tools; we *cannot* serve it (see §5) |
| Ads | In an engineering tool? No. |

---

## 4. Naming — **read this before selling anything** ⚠️

"HEC-RAS" is the name of a U.S. Army Corps of Engineers product, and "RAS"
appears in their related marks. The *software* is public domain; the *name*
is not yours to sell under:

* **Fine:** "compatible with HEC-RAS concepts", "inspired by HEC-RAS"
  in descriptions — truthful, nominative references.
* **Not fine for a paid product:** "Hecras" *in the product name itself*
  ("MirrorZ-Hecras") — app stores reject look-alike names, and it
  invites a USACE objection plus buyer confusion.

**Action item before first paid release:** rename the *product* (the repo
can keep its name). Candidates in the codebase's spirit: **ChannelMirror**,
**OpenReach**, **FlowProfile Studio**, **RiverStep**. One `sed` over
`APP_NAME` in `mirrorz/__init__.py` + the packaging files is all it takes —
that constant was centralized for exactly this reason.

---

## 5. Liability & positioning (this shapes pricing more than psychology)

This software **must be sold as an educational tool**, never as a design
tool. Real floodplain/levee work legally requires validated software and a
licensed PE's stamp. That's why:

* The EULA (`docs/legal/EULA_template.md`) contains a conspicuous
  "not for regulatory or life-safety design" clause — **non-negotiable**.
* Marketing copy says "learn", "explore", "understand" — never "design",
  "certify", "FEMA".
* Staying educational *protects the low price*: the moment you market
  design capability you inherit professional-liability insurance costs
  that $29.99 cannot carry.

---

## 6. Launch sequence (cheapest validation first)

1. **Now:** GitHub release + free DMG/EXE artifacts → gauge stars/downloads.
2. **+1 month:** Direct paid sales via Gumroad/Paddle at $29.99 (they handle
   VAT/sales tax — do not do this yourself). Landing page with the profile
   plot GIF.
3. **+2–3 months:** Microsoft Store (cheapest store entry, $19 once,
   Microsoft signs the package), then Mac App Store via Briefcase port.
4. **Each release:** one teaching artifact (blog post or video: "what is
   critical depth, with a live model") — content marketing is *the* channel
   for educational tools; teachers share it for you.

## 7. Success metrics to decide whether to invest further

* 1,000 free downloads or 100 paid in 6 months → keep going, build Pro tier.
* A professor adopts the classroom tier unprompted → double down on
  classroom features; that's the actual scalable revenue.
* Below that → keep it as a portfolio/teaching project; it still pays in
  reputation.
