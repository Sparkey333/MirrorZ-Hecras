# Getting Started — local Mac (DMG → `~/Downloads`)

Source of truth for steps + URLs also lives in `mirrorz/resources.py`
(app Help menu) and `landing/index.html`.

## Clear steps

1. **Get the code on this Mac**
   ```bash
   git clone https://github.com/Sparkey333/MirrorZ-Hecras.git
   cd MirrorZ-Hecras
   # or: git pull
   ```
   PR with the full engine: https://github.com/Sparkey333/MirrorZ-Hecras/pull/2

2. **Optional — sync private HEC-RAS / book materials** (gitignored)
   ```bash
   ./scripts/sync_local_reference.sh \
     "/Users/ansom/Downloads/HECRAS-Breaking Hecras Code"
   ```

3. **Dev env + tests**
   ```bash
   bash scripts/install_dev.sh
   source .venv/bin/activate
   pytest -q
   ```

4. **Build DMG → always `~/Downloads`, then open it**
   ```bash
   bash packaging/build_macos_dmg.sh
   ```
   Writes `~/Downloads/MirrorZ-Hecras-<version>.dmg`, copies into
   `landing/downloads/`, **opens the DMG**, and opens `landing/index.html`.

5. **Install from the DMG**  
   Drag `MirrorZ-Hecras.app` → Applications. If Gatekeeper warns:
   right-click → Open → Open.

6. **Landing page**
   ```bash
   open landing/index.html
   # or: bash packaging/open_landing.sh
   ```

7. **First model in the app**  
   File → Open → `examples/beaver_creek.json` → Run → Compute Profile.  
   Help → Getting Started… / Key Sites… for this checklist and live links.

## Key sites

| Site | URL |
|---|---|
| MirrorZ GitHub (this project) | https://github.com/Sparkey333/MirrorZ-Hecras |
| Pull request #2 (engine + landing + v0.5) | https://github.com/Sparkey333/MirrorZ-Hecras/pull/2 |
| HEC-RAS home (USACE download & docs) | https://www.hec.usace.army.mil/software/hec-ras/ |
| HEC-RAS 2025 (next-gen alpha) | https://www.hec.usace.army.mil/software/hec-ras/2025/ |
| HEC-RAS documentation library | https://www.hec.usace.army.mil/software/hec-ras/documentation.aspx |
| Breaking the HEC-RAS Code (Goodell / The RAS Solution) | https://therassolution.kleinschmidtgroup.com/ |
| Automating HEC-RAS intro post | http://hecrasmodel.blogspot.com/2014/10/automating-hec-ras.html |
| Higgsfield AI (hero / video assets) | https://higgsfield.ai/ |
| Higgsfield AI video studio | https://higgsfield.ai/ai-video |
| CivilGEO GeoHECRAS (commercial alternative) | https://www.civilgeo.com/ |

Educational only — not for regulatory floodplain work. Use official HEC-RAS
for permit / life-safety deliverables.
