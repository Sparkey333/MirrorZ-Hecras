"""
mirrorz/settings.py
================================================================================
Persistent user settings for MirrorZ-Hecras.

WHAT THIS FILE DOES
--------------------------------------------------------------------------------
HEC-RAS remembers your preferences (units, tolerances, recent projects)
between sessions. We mirror that with a small JSON file stored in the
platform's standard per-user configuration directory:

    Linux   : ~/.config/mirrorz-hecras/settings.json
    macOS   : ~/Library/Application Support/MirrorZ-Hecras/settings.json
    Windows : %APPDATA%\\MirrorZ-Hecras\\settings.json

WHY A SEPARATE FILE AND NOT THE PROJECT JSON?
--------------------------------------------------------------------------------
Settings are about the *user* (their preferred tolerances, their recent
files); projects are about the *river*. Mixing the two means a project
emailed to a colleague would drag your personal preferences along with it.
Keeping them separate is also what every app store reviewer expects: user
data in user space, documents wherever the user chooses.

HOW SETTINGS REACH THE SOLVER
--------------------------------------------------------------------------------
The numerical modules (solver.py, analyzer.py, hydraulics.py) keep their
knobs as module-level globals so they're easy to find and easy to grep
(### TWEAK ### markers). `AppSettings.apply()` simply assigns those globals.
Because Python looks up module globals at call time, the change takes
effect on the very next solver run - no restart needed.

HIGHLIGHTED TWEAK AREAS
--------------------------------------------------------------------------------
  ### TWEAK: SETTINGS_DEFAULTS ###  Factory defaults for a fresh install.
  ### TWEAK: RECENT_MAX ###         How many recent files to remember.
  ### TWEAK: CONFIG_DIR ###         Where the settings file lives.
================================================================================
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field, asdict
from typing import List, Optional

from . import hydraulics as hy
from . import solver as so
from . import analyzer as an


# ### TWEAK: RECENT_MAX ### - how many entries the File > Recent menu keeps.
RECENT_MAX = 8

# Bump this when the settings schema changes so old files can be migrated.
SETTINGS_VERSION = 1


# =============================================================================
# ### TWEAK: CONFIG_DIR ###
# -----------------------------------------------------------------------------
# Platform-correct config location. App stores *require* this: the macOS App
# Sandbox only grants write access to your app container, which maps to
# ~/Library/Application Support/<bundle>. Writing next to the executable
# (the old DOS habit) fails code-signing review and breaks on read-only
# installs, so resist the temptation.
# =============================================================================

APP_DIR_NAME = "MirrorZ-Hecras"   # used on macOS / Windows
APP_DIR_UNIX = "mirrorz-hecras"   # lowercase-hyphen is the XDG convention


def config_dir() -> str:
    """Return (and create) the per-user configuration directory."""
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
        path = os.path.join(base, APP_DIR_NAME)
    elif os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        path = os.path.join(base, APP_DIR_NAME)
    else:
        # XDG Base Directory spec: honor $XDG_CONFIG_HOME, default ~/.config
        base = os.environ.get("XDG_CONFIG_HOME",
                              os.path.expanduser("~/.config"))
        path = os.path.join(base, APP_DIR_UNIX)
    os.makedirs(path, exist_ok=True)
    return path


def settings_path() -> str:
    return os.path.join(config_dir(), "settings.json")


# =============================================================================
# ### TWEAK: SETTINGS_DEFAULTS ###
# -----------------------------------------------------------------------------
# Factory defaults. Each value mirrors the module-level constant it controls,
# so a fresh install behaves exactly like the hard-coded v0.1 release:
#
#   unit_system      -> hydraulics._UNIT_SYSTEM   ("SI" or "US")
#   wse_tolerance    -> solver.WSE_TOL            (m; HEC-RAS uses 0.01 ft)
#   max_step_iters   -> solver.MAX_STEP_ITERS
#   friction_method  -> solver.FRICTION_AVG_METHOD
#                       ("average" | "harmonic" | "geometric" | "conveyance")
#   freeboard_req    -> analyzer.FREEBOARD_REQ    (m; 0.5 m levee practice)
#   show_welcome     -> GUI: open the Companion tab with the intro text
#   window_geometry  -> GUI: Tk geometry string, restored at launch
# =============================================================================

@dataclass
class AppSettings:
    settings_version: int = SETTINGS_VERSION
    unit_system: str = "SI"
    wse_tolerance: float = 0.003
    max_step_iters: int = 30
    friction_method: str = "average"
    freeboard_req: float = 0.5
    show_welcome: bool = True
    window_geometry: str = ""          # "" = let Tk decide on first launch
    recent_files: List[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Validation - clamp anything a hand-edited file could break.
    # ------------------------------------------------------------------
    def sanitize(self) -> None:
        if self.unit_system not in ("SI", "US"):
            self.unit_system = "SI"
        if self.friction_method not in ("average", "harmonic",
                                        "geometric", "conveyance"):
            self.friction_method = "average"
        # Tolerances must be positive; iteration caps must be sane.
        if not (0 < self.wse_tolerance < 1.0):
            self.wse_tolerance = 0.003
        self.max_step_iters = max(5, min(int(self.max_step_iters), 500))
        if not (0 <= self.freeboard_req < 100.0):
            self.freeboard_req = 0.5
        # Drop recent files that no longer exist, keep the cap.
        self.recent_files = [p for p in self.recent_files
                             if isinstance(p, str) and os.path.exists(p)]
        self.recent_files = self.recent_files[:RECENT_MAX]

    # ------------------------------------------------------------------
    # Push values into the numeric modules.
    # ------------------------------------------------------------------
    def apply(self) -> None:
        """Make these settings live for the next solver/analyzer call."""
        hy.set_unit_system(self.unit_system)
        so.WSE_TOL = float(self.wse_tolerance)
        so.MAX_STEP_ITERS = int(self.max_step_iters)
        so.FRICTION_AVG_METHOD = self.friction_method
        an.FREEBOARD_REQ = float(self.freeboard_req)

    # ------------------------------------------------------------------
    # Recent-files bookkeeping (most-recent-first, de-duplicated).
    # ------------------------------------------------------------------
    def remember_file(self, path: str) -> None:
        path = os.path.abspath(path)
        if path in self.recent_files:
            self.recent_files.remove(path)
        self.recent_files.insert(0, path)
        del self.recent_files[RECENT_MAX:]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def save(self, path: Optional[str] = None) -> None:
        path = path or settings_path()
        # Write-then-rename so a crash mid-write can't corrupt the file.
        tmp = path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(asdict(self), fh, indent=2)
        os.replace(tmp, path)

    @classmethod
    def load(cls, path: Optional[str] = None) -> "AppSettings":
        """Load settings; any problem falls back to factory defaults.

        ### WARN ###: never let a corrupt settings file stop the app from
        launching. Users (and app-store reviewers) judge harshly when an
        app dies on startup over a preferences file.
        """
        path = path or settings_path()
        try:
            with open(path) as fh:
                data = json.load(fh)
            known = {f for f in cls.__dataclass_fields__}  # ignore unknown keys
            s = cls(**{k: v for k, v in data.items() if k in known})
        except Exception:
            s = cls()
        s.sanitize()
        return s
