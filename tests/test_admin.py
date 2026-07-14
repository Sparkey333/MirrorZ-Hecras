"""
Tests for the admin/edition/theme system added in v0.3.
"""

import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mirrorz import plotting as pl
from mirrorz.admin import (
    AdminState, EDITIONS, THEMES, LicenseManager,
)


class TestEditions(unittest.TestCase):

    def test_free_locks_paid_features(self):
        s = AdminState(edition="free")
        self.assertFalse(s.feature_enabled("csv_export"))
        self.assertFalse(s.feature_enabled("branding"))
        # Anything we left default-True is unchanged.
        self.assertTrue(s.feature_enabled("controller_api"))

    def test_pro_unlocks_csv_and_reports(self):
        s = AdminState(edition="pro")
        self.assertTrue(s.feature_enabled("csv_export"))
        self.assertTrue(s.feature_enabled("html_report"))
        self.assertFalse(s.feature_enabled("branding"))  # classroom-only

    def test_classroom_unlocks_branding(self):
        s = AdminState(edition="classroom")
        self.assertTrue(s.feature_enabled("branding"))

    def test_unknown_edition_safely_falls_back_to_free(self):
        # A corrupt admin.json could carry a stale edition name.
        s = AdminState(edition="enterprise-mega-deluxe")
        # We don't lie about edition (the string is preserved), but the
        # feature-flag lookup defaults to free's table so nothing leaks.
        self.assertFalse(s.feature_enabled("csv_export"))


class TestLicense(unittest.TestCase):

    def test_make_then_apply_roundtrips(self):
        key = LicenseManager.make_key("pro", "ORDER-12345")
        self.assertTrue(key.startswith("MZH-"))
        # In dev-mode the parser permissively returns "pro" for any
        # well-formed key. That's the intended behavior until the
        # storefront is wired up - documented in admin.py.
        self.assertEqual(LicenseManager.parse(key), "pro")

    def test_rejects_malformed_keys(self):
        for bad in ("", "ABC-1234-5678", "MZH-1234567890",
                    "MZH-XXXX-YYYY", "MZH-ZZZZ-ZZZZ"):
            self.assertIsNone(LicenseManager.parse(bad), msg=bad)

    def test_apply_updates_state(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch("mirrorz.admin.config_dir", return_value=d):
                s = AdminState()
                key = LicenseManager.make_key("pro", "ORDER-9")
                msg = s.apply_license_key(key)
                self.assertIn("pro", msg.lower())
                self.assertEqual(s.edition, "pro")
                # Persisted to admin.json in the mocked dir.
                self.assertTrue(os.path.exists(os.path.join(d, "admin.json")))
                # Reload picks it up.
                s2 = AdminState.load()
                self.assertEqual(s2.edition, "pro")

    def test_invalid_key_leaves_state_free(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch("mirrorz.admin.config_dir", return_value=d):
                s = AdminState()
                msg = s.apply_license_key("nope")
                self.assertIn("Invalid", msg)
                self.assertEqual(s.edition, "free")


class TestThemes(unittest.TestCase):

    def test_every_theme_defines_required_colors(self):
        required = {"ground", "water", "energy", "critical", "bg"}
        for name, palette in THEMES.items():
            self.assertTrue(required.issubset(palette),
                            msg=f"theme {name!r} missing keys")

    def test_apply_palette_changes_module_globals(self):
        old = (pl.GROUND_COLOR, pl.WATER_COLOR, pl.BRAND_CAPTION)
        try:
            pl.apply_palette(THEMES["colorblind"], "Test University")
            self.assertEqual(pl.GROUND_COLOR, THEMES["colorblind"]["ground"])
            self.assertEqual(pl.BRAND_CAPTION, "Test University")
        finally:
            pl.apply_palette({"ground": old[0], "water": old[1]}, "")

    def test_unknown_theme_falls_back_to_river(self):
        s = AdminState(theme="taupe-dreams")
        self.assertEqual(s.palette(), THEMES["river"])


class TestBranding(unittest.TestCase):

    def test_header_caption_empty_when_free(self):
        s = AdminState(edition="free", institution="U of X",
                       course_code="CIVE 462")
        self.assertEqual(s.header_caption(), "")

    def test_header_caption_joins_classroom_fields(self):
        s = AdminState(edition="classroom",
                       institution="U of X", course_code="CIVE 462",
                       instructor="Dr. Jane")
        cap = s.header_caption()
        self.assertIn("U of X",   cap)
        self.assertIn("CIVE 462", cap)
        self.assertIn("Dr. Jane", cap)


if __name__ == "__main__":
    unittest.main()
