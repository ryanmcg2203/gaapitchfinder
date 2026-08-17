"""Build orchestration for generated club and county pages."""

from __future__ import annotations

from site_builder.page_data import county_pages, county_slug
from site_builder.pages import (
    render_club_page,
    render_counties_index,
    render_county_page,
    render_index_page,
)
from site_builder.sitemap import LEGACY_REDIRECTS, write_legacy_redirects, write_sitemap
from site_build_utils import SITE_DIR, build_club_page_records, load_rows


CLUBS_DIR = SITE_DIR / "clubs"
COUNTIES_DIR = SITE_DIR / "counties"


def _clear_generated_pages(directory) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for old_file in directory.glob("*.html"):
        old_file.unlink()


def main() -> None:
    pages, _row_to_url = build_club_page_records(load_rows())
    counties = county_pages(pages)

    _clear_generated_pages(CLUBS_DIR)
    _clear_generated_pages(COUNTIES_DIR)

    for page in pages:
        (CLUBS_DIR / f"{page['slug']}.html").write_text(
            render_club_page(page, pages)
        )
    (CLUBS_DIR / "index.html").write_text(render_index_page(pages))
    (COUNTIES_DIR / "index.html").write_text(render_counties_index(counties))
    for county, county_page_records in counties.items():
        (COUNTIES_DIR / f"{county_slug(county)}.html").write_text(
            render_county_page(county, county_page_records)
        )

    write_legacy_redirects()
    write_sitemap(pages, counties)

    print(f"Generated {len(pages)} club pages -> {CLUBS_DIR}")
    print(f"Generated club index -> {CLUBS_DIR / 'index.html'}")
    print(f"Generated {len(counties)} county pages -> {COUNTIES_DIR}")
    print(f"Generated {len(LEGACY_REDIRECTS)} legacy redirects")
    print(f"Generated sitemap -> {SITE_DIR / 'sitemap.xml'}")
