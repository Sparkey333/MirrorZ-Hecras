# MirrorZ landing + Mac download

Open **`index.html`** in a browser. The primary CTA downloads:

`downloads/MirrorZ-Hecras-0.5.0.dmg`

## Produce the DMG (must be a Mac)

From the repo root on macOS:

```bash
bash packaging/build_macos_dmg.sh
```

That freezes the app, wraps a DMG, and copies it to:

1. `~/Downloads/MirrorZ-Hecras-<ver>.dmg` ← your Downloads folder  
2. `landing/downloads/` ← linked by this page  
3. `releases/` ← archive copy  
4. `~/Desktop/` (if present)

Then reopen `landing/index.html` — the Download button lights up as ready.

## Local preview

```bash
python3 -m http.server 8765 --directory landing
# visit http://127.0.0.1:8765/
```
