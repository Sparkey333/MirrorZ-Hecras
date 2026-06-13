# 30-Day Launch Checklist — from repo to first paid customer

Goal: take the code that exists today and book the **first paid sale**
within 30 days. No new features required — all blockers are
business / packaging / wording.

> Why 30 days: every day past launch is a day of compounding feedback
> from real users. Engineering perfection later, learning loop now.

---

## Week 1 — Make it legally sellable (≈ 6 hours)

### 1.1 Rename the product (1 hour)
- [ ] Choose final name from the shortlist in `docs/pricing.md` §"Naming"
      (current favorites: **ChannelMirror**, **OpenReach**, **RiverStep**,
      **FlowProfile Studio**).
- [ ] Update `APP_NAME` in `mirrorz/__init__.py` — every artifact
      (DMG, MSI, GUI title, installer) follows automatically.
- [ ] Buy the matching `.app` / `.io` / `.com` domain (~$15/yr).

### 1.2 Legal pages (2 hours)
- [ ] Customize `docs/legal/EULA_template.md` — fill bracketed `[FIELDS]`,
      keep the engineering-disclaimer clause (§2) intact.
- [ ] Customize `docs/legal/privacy_policy_template.md` — change nothing
      substantive, fill `[SUPPORT EMAIL]`.
- [ ] Host both at `https://yoursite/eula` and `/privacy`. App stores will
      require the URLs verbatim.

### 1.3 Storefront pick (1 hour)
- [ ] Sign up for **Paddle** (recommended) or **Gumroad**. Both handle
      VAT / sales tax globally — do not try to do this yourself.
- [ ] Create a single product: "App tier, $29.99 one-time".
- [ ] Create webhook → email script that mints a real license key
      (replace the dev parser in `mirrorz/admin.py` — the placeholder
      is marked with `### TWEAK: KEY_SECRET ###`).

### 1.4 Code-signing certs (2 hours)
- [ ] Apple Developer Program ($99/yr) — needed for the Mac DMG path.
- [ ] **OR** skip Apple for now and ship Windows + direct Mac DMG.
- [ ] Azure Trusted Signing ($10/mo) — best value for Windows EXE.
- [ ] Microsoft Partner Center ($19 one-time) — required for the
      Microsoft Store; signing is done by MS, no cert fee. **Highest-ROI
      single step** in this whole list.

## Week 2 — Build the artifacts (≈ 4 hours)

### 2.1 macOS DMG (1 hour, on a Mac)
- [ ] `export CODESIGN_ID="Developer ID Application: …"`
- [ ] `bash packaging/build_macos_dmg.sh`
- [ ] Test the DMG by dragging into Applications on a fresh user account.
- [ ] If you don't have an Apple Dev account: skip the env vars, ship
      ad-hoc-signed DMG with a "first-launch: right-click → Open"
      instruction on the download page.

### 2.2 Windows installer (1 hour, on Windows)
- [ ] Install Inno Setup 6 (free).
- [ ] `packaging\build_windows.bat`
- [ ] Sign the resulting `.exe` with your cert (Trusted Signing one-liner).

### 2.3 Microsoft Store MSIX (2 hours, on Windows)
- [ ] Install Microsoft's free **MSIX Packaging Tool**.
- [ ] Wrap the PyInstaller folder as MSIX, point identity at Partner Center.
- [ ] Submit. Review usually takes 24–72 h.

## Week 3 — Site, copy, and one tutorial (≈ 8 hours)

### 3.1 Landing page (4 hours)
- [ ] One page. Above the fold: animated profile GIF (use the
      `docs/deck/img/profile.png` as a starting frame), tagline
      ("Learn river hydraulics by doing"), $29.99 buy button.
- [ ] Three sections: <strong>Problem</strong> · <strong>Solution</strong>
      (with screenshots) · <strong>FAQ</strong> (incl. "How is this
      different from HEC-RAS?" — see deck slide 7).
- [ ] Footer: EULA + Privacy + Contact.
- [ ] Carrd / Framer / plain HTML — do not over-engineer; ship in an
      afternoon.

### 3.2 First public tutorial (4 hours)
- [ ] Pick ONE concept: "Why critical depth matters."
- [ ] 1,200-word post + 4 figures generated from the app + GIF of the
      cross-section editor.
- [ ] Embed the buy button at the bottom.
- [ ] Publish to your blog + cross-post Dev.to / Medium for SEO juice.

## Week 4 — Launch loud (≈ 6 hours)

### 4.1 Soft-launch beta (Day 22) — friends + 5 professors
- [ ] Personal email to 5 hydraulics professors. Subject line:
      "I built a teaching tool for HEC-RAS — would your TA try it?"
- [ ] Offer free Pro keys to anyone who reports a real bug.

### 4.2 Show-HN (Day 26)
- [ ] Title format: `Show HN: <Name> — a free, Mac-friendly companion
      for learning HEC-RAS hydraulics`.
- [ ] Best window: Tue–Thu 8–10am ET.
- [ ] Be in the comment thread for the first 4 hours. Answer every reply.
- [ ] Linked from r/civilengineering, r/Python, /r/programming
      (modlinkkk-friendly framing) **30 minutes after** HN post.

### 4.3 First sale & invoice (Day 30)
- [ ] If you don't have a paid customer by Day 30, look at your storefront
      analytics. The fix is almost always: landing-page copy, not product.
- [ ] If you do — thank them personally. The first 50 paying customers
      should each get a personal thank-you reply. Single highest-ROI
      activity in this whole document.

---

## Anti-checklist — things NOT to do in the first 30 days

| Tempting | Don't | Why |
|---|---|---|
| Build the Pro tier features | ❌ | Sell Free → App first. Pro waits for demand. |
| Set up a Discord / forum | ❌ | Premature community = empty community. Use email until you have 100+ customers. |
| Wait for 2-D unsteady flow | ❌ | Ship the niche you have. |
| Lower the price "to get traction" | ❌ | $29.99 is already textbook-cheap. Discount = doubt. |
| Add telemetry "just to see" | ❌ | Privacy promise is part of the pitch. Don't break it for vanity. |
| Cold-email engineering firms | ❌ | Wrong customer. Stay in academia / juniors. |
| Take meetings with VCs | ❌ | Don't sell equity for ramen money in a niche market. |

## The single most important sentence

If you have to choose between **shipping the renamed v0.3 DMG with rough
edges** vs **another week of polish before launch**, ship. Reviews,
positioning, and the next feature priority all come from real users —
nothing in your head substitutes for that signal.
