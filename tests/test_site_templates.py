from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from audit_site import shared_chrome_errors, static_page_output_errors  # noqa: E402
from build_metadata import GitBuildMetadata  # noqa: E402
from dataset_contract import build_dataset_metadata  # noqa: E402
from generate_static_pages import TEMPLATE_DIR  # noqa: E402
from site_build_utils import SITE_DIR, load_rows  # noqa: E402


class SiteTemplateTests(unittest.TestCase):
    def test_unsupported_legacy_map_is_removed(self):
        self.assertFalse((ROOT_DIR / "map").exists())

    def test_static_templates_delegate_shared_chrome(self):
        for template_path in sorted(TEMPLATE_DIR.rglob("*.html")):
            with self.subTest(template=template_path.relative_to(TEMPLATE_DIR)):
                template = template_path.read_text()
                self.assertEqual(template.count("{{ navigation }}"), 1)
                self.assertEqual(template.count("{{ navigation_script }}"), 1)
                self.assertNotIn('<nav class="site-nav">', template)
                self.assertNotIn('<footer class="site-footer">', template)
                self.assertNotIn('/js/ga.js', template)
                self.assertNotIn('/js/navigation.js', template)

    def test_static_page_outputs_match_templates(self):
        metadata = build_dataset_metadata(load_rows(), GitBuildMetadata(ROOT_DIR))
        self.assertEqual(static_page_output_errors(metadata), [])

    def test_representative_pages_use_shared_chrome(self):
        page_paths = (
            SITE_DIR / "index.html",
            SITE_DIR / "about.html",
            SITE_DIR / "data-quality.html",
            SITE_DIR / "blog" / "index.html",
            SITE_DIR / "clubs" / "index.html",
            SITE_DIR / "counties" / "index.html",
            next(path for path in sorted((SITE_DIR / "clubs").glob("*.html")) if path.name != "index.html"),
        )
        for page_path in page_paths:
            with self.subTest(page=page_path.relative_to(SITE_DIR)):
                self.assertEqual(shared_chrome_errors(page_path), [])


if __name__ == "__main__":
    unittest.main()
