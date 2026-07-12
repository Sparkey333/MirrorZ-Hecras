# Local reference materials (gitignored)

This folder is the **staging area** for private / copyrighted / redistributable-
restricted materials that guide MirrorZ development but must **not** be
committed to GitHub.

## What belongs here

Copy (or symlink) contents from your local Downloads folder:

```
/Users/ansom/Downloads/HECRAS-Breaking Hecras Code/
```

Suggested layout after you sync:

```
docs/reference/
├── README.md                         ← this file (tracked)
├── breaking-hecras-code/             ← Goodell book PDF / notes / Excel workbook
│   └── NOTES.md                      ← your chapter → MirrorZ recipe map
├── hec-ras-install/                  ← USACE installer(s) — do NOT redistribute
├── hec-ras-examples/                 ← Example Data / Steady Examples / Applications Guide
│   ├── Steady Examples/
│   ├── Example Data/
│   └── Applications Guide/
└── other/                            ← anything else from that download bundle
```

## How to sync from your Mac

From the MirrorZ repo root on a machine that can see your Downloads folder:

```bash
# Option A — helper script (creates dirs + copies, skips huge installers by default)
./scripts/sync_local_reference.sh

# Option B — manual
mkdir -p docs/reference/{breaking-hecras-code,hec-ras-install,hec-ras-examples,other}
rsync -av "/Users/ansom/Downloads/HECRAS-Breaking Hecras Code/" docs/reference/other/
# Then sort into the subfolders above.
```

For **Cursor Cloud Agents**: this cloud VM cannot see `/Users/ansom/...`.
Either (1) run the sync locally and attach needed excerpts in chat, or
(2) upload specific non-copyrighted example project trees / notes as
artifacts into `docs/reference/` via a local Cursor session, then ask the
cloud agent to analyze them.

## Redistribution rules (important)

| Material | Commit to public GitHub? | Why |
|---|---|---|
| *Breaking the HEC-RAS Code* PDF / Excel | **No** | Commercial copyright (Goodell / h2ls) |
| HEC-RAS Windows installer | **No** | Redistribute from [HEC](https://www.hec.usace.army.mil/software/hec-ras/), not this repo |
| Raw USACE example `.prj`/`.g01`/`.f01` trees | Prefer **private** / local only | Keep as calibration fixtures; convert distilled JSON into `examples/` |
| Your own notes mapping book chapters → MirrorZ APIs | **Yes** (in `docs/`) | Original work |
| Distilled MirrorZ JSON examples derived from public patterns | **Yes** (in `examples/`) | Original project files |

## What MirrorZ already mirrors from the book

See [`docs/automation.md`](../automation.md) — open → compute → read outputs,
roughness sweeps, discharge sweeps — without Windows COM.
