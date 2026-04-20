"""
src/hydraulics.py
================================================================================
Core open-channel hydraulics for MirrorZ-Hecras.

WHAT THIS FILE CONTAINS
--------------------------------------------------------------------------------
  * Manning's equation (discharge, velocity, friction slope)
  * Energy/momentum helpers (specific energy, Froude number, hydraulic depth)
  * Critical-depth solver (minimum specific energy)
  * Normal-depth solver (uniform flow for a given slope)
  * Conveyance (K) used by the standard-step method in src/solver.py

HEC-RAS PARALLEL
--------------------------------------------------------------------------------
HEC-RAS computes these same quantities at every cross-section for every
profile. The math here matches HEC-RAS Reference Manual Chapter 2 ("Theoretical
Basis for 1-D Flow Calculations"); we just expose it in plain Python so you
can inspect each step.

HIGHLIGHTED TWEAK AREAS  (search the tags to jump straight there)
--------------------------------------------------------------------------------
  ### TWEAK: UNITS ###           Switch between SI and US customary units.
  ### TWEAK: ROOT_FINDER ###     Swap scipy.brentq for a bisection fallback.
  ### TWEAK: NUMERIC_TOLS ###    Convergence tolerances & iteration caps.
  ### TWEAK: MIN_DEPTH ###       Floor on depth to avoid divide-by-zero.

LEARNING ANCHORS
--------------------------------------------------------------------------------
  ### LEARN: MANNING ###         Plain-English walkthrough of Manning's eq.
  ### LEARN: CRITICAL ###        Why critical depth matters.
  ### LEARN: FROUDE ###          Sub-/super-critical flow regimes.
  ### LEARN: CONVEYANCE ###      Why we split a cross-section into strips.
================================================================================
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Optional

# scipy.brentq is a robust bracketed root-finder. If scipy isn't available
# we fall back to the bisection function defined below. See ### TWEAK: ROOT_FINDER ###.
try:
    from scipy.optimize import brentq as _scipy_brentq  # type: ignore
    _HAS_SCIPY = True
except Exception:  # pragma: no cover - environment-dependent
    _HAS_SCIPY = False


# =============================================================================
# ### TWEAK: UNITS ###
# -----------------------------------------------------------------------------
# Manning's equation has a unit coefficient "k" that changes with unit system.
#   SI (meters, seconds):   k = 1.0
#   US customary (feet, s): k = 1.486
# HEC-RAS lets the user pick; we expose the same choice. All downstream
# modules import MANNING_K via get_unit_system() so a single switch
# propagates everywhere.
# =============================================================================
_UNIT_SYSTEM = "SI"  # change via set_unit_system("US") at runtime

_MANNING_K = {"SI": 1.0, "US": 1.486}
_GRAVITY   = {"SI": 9.80665, "US": 32.174}   # m/s^2 or ft/s^2

def set_unit_system(system: str) -> None:
    """Set global unit system. Accepts 'SI' or 'US'."""
    global _UNIT_SYSTEM
    system = system.upper()
    if system not in _MANNING_K:
        raise ValueError(f"Unknown unit system: {system!r}. Use 'SI' or 'US'.")
    _UNIT_SYSTEM = system

def get_unit_system() -> str:
    return _UNIT_SYSTEM

def manning_k() -> float:
    """Manning conversion factor for the current unit system."""
    return _MANNING_K[_UNIT_SYSTEM]

def gravity() -> float:
    """Gravitational acceleration (m/s^2 or ft/s^2 depending on units)."""
    return _GRAVITY[_UNIT_SYSTEM]


# =============================================================================
# ### TWEAK: NUMERIC_TOLS ###
# -----------------------------------------------------------------------------
# These control how fast / how precisely the solvers converge. If you see
# "did not converge" warnings, loosen DEPTH_TOL or raise MAX_ITERS. If you
# want super-crisp answers for research, tighten DEPTH_TOL.
# =============================================================================
DEPTH_TOL  = 1.0e-6   # convergence tolerance on depth (ft or m)
ENERGY_TOL = 1.0e-4   # convergence tolerance on energy (HEC-RAS default 0.01 ft; we use 1e-4 m ≈ 0.0003 ft)
MAX_ITERS  = 40       # iteration cap for any local solver
# ### TWEAK: MIN_DEPTH ### - guard against zero-depth blow-ups.
MIN_DEPTH  = 1.0e-4   # absolute floor on depth used in friction-slope calcs


# =============================================================================
# ### TWEAK: ROOT_FINDER ###
# -----------------------------------------------------------------------------
# scipy.optimize.brentq is the default. This pure-Python bisection is used if
# scipy is missing OR if you want a dependency-free build. To force the
# fallback without uninstalling scipy, set USE_PURE_BISECTION = True.
# =============================================================================
USE_PURE_BISECTION = False

def _bisect(f: Callable[[float], float], lo: float, hi: float,
            tol: float = DEPTH_TOL, max_iter: int = 200) -> float:
    """Classic bisection. Requires a sign change between lo and hi."""
    flo, fhi = f(lo), f(hi)
    if flo * fhi > 0:
        raise ValueError("Bisection bracket does not contain a root.")
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        fmid = f(mid)
        if abs(fmid) < tol or (hi - lo) < tol:
            return mid
        if flo * fmid < 0:
            hi, fhi = mid, fmid
        else:
            lo, flo = mid, fmid
    return 0.5 * (lo + hi)

def _root(f: Callable[[float], float], lo: float, hi: float,
          tol: float = DEPTH_TOL) -> float:
    if _HAS_SCIPY and not USE_PURE_BISECTION:
        return float(_scipy_brentq(f, lo, hi, xtol=tol))
    return _bisect(f, lo, hi, tol=tol)


# =============================================================================
# ### LEARN: MANNING ###
# -----------------------------------------------------------------------------
# Manning's equation (empirical, 1889) relates channel discharge Q to shape
# and slope:
#
#     Q = (k / n) * A * R^(2/3) * S^(1/2)
#
# where:
#     n  = Manning roughness coefficient (dimensionless, tabulated by surface)
#     A  = flow area                    (m^2 or ft^2)
#     R  = hydraulic radius = A / P     (m or ft); P = wetted perimeter
#     S  = slope (energy slope for gradually varied flow; bed slope for uniform)
#     k  = 1.0 in SI, 1.486 in US customary
#
# Typical n values (glance table):
#     smooth concrete channel ....... 0.012 - 0.015
#     earthen canal, clean .......... 0.018 - 0.025
#     natural stream, few weeds ..... 0.030 - 0.035
#     dense vegetation / floodplain . 0.050 - 0.100+
#
# We keep the math in Python, not numpy, for scalar calls so the code is
# easy to trace in a debugger.
# =============================================================================

def manning_discharge(n: float, area: float, hyd_radius: float, slope: float) -> float:
    """Return Q using Manning's equation. Slope must be > 0."""
    if area <= 0.0 or hyd_radius <= 0.0:
        return 0.0
    # NOTE: slope can be extremely small (mild rivers). We clamp to a tiny
    # positive number so sqrt doesn't explode or go complex on numerical noise.
    s = max(slope, 1.0e-12)
    return (manning_k() / n) * area * (hyd_radius ** (2.0 / 3.0)) * math.sqrt(s)


def manning_velocity(n: float, hyd_radius: float, slope: float) -> float:
    """Return mean velocity V = Q / A (useful when A is already known)."""
    s = max(slope, 1.0e-12)
    return (manning_k() / n) * (hyd_radius ** (2.0 / 3.0)) * math.sqrt(s)


def friction_slope(q: float, n: float, area: float, hyd_radius: float) -> float:
    """
    Energy / friction slope S_f from Manning's equation, given a discharge.

        S_f = ( Q * n / ( k * A * R^(2/3) ) )^2

    This is what the standard-step solver uses to balance the energy equation
    between two cross-sections.
    """
    area = max(area, MIN_DEPTH)       # guard
    hyd_radius = max(hyd_radius, MIN_DEPTH)
    num = q * n
    den = manning_k() * area * (hyd_radius ** (2.0 / 3.0))
    return (num / den) ** 2


# =============================================================================
# ### LEARN: CONVEYANCE ###
# -----------------------------------------------------------------------------
# Conveyance K lumps geometry + roughness into one number:
#
#     K = (k / n) * A * R^(2/3)       so that   Q = K * sqrt(S)
#
# HEC-RAS subdivides a cross-section into "panels" (left overbank, channel,
# right overbank) and sums the K of each panel. That lets a single section
# carry different n values across its width - which matches reality: a
# grassy floodplain is much rougher than the main channel.
# =============================================================================

def conveyance(n: float, area: float, hyd_radius: float) -> float:
    if area <= 0.0 or hyd_radius <= 0.0:
        return 0.0
    return (manning_k() / n) * area * (hyd_radius ** (2.0 / 3.0))


# =============================================================================
# ### LEARN: FROUDE ### and ### LEARN: CRITICAL ###
# -----------------------------------------------------------------------------
# Froude number Fr = V / sqrt(g * D_h) where D_h = A / T (hydraulic depth,
# T = top width). Fr < 1: sub-critical (tranquil, slow, deep); Fr > 1:
# super-critical (fast, shallow). Fr = 1 at *critical depth*, where the
# specific-energy curve reaches its minimum for a given discharge. Critical
# depth is a natural control section (weirs, free overfalls).
# =============================================================================

def froude_number(velocity: float, hyd_depth: float) -> float:
    if hyd_depth <= 0.0:
        return float("inf")
    return velocity / math.sqrt(gravity() * hyd_depth)


def specific_energy(depth: float, velocity: float) -> float:
    """E = y + V^2 / (2g). Energy measured from channel bed."""
    return depth + (velocity * velocity) / (2.0 * gravity())


# -----------------------------------------------------------------------------
# Rectangular channel closed-form helpers (used by the wizard for quick checks
# and by unit tests). For non-rectangular/natural sections use geometry.py.
# -----------------------------------------------------------------------------

@dataclass
class RectResult:
    depth: float
    velocity: float
    area: float
    froude: float


def rect_critical_depth(q: float, width: float) -> float:
    """
    Closed-form critical depth for a rectangular channel:

        y_c = ( q^2 / (g * b^2) )^(1/3)       with q the TOTAL discharge

    Useful as a sanity check against the generic numerical solver.
    """
    if width <= 0 or q <= 0:
        return 0.0
    return (q * q / (gravity() * width * width)) ** (1.0 / 3.0)


def rect_normal_depth(q: float, width: float, n: float, slope: float,
                      depth_max: float = 100.0) -> float:
    """Normal depth in a rectangular channel (Manning) via root-finding."""
    def f(y: float) -> float:
        a = width * y
        p = width + 2.0 * y
        r = a / p
        return manning_discharge(n, a, r, slope) - q
    # Bracket: y -> 0 gives Q=0, y large gives Q huge; root exists for q>0.
    return _root(f, MIN_DEPTH, depth_max)


# =============================================================================
# Generic critical / normal depth on arbitrary section functions.
# -----------------------------------------------------------------------------
# `section_fn(y)` returns a tuple (A, T, P):
#     A = wetted area at depth y
#     T = top width at depth y
#     P = wetted perimeter at depth y
# This is exactly what src/geometry.py.CrossSection.hydraulic_properties()
# produces, so the two modules plug together cleanly.
# =============================================================================

SectionFn = Callable[[float], tuple]  # (A, T, P)


def critical_depth(q: float, section_fn: SectionFn,
                   y_lo: float = MIN_DEPTH, y_hi: float = 100.0) -> float:
    """
    Critical depth: the y where Fr = 1, i.e. Q^2 * T / (g * A^3) = 1.

    We solve g(y) = Q^2 * T(y) - g * A(y)^3 = 0. The function is monotone
    under normal conditions, so a bracketed root-finder converges quickly.
    """
    g_acc = gravity()

    def residual(y: float) -> float:
        A, T, _P = section_fn(y)
        A = max(A, MIN_DEPTH)
        T = max(T, MIN_DEPTH)
        return q * q * T - g_acc * A ** 3

    # ### WARN ###: if residual has the same sign at both ends, the bracket
    # is wrong (e.g. y_hi too small). We expand once before giving up.
    try:
        return _root(residual, y_lo, y_hi)
    except ValueError:
        return _root(residual, y_lo, y_hi * 10.0)


def normal_depth(q: float, slope: float, n: float, section_fn: SectionFn,
                 y_lo: float = MIN_DEPTH, y_hi: float = 100.0) -> float:
    """
    Normal depth for uniform flow on arbitrary section. Solves
    Manning's discharge = Q.
    """
    def residual(y: float) -> float:
        A, _T, P = section_fn(y)
        if P <= 0 or A <= 0:
            return -q
        R = A / P
        return manning_discharge(n, A, R, slope) - q
    try:
        return _root(residual, y_lo, y_hi)
    except ValueError:
        return _root(residual, y_lo, y_hi * 10.0)


# =============================================================================
# Convenience dataclass used by the analyzer to carry a section snapshot.
# =============================================================================

@dataclass
class HydraulicState:
    """A single-section hydraulic snapshot - what the GUI/analyzer renders."""
    depth: float
    area: float
    top_width: float
    wetted_perimeter: float
    hyd_radius: float
    velocity: float
    froude: float
    energy: float
    conveyance: float
    friction_slope: float
