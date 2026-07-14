"""
mirrorz/project.py
================================================================================
Project file I/O + sensible defaults, for MirrorZ-Hecras.

A "project" is the top-level container - roughly equivalent to a .prj file in
HEC-RAS. It holds:
  * metadata (name, units, description)
  * one or more Reaches (each a list of CrossSection)
  * one or more FlowPlans (discharge + boundary condition + regime)

FILE FORMAT
--------------------------------------------------------------------------------
JSON. Readable by humans, diff-friendly in git. HEC-RAS uses a proprietary
ASCII format split across many files (.prj/.g01/.f01/.p01); we consolidate
everything into one JSON for clarity. A future version could mimic the real
HEC-RAS split (see ### TODO ### at the bottom).

HIGHLIGHTED TWEAK AREAS
--------------------------------------------------------------------------------
  ### TWEAK: DEFAULT_PROJECT ###  The template wizard starts from.
  ### TWEAK: FILE_VERSION ###     Bump when the schema changes.
================================================================================
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Optional

from .geometry import CrossSection, Reach
from . import hydraulics as hy


FILE_VERSION = 1   # ### TWEAK: FILE_VERSION ###


# =============================================================================
# Flow plans describe *what* to simulate.
# =============================================================================

@dataclass
class FlowPlan:
    name: str
    discharge: float                # constant Q for now (steady)
    boundary_wse: float             # known WSE at the boundary
    regime: str = "subcritical"     # or "supercritical"

    # ### TODO ### future: mixed regime, multiple profiles per plan,
    # per-reach boundary dictionary, lateral inflows.


# =============================================================================
# Project container
# =============================================================================

@dataclass
class Project:
    name: str = "Untitled"
    description: str = ""
    unit_system: str = "SI"         # "SI" or "US"
    reaches: List[Reach] = field(default_factory=list)
    flows: List[FlowPlan] = field(default_factory=list)
    file_version: int = FILE_VERSION

    # ------------------------------------------------------------------
    # Mutations the GUI calls
    # ------------------------------------------------------------------
    def add_reach(self, reach: Reach) -> None:
        self.reaches.append(reach)

    def add_flow(self, flow: FlowPlan) -> None:
        self.flows.append(flow)

    def apply_units(self) -> None:
        """Push our unit_system into the hydraulics module (global k, g)."""
        hy.set_unit_system(self.unit_system)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "file_version": self.file_version,
            "name": self.name,
            "description": self.description,
            "unit_system": self.unit_system,
            "reaches": [
                {
                    "name": r.name,
                    "cross_sections": [_xs_to_dict(xs) for xs in r.cross_sections],
                }
                for r in self.reaches
            ],
            "flows": [asdict(f) for f in self.flows],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Project":
        if d.get("file_version", 1) > FILE_VERSION:
            raise ValueError(
                f"Project file version {d['file_version']} is newer than "
                f"this software ({FILE_VERSION}). Please upgrade."
            )
        p = cls(
            name=d.get("name", "Untitled"),
            description=d.get("description", ""),
            unit_system=d.get("unit_system", "SI"),
        )
        for rd in d.get("reaches", []):
            reach = Reach(name=rd["name"])
            for xd in rd.get("cross_sections", []):
                reach.add(_xs_from_dict(xd))
            p.reaches.append(reach)
        for fd in d.get("flows", []):
            p.flows.append(FlowPlan(**fd))
        return p

    def save(self, path: str) -> None:
        with open(path, "w") as fh:
            json.dump(self.to_dict(), fh, indent=2)

    @classmethod
    def load(cls, path: str) -> "Project":
        with open(path) as fh:
            return cls.from_dict(json.load(fh))


def _xs_to_dict(xs: CrossSection) -> dict:
    return {
        "name": xs.name,
        "river_station": xs.river_station,
        "stations": list(xs.stations),
        "elevations": list(xs.elevations),
        "left_bank": xs.left_bank,
        "right_bank": xs.right_bank,
        "n_channel": xs.n_channel,
        "n_left":    xs.n_left,
        "n_right":   xs.n_right,
        "reach_length_channel": xs.reach_length_channel,
        "reach_length_lob":     xs.reach_length_lob,
        "reach_length_rob":     xs.reach_length_rob,
        "contraction_coeff":    xs.contraction_coeff,
        "expansion_coeff":      xs.expansion_coeff,
    }


def _xs_from_dict(d: dict) -> CrossSection:
    return CrossSection(
        name=d["name"],
        river_station=d["river_station"],
        stations=list(d["stations"]),
        elevations=list(d["elevations"]),
        left_bank=d.get("left_bank"),
        right_bank=d.get("right_bank"),
        n_channel=d.get("n_channel", 0.035),
        n_left=d.get("n_left", 0.035),
        n_right=d.get("n_right", 0.035),
        reach_length_channel=d.get("reach_length_channel", 100.0),
        reach_length_lob=d.get("reach_length_lob", 100.0),
        reach_length_rob=d.get("reach_length_rob", 100.0),
        contraction_coeff=d.get("contraction_coeff", 0.10),
        expansion_coeff=d.get("expansion_coeff", 0.30),
    )


# =============================================================================
# ### TWEAK: DEFAULT_PROJECT ###
# -----------------------------------------------------------------------------
# The companion wizard calls this to hand a brand-new user something that
# already runs. The defaults are a mild-slope trapezoidal stream with five
# identical cross-sections spaced 100 m apart.
#
# Why these values?
#   * Bottom width 10 m, side slopes 2H:1V: common drainage/irrigation canal.
#   * n = 0.035: "natural stream, clean" - Chow (1959).
#   * Bed slope ~ 0.001: typical lowland river.
#   * Design Q = 20 m^3/s: a modest flood-stage flow for this geometry.
#   * Downstream boundary WSE = normal depth at the downstream-most XS.
# =============================================================================

def default_project(name: str = "Sample Stream", units: str = "SI") -> Project:
    p = Project(name=name, unit_system=units,
                description="Auto-generated trapezoidal sample reach. "
                            "Edit cross-sections to model your own river.")
    p.apply_units()

    reach = Reach(name="Main Reach")
    n_xs = 5
    slope = 0.001
    spacing = 100.0  # meters between sections
    # Build a trapezoid at descending elevations.
    for i in range(n_xs):
        thalweg = slope * spacing * i       # upstream-most is highest
        xs = _make_trapezoid(
            name=f"XS-{i+1}",
            station=float(i) * spacing,     # river_station increases upstream
            thalweg_elev=thalweg,
            bottom_width=10.0,
            side_slope=2.0,
            depth=3.0,
            n=0.035,
        )
        xs.reach_length_channel = spacing
        xs.reach_length_lob     = spacing
        xs.reach_length_rob     = spacing
        reach.add(xs)
    p.add_reach(reach)

    # A default flow plan: 20 cms, downstream boundary at ~normal depth.
    p.add_flow(FlowPlan(
        name="Design flow 20 cms",
        discharge=20.0,
        boundary_wse=_estimate_normal_wse(reach.cross_sections[0], q=20.0, slope=0.001),
        regime="subcritical",
    ))
    return p


def _make_trapezoid(name: str, station: float, thalweg_elev: float,
                    bottom_width: float, side_slope: float,
                    depth: float, n: float) -> CrossSection:
    """
    Generate a 5-point trapezoidal cross-section:

        top-left ------------- top-right
             \\                 /
              bot-left --- bot-right
    side_slope is horizontal:vertical (so 2.0 = 2H:1V).
    Horizontal padding on the "top" extends the overbank for plotting.
    """
    pad = 5.0  # meters of floodplain beyond the top of bank, ### TWEAK ###
    bw = bottom_width
    z0 = thalweg_elev
    top_z = z0 + depth
    dx_side = side_slope * depth
    x0 = 0.0
    stations = [
        x0 - pad - dx_side,           # far left
        x0 - dx_side,                 # top of bank, left
        x0,                           # bottom-left
        x0 + bw,                      # bottom-right
        x0 + bw + dx_side,            # top of bank, right
        x0 + bw + dx_side + pad,      # far right
    ]
    elevations = [top_z + 0.5, top_z, z0, z0, top_z, top_z + 0.5]
    return CrossSection(
        name=name,
        river_station=station,
        stations=stations,
        elevations=elevations,
        left_bank=x0 - dx_side,
        right_bank=x0 + bw + dx_side,
        n_channel=n, n_left=n * 1.5, n_right=n * 1.5,
    )


def _estimate_normal_wse(xs: CrossSection, q: float, slope: float) -> float:
    """Quick normal-depth estimate to seed the downstream boundary."""
    yn = hy.normal_depth(q, slope, xs.n_channel, xs.section_fn())
    return xs.min_elevation + yn


# =============================================================================
# ### TODO ###
# -----------------------------------------------------------------------------
# Future work: import real HEC-RAS geometry (.g01) and flow (.f01) files.
# The format is text-based; Pugh et al. published a reference that a parser
# can follow. Leaving as an exercise/extension point.
# =============================================================================
