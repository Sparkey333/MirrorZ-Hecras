"""
Smoke tests for MirrorZ-Hecras.

Run with:  python -m unittest tests.test_smoke
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import hydraulics as hy
from src.geometry import CrossSection, Reach
from src.project import default_project, Project
from src.solver import solve_profile


class TestHydraulics(unittest.TestCase):

    def test_rectangular_critical_depth_closed_form(self):
        hy.set_unit_system("SI")
        q, b = 20.0, 10.0
        yc_closed = hy.rect_critical_depth(q, b)
        # Near-vertical walls so geometry matches the closed-form rectangle.
        eps = 1e-4
        xs = CrossSection(
            name="rect", river_station=0.0,
            stations=[-eps, 0.0, b, b + eps],
            elevations=[100.0, 0.0, 0.0, 100.0],
        )
        yc_solver = hy.critical_depth(q, xs.section_fn())
        self.assertAlmostEqual(yc_closed, yc_solver, places=3)

    def test_rectangular_normal_depth_closed_form(self):
        hy.set_unit_system("SI")
        q, b, n, S = 20.0, 10.0, 0.030, 0.001
        yn_closed = hy.rect_normal_depth(q, b, n, S)
        eps = 1e-4
        xs = CrossSection(
            name="rect", river_station=0.0,
            stations=[-eps, 0.0, b, b + eps],
            elevations=[100.0, 0.0, 0.0, 100.0],
            n_channel=n,
        )
        yn_solver = hy.normal_depth(q, S, n, xs.section_fn())
        self.assertAlmostEqual(yn_closed, yn_solver, places=2)

    def test_manning_roundtrip(self):
        hy.set_unit_system("SI")
        A, R, n, S = 30.0, 1.5, 0.035, 0.001
        Q = hy.manning_discharge(n, A, R, S)
        Sf = hy.friction_slope(Q, n, A, R)
        self.assertAlmostEqual(Sf, S, places=8)


class TestSolver(unittest.TestCase):

    def test_default_project_runs(self):
        p = default_project()
        p.apply_units()
        f = p.flows[0]
        r = solve_profile(p.reaches[0], f.discharge, f.boundary_wse, regime=f.regime)
        self.assertEqual(len(r.sections), 5)
        self.assertTrue(all(s.converged for s in r.sections))
        # Water goes up going upstream for a mild slope (sub-critical):
        wses = [s.wse for s in r.sections]
        self.assertTrue(wses[-1] >= wses[0] - 1e-6,
                        f"Upstream WSE should not be below downstream: {wses}")

    def test_example_files_load(self):
        here = os.path.dirname(os.path.abspath(__file__))
        root = os.path.dirname(here)
        for name in ("simple_channel.json", "natural_river.json"):
            p = Project.load(os.path.join(root, "examples", name))
            p.apply_units()
            f = p.flows[0]
            r = solve_profile(p.reaches[0], f.discharge, f.boundary_wse,
                              regime=f.regime)
            self.assertGreater(len(r.sections), 0)


if __name__ == "__main__":
    unittest.main()
