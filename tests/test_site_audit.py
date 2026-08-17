from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from audit_site import audit_html_file, public_metadata_errors  # noqa: E402
from generate_public_metadata import DatasetMetadata  # noqa: E402


class SiteAuditTests(unittest.TestCase):
    def test_html_audit_rejects_duplicate_gaa_wording(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            site_dir = Path(temporary_directory)
            page_path = site_dir / "club.html"
            page_path.write_text("<html><body>Example GAA GAA pitch</body></html>")

            errors = audit_html_file(page_path, site_dir)

        self.assertIn('contains duplicate "GAA GAA" wording', errors)

    def test_html_audit_rejects_eager_google_analytics_connections(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            site_dir = Path(temporary_directory)
            page_path = site_dir / "club.html"
            page_path.write_text(
                '<link rel="preconnect" href="https://www.googletagmanager.com">'
                '<script src="https://www.googletagmanager.com/gtag/js?id=G-123">'
                "</script>"
            )

            errors = audit_html_file(page_path, site_dir)

        self.assertIn("loads Google Analytics before consent", errors)
        self.assertIn("connects to Google Analytics before consent", errors)

    def test_public_metadata_audit_rejects_stale_outputs(self):
        metadata = DatasetMetadata(1989, "2026-08-06", "a" * 40)

        errors = public_metadata_errors(
            metadata,
            "<html>1,988 records</html>",
            "As of July 2026, there are 1,988 records.",
        )

        self.assertEqual(len(errors), 4)
        self.assertTrue(all("stale" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
