# ============================================================================
# MirrorZ-Hecras - an educational open-source mirror of HEC-RAS concepts.
# ============================================================================
# This package provides the building blocks of 1D steady-flow hydraulic
# river analysis, modeled after the U.S. Army Corps of Engineers' HEC-RAS.
#
# WHY A "MIRROR" AND NOT A "CLONE"?
#   HEC-RAS is ~30 years of engineering work. This project mirrors the
#   *concepts* (cross-sections, reaches, Manning's equation, the standard-step
#   method, critical/normal depth, companion guidance) in a readable form
#   you can learn from. It is NOT a drop-in replacement for HEC-RAS and is
#   not certified for regulatory floodplain work.
#
# NAMESPACES / SEARCH TAGS (used throughout the source for easy navigation):
#   ### TWEAK ###   - knobs you are likely to change (constants, defaults)
#   ### LEARN ###   - short teaching blocks about hydraulics or numerics
#   ### WARN  ###   - common pitfalls and failure modes
#   ### TODO  ###   - explicit extension points for future work
# ============================================================================

# Single source of truth for the version: pyproject.toml reads it from here,
# the GUI title shows it, and the packaging scripts stamp it into the DMG /
# installer file names. Bump it in exactly one place - this one.
__version__ = "0.2.0"
__author__ = "MirrorZ-Hecras contributors"

# Friendly app-store-facing name (used by packaging and the GUI title).
APP_NAME = "MirrorZ-Hecras"
