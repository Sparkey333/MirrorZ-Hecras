# Changelog

All notable changes to MirrorZ-Hecras. Format follows
[Keep a Changelog](https://keepachangelog.com); versions follow SemVer.

## [0.2.0] - 2026-06-11

### Added
- **Persistent settings** (`mirrorz/settings.py`): unit system, solver
  tolerance/iterations, friction-averaging method, freeboard requirement,
  welcome-screen toggle, window geometry, and recent files — stored in the
  platform-standard per-user config directory and editable live via
  **Tools → Settings…** in the GUI.
- **Automation controller** (`mirrorz/controller.py`): a scripting API
  inspired by the HECRASController workflow from *Breaking the HEC-RAS
  Code* (Goodell) — `open_project / set_current_plan / compute_current_plan
  / output / compute_sweep / set_manning_n`. See `docs/automation.md`.
- **Packaging kit** (`packaging/`): PyInstaller spec, macOS DMG build
  script (codesign + notarize + copy-to-Desktop), Windows installer
  (Inno Setup) script, Linux tarball script, programmatic icon generator,
  and hardened-runtime entitlements. Guide in `docs/packaging.md`.
- **Business docs**: pricing strategy with tier table (`docs/pricing.md`),
  EULA and privacy-policy templates (`docs/legal/`), including the
  product-rename trademark caution and engineering-liability disclaimer.
- `pyproject.toml`: pip-installable package with `mirrorz-hecras`
  GUI entry point; version read from `mirrorz/__init__.py`.
- GUI: recent-files menu, **File → Export Summary CSV…**, version in the
  window title, window size remembered between sessions.
- `--version` flag on `main.py`.
- Tests for settings round-trip/sanitization and controller recipes
  (14 tests total).

### Changed
- Package renamed `src/` → `mirrorz/` (required for proper distribution;
  imports are now `from mirrorz import …`).
- Version bumped to 0.2.0; `APP_NAME` centralized in `mirrorz/__init__.py`
  so a future product rename is a one-line change.

### Fixed
- **Matplotlib backend clash**: `plotting.py` no longer force-switches to
  the non-interactive Agg backend when a display is available, which could
  override the GUI's TkAgg selection (import-order dependent).
- **Stale default argument**: `analyzer.freeboard_check` resolved its
  `required` threshold at definition time, so runtime settings changes were
  ignored; now resolved at call time.
- **Solver performance**: critical depth is memoized per (section, Q)
  instead of being re-solved on every standard-step iteration (~30× fewer
  root-finder calls per section); cache is invalidated on geometry edits.

## [0.1.0] - 2026-06-11

Initial release: 1D steady-flow standard-step solver, cross-section
geometry with LOB/channel/ROB panels, critical/normal depth, Tk GUI,
companion wizard, analyzer (rating curves, freeboard), JSON projects,
example models, smoke tests.
