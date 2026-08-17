"""Sitemap metadata and legacy URL redirects."""

from __future__ import annotations

import html

from build_metadata import GitBuildMetadata
from site_builder.page_data import county_url
from site_builder.shared import absolute_url, esc, esc_attr
from site_build_utils import SITE_BASE_URL, SITE_DIR


STATIC_URLS = (
    ("/", 1.0),
    ("/pitch-of-the-day.html", 0.8),
    ("/directions.html", 0.9),
    ("/dataset.html", 0.8),
    ("/data-quality.html", 0.7),
    ("/about.html", 0.7),
    ("/privacy.html", 0.5),
    ("/donate.html", 0.6),
    ("/donate-thanks.html", 0.4),
    ("/blog/", 0.8),
)
LEGACY_REDIRECTS = {
    "/home": "/",
    "/cart": "/donate.html",
    "/directions": "/directions.html",
    "/blog/category/list": "/blog/",
    "/blog/tag/ireland": "/blog/",
    "/blog/tag/update": "/blog/",
    "/blog/2020update": "/blog/",
    "/clubs/halloway-gaels-england.html": "/clubs/holloway-gaels-england.html",
    "/clubs/cayman-gaa-cayman-island.html": "/clubs/cayman-gaa-cayman-islands.html",
    "/clubs/singapore-gaelic-lions-signapore.html": "/clubs/singapore-gaelic-lions-singapore.html",
}
GENERATED_PAGE_SOURCES = (
    "gaapitchfinder_data.csv",
    "scripts/generate_club_pages.py",
    "scripts/site_build_utils.py",
    "scripts/site_builder/build.py",
    "scripts/site_builder/page_data.py",
    "scripts/site_builder/pages.py",
    "scripts/site_builder/shared.py",
    "scripts/site_builder/sitemap.py",
)


def _static_source_paths(path: str) -> tuple[str, str]:
    if path == "/":
        relative_path = "index.html"
    elif path.endswith("/"):
        relative_path = f"{path.lstrip('/')}index.html"
    else:
        relative_path = path.lstrip("/")
    return f"templates/static/{relative_path}", f"site/{relative_path}"


def lastmod_for_path(path: str, build_metadata: GitBuildMetadata) -> str:
    if path == "/clubs/" or path.startswith("/clubs/"):
        return build_metadata.last_modified_date(*GENERATED_PAGE_SOURCES)
    if path == "/counties/" or path.startswith("/counties/"):
        return build_metadata.last_modified_date(*GENERATED_PAGE_SOURCES)
    if path == "/data-quality.html":
        return build_metadata.last_modified_date(
            "gaapitchfinder_data.csv",
            "data/derived/osm_coverage_report.csv",
            "scripts/generate_data_quality.py",
            "scripts/site_builder/shared.py",
        )
    return build_metadata.last_modified_date(*_static_source_paths(path))


def write_sitemap(pages: list[dict], counties: dict) -> None:
    build_metadata = GitBuildMetadata(SITE_DIR.parent)
    urls = [
        (path, f"{SITE_BASE_URL}{path}", priority)
        for path, priority in STATIC_URLS
    ]

    for blog_file in sorted((SITE_DIR / "blog").glob("*.html")):
        if blog_file.name == "index.html":
            continue
        path = f"/blog/{blog_file.name}"
        urls.append((path, f"{SITE_BASE_URL}{path}", 0.6))

    urls.append(("/clubs/", f"{SITE_BASE_URL}/clubs/", 0.8))
    for page in pages:
        path = f"/{page['rel_url']}"
        urls.append((path, f"{SITE_BASE_URL}{path}", 0.6))
    urls.append(("/counties/", f"{SITE_BASE_URL}/counties/", 0.8))
    for county in counties:
        path = f"/{county_url(county)}"
        urls.append((path, f"{SITE_BASE_URL}{path}", 0.7))

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path, url, priority in urls:
        lines.append(
            f"  <url><loc>{html.escape(url)}</loc><lastmod>{lastmod_for_path(path, build_metadata)}</lastmod><priority>{priority:.1f}</priority></url>"
        )
    lines.append("</urlset>")
    (SITE_DIR / "sitemap.xml").write_text("\n".join(lines) + "\n")


def legacy_page_path(path: str):
    if path.endswith(".html"):
        return SITE_DIR / path.lstrip("/")
    return SITE_DIR / path.lstrip("/") / "index.html"


def render_legacy_redirect_page(source_path: str, target_path: str) -> str:
    target_url = absolute_url(target_path)
    source_url = absolute_url(source_path)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, follow">
<meta http-equiv="refresh" content="0; url={esc_attr(target_path)}">
<title>Moved - GAA Pitch Finder</title>
<link rel="canonical" href="{esc_attr(target_url)}">
</head>
<body>
<p>This page has moved to <a href="{esc_attr(target_path)}">{esc(target_url)}</a>.</p>
<!-- Legacy URL: {esc(source_url)} -->
</body>
</html>
"""


def write_legacy_redirects() -> None:
    for source_path, target_path in LEGACY_REDIRECTS.items():
        output_path = legacy_page_path(source_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(render_legacy_redirect_page(source_path, target_path))
