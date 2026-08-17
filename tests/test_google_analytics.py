from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from generate_club_pages import ga_snippet  # noqa: E402


GA_SCRIPT = ROOT / "site" / "js" / "ga.js"
README = ROOT / "README.md"
SITE_DIR = ROOT / "site"


class GoogleAnalyticsScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = GA_SCRIPT.read_text(encoding="utf-8")

    def test_http_pages_are_not_redirected(self):
        self.assertNotRegex(self.script, r"\blocation\.replace\s*\(")
        self.assertNotRegex(
            self.script, r"\blocation\.protocol\s*===?\s*[\"']http:[\"']"
        )

    def test_analytics_tag_is_created_only_by_the_consent_controller(self):
        analytics_pages = []
        for html_path in SITE_DIR.rglob("*.html"):
            html = html_path.read_text(encoding="utf-8")
            if '/js/ga.js' not in html:
                continue
            analytics_pages.append(html_path)
            self.assertNotIn("googletagmanager.com/gtag", html, html_path)
            self.assertNotIn("preconnect\" href=\"https://www.googletagmanager.com", html, html_path)
            self.assertIn('<script src="/js/ga.js" defer></script>', html, html_path)

        self.assertGreater(len(analytics_pages), 10)
        self.assertIn("currentChoice !== 'accepted'", self.script)
        self.assertIn("document.createElement('script')", self.script)
        self.assertIn("https://www.googletagmanager.com/gtag/js", self.script)
        self.assertEqual(ga_snippet(), '<script src="/js/ga.js" defer></script>')

    def test_consent_can_be_rejected_persisted_and_withdrawn(self):
        self.assertIn("gaa-analytics-consent", self.script)
        self.assertIn("Reject analytics", self.script)
        self.assertIn("Accept analytics", self.script)
        self.assertIn("CONSENT_MAX_AGE_MS", self.script)
        self.assertIn("clearAnalyticsCookies", self.script)
        self.assertIn("window[disableKey] = true", self.script)
        self.assertIn("Analytics preferences", self.script)

    def test_readme_documents_plain_http_development(self):
        readme = README.read_text(encoding="utf-8")

        self.assertIn("python3 -m http.server 8000 --directory site", readme)
        self.assertIn("Then open `http://localhost:8000`.", readme)


if __name__ == "__main__":
    unittest.main()
