# Changelog

All notable changes to MirrorZ-Hecras. Format follows
[Keep a Changelog](https://keepachangelog.com); versions follow SemVer.

## [0.3.0] - 2026-06-13

### Added
- **Admin tab** in the GUI: Edition + License (with `Activate` / `Deactivate` /
  `Buy…`), Design Choices (theme picker with live palette swap), Classroom
  Branding fields (institution / instructor / course code, gated on the
  classroom edition), Telemetry consent toggle (opt-in, default OFF and
  documented to be inert until an endpoint exists), About panel.
- **`mirrorz/admin.py`** — edition model with per-edition feature flags
  (`free` / `pro` / `classroom`), themed palette set (`river`,
  `blueprint`, `print`, `colorblind`), and offline checksum-based
  `LicenseManager`. Persisted to `admin.json` alongside `settings.json`.
- **CSV export gated by edition** — paid-feature gate wired through the
  `csv_export` flag so the same code path serves both editions.
- **Plot palette swap & branding caption** — `plotting.apply_palette()`
  lets the admin tab apply a theme without restart; branding caption
  appears on cross-section and profile titles when classroom is active.
- **HTML pitch deck** (`docs/deck/pitch.html`) — 12-slide single-file
  deck with embedded showcase plots; arrow-key navigation, print-to-PDF,
  and deep-link fragments.
- **Earnings projection** (`docs/earnings_projection.md`) — baseline
  (~70 % probability) and "Musk-mode" (~15 %) Y1/Y2 scenarios with channel
  mix, refund rates, sensitivity sweep, and an expected-value blend
  (~$118 k over 24 months).
- **30-day launch checklist** (`docs/launch_checklist.md`) — weekly steps
  and an explicit anti-checklist of things not to do pre-launch.
- 13 admin tests (edition gating, license parser including the
  off-by-one regression below, theme fallback, branding caption logic).

### Fixed
- License-key parser checked the dash at index 7 instead of 8, rejecting
  every legitimate `MZH-XXXX-XXXX` key — caught by the new
  `test_make_then_apply_roundtrips` test.

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
