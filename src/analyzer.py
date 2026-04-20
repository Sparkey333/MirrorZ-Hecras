"""
src/analyzer.py
================================================================================
Post-run analysis utilities for MirrorZ-Hecras profiles.

CURRENT FEATURES
--------------------------------------------------------------------------------
  * Rating curve: discharge -> WSE at a control section, by re-running the
    solver across a series of flows.
  * Freeboard check: compares WSE to a user-supplied top-of-bank elevation.
  * Summary table: compact CSV-like string dump of a ProfileResult.
  * Energy grade line & hydraulic grade line sampling.

HIGHLIGHTED TWEAK AREAS
--------------------------------------------------------------------------------
  ### TWEAK: RATING_POINTS ###   Number / spacing of flow samples.
  ### TWEAK: FREEBOARD_REQ ###   Minimum freeboard used by freeboard_check.
================================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .geometry import Reach, CrossSection
from .solver import ProfileResult, solve_profile
from .project import Project, FlowPlan


# ### TWEAK: RATING_POINTS ### default number of discharges in a rating curve.
RATING_POINTS = 12

# ### TWEAK: FREEBOARD_REQ ### 0.5 m is a common minimum for levees; FEMA
# requires 1 ft (0.305 m) in regulatory floodplains. Edit as needed.
FREEBOARD_REQ = 0.5


# =============================================================================
# Rating curve
# =============================================================================

@dataclass
class RatingPoint:
    discharge: float
    wse: float
    depth: float
    velocity: float
    froude: float


def rating_curve(project: Project, reach_index: int, xs_index: int,
                 q_min: float, q_max: float,
                 n_points: int = RATING_POINTS,
                 regime: str = "subcritical",
                 boundary_fn=None) -> List[RatingPoint]:
    """
    Produce a rating curve at one cross-section by sweeping discharge.

    Parameters
    ----------
    boundary_fn : callable(q) -> float, optional
        Function returning the boundary WSE for each Q. If None, we assume
        normal depth at the downstream section for each Q (handy for quick
        sensitivity studies).
    """
    project.apply_units()
    reach = project.reaches[reach_index]
    reach.sort_upstream()
    if boundary_fn is None:
        from .companion import recommend_boundary
        boundary_fn = lambda q: recommend_boundary(project, q, regime)

    step = (q_max - q_min) / max(n_points - 1, 1)
    points: List[RatingPoint] = []
    for i in range(n_points):
        q = q_min + i * step
        wse_boundary = boundary_fn(q)
        result = solve_profile(reach, q, wse_boundary, regime=regime)
        # Report at requested xs_index (after the solver sorted upstream).
        if 0 <= xs_index < len(result.sections):
            s = result.sections[xs_index]
            points.append(RatingPoint(
                discharge=q, wse=s.wse, depth=s.depth,
                velocity=s.velocity, froude=s.froude,
            ))
    return points


# =============================================================================
# Freeboard check
# =============================================================================

@dataclass
class FreeboardRow:
    xs_name: str
    wse: float
    top_of_bank: float
    freeboard: float
    ok: bool


def freeboard_check(result: ProfileResult, reach: Reach,
                    required: float = FREEBOARD_REQ) -> List[FreeboardRow]:
    """
    For each XS in the result, compare WSE to the lower of the two bank tops
    (if bank stations are set) and report freeboard.
    """
    by_name: Dict[str, CrossSection] = {xs.name: xs for xs in reach.cross_sections}
    rows: List[FreeboardRow] = []
    for s in result.sections:
        xs = by_name.get(s.name)
        if xs is None:
            continue
        tob = _top_of_bank(xs)
        fb = tob - s.wse
        rows.append(FreeboardRow(
            xs_name=s.name, wse=s.wse, top_of_bank=tob,
            freeboard=fb, ok=(fb >= required),
        ))
    return rows


def _top_of_bank(xs: CrossSection) -> float:
    """Elevation of the *lower* of the two bank tops - that's what overtops
    first. If bank stations aren't set, we use the lowest of the two end
    ground points as a conservative estimate."""
    if xs.left_bank is None or xs.right_bank is None:
        return min(xs.elevations[0], xs.elevations[-1])
    lo = _z_at_station(xs, xs.left_bank)
    hi = _z_at_station(xs, xs.right_bank)
    return min(lo, hi)


def _z_at_station(xs: CrossSection, x: float) -> float:
    """Linearly interpolate ground elevation at station `x`."""
    xs_stations, xs_z = xs.stations, xs.elevations
    if x <= xs_stations[0]:
        return xs_z[0]
    if x >= xs_stations[-1]:
        return xs_z[-1]
    for i in range(len(xs_stations) - 1):
        x1, x2 = xs_stations[i], xs_stations[i + 1]
        if x1 <= x <= x2:
            t = (x - x1) / (x2 - x1) if x2 != x1 else 0.0
            return xs_z[i] + t * (xs_z[i + 1] - xs_z[i])
    return xs_z[-1]


# =============================================================================
# Summary table
# =============================================================================

def summarize(result: ProfileResult) -> str:
    """Return a CSV-style text block of the profile for display/export."""
    headers = ("Name", "Station", "WSE", "Depth", "Velocity",
               "Froude", "EnergyGrade", "Regime", "Iter", "Converged")
    lines = [",".join(headers)]
    for s in result.sections:
        lines.append(",".join([
            s.name,
            f"{s.station:.2f}",
            f"{s.wse:.3f}",
            f"{s.depth:.3f}",
            f"{s.velocity:.3f}",
            f"{s.froude:.3f}",
            f"{s.energy_grade:.3f}",
            s.flow_regime,
            str(s.iterations),
            "yes" if s.converged else "NO",
        ]))
    return "\n".join(lines)
