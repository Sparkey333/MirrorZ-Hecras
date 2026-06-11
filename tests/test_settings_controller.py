"""
Tests for the v0.2 additions: persistent settings and the automation
controller (the Breaking-the-HEC-RAS-Code-style API).

Run with:  python -m unittest tests.test_settings_controller
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mirrorz import hydraulics as hy
from mirrorz import solver as so
from mirrorz import analyzer as an
from mirrorz.settings import AppSettings
from mirrorz.controller import Controller, ControllerError


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLE = os.path.join(ROOT, "examples", "simple_channel.json")


class TestSettings(unittest.TestCase):

    def test_roundtrip(self):
        """Settings survive a save/load cycle byte-for-byte."""
        s = AppSettings(unit_system="US", wse_tolerance=0.01,
                        max_step_iters=50, friction_method="harmonic",
                        freeboard_req=1.0, show_welcome=False)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "settings.json")
            s.save(path)
            s2 = AppSettings.load(path)
        self.assertEqual(s2.unit_system, "US")
        self.assertEqual(s2.friction_method, "harmonic")
        self.assertEqual(s2.max_step_iters, 50)
        self.assertFalse(s2.show_welcome)

    def test_corrupt_file_falls_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "settings.json")
            with open(path, "w") as fh:
                fh.write("{not valid json!!")
            s = AppSettings.load(path)
        self.assertEqual(s.unit_system, "SI")   # factory default

    def test_sanitize_clamps_garbage(self):
        s = AppSettings(unit_system="MARTIAN", wse_tolerance=-5,
                        max_step_iters=99999, friction_method="vibes")
        s.sanitize()
        self.assertEqual(s.unit_system, "SI")
        self.assertGreater(s.wse_tolerance, 0)
        self.assertLessEqual(s.max_step_iters, 500)
        self.assertEqual(s.friction_method, "average")

    def test_apply_reaches_numeric_modules(self):
        """The whole point of settings: module globals actually change."""
        old = (hy.get_unit_system(), so.WSE_TOL,
               so.FRICTION_AVG_METHOD, an.FREEBOARD_REQ)
        try:
            s = AppSettings(unit_system="US", wse_tolerance=0.0123,
                            friction_method="geometric", freeboard_req=0.9)
            s.apply()
            self.assertEqual(hy.get_unit_system(), "US")
            self.assertAlmostEqual(so.WSE_TOL, 0.0123)
            self.assertEqual(so.FRICTION_AVG_METHOD, "geometric")
            self.assertAlmostEqual(an.FREEBOARD_REQ, 0.9)
        finally:
            # Restore so other tests aren't poisoned by this one.
            hy.set_unit_system(old[0])
            so.WSE_TOL = old[1]
            so.FRICTION_AVG_METHOD = old[2]
            an.FREEBOARD_REQ = old[3]

    def test_recent_files_dedupe_and_cap(self):
        s = AppSettings()
        with tempfile.TemporaryDirectory() as d:
            paths = []
            for i in range(12):
                p = os.path.join(d, f"f{i}.json")
                open(p, "w").close()
                paths.append(p)
                s.remember_file(p)
            s.remember_file(paths[0])           # re-open the first file
            self.assertEqual(s.recent_files[0], os.path.abspath(paths[0]))
            self.assertLessEqual(len(s.recent_files), 8)
            self.assertEqual(len(set(s.recent_files)),
                             len(s.recent_files))  # no duplicates


class TestController(unittest.TestCase):

    def setUp(self):
        hy.set_unit_system("SI")

    def test_open_compute_output(self):
        rc = Controller().open_project(EXAMPLE)
        self.assertIn("Design flow 20 cms", rc.plan_names())
        result = rc.compute_current_plan()
        self.assertEqual(len(result.sections), 5)
        wse = rc.output("XS-3", "wse")
        self.assertGreater(wse, 0.0)
        # Table form returns every node.
        table = rc.output_table("velocity")
        self.assertEqual(set(table), set(rc.node_names()))

    def test_errors_are_controller_errors(self):
        rc = Controller()
        with self.assertRaises(ControllerError):
            rc.compute_current_plan()           # no project open
        rc.open_project(EXAMPLE)
        with self.assertRaises(ControllerError):
            rc.set_current_plan("nope")
        rc.compute_current_plan()
        with self.assertRaises(ControllerError):
            rc.output("XS-3", "not_a_variable")
        with self.assertRaises(ControllerError):
            rc.output("XS-99", "wse")

    def test_manning_sweep_monotonic(self):
        """Physics check: rougher channel -> deeper water (same Q)."""
        rc = Controller().open_project(EXAMPLE)
        depths = []
        for n in (0.025, 0.035, 0.045):
            rc.set_manning_n(n)
            rc.compute_current_plan()
            depths.append(rc.output("XS-5", "depth"))
        self.assertLess(depths[0], depths[1])
        self.assertLess(depths[1], depths[2])

    def test_discharge_sweep(self):
        rc = Controller().open_project(EXAMPLE)
        results = rc.compute_sweep([10.0, 20.0, 40.0])
        self.assertEqual(len(results), 3)
        # Higher Q -> higher upstream WSE.
        top_wses = [r.sections[-1].wse for r in results]
        self.assertLess(top_wses[0], top_wses[1])
        self.assertLess(top_wses[1], top_wses[2])


if __name__ == "__main__":
    unittest.main()
