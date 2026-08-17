from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from audit_site import (  # noqa: E402
    audit_html_file,
    data_quality_output_errors,
    public_metadata_errors,
)
from generate_data_quality import render_data_quality_page  # noqa: E402
from generate_public_metadata import DatasetMetadata  # noqa: E402


class SiteAuditTests(unittest.TestCase):
    def data_quality_report(self):
        return json.loads((ROOT_DIR / "site" / "data-quality.json").read_text())

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

    def test_data_quality_audit_rejects_stale_json_and_html(self):
        report = self.data_quality_report()

        errors = data_quality_output_errors(report, "{}", "<html>stale</html>")

        self.assertEqual(
            errors,
            [
                "data quality JSON is stale; run scripts/generate_data_quality.py",
                "data quality page is stale; run scripts/generate_data_quality.py",
            ],
        )

    def test_data_quality_audit_accepts_current_outputs(self):
        report = self.data_quality_report()
        page = render_data_quality_page(report)

        errors = data_quality_output_errors(report, json.dumps(report), page)

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
