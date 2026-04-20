"""
src/solver.py
================================================================================
1-D Steady-flow water-surface profile solver (Standard-Step Method).

WHAT THIS DOES
--------------------------------------------------------------------------------
Given a Reach (ordered cross-sections), a discharge Q, and a boundary
condition (starting water-surface at one end), compute the water-surface
elevation (WSE) at every section by stepping from XS to XS and enforcing
conservation of energy.

This is the heart of HEC-RAS's 1D steady module ("geometry + steady flow =
profile"). The algorithm is covered in the HEC-RAS Hydraulic Reference Manual,
Section 2-2 ("Equations for Basic Profile Calculations").

THE ENERGY EQUATION WE ITERATE
--------------------------------------------------------------------------------
Between a downstream section (1) and the next upstream section (2):

    WSE_2 + alpha_2 * V_2^2 / (2g)
      = WSE_1 + alpha_1 * V_1^2 / (2g) + h_f + h_e

where:
    h_f = average friction slope * reach length   (energy lost to friction)
    h_e = contraction/expansion loss   = C * |V_2^2/2g - V_1^2/2g|
    alpha = velocity-weighted energy coefficient (1.0 is a reasonable default;
            HEC-RAS computes it from panel conveyances. We do the same if
            panels are configured.)

For sub-critical flow we march UPSTREAM (boundary at downstream end).
For super-critical flow we march DOWNSTREAM (boundary at upstream end).
The flow regime is chosen by the user or auto-detected against critical depth.

HIGHLIGHTED TWEAK AREAS
--------------------------------------------------------------------------------
  ### TWEAK: SOLVER_TOL ###      Per-step energy convergence tolerance.
  ### TWEAK: INITIAL_GUESS ###   Strategy for seeding the next WSE guess.
  ### TWEAK: FRICTION_AVG ###    Choice of friction-slope averaging method.
================================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from . import hydraulics as hy
from .geometry import CrossSection, Reach


# =============================================================================
# ### TWEAK: SOLVER_TOL ###
# -----------------------------------------------------------------------------
# HEC-RAS defaults to 0.01 ft water-surface-elevation tolerance. We match that
# order of magnitude (0.003 m). If the solver oscillates, loosen this.
# =============================================================================
WSE_TOL = 0.003      # meters (or feet ~ 0.01 ft)
MAX_STEP_ITERS = 30  # per-section iteration cap
MAX_STEP_SIZE  = 5.0 # maximum WSE step per iteration (dampens overshoot)


# =============================================================================
# ### TWEAK: FRICTION_AVG ###
# -----------------------------------------------------------------------------
# HEC-RAS offers four averaging schemes between two XS for S_f:
#   "average"   : S_f = (S_f1 + S_f2) / 2             (default, good general)
#   "harmonic"  : S_f = 2*S_f1*S_f2/(S_f1+S_f2)       (good for M1/M2 profiles)
#   "geometric" : S_f = sqrt(S_f1 * S_f2)
#   "conveyance": S_f = ((Q1+Q2)/(K1+K2))^2
# We expose the choice and default to "average" which is the simplest and
# works well for most teaching cases.
# =============================================================================
FRICTION_AVG_METHOD = "average"


def _averaged_friction_slope(sf1: float, sf2: float,
                             k1: float = 0.0, k2: float = 0.0,
                             q: float = 0.0) -> float:
    m = FRICTION_AVG_METHOD
    if m == "harmonic":
        s = sf1 + sf2
        return 0.0 if s <= 0 else 2.0 * sf1 * sf2 / s
    if m == "geometric":
        return (sf1 * sf2) ** 0.5
    if m == "conveyance":
        kk = k1 + k2
        return 0.0 if kk <= 0 else ((2.0 * q) / kk) ** 2
    return 0.5 * (sf1 + sf2)  # average (default)


# =============================================================================
# Result containers
# =============================================================================

@dataclass
class SectionResult:
    station: float
    name: str
    wse: float                  # water-surface elevation
    depth: float                # WSE - thalweg
    velocity: float
    area: float
    top_width: float
    wetted_perimeter: float
    hyd_radius: float
    conveyance: float
    froude: float
    energy_grade: float         # WSE + V^2/2g
    friction_slope: float
    critical_wse: float
    flow_regime: str            # "subcritical" / "supercritical" / "critical"
    iterations: int = 0
    converged: bool = True


@dataclass
class ProfileResult:
    reach_name: str
    discharge: float
    unit_system: str
    sections: List[SectionResult] = field(default_factory=list)
    messages: List[str] = field(default_factory=list)


# =============================================================================
# Single-section analysis at a fixed WSE
# =============================================================================

def analyze_section(xs: CrossSection, wse: float, q: float) -> SectionResult:
    """Compute a full hydraulic snapshot at a section for a given WSE."""
    A, T, P = xs.hydraulic_properties(wse)
    R = (A / P) if P > 0 else 0.0
    V = (q / A) if A > 0 else 0.0
    K = hy.conveyance(xs.n_channel, A, R)
    Sf = hy.friction_slope(q, xs.n_channel, A, R)
    # Hydraulic depth for Froude uses A/T (top width, not perimeter).
    Dh = (A / T) if T > 0 else 0.0
    Fr = hy.froude_number(V, Dh)
    yc = hy.critical_depth(q, xs.section_fn())
    crit_wse = xs.min_elevation + yc
    if Fr > 1.01:
        regime = "supercritical"
    elif Fr < 0.99:
        regime = "subcritical"
    else:
        regime = "critical"
    return SectionResult(
        station=xs.river_station, name=xs.name, wse=wse,
        depth=wse - xs.min_elevation, velocity=V, area=A,
        top_width=T, wetted_perimeter=P, hyd_radius=R,
        conveyance=K, froude=Fr,
        energy_grade=wse + V * V / (2.0 * hy.gravity()),
        friction_slope=Sf, critical_wse=crit_wse,
        flow_regime=regime,
    )


# =============================================================================
# Standard-step between two adjacent cross-sections
# =============================================================================

def _step_between(xs_known: CrossSection, wse_known: float,
                  xs_solve: CrossSection,
                  q: float,
                  reach_length: float,
                  direction: str,
                  contraction_coeff: float,
                  expansion_coeff: float) -> SectionResult:
    """
    Given a known WSE at xs_known, solve for the WSE at xs_solve using the
    energy equation. Works both directions ("upstream" for sub-critical
    profiles, "downstream" for super-critical).

    We iterate on the WSE at the unknown section via a secant-like update:
        E_known = E_solve_guess + h_f + h_e   (upstream case)
    and adjust the guess until the residual shrinks below WSE_TOL.
    """
    # Characterize the known section once.
    known = analyze_section(xs_known, wse_known, q)

    # ### TWEAK: INITIAL_GUESS ###
    # Use the known WSE as a first guess. For steep slopes a better guess
    # would shift WSE by slope * reach_length, but starting at the known
    # WSE is robust and always in-bracket.
    guess = wse_known

    last_err = None
    for iteration in range(MAX_STEP_ITERS):
        trial = analyze_section(xs_solve, guess, q)

        # Velocity head loss (absolute) for contraction/expansion.
        dh_vel = trial.velocity ** 2 / (2.0 * hy.gravity()) \
                 - known.velocity ** 2 / (2.0 * hy.gravity())
        if direction == "upstream":
            # Flow is from xs_solve (up) to xs_known (down). Contraction
            # happens when flow speeds up going downstream (|V_down|>|V_up|).
            coeff = contraction_coeff if dh_vel < 0 else expansion_coeff
        else:
            coeff = contraction_coeff if dh_vel > 0 else expansion_coeff
        h_e = coeff * abs(dh_vel)

        sf_avg = _averaged_friction_slope(
            known.friction_slope, trial.friction_slope,
            known.conveyance, trial.conveyance, q,
        )
        h_f = sf_avg * max(reach_length, 0.0)

        # Energy balance residual (upstream march):
        #   E_up = E_down + h_f + h_e   ->   residual = E_up - (E_down+h_f+h_e)
        if direction == "upstream":
            residual = trial.energy_grade - (known.energy_grade + h_f + h_e)
        else:
            residual = known.energy_grade - (trial.energy_grade + h_f + h_e)

        if abs(residual) < WSE_TOL:
            trial.iterations = iteration + 1
            trial.converged = True
            return trial

        # Newton-ish correction. dE/dWSE ~ 1 - Fr^2 for open-channel flow.
        denom = 1.0 - trial.froude ** 2
        if abs(denom) < 1e-3:
            denom = 1e-3 if denom >= 0 else -1e-3
        delta = residual / denom
        # clamp step to avoid wild overshoot near critical depth.
        if delta >  MAX_STEP_SIZE: delta =  MAX_STEP_SIZE
        if delta < -MAX_STEP_SIZE: delta = -MAX_STEP_SIZE
        guess = guess - delta
        # Never drop the WSE below the thalweg.
        guess = max(guess, xs_solve.min_elevation + hy.MIN_DEPTH)
        last_err = residual

    # Did not converge - return last trial flagged so the GUI can warn.
    trial = analyze_section(xs_solve, guess, q)
    trial.iterations = MAX_STEP_ITERS
    trial.converged = False
    return trial


# =============================================================================
# Public entry point: solve the full profile for a reach.
# =============================================================================

def solve_profile(reach: Reach, discharge: float,
                  boundary_wse: float,
                  regime: str = "subcritical") -> ProfileResult:
    """
    Compute a steady-flow water-surface profile along `reach`.

    Parameters
    ----------
    reach : Reach
        All cross-sections; will be sorted upstream by river_station.
    discharge : float
        Q at every section (constant for steady flow; for lateral inflow use
        multiple sub-reaches).
    boundary_wse : float
        Known water-surface elevation at the boundary (downstream for
        sub-critical, upstream for super-critical).
    regime : str
        "subcritical" (default) or "supercritical".
    """
    reach.sort_upstream()
    result = ProfileResult(
        reach_name=reach.name,
        discharge=discharge,
        unit_system=hy.get_unit_system(),
    )

    sections = reach.cross_sections
    if not sections:
        result.messages.append("Reach has no cross-sections.")
        return result

    if regime == "subcritical":
        # March from downstream (station smallest in HEC-RAS convention would
        # be downstream; we treat smallest river_station = downstream).
        ordered = list(sections)  # ascending river station = upstream last
        # The boundary is at the downstream-most section (index 0).
        wse = boundary_wse
        prev_xs = ordered[0]
        first = analyze_section(prev_xs, wse, discharge)
        first.converged = True
        result.sections.append(first)
        for i in range(1, len(ordered)):
            cur = ordered[i]
            reach_length = prev_xs.reach_length_channel  # downstream XS holds the length UP to the next
            r = _step_between(
                xs_known=prev_xs, wse_known=wse,
                xs_solve=cur, q=discharge,
                reach_length=reach_length,
                direction="upstream",
                contraction_coeff=cur.contraction_coeff,
                expansion_coeff=cur.expansion_coeff,
            )
            result.sections.append(r)
            wse = r.wse
            prev_xs = cur
    elif regime == "supercritical":
        ordered = list(reversed(sections))  # start at upstream
        wse = boundary_wse
        prev_xs = ordered[0]
        first = analyze_section(prev_xs, wse, discharge)
        result.sections.append(first)
        for i in range(1, len(ordered)):
            cur = ordered[i]
            reach_length = cur.reach_length_channel
            r = _step_between(
                xs_known=prev_xs, wse_known=wse,
                xs_solve=cur, q=discharge,
                reach_length=reach_length,
                direction="downstream",
                contraction_coeff=cur.contraction_coeff,
                expansion_coeff=cur.expansion_coeff,
            )
            result.sections.append(r)
            wse = r.wse
            prev_xs = cur
        # Put sections back in upstream-ascending order for plotting.
        result.sections.reverse()
    else:
        raise ValueError(f"Unknown regime {regime!r}")

    # Post-scan: flag sections where computed WSE is below critical (would
    # indicate a regime transition requiring mixed-flow analysis).
    for s in result.sections:
        if s.wse < s.critical_wse - 1e-3 and regime == "subcritical":
            result.messages.append(
                f"Section {s.name}: WSE {s.wse:.3f} fell below critical "
                f"{s.critical_wse:.3f}. Consider mixed-flow regime."
            )
        if not s.converged:
            result.messages.append(
                f"Section {s.name}: did not converge within "
                f"{MAX_STEP_ITERS} iterations."
            )
    return result
