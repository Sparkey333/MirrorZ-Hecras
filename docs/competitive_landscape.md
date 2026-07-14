# Competitive landscape & alternatives (2026)

Where MirrorZ sits among HEC-RAS, commercial wrappers, next-gen USACE
tools, and creative AI asset pipelines (Higgsfield and peers).

## 1. Hydraulic / river-analysis alternatives

| Product | Price posture | Strength | Gap MirrorZ fills |
|---|---|---|---|
| **HEC-RAS 6.x** (USACE) | Free | Regulatory standard, 1D/2D, sediment, WQ | Opaque math; Windows-first; steep for learners |
| **HEC-RAS 2025** (USACE alpha) | Free | C#/.NET rewrite, modern meshing, cloud-friendly, multi-core | Still production-maturing; 1D teaching UX not the focus yet |
| **CivilGEO GeoHECRAS** | Firm pricing ($1.5k–$8k) | CAD/GIS polish on top of HEC-RAS | Not priced or designed for students |
| **Flood Modeller / TUFLOW / RiverFlow2D** | Commercial | Advanced 2D/urban/flood | Overkill + license for undergrad learning |
| **Breaking the HEC-RAS Code** workflow | Book + Excel/VBA | Automation literacy via COM | Windows COM only; no readable engine |
| **MirrorZ-Hecras** | Free MIT + optional paid shell | Readable 1D steady math, Mac/Linux, companion, Controller API | Not regulatory; no 2D/unsteady (intentional) |

### Positioning rule

Sell **understanding**, not **permits**. HEC-RAS / RAS 2025 remain the
deliverable engines; MirrorZ is the textbook you can run.

## 2. Creative AI for product assets (Higgsfield & peers)

"Upgrading existing assets" for the landing page, pitch deck, and store
listings is a **separate track** from the solver. Recommended stack:

| Tool | Best for | Notes |
|---|---|---|
| **[Higgsfield AI](https://higgsfield.ai/)** | Hero stills → cinematic short videos (Kling / Veo / Sora / Seedance in one studio) | Primary recommendation for launch clips & social |
| **Midjourney / Flux / Seedream** | Still hero & icon explorations | Keep brand palette: teal river `#0e5f6b`, sand `#c4a574`, foam `#f3f7f4` |
| **Cursor GenerateImage / local matplotlib** | Deterministic icons, plot screenshots | Already in-repo (`packaging/make_icons.py`, deck images) |
| **Runway / Pika** | Alternate video vendors | Use if Higgsfield queue/cost is an issue |

Prompt pack (copy/paste): [`docs/assets/higgsfield_prompts.md`](assets/higgsfield_prompts.md).

### Asset upgrade pipeline

1. Generate still hero in Higgsfield (or use `landing/assets/hero-river.png`).
2. Image→video: slow downstream dolly over the river, 4–6 s, no text baked in.
3. Composite UI chrome (profile plot / XS) in the landing or a short editor — **never** put product UI text into the generative model if you need crisp labels.
4. Export MP4/WebM into `landing/assets/` (git-lfs or Releases if large).
5. Keep the educational disclaimer on every paid surface.

## 3. What to build next because of this map

- **Keep** 1D steady + Controller automation (unique vs HEC-RAS for teaching).
- **Track** RAS 2025 as the long-term "compare against" — not a clone target.
- **Ship** better visuals via Higgsfield so the $29 landing does not look like a 2014 engineering blog.
- **Do not** chase CivilGEO feature parity; that market already has PE-stamped tools.
