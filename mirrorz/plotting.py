"""
mirrorz/plotting.py
================================================================================
Matplotlib renderings for cross-sections and water-surface profiles.

The GUI embeds these figures in Tk canvases (see mirrorz/gui.py), but every
function here is also usable standalone:

    fig = cross_section_figure(xs, wse=100.5)
    fig.savefig("xs.png")

HIGHLIGHTED TWEAK AREAS
--------------------------------------------------------------------------------
  ### TWEAK: STYLE ###        Colors, line widths, fill alphas.
  ### TWEAK: FIG_SIZE ###     Default figure sizes.
================================================================================
"""

from __future__ import annotations

import os
import sys
from typing import List, Optional

import matplotlib
# ### WARN ###: matplotlib allows only ONE backend per process, and whoever
# calls matplotlib.use() last before pyplot starts drawing wins. The GUI
# selects "TkAgg" (interactive, embeds in Tk); headless scripts need "Agg"
# (renders to memory, no display required). v0.1 forced Agg unconditionally
# here, which silently overrode the GUI's TkAgg because gui.py imports this
# module *after* choosing its backend. The fix: only force Agg when there is
# genuinely no display to draw on (Linux/BSD without $DISPLAY / $WAYLAND).
# macOS and Windows always have a windowing system available.
if (sys.platform.startswith("linux")
        and not os.environ.get("DISPLAY")
        and not os.environ.get("WAYLAND_DISPLAY")):
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .geometry import CrossSection
from .solver import ProfileResult


# =============================================================================
# ### TWEAK: STYLE ###
# Default palette - the admin tab overrides these at draw time via apply_palette.
# =============================================================================
GROUND_COLOR   = "#7a5230"   # earthy brown
WATER_COLOR    = "#2a72c1"   # river blue
ENERGY_COLOR   = "#d24a2a"   # red for EGL
CRITICAL_COLOR = "#b8b800"   # dashed yellow for critical line
BG_COLOR       = "#ffffff"
FILL_ALPHA     = 0.35
LINE_WIDTH     = 1.8

# Optional branding caption appended to plot titles (classroom edition).
BRAND_CAPTION  = ""


def apply_palette(palette: dict, brand_caption: str = "") -> None:
    """Swap the active plot palette and brand caption. Called by the admin
    tab whenever the user picks a different theme or edits branding fields;
    next redraw picks up the change. Keeping this as module-level globals
    (instead of plumbing a Palette object through every function signature)
    matches how the rest of MirrorZ exposes ### TWEAK ### knobs."""
    global GROUND_COLOR, WATER_COLOR, ENERGY_COLOR, CRITICAL_COLOR, BG_COLOR
    global BRAND_CAPTION
    GROUND_COLOR   = palette.get("ground",   GROUND_COLOR)
    WATER_COLOR    = palette.get("water",    WATER_COLOR)
    ENERGY_COLOR   = palette.get("energy",   ENERGY_COLOR)
    CRITICAL_COLOR = palette.get("critical", CRITICAL_COLOR)
    BG_COLOR       = palette.get("bg",       BG_COLOR)
    BRAND_CAPTION  = brand_caption or ""

# ### TWEAK: FIG_SIZE ###
XS_FIGSIZE      = (6.5, 3.8)
PROFILE_FIGSIZE = (7.5, 4.0)


def cross_section_figure(xs: CrossSection,
                         wse: Optional[float] = None,
                         ax=None):
    """Draw one cross-section with optional water surface."""
    import matplotlib.pyplot as _plt
    if ax is None:
        fig, ax = _plt.subplots(figsize=XS_FIGSIZE)
    else:
        fig = ax.figure

    ax.plot(xs.stations, xs.elevations,
            color=GROUND_COLOR, linewidth=LINE_WIDTH, label="Ground")
    # Shade the ground below to make the "floor" obvious.
    bottom = min(xs.elevations) - 1.0
    ax.fill_between(xs.stations, xs.elevations, bottom,
                    color=GROUND_COLOR, alpha=0.2)

    if wse is not None and wse > min(xs.elevations):
        ax.axhline(wse, color=WATER_COLOR, linewidth=1.5,
                   linestyle="--", label=f"WSE = {wse:.2f}")
        # Shade the water body: between ground and WSE where ground < WSE.
        ys_water_top = [min(wse, z) for z in xs.elevations]  # unused but keeps intent
        ax.fill_between(xs.stations, xs.elevations,
                        [wse] * len(xs.stations),
                        where=[z < wse for z in xs.elevations],
                        color=WATER_COLOR, alpha=FILL_ALPHA, interpolate=True)

    if xs.left_bank is not None:
        ax.axvline(xs.left_bank, color="k", linestyle=":", linewidth=0.8)
    if xs.right_bank is not None:
        ax.axvline(xs.right_bank, color="k", linestyle=":", linewidth=0.8)

    ax.set_xlabel("Station")
    ax.set_ylabel("Elevation")
    title = f"Cross-section: {xs.name}  (RS {xs.river_station:.1f})"
    if BRAND_CAPTION:
        title += f"\n{BRAND_CAPTION}"
    ax.set_title(title)
    ax.set_facecolor(BG_COLOR)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="best", fontsize=8)
    return fig


def profile_figure(result: ProfileResult,
                   reach_cross_sections: List[CrossSection],
                   ax=None):
    """
    Plot the water-surface profile along a reach:
      * thalweg elevation vs river station
      * computed WSE vs river station
      * energy grade line (EGL)
      * critical WSE (dashed)
    """
    import matplotlib.pyplot as _plt
    if ax is None:
        fig, ax = _plt.subplots(figsize=PROFILE_FIGSIZE)
    else:
        fig = ax.figure

    # Ensure alignment between geometry and results by name lookup.
    by_name = {xs.name: xs for xs in reach_cross_sections}
    xs_list = [s for s in result.sections if s.name in by_name]
    xs_list.sort(key=lambda s: s.station)

    stations = [s.station for s in xs_list]
    thalweg  = [by_name[s.name].min_elevation for s in xs_list]
    wse      = [s.wse for s in xs_list]
    egl      = [s.energy_grade for s in xs_list]
    crit     = [s.critical_wse for s in xs_list]

    ax.plot(stations, thalweg, color=GROUND_COLOR, linewidth=LINE_WIDTH,
            marker="o", label="Thalweg (bed)")
    ax.plot(stations, wse, color=WATER_COLOR, linewidth=LINE_WIDTH,
            marker="s", label="Water surface")
    ax.plot(stations, egl, color=ENERGY_COLOR, linewidth=1.2,
            linestyle="-", marker="^", label="Energy grade line")
    ax.plot(stations, crit, color=CRITICAL_COLOR, linewidth=1.0,
            linestyle="--", label="Critical WSE")

    ax.fill_between(stations, thalweg, wse, color=WATER_COLOR, alpha=FILL_ALPHA)

    ax.set_xlabel("River station (upstream →)")
    ax.set_ylabel("Elevation")
    title = f"Profile: {result.reach_name}   Q = {result.discharge:g}"
    if BRAND_CAPTION:
        title += f"\n{BRAND_CAPTION}"
    ax.set_title(title)
    ax.set_facecolor(BG_COLOR)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="best", fontsize=8)
    return fig


def rating_figure(points, xs_name: str, ax=None):
    """Discharge vs WSE plot at a single section."""
    import matplotlib.pyplot as _plt
    if ax is None:
        fig, ax = _plt.subplots(figsize=XS_FIGSIZE)
    else:
        fig = ax.figure
    qs = [p.discharge for p in points]
    ws = [p.wse for p in points]
    ax.plot(qs, ws, "o-", color=WATER_COLOR, linewidth=LINE_WIDTH)
    ax.set_xlabel("Discharge")
    ax.set_ylabel("Water-surface elevation")
    ax.set_title(f"Rating curve at {xs_name}")
    ax.grid(True, linestyle=":", alpha=0.5)
    return fig
