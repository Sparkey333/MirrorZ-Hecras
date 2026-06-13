"""
mirrorz/controller.py
================================================================================
Scripting / automation API for MirrorZ-Hecras - inspired by the
HECRASController described in Chris Goodell's book "Breaking the HEC-RAS
Code: A User's Guide to Automating HEC-RAS".

WHY THIS MODULE EXISTS
--------------------------------------------------------------------------------
Goodell's central insight is that HEC-RAS's real power is unlocked when you
stop clicking buttons and start DRIVING IT FROM CODE: parameter sweeps,
Monte-Carlo roughness studies, automated calibration, batch floodplain runs.
HEC-RAS exposes this through a Windows COM object ("HECRASController") with
functions like:

    HEC-RAS COM API (per the book)        MirrorZ equivalent here
    --------------------------------      ----------------------------------
    Project_Open(path)                    Controller.open_project(path)
    Project_Save()                        Controller.save_project(path)
    Compute_CurrentPlan()                 Controller.compute_current_plan()
    Plan_SetCurrent(name)                 Controller.set_current_plan(name)
    Plan_Names()                          Controller.plan_names()
    Geometry_GetNodes(...)                Controller.node_names(...)
    Output_NodeOutput(... variable id)    Controller.output(...) by keyword
    QuitRAS()                             (not needed - no external process)

NOTE: this is an ORIGINAL implementation that mirrors the *shape* of that
workflow, not the COM plumbing. Because our engine is plain Python, what
takes a COM round-trip in HEC-RAS is a direct function call here - and it
runs on macOS/Linux too, which the real HECRASController cannot.

WHAT YOU CAN DO WITH IT (the book's classic recipes, translated)
--------------------------------------------------------------------------------
    from mirrorz.controller import Controller

    rc = Controller()
    rc.open_project("examples/simple_channel.json")
    rc.compute_current_plan()
    print(rc.output("XS-3", "wse"))          # water surface at one node

    # Goodell-style parameter sweep: how sensitive is WSE to roughness?
    for n in (0.025, 0.030, 0.035, 0.040, 0.045):
        rc.set_manning_n(n)
        rc.compute_current_plan()
        print(n, rc.output("XS-5", "wse"))

HIGHLIGHTED TWEAK AREAS
--------------------------------------------------------------------------------
  ### TWEAK: OUTPUT_VARS ###   Add new output keywords to the variable map.
================================================================================
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .project import Project, FlowPlan
from .solver import solve_profile, ProfileResult, SectionResult, \
    clear_critical_cache


# =============================================================================
# ### TWEAK: OUTPUT_VARS ###
# -----------------------------------------------------------------------------
# HEC-RAS identifies output variables by integer ID (the book's Appendix lists
# ~280 of them: 2 = WSE, 23 = velocity, ...). Integer IDs are hostile to
# readers, so we use keywords instead, mapped to SectionResult attributes.
# Add a keyword here whenever SectionResult grows a new field.
# =============================================================================
OUTPUT_VARS: Dict[str, str] = {
    "wse":          "wse",                # water-surface elevation
    "depth":        "depth",
    "velocity":     "velocity",
    "area":         "area",
    "top_width":    "top_width",
    "froude":       "froude",
    "energy":       "energy_grade",       # energy grade line elevation
    "conveyance":   "conveyance",
    "crit_wse":     "critical_wse",
    "regime":       "flow_regime",
}


class ControllerError(RuntimeError):
    """Raised for misuse: no project open, unknown plan, unknown node, etc.
    A dedicated exception type lets calling scripts catch automation errors
    without swallowing genuine bugs (TypeError and friends still surface)."""


class Controller:
    """
    Programmatic driver for MirrorZ projects.

    Mirrors the open -> select plan -> compute -> read output rhythm that
    "Breaking the HEC-RAS Code" teaches for the HECRASController, minus the
    COM ceremony. Every method is synchronous; computations are fast enough
    that asynchronous plumbing would only add reading overhead.
    """

    def __init__(self) -> None:
        self.project: Optional[Project] = None
        self.current_plan: Optional[FlowPlan] = None
        self.last_result: Optional[ProfileResult] = None

    # ------------------------------------------------------------------
    # Project lifecycle  (Project_Open / Project_Save)
    # ------------------------------------------------------------------
    def open_project(self, path: str) -> "Controller":
        """Load a project JSON and select its first flow plan.
        Returns self so calls can be chained fluently."""
        self.project = Project.load(path)
        self.project.apply_units()
        clear_critical_cache()        # new geometry, old cache is invalid
        self.current_plan = self.project.flows[0] if self.project.flows else None
        self.last_result = None
        return self

    def save_project(self, path: str) -> None:
        self._require_project().save(path)

    # ------------------------------------------------------------------
    # Plan management  (Plan_Names / Plan_SetCurrent)
    # ------------------------------------------------------------------
    def plan_names(self) -> List[str]:
        return [f.name for f in self._require_project().flows]

    def set_current_plan(self, name: str) -> None:
        for f in self._require_project().flows:
            if f.name == name:
                self.current_plan = f
                return
        raise ControllerError(
            f"No flow plan named {name!r}. Available: {self.plan_names()}")

    # ------------------------------------------------------------------
    # Geometry helpers  (Geometry_GetNodes)
    # ------------------------------------------------------------------
    def node_names(self, reach_index: int = 0) -> List[str]:
        reach = self._require_project().reaches[reach_index]
        reach.sort_upstream()
        return [xs.name for xs in reach.cross_sections]

    def set_manning_n(self, n: float, reach_index: int = 0,
                      node: Optional[str] = None) -> None:
        """Set channel roughness on one node, or on every node if node=None.
        This is THE most common automation tweak (calibration sweeps)."""
        reach = self._require_project().reaches[reach_index]
        hit = False
        for xs in reach.cross_sections:
            if node is None or xs.name == node:
                xs.n_channel = float(n)
                hit = True
        if not hit:
            raise ControllerError(f"No node named {node!r} in reach "
                                  f"{reach.name!r}.")
        clear_critical_cache()   # n doesn't change yc, but cheap + safe habit

    # ------------------------------------------------------------------
    # Compute  (Compute_CurrentPlan)
    # ------------------------------------------------------------------
    def compute_current_plan(self, reach_index: int = 0) -> ProfileResult:
        p = self._require_project()
        if self.current_plan is None:
            raise ControllerError("Project has no flow plan to compute.")
        f = self.current_plan
        self.last_result = solve_profile(
            p.reaches[reach_index], f.discharge, f.boundary_wse,
            regime=f.regime)
        return self.last_result

    def compute_sweep(self, discharges: List[float],
                      reach_index: int = 0) -> List[ProfileResult]:
        """Batch-run a list of discharges against the current plan's boundary
        logic - the book's bread-and-butter use case. Boundary WSE is
        re-estimated per Q via the companion's normal-depth heuristic so the
        downstream condition stays physically consistent across the sweep."""
        from .companion import recommend_boundary
        p = self._require_project()
        if self.current_plan is None:
            raise ControllerError("Project has no flow plan to sweep.")
        results = []
        for q in discharges:
            wse0 = recommend_boundary(p, q, self.current_plan.regime)
            results.append(solve_profile(
                p.reaches[reach_index], q, wse0,
                regime=self.current_plan.regime))
        # Leave last_result pointing at the final run, mirroring HEC-RAS
        # which always reflects the most recent compute.
        self.last_result = results[-1] if results else None
        return results

    # ------------------------------------------------------------------
    # Output  (Output_NodeOutput)
    # ------------------------------------------------------------------
    def output(self, node: str, variable: str = "wse"):
        """Read one output variable at one node from the last compute.

        `variable` is a keyword from OUTPUT_VARS ("wse", "velocity", ...).
        Raises ControllerError if nothing has been computed yet - the same
        guard the real controller enforces by erroring on missing output
        files.
        """
        if self.last_result is None:
            raise ControllerError(
                "No results - call compute_current_plan() first.")
        attr = OUTPUT_VARS.get(variable)
        if attr is None:
            raise ControllerError(
                f"Unknown output variable {variable!r}. "
                f"Choose from: {sorted(OUTPUT_VARS)}")
        s = self._find_section(node)
        return getattr(s, attr)

    def output_table(self, variable: str = "wse") -> Dict[str, float]:
        """The same variable at EVERY node, as {node_name: value}."""
        if self.last_result is None:
            raise ControllerError(
                "No results - call compute_current_plan() first.")
        attr = OUTPUT_VARS.get(variable)
        if attr is None:
            raise ControllerError(
                f"Unknown output variable {variable!r}. "
                f"Choose from: {sorted(OUTPUT_VARS)}")
        return {s.name: getattr(s, attr) for s in self.last_result.sections}

    # ------------------------------------------------------------------
    # Reports  (no HEC-RAS COM equivalent - this is a MirrorZ extra)
    # ------------------------------------------------------------------
    def export_html_report(self, path: str, reach_index: int = 0,
                           brand_caption: str = "") -> str:
        """Write a self-contained HTML report of the last compute; return
        the path. Raises ControllerError if nothing has been computed.

        Reports are deliberately NOT edition-gated at the library layer -
        the MIT engine stays fully capable for scripting. Edition gating is
        a GUI/storefront concern (see gui.py), not an engine limitation."""
        from . import report  # local import keeps matplotlib off the hot path
        if self.last_result is None:
            raise ControllerError(
                "No results - call compute_current_plan() first.")
        p = self._require_project()
        report.save_html_report(
            path, self.last_result, p.reaches[reach_index],
            project_name=p.name, brand_caption=brand_caption)
        return path

    def export_pdf_report(self, path: str, reach_index: int = 0,
                          brand_caption: str = "") -> str:
        """Write a multi-page PDF report of the last compute; return path."""
        from . import report
        if self.last_result is None:
            raise ControllerError(
                "No results - call compute_current_plan() first.")
        p = self._require_project()
        report.build_pdf_report(
            path, self.last_result, p.reaches[reach_index],
            project_name=p.name, brand_caption=brand_caption)
        return path

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _require_project(self) -> Project:
        if self.project is None:
            raise ControllerError(
                "No project open - call open_project(path) first.")
        return self.project

    def _find_section(self, node: str) -> SectionResult:
        assert self.last_result is not None
        for s in self.last_result.sections:
            if s.name == node:
                return s
        names = [s.name for s in self.last_result.sections]
        raise ControllerError(f"No node named {node!r}. Available: {names}")
