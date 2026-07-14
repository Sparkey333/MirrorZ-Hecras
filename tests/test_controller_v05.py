"""Controller Phase-3 API: boundary, geometry mutators, exports, Monte Carlo."""

import csv
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mirrorz import hydraulics as hy
from mirrorz.controller import Controller, ControllerError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIMPLE = os.path.join(ROOT, "examples", "simple_channel.json")
BEAVER = os.path.join(ROOT, "examples", "beaver_creek.json")
CRITICAL = os.path.join(ROOT, "examples", "critical_creek.json")


class TestControllerV05(unittest.TestCase):
    def setUp(self):
        hy.set_unit_system("SI")

    def test_set_boundary_discharge_and_wse(self):
        rc = Controller().open_project(SIMPLE)
        rc.set_boundary(wse=1.25, discharge=25.0)
        self.assertAlmostEqual(rc.current_plan.discharge, 25.0)
        self.assertAlmostEqual(rc.current_plan.boundary_wse, 1.25)
        rc.compute_current_plan()
        self.assertGreater(rc.output("XS-5", "wse"), 0)

    def test_raise_bed_increases_wse(self):
        rc = Controller().open_project(SIMPLE)
        rc.compute_current_plan()
        wse0 = rc.output("XS-3", "wse")
        rc.raise_bed(0.2)
        rc.compute_current_plan()
        self.assertGreater(rc.output("XS-3", "wse"), wse0)

    def test_widen_channel_reduces_depth(self):
        rc = Controller().open_project(SIMPLE)
        rc.compute_current_plan()
        d0 = rc.output("XS-3", "depth")
        rc.widen_channel(1.35)
        rc.compute_current_plan()
        self.assertLess(rc.output("XS-3", "depth"), d0)

    def test_export_csv_and_json(self):
        rc = Controller().open_project(SIMPLE)
        rc.compute_current_plan()
        with tempfile.TemporaryDirectory() as d:
            csv_path = os.path.join(d, "out.csv")
            json_path = os.path.join(d, "out.json")
            rc.export_results_csv(csv_path)
            rc.export_results_json(json_path)
            with open(csv_path, newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual(len(rows), 5)
            self.assertIn("wse", rows[0])
            data = json.loads(open(json_path, encoding="utf-8").read())
            self.assertEqual(len(data["sections"]), 5)

    def test_monte_carlo_restores_n(self):
        rc = Controller().open_project(BEAVER)
        n_before = [xs.n_channel for xs in rc.project.reaches[0].cross_sections]
        pairs = rc.monte_carlo_manning(
            n_mean=0.032, n_std=0.003, samples=12, node="BC-5", seed=7)
        self.assertEqual(len(pairs), 12)
        n_after = [xs.n_channel for xs in rc.project.reaches[0].cross_sections]
        self.assertEqual(n_before, n_after)
        self.assertTrue(all(wse > 0 for _, wse in pairs))

    def test_export_without_compute_errors(self):
        rc = Controller().open_project(SIMPLE)
        with self.assertRaises(ControllerError):
            rc.export_results_csv("/tmp/nope.csv")


class TestExampleProjects(unittest.TestCase):
    """Smoke + soft regression locks for teaching distills."""

    def setUp(self):
        hy.set_unit_system("SI")

    def test_critical_creek_converges(self):
        rc = Controller().open_project(CRITICAL)
        res = rc.compute_current_plan()
        self.assertTrue(all(s.converged for s in res.sections))
        wse = rc.output("CC-160", "wse")
        # Soft band — tighten when real USACE XS are swapped in.
        self.assertGreater(wse, 1.0)
        self.assertLess(wse, 4.5)

    def test_beaver_creek_converges(self):
        rc = Controller().open_project(BEAVER)
        res = rc.compute_current_plan()
        self.assertTrue(all(s.converged for s in res.sections))
        wse = rc.output("BC-5", "wse")
        self.assertGreater(wse, 1.5)
        self.assertLess(wse, 6.0)


if __name__ == "__main__":
    unittest.main()
