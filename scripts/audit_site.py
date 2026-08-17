#!/usr/bin/env python3
"""
Audit generated site output for basic SEO and link-safety regressions.

Run from repo root:
    python3 scripts/audit_site.py
"""

from __future__ import annotations

import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

from build_metadata import BuildMetadataError, GitBuildMetadata
from generate_data_quality import (
    REPORT_HTML_PATH,
    REPORT_JSON_PATH,
    build_current_report,
    render_data_quality_page,
)
from generate_public_metadata import (
    build_dataset_metadata,
    format_iso_date,
    render_dataset_contract,
    render_dataset_head,
    render_dataset_summary,
    render_readme_summary,
    update_dataset_page,
)
from generate_static_pages import TEMPLATE_DIR
from dataset_contract import FIELD_DEFINITIONS, build_geojson, build_schema
from generate_dataset_downloads import DOWNLOADS_DIR
from site_builder.shared import (
    active_navigation_for_path,
    analytics_html,
    footer_html,
    navigation_html,
    navigation_script_html,
    render_static_template,
)
from site_build_utils import DATASET_PATH, ROOT_DIR, SITE_DIR, load_rows


SAFE_SCHEMES = {"", "http", "https", "mailto"}
REQUIRED_META_PAGES = {
    "index.html",
    "about.html",
    "dataset.html",
    "data-quality.html",
    "donate.html",
    "directions.html",
    "pitch-of-the-day.html",
}
PRIVACY_SERVICES = (
    "Google Analytics",
    "CARTO",
    "OpenStreetMap Foundation",
    "Google Maps",
    "GitHub Pages",
    "PayPal",
)
SHARED_NAV_PATTERN = re.compile(
    r'<nav class="site-nav">.*?</nav>\s*<div class="nav-drawer"[^>]*>.*?</div>',
    re.DOTALL,
)
SHARED_FOOTER_PATTERN = re.compile(
    r'<footer class="site-footer">.*?</footer>', re.DOTALL
)


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.in_title = False
        self.description = False
        self.canonical = False
        self.json_ld = False
        self.noindex = False
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self.in_title = True
        if tag == "meta" and attrs.get("name") == "description" and attrs.get("content"):
            self.description = True
        if tag == "meta" and attrs.get("name") == "robots":
            self.noindex = "noindex" in attrs.get("content", "").lower()
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


def audit_html_file(path, site_dir=SITE_DIR):
    rel_path = path.relative_to(site_dir)
    parser = PageParser()
    page_html = path.read_text(errors="replace")
    parser.feed(page_html)
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
    if "search_term_string" in page_html:
        errors.append("declares URL-based SearchAction without a search results page")
    if re.search(r"\bGAA\s+GAA\b", page_html, re.IGNORECASE):
        errors.append('contains duplicate "GAA GAA" wording')
    if "googletagmanager.com/gtag" in page_html:
        errors.append("loads Google Analytics before consent")
    if re.search(
        r'<link[^>]+rel=["\']preconnect["\'][^>]+googletagmanager\.com',
        page_html,
        re.IGNORECASE,
    ):
        errors.append("connects to Google Analytics before consent")

    for attrs in parser.links:
        href = attrs.get("href", "")
        if not is_safe_href(href):
            errors.append(f"unsafe href: {href}")
        if attrs.get("target") == "_blank":
            rel = set((attrs.get("rel") or "").split())
            if not {"noopener", "noreferrer"}.issubset(rel):
                errors.append(f'target="_blank" missing noopener noreferrer: {href}')
    return errors


def shared_chrome_errors(path, site_dir=SITE_DIR):
    rel_path = path.relative_to(site_dir)
    page_html = path.read_text(errors="replace")
    parser = PageParser()
    parser.feed(page_html)
    if parser.noindex:
        return []

    errors = []
    nav_matches = SHARED_NAV_PATTERN.findall(page_html)
    expected_nav = navigation_html(active_navigation_for_path(rel_path))
    if nav_matches != [expected_nav]:
        errors.append("navigation differs from the shared template")

    footer_matches = SHARED_FOOTER_PATTERN.findall(page_html)
    expected_footers = [] if rel_path.as_posix() == "index.html" else [footer_html()]
    if footer_matches != expected_footers:
        errors.append("footer differs from the shared template")

    expected_analytics_count = 0 if rel_path.as_posix() == "404.html" else 1
    if page_html.count(analytics_html()) != expected_analytics_count:
        errors.append("analytics hook differs from the shared template")
    if page_html.count(navigation_script_html()) != 1:
        errors.append("navigation behavior differs from the shared template")
    return errors


def static_page_output_errors(
    metadata,
    template_dir=TEMPLATE_DIR,
    site_dir=SITE_DIR,
):
    errors = []
    for template_path in sorted(template_dir.rglob("*.html")):
        relative_path = template_path.relative_to(template_dir)
        output_path = site_dir / relative_path
        if not output_path.exists():
            errors.append(f"missing generated static page: {relative_path}")
            continue
        expected = render_static_template(template_path.read_text(), relative_path)
        if relative_path.as_posix() == "dataset.html":
            expected = update_dataset_page(expected, metadata)
        if output_path.read_text() != expected:
            errors.append(
                f"stale generated static page: {relative_path}; "
                "run scripts/generate_static_pages.py"
            )
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
    sitemap_paths = set()
    for url in root.findall("sm:url", namespace):
        loc = url.findtext("sm:loc", default="", namespaces=namespace)
        lastmod = url.findtext("sm:lastmod", default="", namespaces=namespace)
        if not loc:
            errors.append("sitemap URL missing loc")
            continue
        if not lastmod:
            errors.append(f"sitemap URL missing lastmod: {loc}")
        parsed = urlparse(loc)
        if parsed.netloc and parsed.netloc != "gaapitchfinder.com":
            errors.append(f"sitemap URL has unexpected host: {loc}")
            continue
        url_path = parsed.path or "/"
        local_path = sitemap_local_path(url_path)
        sitemap_paths.add(local_path.relative_to(SITE_DIR).as_posix())
        if not local_path.exists():
            errors.append(f"sitemap URL has no generated HTML file: {loc}")

    for html_path in sorted(SITE_DIR.rglob("*.html")):
        if html_path.name == "404.html":
            continue
        rel_path = html_path.relative_to(SITE_DIR).as_posix()
        parser = PageParser()
        parser.feed(html_path.read_text(errors="replace"))
        if parser.noindex:
            continue
        if rel_path not in sitemap_paths:
            errors.append(f"generated HTML page missing from sitemap: {rel_path}")
    return errors


def public_metadata_errors(metadata, dataset_html, readme):
    errors = []
    expected_outputs = (
        ("dataset metadata", render_dataset_head(metadata), dataset_html),
        ("dataset summary", render_dataset_summary(metadata), dataset_html),
        ("dataset contract", render_dataset_contract(metadata), dataset_html),
        ("README dataset summary", render_readme_summary(metadata), readme),
    )
    for label, expected, content in expected_outputs:
        if expected not in content:
            errors.append(
                f"stale {label}; run scripts/generate_public_metadata.py"
            )
    return errors


def audit_public_metadata():
    metadata = build_dataset_metadata(load_rows(), GitBuildMetadata(ROOT_DIR))
    dataset_html = (SITE_DIR / "dataset.html").read_text()
    readme = (ROOT_DIR / "README.md").read_text()
    return public_metadata_errors(metadata, dataset_html, readme)


def data_quality_output_errors(expected_report, report_json, page_html):
    errors = []
    try:
        parsed_report = json.loads(report_json)
    except json.JSONDecodeError as error:
        errors.append(f"data quality JSON is invalid: {error}")
    else:
        if parsed_report != expected_report:
            errors.append(
                "data quality JSON is stale; run scripts/generate_data_quality.py"
            )

    if page_html != render_data_quality_page(expected_report):
        errors.append(
            "data quality page is stale; run scripts/generate_data_quality.py"
        )
    return errors


def audit_data_quality():
    missing = [
        f"{path.relative_to(ROOT_DIR)} does not exist; run scripts/generate_data_quality.py"
        for path in (REPORT_JSON_PATH, REPORT_HTML_PATH)
        if not path.exists()
    ]
    if missing:
        return missing
    return data_quality_output_errors(
        build_current_report(),
        REPORT_JSON_PATH.read_text(encoding="utf-8"),
        REPORT_HTML_PATH.read_text(encoding="utf-8"),
    )


def geojson_structure_errors(geojson, expected_feature_count):
    errors = []
    if not isinstance(geojson, dict) or geojson.get("type") != "FeatureCollection":
        return ["GeoJSON root must be a FeatureCollection object"]

    features = geojson.get("features")
    if not isinstance(features, list):
        return ["GeoJSON features must be an array"]
    if len(features) != expected_feature_count:
        errors.append(
            "GeoJSON feature count does not match canonical CSV: "
            f"{len(features)} != {expected_feature_count}"
        )
    if geojson.get("feature_count") != expected_feature_count:
        errors.append("GeoJSON feature_count metadata does not match canonical CSV")

    expected_properties = {field.name for field in FIELD_DEFINITIONS}
    for index, feature in enumerate(features):
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            errors.append(f"GeoJSON feature {index} is not a Feature object")
            continue
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict) or geometry.get("type") != "Point":
            errors.append(f"GeoJSON feature {index} geometry is not a Point")
            continue
        coordinates = geometry.get("coordinates")
        if not isinstance(coordinates, list) or len(coordinates) != 2:
            errors.append(f"GeoJSON feature {index} coordinates are not [lon, lat]")
            continue
        longitude, latitude = coordinates
        if (
            not isinstance(longitude, (int, float))
            or isinstance(longitude, bool)
            or not math.isfinite(longitude)
            or not -180 <= longitude <= 180
            or not isinstance(latitude, (int, float))
            or isinstance(latitude, bool)
            or not math.isfinite(latitude)
            or not -90 <= latitude <= 90
        ):
            errors.append(f"GeoJSON feature {index} coordinates are invalid")
        properties = feature.get("properties")
        if not isinstance(properties, dict) or set(properties) != expected_properties:
            errors.append(
                f"GeoJSON feature {index} properties do not match the dataset schema"
            )
            continue
        if (
            properties["Longitude"] != longitude
            or properties["Latitude"] != latitude
        ):
            errors.append(
                f"GeoJSON feature {index} geometry and coordinate properties differ"
            )
    return errors


def dataset_download_errors(
    rows,
    metadata,
    dataset_path=DATASET_PATH,
    downloads_dir=DOWNLOADS_DIR,
):
    paths = {
        "CSV": downloads_dir / "gaapitchfinder.csv",
        "GeoJSON": downloads_dir / "gaapitchfinder.geojson",
        "schema": downloads_dir / "schema.json",
    }
    missing = [
        f"dataset {label} download does not exist"
        for label, path in paths.items()
        if not path.exists()
    ]
    if missing:
        return missing

    errors = []
    if paths["CSV"].read_bytes() != dataset_path.read_bytes():
        errors.append("dataset CSV download differs from the canonical CSV")

    parsed = {}
    for label in ("GeoJSON", "schema"):
        try:
            parsed[label] = json.loads(paths[label].read_text())
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            errors.append(f"dataset {label} download is not valid JSON: {error}")
    if "GeoJSON" in parsed:
        errors.extend(
            geojson_structure_errors(parsed["GeoJSON"], metadata.record_count)
        )
        if parsed["GeoJSON"] != build_geojson(rows, metadata):
            errors.append("dataset GeoJSON download is stale")
    if "schema" in parsed and parsed["schema"] != build_schema(metadata):
        errors.append("dataset schema download is stale")
    return errors


def audit_dataset_downloads():
    rows = load_rows()
    metadata = build_dataset_metadata(rows, GitBuildMetadata(ROOT_DIR))
    return dataset_download_errors(rows, metadata)


def audit_privacy_page():
    privacy_html = (SITE_DIR / "privacy.html").read_text()
    errors = []
    for service in PRIVACY_SERVICES:
        if service not in privacy_html:
            errors.append(f"privacy page is missing service inventory item: {service}")

    build_metadata = GitBuildMetadata(ROOT_DIR)
    try:
        privacy_last_modified = build_metadata.last_modified_date(
            "templates/static/privacy.html"
        )
    except BuildMetadataError:
        # The template path has no Git history until the consolidation commit exists.
        privacy_last_modified = build_metadata.last_modified_date("site/privacy.html")
    expected_date = (
        f'<time datetime="{privacy_last_modified}">'
        f"{format_iso_date(privacy_last_modified)}</time>"
    )
    if expected_date not in privacy_html:
        errors.append("privacy page last-updated date does not match Git history")
    if "Google Analytics is optional and does not load unless you accept it" not in privacy_html:
        errors.append("privacy page does not state the current analytics consent behavior")
    return errors


def sitemap_local_path(url_path):
    if url_path == "/":
        return SITE_DIR / "index.html"
    if url_path.endswith("/"):
        return SITE_DIR / url_path.lstrip("/") / "index.html"
    return SITE_DIR / url_path.lstrip("/")


def main():
    failures = []
    for html_path in sorted(SITE_DIR.rglob("*.html")):
        for error in audit_html_file(html_path):
            failures.append(f"{html_path.relative_to(SITE_DIR)}: {error}")
        for error in shared_chrome_errors(html_path):
            failures.append(f"{html_path.relative_to(SITE_DIR)}: {error}")
    metadata = build_dataset_metadata(load_rows(), GitBuildMetadata(ROOT_DIR))
    failures.extend(static_page_output_errors(metadata))
    failures.extend(audit_data_json())
    failures.extend(audit_sitemap())
    failures.extend(audit_public_metadata())
    failures.extend(audit_data_quality())
    failures.extend(audit_dataset_downloads())
    failures.extend(audit_privacy_page())

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1

    print("Site audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
