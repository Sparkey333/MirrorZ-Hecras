"""Getting Started resources: URLs + steps stay non-empty and consistent."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mirrorz import companion
from mirrorz.resources import KEY_SITES, LOCAL_MAC_STEPS, getting_started_text


class TestResources(unittest.TestCase):
    def test_key_sites_have_https_or_http(self):
        self.assertGreaterEqual(len(KEY_SITES), 8)
        for label, url in KEY_SITES:
            self.assertTrue(url.startswith("http://") or url.startswith("https://"),
                            msg=label)
            self.assertTrue(label.strip())

    def test_local_mac_steps_mention_downloads(self):
        blob = " ".join(LOCAL_MAC_STEPS).lower()
        self.assertIn("downloads", blob)
        self.assertIn("build_macos_dmg", blob)

    def test_getting_started_text_includes_urls(self):
        text = getting_started_text()
        self.assertIn("github.com/Sparkey333/MirrorZ-Hecras", text)
        self.assertIn("hec.usace.army.mil", text)
        self.assertIn("higgsfield.ai", text)

    def test_companion_welcome_has_links(self):
        w = companion.welcome()
        self.assertIn("https://", w)
        self.assertIn("Getting Started", w)


if __name__ == "__main__":
    unittest.main()
