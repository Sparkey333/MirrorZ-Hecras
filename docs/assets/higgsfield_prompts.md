# Higgsfield AI & peer prompts — MirrorZ asset upgrade

Use these in [Higgsfield](https://higgsfield.ai/) (or Flux / Midjourney / Kling)
to upgrade landing, store, and social assets. Prefer **no baked-in text**;
add MirrorZ wordmark in HTML/CSS or After Effects.

Brand anchors: river teal `#0e5f6b`, deep `#083943`, sand `#c4a574`, foam `#f3f7f4`.

---

## A. Still — full-bleed hero (16:9)

```
Photoreal cinematic landscape, clear mountain river flowing toward camera
over gravel and sand banks at blue hour, soft mist in distant pines,
muted teal-green water with gentle riffles, elevated bank viewpoint looking
downstream, natural atmospheric haze, no people, no text, no logos,
no UI overlays, 16:9, high detail water surface
```

Negative: `text, watermark, logo, illustration, cartoon, purple neon, sci-fi`

## B. Still — cross-section teaching vibe

```
Photoreal cutaway view of a small natural river channel in soft daylight,
visible left overbank vegetation, main channel gravel bed, right overbank,
calm water surface, educational documentary still, no labels, no diagrams,
no text, landscape orientation
```

## C. Video — 5 s hero loop (Higgsfield image→video / Kling / Veo)

Start from hero still. Motion prompt:

```
Slow cinematic push downstream along the river centerline, subtle camera
drift, gentle water motion and soft mist, natural light only, no text,
no transitions, seamless loop-friendly ending
```

Camera: mild dolly-in, 24–30 fps, 5–6 seconds.

## D. Social cut (vertical 9:16)

```
Same river scene reframed vertical, banks left/right, water filling lower
two-thirds, soft morning light, no text, no logo
```

Then add on-screen captions in CapCut/Descript: “MirrorZ — read the
water-surface profile.”

## E. Alternatives if Higgsfield is unavailable

| Need | Fallback |
|---|---|
| Hero still | `landing/assets/hero-river.png` (in-repo) or Flux |
| Product truth | Real GUI screenshot / matplotlib profile (`docs/deck/img/`) |
| Icon | `python packaging/make_icons.py` (deterministic) |
| Pitch motion | Screen recording of Compute Profile (sibling setup agent path) |

## F. Do not generate

- Fake HEC-RAS UI chrome that could confuse buyers
- FEMA / flood-insurance imagery implying regulatory use
- “Hecras” wordmarks that fight the rename plan in `docs/pricing.md`
