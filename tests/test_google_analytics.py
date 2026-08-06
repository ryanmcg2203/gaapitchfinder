from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
GA_SCRIPT = ROOT / "site" / "js" / "ga.js"
README = ROOT / "README.md"


class GoogleAnalyticsScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = GA_SCRIPT.read_text(encoding="utf-8")

    def test_http_pages_are_not_redirected(self):
        self.assertNotRegex(self.script, r"\blocation\.replace\s*\(")
        self.assertNotRegex(
            self.script, r"\blocation\.protocol\s*===?\s*[\"']http:[\"']"
        )

    def test_google_analytics_initialization_is_preserved(self):
        self.assertIn("window.dataLayer = window.dataLayer || [];", self.script)
        self.assertIn("dataLayer.push(arguments);", self.script)
        self.assertIn('gtag("js", new Date());', self.script)
        self.assertIn('gtag("config", "G-8R6YMPVNWH");', self.script)

    def test_readme_documents_plain_http_development(self):
        readme = README.read_text(encoding="utf-8")

        self.assertIn("python3 -m http.server 8000 --directory site", readme)
        self.assertIn("Then open `http://localhost:8000`.", readme)


if __name__ == "__main__":
    unittest.main()
