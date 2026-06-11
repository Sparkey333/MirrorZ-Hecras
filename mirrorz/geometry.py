"""
mirrorz/geometry.py
================================================================================
Cross-section and reach geometry for MirrorZ-Hecras.

CORE IDEAS
--------------------------------------------------------------------------------
A river is modeled as an ordered chain of *cross-sections* (XS) along a
*reach*. Each XS is a polyline of (station, elevation) points describing
the channel shape looking downstream. Stations increase left-to-right.
Elevations are in the same vertical datum across the whole project.

At a given water-surface elevation (WSE), we compute:
    A = wetted flow area        (integrated under the WSE, above the ground)
    T = top width               (length of WSE inside the section)
    P = wetted perimeter        (length of ground below the WSE)
This trio is everything hydraulics.py needs.

HEC-RAS adds subdivisions for LEFT OVERBANK / MAIN CHANNEL / RIGHT OVERBANK
so different Manning's n values can coexist in one section. We support the
same with `bank_stations` and per-region `n_values` (see CrossSection).

HIGHLIGHTED TWEAK AREAS
--------------------------------------------------------------------------------
  ### TWEAK: DEFAULT_N ###      Default Manning roughness if not supplied.
  ### TWEAK: INTERP ###         Wetted-intersection linear interpolation.
  ### TWEAK: CONTRACTION ###    Default expansion/contraction losses.
  ### TWEAK: REACH_LENGTHS ###  Default distance between sections.
================================================================================
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# =============================================================================
# ### TWEAK: DEFAULT_N ###
# -----------------------------------------------------------------------------
# If a user creates a section but forgets to provide roughness, we assume a
# typical earthen natural channel. This matches Chow (1959) Table 5-6 for
# "natural streams - clean, straight, full stage, no rifts or deep pools".
# =============================================================================
DEFAULT_MANNING_N = 0.035

# ### TWEAK: CONTRACTION ### - HEC-RAS defaults are 0.1/0.3 for gradual
# transitions, 0.3/0.5 for typical bridges, 0.6/0.8 for abrupt transitions.
DEFAULT_CONTRACTION_COEFF = 0.10
DEFAULT_EXPANSION_COEFF   = 0.30


# =============================================================================
# Cross-section
# =============================================================================

@dataclass
class CrossSection:
    """
    One station on the river. All coordinates are in project units (m or ft).

    Attributes
    ----------
    name : str
        Human-readable label (often a river station like "1000+00" or a mile).
    river_station : float
        Distance along the river; larger values are upstream in HEC-RAS
        convention. The solver sorts by this field.
    stations : list[float]
        Transverse coordinates of ground points (left bank to right bank).
    elevations : list[float]
        Ground elevations at each station (same length as `stations`).
    left_bank, right_bank : float
        Station locations separating LOB / channel / ROB. If None, the whole
        section uses the default n and is treated as a single panel.
    n_left, n_channel, n_right : float
        Manning's roughness for each sub-region.
    reach_length_channel, reach_length_lob, reach_length_rob : float
        Downstream distance to the next (lower-station) XS for each region.
        HEC-RAS uses three lengths because overbanks often follow different
        flow paths than the main channel.
    """
    name: str
    river_station: float
    stations: List[float]
    elevations: List[float]
    left_bank:  Optional[float] = None
    right_bank: Optional[float] = None
    n_channel: float = DEFAULT_MANNING_N
    n_left:    float = DEFAULT_MANNING_N
    n_right:   float = DEFAULT_MANNING_N
    # ### TWEAK: REACH_LENGTHS ### default to 100 m / ft between XS.
    reach_length_channel: float = 100.0
    reach_length_lob:     float = 100.0
    reach_length_rob:     float = 100.0
    contraction_coeff: float = DEFAULT_CONTRACTION_COEFF
    expansion_coeff:   float = DEFAULT_EXPANSION_COEFF
    # Ineffective flow areas, levees, bridges -> ### TODO ### future work.

    # ------------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------------
    def __post_init__(self) -> None:
        if len(self.stations) != len(self.elevations):
            raise ValueError("stations and elevations must be the same length")
        if len(self.stations) < 3:
            raise ValueError("A cross-section needs at least 3 points")
        # Enforce monotonic stations left-to-right. We sort defensively so a
        # user importing points out of order still gets a usable section.
        pts = sorted(zip(self.stations, self.elevations), key=lambda p: p[0])
        self.stations  = [p[0] for p in pts]
        self.elevations = [p[1] for p in pts]

    # ------------------------------------------------------------------------
    # Basic extents
    # ------------------------------------------------------------------------
    @property
    def min_elevation(self) -> float:
        """Thalweg = lowest ground point in the section."""
        return min(self.elevations)

    @property
    def max_elevation(self) -> float:
        return max(self.elevations)

    @property
    def left_station(self) -> float:
        return self.stations[0]

    @property
    def right_station(self) -> float:
        return self.stations[-1]

    # ------------------------------------------------------------------------
    # Core hydraulic geometry at a given water-surface elevation
    # ------------------------------------------------------------------------
    def hydraulic_properties(self, wse: float) -> Tuple[float, float, float]:
        """
        Return (area, top_width, wetted_perimeter) at the given WSE.

        ### LEARN ###
        We walk each segment (P_i -> P_{i+1}) of the ground line and ask:
        is this segment fully submerged, partly submerged, or dry? For the
        wetted portion we add a trapezoid to the area, the horizontal span
        to the top width, and the segment length to P.

        ### TWEAK: INTERP ###
        We use linear interpolation to find where the WSE crosses a ground
        segment. That's the standard HEC-RAS assumption and is accurate when
        ground points are dense. If you have coarse bathymetry, add more
        points rather than changing the interpolation scheme.
        """
        if wse <= self.min_elevation:
            return 0.0, 0.0, 0.0

        area = 0.0
        top_width = 0.0
        wet_perim = 0.0

        xs, zs = self.stations, self.elevations
        for i in range(len(xs) - 1):
            x1, x2 = xs[i], xs[i + 1]
            z1, z2 = zs[i], zs[i + 1]
            dx = x2 - x1
            if dx <= 0:
                continue

            # Depths of water above each endpoint (negative if dry).
            d1 = wse - z1
            d2 = wse - z2

            if d1 <= 0 and d2 <= 0:
                continue  # fully dry segment

            if d1 >= 0 and d2 >= 0:
                # Fully submerged - trapezoidal area, full horizontal width.
                area      += 0.5 * (d1 + d2) * dx
                top_width += dx
                wet_perim += math.hypot(dx, z2 - z1)
                continue

            # Partially submerged: find crossing point via similar triangles.
            # Water enters from the wet end to where z == wse.
            #   t = (wse - z_wet) / (z_other - z_wet)   in [0, 1]
            if d1 > 0 and d2 < 0:
                t = (wse - z1) / (z2 - z1)
                xc = x1 + t * dx
                # submerged span is from x1 to xc, depth 0 at xc
                area      += 0.5 * d1 * (xc - x1)
                top_width += (xc - x1)
                wet_perim += math.hypot(xc - x1, wse - z1)
            else:  # d1 < 0, d2 > 0
                t = (wse - z1) / (z2 - z1)
                xc = x1 + t * dx
                area      += 0.5 * d2 * (x2 - xc)
                top_width += (x2 - xc)
                wet_perim += math.hypot(x2 - xc, wse - z2)

        return area, top_width, wet_perim

    # Convenience: make a section_fn for hydraulics.normal_depth / critical.
    def section_fn(self):
        thalweg = self.min_elevation
        def f(depth: float) -> Tuple[float, float, float]:
            return self.hydraulic_properties(thalweg + depth)
        return f

    # ------------------------------------------------------------------------
    # Panel conveyance: HEC-RAS-style LOB / channel / ROB split.
    # ------------------------------------------------------------------------
    def panels(self, wse: float):
        """
        Yield one or three (A, P, n) tuples corresponding to LOB / channel /
        ROB panels under the current WSE. If bank stations aren't set, a
        single panel for the whole section is returned.
        """
        if self.left_bank is None or self.right_bank is None:
            A, _T, P = self.hydraulic_properties(wse)
            return [(A, P, self.n_channel)]

        left = self._panel(wse, self.left_station, self.left_bank,  self.n_left)
        chan = self._panel(wse, self.left_bank,    self.right_bank, self.n_channel)
        rght = self._panel(wse, self.right_bank,   self.right_station, self.n_right)
        return [left, chan, rght]

    def _panel(self, wse: float, x_lo: float, x_hi: float, n: float):
        """
        Clip the section to [x_lo, x_hi] and compute (A, P, n) there.
        For brevity we re-sample the ground line at x_lo and x_hi using
        linear interpolation, then hand the slice to hydraulic_properties.
        """
        sliced = _slice_ground(self.stations, self.elevations, x_lo, x_hi)
        if len(sliced) < 2:
            return (0.0, 0.0, n)
        xs = [p[0] for p in sliced]
        zs = [p[1] for p in sliced]
        xs2 = CrossSection(
            name=self.name + "_panel",
            river_station=self.river_station,
            stations=xs, elevations=zs,
            n_channel=n,
        )
        A, _T, P = xs2.hydraulic_properties(wse)
        return (A, P, n)


def _slice_ground(xs: List[float], zs: List[float],
                  x_lo: float, x_hi: float) -> List[Tuple[float, float]]:
    """Linearly interpolate a ground polyline to the range [x_lo, x_hi]."""
    out: List[Tuple[float, float]] = []
    for i in range(len(xs) - 1):
        x1, x2 = xs[i], xs[i + 1]
        z1, z2 = zs[i], zs[i + 1]
        seg_lo, seg_hi = min(x1, x2), max(x1, x2)
        # Skip segments entirely outside the slice.
        if seg_hi < x_lo or seg_lo > x_hi:
            continue
        # Clip endpoints to the slice.
        def z_at(x: float) -> float:
            if x2 == x1:
                return z1
            t = (x - x1) / (x2 - x1)
            return z1 + t * (z2 - z1)
        a, b = max(seg_lo, x_lo), min(seg_hi, x_hi)
        if not out or out[-1][0] < a:
            out.append((a, z_at(a)))
        out.append((b, z_at(b)))
    return out


# =============================================================================
# Reach: an ordered list of cross-sections that share a flow path.
# =============================================================================

@dataclass
class Reach:
    name: str
    cross_sections: List[CrossSection] = field(default_factory=list)

    def sort_upstream(self) -> None:
        """Sort XS by river_station ASCENDING - upstream last, downstream first.
        The solver iterates downstream-to-upstream for sub-critical flow.
        """
        self.cross_sections.sort(key=lambda xs: xs.river_station)

    def __len__(self) -> int:
        return len(self.cross_sections)

    def add(self, xs: CrossSection) -> None:
        self.cross_sections.append(xs)
        self.sort_upstream()
