#!/usr/bin/env python3
"""
Audit generated site output for basic SEO and link-safety regressions.

Run from repo root:
    python3 scripts/audit_site.py
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

from site_build_utils import SITE_DIR


SAFE_SCHEMES = {"", "http", "https", "mailto"}
REQUIRED_META_PAGES = {
    "index.html",
    "about.html",
    "dataset.html",
    "directions.html",
}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.in_title = False
        self.description = False
        self.canonical = False
        self.json_ld = False
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self.in_title = True
        if tag == "meta" and attrs.get("name") == "description" and attrs.get("content"):
            self.description = True
        if tag == "link" and attrs.get("rel") == "canonical" and attrs.get("href"):
            self.canonical = True
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self.json_ld = True
        if tag == "a":
            self.links.append(attrs)

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data.strip()


def is_safe_href(href):
    parsed = urlparse(href or "")
    return parsed.scheme.lower() in SAFE_SCHEMES


def audit_html_file(path):
    rel_path = path.relative_to(SITE_DIR)
    parser = PageParser()
    parser.feed(path.read_text(errors="replace"))
    errors = []

    if rel_path.as_posix() in REQUIRED_META_PAGES:
        if not parser.title:
            errors.append("missing <title>")
        if not parser.description:
            errors.append("missing meta description")
        if not parser.canonical and rel_path.name != "404.html":
            errors.append("missing canonical link")
    if rel_path.as_posix() == "index.html" and not parser.json_ld:
        errors.append("homepage missing JSON-LD")

    for attrs in parser.links:
        href = attrs.get("href", "")
        if not is_safe_href(href):
            errors.append(f"unsafe href: {href}")
        if attrs.get("target") == "_blank":
            rel = set((attrs.get("rel") or "").split())
            if not {"noopener", "noreferrer"}.issubset(rel):
                errors.append(f'target="_blank" missing noopener noreferrer: {href}')
    return errors


def audit_data_json():
    path = SITE_DIR / "data.json"
    if not path.exists():
        return ["site/data.json does not exist; run scripts/generate_map_data.py first"]
    errors = []
    for index, row in enumerate(json.loads(path.read_text())):
        directions_url = row.get("d", "")
        parsed = urlparse(directions_url)
        if parsed.scheme not in {"https", "http"} or parsed.hostname != "maps.google.com":
            errors.append(f"row {index} has unsafe directions URL: {directions_url}")
    return errors


def audit_sitemap():
    path = SITE_DIR / "sitemap.xml"
    if not path.exists():
        return ["site/sitemap.xml does not exist"]
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    root = ET.parse(path).getroot()
    errors = []
    for url in root.findall("sm:url", namespace):
        loc = url.findtext("sm:loc", default="", namespaces=namespace)
        lastmod = url.findtext("sm:lastmod", default="", namespaces=namespace)
        if not loc:
            errors.append("sitemap URL missing loc")
        if not lastmod:
            errors.append(f"sitemap URL missing lastmod: {loc}")
    return errors


def main():
    failures = []
    for html_path in sorted(SITE_DIR.rglob("*.html")):
        for error in audit_html_file(html_path):
            failures.append(f"{html_path.relative_to(SITE_DIR)}: {error}")
    failures.extend(audit_data_json())
    failures.extend(audit_sitemap())

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1

    print("Site audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
