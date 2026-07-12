# AGENTS.md

## Cursor Cloud specific instructions

MirrorZ-Hecras is a pure-Python educational reimplementation of HEC-RAS
(1‑D steady-flow open-channel hydraulics). It is a single desktop app plus a
scriptable engine — there is no backend/database, so there is nothing to
"start" other than the app itself.

### Environment

- Python deps (`numpy`, `scipy`, `matplotlib`) live in a virtualenv at `.venv`
  created by the startup update script. Activate it with
  `source .venv/bin/activate` before running anything.
- The Tkinter GUI needs the system package `python3-tk` and an X display.
  Both are already present in the Cloud VM (an X server runs on `DISPLAY=:1`);
  `python3-tk` is baked into the VM image, so the update script does not
  reinstall it. If `import tkinter` ever fails, install `python3-tk` via apt.

### Run / test / build

Standard commands are documented in `README.md` (Quick start + Running the
tests). In short, from the repo root with the venv activated:

- Tests: `python -m unittest discover tests -v` (35 tests, all offline).
- Headless solve (no display): `python main.py --run examples/simple_channel.json`
  (add `--report out.html` or `--report out.pdf` to export a report).
- Text REPL (no display): `python main.py --cli`.
- GUI: `DISPLAY=:1 python main.py` — then use Run → Compute Profile and view
  the Profile / Summary tabs. Launch it under tmux so it keeps running.
- No linter/formatter is configured in this repo; `python -m compileall main.py mirrorz`
  is a quick syntax check.

### Gotchas

- `main.py` (GUI) exits gracefully with a printed message if Tk cannot import,
  so a silent GUI failure usually means a missing display, not a code bug —
  prefer `--run`/`--cli` for automated checks.
