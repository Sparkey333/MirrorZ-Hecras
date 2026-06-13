"""
Tests for the report generator (HTML + PDF) added in v0.4.

These verify structure and the non-negotiables (disclaimer present, images
embedded, valid file headers) rather than pixel output.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mirrorz import hydraulics as hy
from mirrorz.project import Project
from mirrorz.solver import solve_profile
from mirrorz import report
from mirrorz.controller import Controller, ControllerError


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIMPLE = os.path.join(ROOT, "examples", "simple_channel.json")
NATURAL = os.path.join(ROOT, "examples", "natural_river.json")


def _run(path):
    hy.set_unit_system("SI")
    p = Project.load(path); p.apply_units()
    f = p.flows[0]
    res = solve_profile(p.reaches[0], f.discharge, f.boundary_wse,
                        regime=f.regime)
    return p, p.reaches[0], res


class TestHtmlReport(unittest.TestCase):

    def test_contains_required_elements(self):
        p, reach, res = _run(NATURAL)
        html = report.build_html_report(res, reach, project_name=p.name,
                                        brand_caption="U of X · CIVE 462")
        # Mandatory disclaimer.
        self.assertIn("EDUCATIONAL", html)
        self.assertIn("licensed", html.lower())
        # Branding caption rendered.
        self.assertIn("U of X", html)
        # Project + reach metadata.
        self.assertIn("Wiggle Creek", html)
        # Every section name appears in the results table.
        for s in res.sections:
            self.assertIn(s.name, html)
        # At least the profile plot + some cross-section thumbnails embedded.
        self.assertGreaterEqual(html.count("data:image/png;base64,"), 2)
        # Valid-ish HTML document.
        self.assertTrue(html.lstrip().lower().startswith("<!doctype html"))
        self.assertIn("</html>", html)

    def test_html_escapes_section_names(self):
        """A section name with HTML metacharacters must not break markup."""
        p, reach, res = _run(SIMPLE)
        res.sections[0].name = "XS <script>&'\""
        reach.cross_sections[0].name = res.sections[0].name
        html = report.build_html_report(res, reach)
        self.assertNotIn("<script>", html)         # raw tag never present
        self.assertIn("&lt;script&gt;", html)       # escaped form is

    def test_save_html_writes_file(self):
        p, reach, res = _run(SIMPLE)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "r.html")
            report.save_html_report(path, res, reach, project_name=p.name)
            self.assertTrue(os.path.getsize(path) > 1000)
            with open(path, encoding="utf-8") as fh:
                self.assertIn("Disclaimer", fh.read())


class TestPdfReport(unittest.TestCase):

    def test_pdf_header_and_size(self):
        p, reach, res = _run(NATURAL)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "r.pdf")
            report.build_pdf_report(path, res, reach, project_name=p.name,
                                    brand_caption="U of X")
            with open(path, "rb") as fh:
                self.assertEqual(fh.read(4), b"%PDF")
            self.assertGreater(os.path.getsize(path), 5000)


class TestThumbnailSampling(unittest.TestCase):

    def test_sampling_caps_thumbnails(self):
        p, reach, res = _run(SIMPLE)
        original = report.THUMB_LIMIT
        try:
            report.THUMB_LIMIT = 3
            sampled = report._sampled_sections(res)   # 5-section example
            self.assertEqual(len(sampled), 3)
            # Should include the first section (downstream control).
            self.assertEqual(sampled[0].name, res.sections[0].name)
        finally:
            report.THUMB_LIMIT = original

    def test_no_sampling_when_under_cap(self):
        p, reach, res = _run(SIMPLE)
        self.assertEqual(len(report._sampled_sections(res)),
                         len(res.sections))


class TestControllerReportIntegration(unittest.TestCase):

    def test_controller_requires_compute_first(self):
        rc = Controller().open_project(SIMPLE)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ControllerError):
                rc.export_html_report(os.path.join(d, "r.html"))

    def test_controller_exports_both(self):
        rc = Controller().open_project(SIMPLE)
        rc.compute_current_plan()
        with tempfile.TemporaryDirectory() as d:
            h = rc.export_html_report(os.path.join(d, "r.html"))
            pdf = rc.export_pdf_report(os.path.join(d, "r.pdf"))
            self.assertTrue(os.path.exists(h))
            self.assertTrue(os.path.exists(pdf))


if __name__ == "__main__":
    unittest.main()
