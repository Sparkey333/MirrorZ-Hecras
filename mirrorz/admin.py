"""
mirrorz/admin.py
================================================================================
Admin model: edition gating, theme/design choices, license entry, classroom
branding. The "Admin" tab in the GUI is the user-facing surface for these.

WHY THIS LIVES IN ITS OWN MODULE
--------------------------------------------------------------------------------
Admin concerns mix three different lifetimes:
  * Edition / license  -> per-install, set once (or revisited at upgrade)
  * Design choices     -> per-user (theme, plot palette, branding)
  * Telemetry consent  -> per-user, explicit, default OFF (privacy promise)
Putting them next to settings.py keeps each concern small and lets a future
license-server integration replace the LicenseManager without touching
project I/O or the solver.

EDITION GATING (the commercial model in code)
--------------------------------------------------------------------------------
v0.2 ships three editions, gated by a simple feature-flag dict. The free
edition is fully usable; pro / classroom unlock additional features. The
license-key format is intentionally short and human-readable
(MZH-XXXX-XXXX) so users can type it from an email receipt without
copy-paste mistakes.

  Free        : interactive 1-D steady solve, default examples, JSON I/O
  Pro         : + Controller automation, CSV export, advanced friction
                  methods, rating-curve / freeboard tools without nagware
  Classroom   : + branding (school logo + name in headers and exports),
                  multi-seat license, instructor exercise pack

### WARN ###: client-side license checks are an HONOR system, not security.
This is the same posture Sketch, Sublime Text, JetBrains "evaluation" use:
a cracked build will exist; that's fine. We charge customers who VALUE the
ongoing product (updates, support, mission). A determined pirate was never
going to pay. Do NOT add aggressive DRM - it only hurts paying users.

HIGHLIGHTED TWEAK AREAS
--------------------------------------------------------------------------------
  ### TWEAK: EDITIONS ###       Which features each edition unlocks.
  ### TWEAK: THEMES ###         Color palettes for plots and the GUI.
  ### TWEAK: PRICE_DEFAULTS ###  Sticker prices shown in the Edition panel.
================================================================================
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

from .settings import config_dir


# =============================================================================
# Editions and feature flags
# =============================================================================
# ### TWEAK: EDITIONS ###
# Add/remove flags here when a paid feature ships. The GUI uses
# AdminState.feature_enabled("name") to decide whether to enable a button.
EDITIONS: Dict[str, Dict[str, bool]] = {
    "free": {
        "controller_api":       True,    # the library is MIT - never gated
        "csv_export":           False,
        "advanced_friction":    False,
        "rating_curve":         True,    # teaser: free, with watermark
        "freeboard_check":      True,    # teaser: free, with watermark
        "branding":             False,
        "html_report":          False,
        "pdf_report":           False,
    },
    "pro": {
        "controller_api":       True,
        "csv_export":           True,
        "advanced_friction":    True,
        "rating_curve":         True,
        "freeboard_check":      True,
        "branding":             False,
        "html_report":          True,
        "pdf_report":           True,
    },
    "classroom": {
        "controller_api":       True,
        "csv_export":           True,
        "advanced_friction":    True,
        "rating_curve":         True,
        "freeboard_check":      True,
        "branding":             True,
        "html_report":          True,
        "pdf_report":           True,
    },
}

# ### TWEAK: PRICE_DEFAULTS ###
# Sticker prices shown in the Edition panel. Source of truth for marketing
# copy; docs/pricing.md explains the reasoning. Bump these in one place.
EDITION_PRICES = {
    "free":      "Free, MIT-licensed core",
    "pro":       "$29.99 one-time  ·  $14.99 student (.edu)",
    "classroom": "$199 / year  ·  30 seats",
}


# =============================================================================
# Themes - "design choices" the admin tab exposes
# =============================================================================
# ### TWEAK: THEMES ###
# Each theme is a small palette dict. Plotting reads colors from the active
# theme at draw time, so changes appear on the next plot redraw without a
# restart. Add a new theme by appending a dict and it shows up in the menu.
THEMES: Dict[str, Dict[str, str]] = {
    "river":    {  # default, friendly defaults inherited from v0.1
        "ground":   "#7a5230",
        "water":    "#2a72c1",
        "energy":   "#d24a2a",
        "critical": "#b8b800",
        "bg":       "#ffffff",
    },
    "blueprint": {  # white-on-blue, screenshots well in slides
        "ground":   "#bcd1e6",
        "water":    "#ffffff",
        "energy":   "#ffd54f",
        "critical": "#80deea",
        "bg":       "#0d2a47",
    },
    "print":    {  # high-contrast, ink-friendly for student handouts
        "ground":   "#222222",
        "water":    "#666666",
        "energy":   "#111111",
        "critical": "#999999",
        "bg":       "#ffffff",
    },
    "colorblind": {  # Wong / Okabe palette - safe for the ~5% of users with
        "ground":   "#E69F00",   # color-vision deficiencies
        "water":    "#0072B2",
        "energy":   "#D55E00",
        "critical": "#009E73",
        "bg":       "#ffffff",
    },
}


# =============================================================================
# License manager - dead-simple, honest checksum-based key validation.
# =============================================================================

class LicenseManager:
    """
    Generate and validate license keys WITHOUT a server.

    Format:  MZH-XXXX-XXXX
    where XXXX-XXXX is the first 8 hex chars of
          SHA256(secret_salt | edition | order_id).upper()
    The salt prevents trivial key forgery while keeping verification fully
    offline. Compromise of the salt means a leaked binary can mint keys -
    acceptable trade-off (see WARN at top: honor system, not DRM).

    ### TWEAK: KEY_SECRET ###
    Replace this string with a project-specific secret BEFORE you sell the
    first license. (We deliberately keep the dev default obvious so it
    can't be mistaken for production secrecy.)
    """
    KEY_SECRET = "DEV-CHANGE-ME-BEFORE-FIRST-RELEASE"

    @classmethod
    def make_key(cls, edition: str, order_id: str) -> str:
        if edition not in EDITIONS:
            raise ValueError(f"Unknown edition {edition!r}")
        material = f"{cls.KEY_SECRET}|{edition}|{order_id}".encode()
        digest = hashlib.sha256(material).hexdigest().upper()
        return f"MZH-{digest[:4]}-{digest[4:8]}"

    @classmethod
    def parse(cls, key: str) -> Optional[str]:
        """Return the edition the key unlocks, or None if invalid.

        We probe every edition with the key's checksum portion against
        a brute-force search over order ids is NOT possible here because
        the key only stores 32 bits of digest - we'd need the order_id
        to verify it. Instead, the customer's purchase receipt arrives
        with both the key AND the matching `order_id`, and the email
        link prefills both. This method only checks the *format* and
        the embedded edition prefix below.
        """
        key = key.strip().upper()
        # MZH-XXXX-XXXX is 13 chars; dashes at indices 3 and 8.
        if (len(key) != 13 or not key.startswith("MZH-")
                or key[8] != "-"):
            return None
        # For dev-mode we ship a permissive check: any well-formed key
        # whose checksum portion is valid hex activates "pro". Replace with
        # a real check (with an order_id alongside) once the storefront
        # is wired up.
        try:
            int(key[4:8] + key[9:13], 16)
        except ValueError:
            return None
        return "pro"


# =============================================================================
# AdminState - persisted alongside settings.json
# =============================================================================

@dataclass
class AdminState:
    edition:        str  = "free"        # "free" | "pro" | "classroom"
    license_key:    str  = ""
    theme:          str  = "river"
    # Branding (classroom edition)
    institution:    str  = ""            # "University of Example"
    instructor:     str  = ""            # "Dr. Jane Hydro"
    course_code:    str  = ""            # "CIVE 462"
    # Privacy: telemetry is OFF until the user actively opts in. Even then
    # the current build does not send anything (we have no endpoint); this
    # flag is here so a future opt-in analytics feature respects the user's
    # earlier consent (or lack of it) without re-prompting.
    telemetry_optin: bool = False

    # ---- Persistence -----------------------------------------------------
    def path(self) -> str:
        return os.path.join(config_dir(), "admin.json")

    def save(self) -> None:
        tmp = self.path() + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(asdict(self), fh, indent=2)
        os.replace(tmp, self.path())

    @classmethod
    def load(cls) -> "AdminState":
        path = os.path.join(config_dir(), "admin.json")
        try:
            with open(path) as fh:
                data = json.load(fh)
            known = {f for f in cls.__dataclass_fields__}
            return cls(**{k: v for k, v in data.items() if k in known})
        except Exception:
            return cls()

    # ---- Edition / features ---------------------------------------------
    def feature_enabled(self, name: str) -> bool:
        return EDITIONS.get(self.edition, EDITIONS["free"]).get(name, False)

    def apply_license_key(self, key: str) -> str:
        """Apply a key and return a status string for the UI."""
        edition = LicenseManager.parse(key)
        if edition is None:
            return "Invalid key format. Expected MZH-XXXX-XXXX."
        self.license_key = key.strip().upper()
        self.edition = edition
        self.save()
        return f"Activated {edition} edition. Thank you!"

    def clear_license(self) -> None:
        self.license_key = ""
        self.edition = "free"
        self.save()

    # ---- Theme helpers ---------------------------------------------------
    def palette(self) -> Dict[str, str]:
        return THEMES.get(self.theme, THEMES["river"])

    # ---- Branding strings ------------------------------------------------
    def header_caption(self) -> str:
        """One-line caption used on plot titles when branding is enabled."""
        if not self.feature_enabled("branding"):
            return ""
        parts = [p for p in (self.institution, self.course_code,
                             self.instructor) if p]
        return " · ".join(parts)
