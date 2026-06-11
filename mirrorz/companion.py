"""
mirrorz/companion.py
================================================================================
"Hecras Helper" - the guided companion for MirrorZ-Hecras.

WHAT IT DOES
--------------------------------------------------------------------------------
Gives a first-time user a guided workflow, plain-language explanations, and
sanity-check warnings. Think of it as the clippy-for-hydraulics: it does NOT
call a large language model; every tip is rule-based and lives in this file,
so you can read every answer it might give.

The GUI queries three entry points:
    welcome()              -> splash text with a guided first-task list
    explain(topic)         -> plain-english paragraph on a named concept
    inspect_project(p)     -> list of warnings/suggestions about a project
    next_steps(result)     -> post-run guidance based on a ProfileResult

HIGHLIGHTED TWEAK AREAS
--------------------------------------------------------------------------------
  ### TWEAK: EXPLAIN_TEXTS ### Edit/extend the glossary strings.
  ### TWEAK: N_TABLE ###       Typical Manning's n for the "pick a roughness"
                               dialog (Chow 1959 summarized).
  ### TWEAK: SANITY_LIMITS ### Numeric thresholds that trigger warnings.
================================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .project import Project
from .solver import ProfileResult
from . import hydraulics as hy


# =============================================================================
# ### TWEAK: N_TABLE ###
# -----------------------------------------------------------------------------
# Condensed from Chow (1959) Table 5-6 and HEC-RAS reference manual Table 3-1.
# Values are "clean, well-maintained" ranges - multiply by 1.3-1.5 if banks
# are weedy or if obstructions (debris, meanders) are significant.
# =============================================================================
N_TABLE = [
    ("Smooth concrete lining",          0.012),
    ("Rough concrete / gunite",         0.017),
    ("Earthen canal, clean straight",   0.022),
    ("Earthen canal, some weeds",       0.030),
    ("Natural stream, clean",           0.035),
    ("Natural stream, stones & weeds",  0.045),
    ("Floodplain, light brush",         0.060),
    ("Floodplain, heavy brush / trees", 0.100),
]


# =============================================================================
# ### TWEAK: SANITY_LIMITS ###
# -----------------------------------------------------------------------------
# These thresholds determine when the companion flags a model. They are
# educational defaults and can be loosened/tightened for your context.
# =============================================================================
FROUDE_HIGH         = 0.9     # flirts with critical - warn user
FROUDE_CRITICAL_TOL = 0.05    # near-critical if |Fr-1| < this
VELOCITY_HIGH       = 3.0     # m/s - velocities above this erode most soils
DEPTH_SHALLOW       = 0.05    # m  - below this we can't trust Manning's
N_MIN, N_MAX        = 0.010, 0.200
SLOPE_SHALLOW       = 1.0e-5  # below this, friction-slope numerics wobble
SLOPE_STEEP         = 0.10    # above this, 1D assumptions break down


# =============================================================================
# ### TWEAK: EXPLAIN_TEXTS ###
# -----------------------------------------------------------------------------
# One-paragraph primers on concepts the GUI exposes. Keep them short and
# reference-able; the wizard wraps them in a dialog.
# =============================================================================
_EXPLAIN = {
    "manning": (
        "Manning's equation is the workhorse of open-channel hydraulics. "
        "It says discharge equals conveyance times the square root of the "
        "energy slope: Q = (k/n) * A * R^(2/3) * sqrt(S). The roughness n "
        "is empirical - it lumps surface texture, bed forms, vegetation, "
        "and small-scale irregularities into one number."
    ),
    "froude": (
        "Froude number Fr = V / sqrt(g * D) compares inertia to gravity. "
        "Fr < 1 is sub-critical flow - slow, deep, controlled from "
        "downstream. Fr > 1 is super-critical - fast, shallow, controlled "
        "from upstream. At Fr = 1 (critical flow) the specific energy is "
        "minimum and small disturbances can't travel upstream."
    ),
    "critical_depth": (
        "Critical depth is the unique water depth at which the specific "
        "energy E = y + V^2/(2g) is minimum for a given discharge. A free "
        "overfall, a weir crest, and the bottom of a steep-to-mild slope "
        "transition all force the flow through critical depth; that's why "
        "it's useful as a control section."
    ),
    "normal_depth": (
        "Normal depth is the depth at which gravity and friction balance "
        "exactly and the water surface becomes parallel to the bed. For a "
        "long prismatic channel with constant Q, any profile asymptotes "
        "toward normal depth. We use it to seed downstream boundary "
        "conditions when a real rating curve isn't available."
    ),
    "standard_step": (
        "The standard-step method iterates the energy equation between "
        "two cross-sections. Given a known water surface at one section, "
        "guess the WSE at the next, compute average friction slope, and "
        "adjust the guess until energies match. March upstream for "
        "sub-critical profiles, downstream for super-critical."
    ),
    "contraction_expansion": (
        "When a channel narrows (contraction) or widens (expansion) "
        "between sections, some velocity head is lost as turbulence. "
        "HEC-RAS approximates this as a coefficient times the change in "
        "velocity head. Typical values: 0.1/0.3 for gentle transitions, "
        "0.3/0.5 for bridges, 0.6/0.8 for abrupt structures."
    ),
}


def welcome() -> str:
    """Splash message shown the first time the GUI opens."""
    return (
        "Welcome to MirrorZ-Hecras!\n\n"
        "This is an educational mirror of HEC-RAS concepts: 1D steady-flow "
        "hydraulics, the standard-step method, and open-channel geometry. "
        "Everything here is inspectable Python you can read and tweak.\n\n"
        "Suggested first steps:\n"
        "  1. File -> New Project (starts from a default trapezoidal stream)\n"
        "  2. Open the Cross-Section tab and change a point to see the area\n"
        "     update in real time.\n"
        "  3. Run -> Compute Profile and view the water surface plot.\n"
        "  4. Ask the Companion to Explain any term you don't recognize.\n\n"
        "Nothing in this tool is certified for regulatory work - use real "
        "HEC-RAS for anything that matters to a permit or a levee."
    )


def explain(topic: str) -> str:
    """Return a short explanation of a hydraulics term. Unknown -> fallback."""
    topic = topic.strip().lower().replace(" ", "_").replace("-", "_")
    if topic in _EXPLAIN:
        return _EXPLAIN[topic]
    # Fuzzy-ish match: substring search
    for key, text in _EXPLAIN.items():
        if key in topic or topic in key:
            return text
    return (
        f"I don't have a primer on {topic!r} yet. Topics I do know: "
        + ", ".join(sorted(_EXPLAIN.keys())) + "."
    )


# =============================================================================
# Project-level sanity checks.
# =============================================================================

@dataclass
class Hint:
    level: str      # "info", "warn", "error"
    message: str


def inspect_project(project: Project) -> List[Hint]:
    """Run rule-based checks against a project. Returns hints for the GUI."""
    hints: List[Hint] = []

    if not project.reaches:
        hints.append(Hint("error", "Project has no reaches. Add one before running."))
        return hints

    for reach in project.reaches:
        if len(reach.cross_sections) < 2:
            hints.append(Hint("error",
                f"Reach '{reach.name}' needs at least two cross-sections to run."))
            continue
        prev_thalweg = None
        for xs in reach.cross_sections:
            # Roughness plausibility
            for label, n in [("channel", xs.n_channel),
                             ("left",    xs.n_left),
                             ("right",   xs.n_right)]:
                if n < N_MIN or n > N_MAX:
                    hints.append(Hint("warn",
                        f"{reach.name}/{xs.name}: {label} Manning's n={n:.3f} "
                        f"is outside typical range [{N_MIN:.3f}, {N_MAX:.3f}]."))

            # Bank-station ordering
            if xs.left_bank is not None and xs.right_bank is not None:
                if xs.left_bank >= xs.right_bank:
                    hints.append(Hint("error",
                        f"{reach.name}/{xs.name}: left bank station must be "
                        f"less than right bank station."))

            # Thalweg monotonicity for sub-critical default
            if prev_thalweg is not None and xs.min_elevation < prev_thalweg:
                hints.append(Hint("info",
                    f"{reach.name}/{xs.name}: thalweg drops between sections "
                    f"going upstream. Check station direction if unexpected."))
            prev_thalweg = xs.min_elevation

    for flow in project.flows:
        if flow.discharge <= 0:
            hints.append(Hint("error", f"Flow '{flow.name}' has Q <= 0."))
    if not project.flows:
        hints.append(Hint("warn",
            "No flow plan defined. Add one under Run -> Flow Plans."))

    return hints


# =============================================================================
# Post-run guidance based on a ProfileResult.
# =============================================================================

def next_steps(result: ProfileResult) -> List[Hint]:
    hints: List[Hint] = []
    if not result.sections:
        hints.append(Hint("error", "Solver returned no sections."))
        return hints

    for s in result.sections:
        if abs(s.froude - 1.0) < FROUDE_CRITICAL_TOL:
            hints.append(Hint("warn",
                f"{s.name}: Froude {s.froude:.2f} is near critical. "
                "Consider refining geometry or switching to a mixed-flow run."))
        elif s.froude > FROUDE_HIGH and s.flow_regime == "subcritical":
            hints.append(Hint("info",
                f"{s.name}: Froude {s.froude:.2f} is high for a sub-critical "
                "profile. Verify your regime choice."))
        if s.velocity > VELOCITY_HIGH:
            hints.append(Hint("info",
                f"{s.name}: velocity {s.velocity:.2f} m/s may erode "
                "unprotected banks."))
        if s.depth < DEPTH_SHALLOW:
            hints.append(Hint("warn",
                f"{s.name}: depth {s.depth:.3f} m is very shallow; Manning "
                "friction terms become unreliable."))
        if not s.converged:
            hints.append(Hint("error",
                f"{s.name}: iteration did not converge. Tighten geometry "
                "spacing or check for abrupt transitions."))
    if not hints:
        hints.append(Hint("info",
            "Model looks healthy: all sections converged and stayed in the "
            "expected flow regime. Try running at a higher discharge to "
            "explore the rating behavior."))
    return hints


# =============================================================================
# Quick helpers the GUI wizard uses for default flow selection.
# =============================================================================

def recommend_boundary(project: Project, discharge: float,
                       regime: str = "subcritical") -> float:
    """
    Best-guess boundary WSE using normal depth at the controlling section.
    For sub-critical flow the controlling boundary is the downstream-most
    section; for super-critical it's the upstream-most.
    """
    if not project.reaches:
        return 0.0
    reach = project.reaches[0]
    reach.sort_upstream()
    xs = reach.cross_sections[0] if regime == "subcritical" \
         else reach.cross_sections[-1]
    # Infer slope from adjacent section if possible.
    if len(reach.cross_sections) >= 2:
        xs2 = reach.cross_sections[1]
        dz = xs2.min_elevation - xs.min_elevation
        dx = xs.reach_length_channel or 100.0
        slope = max(dz / dx, 1.0e-4)
    else:
        slope = 1.0e-3
    yn = hy.normal_depth(discharge, slope, xs.n_channel, xs.section_fn())
    return xs.min_elevation + yn
