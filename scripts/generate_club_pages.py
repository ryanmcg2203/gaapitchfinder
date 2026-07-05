#!/usr/bin/env python3
"""
Generate static club pages and a clubs index for SEO.

Run from repo root:
    python3 scripts/generate_club_pages.py
"""

from __future__ import annotations

import html
from pathlib import Path

from site_build_utils import (
    SITE_BASE_URL,
    SITE_DIR,
    build_club_page_records,
    load_rows,
    row_display_place,
    row_region,
)


CLUBS_DIR = SITE_DIR / "clubs"
STATIC_URLS = [
    ("/", 1.0),
    ("/directions.html", 0.9),
    ("/dataset.html", 0.8),
    ("/about.html", 0.7),
    ("/blog/", 0.8),
]


def esc(value):
    return html.escape(value or "")


def ga_snippet():
    return """<script async src="https://www.googletagmanager.com/gtag/js?id=G-8R6YMPVNWH"></script>
<script src="/js/ga.js"></script>"""


def page_title(page):
    first_row = page["rows"][0]
    pitch = first_row["Pitch"].strip()
    if len(page["rows"]) == 1 and pitch:
        return f"{pitch} ({page['club']}) – GAA Pitch Finder"
    return f"{page['club']} – {page['location_label']} | GAA Pitch Finder"


def page_description(page):
    pitches = [row["Pitch"].strip() for row in page["rows"] if row["Pitch"].strip()]
    if len(page["rows"]) == 1 and pitches:
        return (
            f"Find {pitches[0]}, home of {page['club']}, with location details, "
            f"coordinates, and Google Maps directions."
        )
    if pitches:
        sample = ", ".join(pitches[:2])
        return (
            f"Find {page['club']} in {page['location_label']}. "
            f"View pitch details including {sample}, coordinates, and directions."
        )
    return (
        f"Find {page['club']} in {page['location_label']} with pitch coordinates, "
        "location details, and Google Maps directions."
    )


def row_details_html(row):
    details = []
    if row["Code"].strip():
        details.append(("Code", row["Code"].strip()))
    if row["Division"].strip():
        details.append(("Division", row["Division"].strip()))
    if row["Province"].strip() and row["File"].strip() == "Ireland":
        details.append(("Province", row["Province"].strip()))
    if row["Country"].strip():
        details.append(("Country", row["Country"].strip()))
    if row["Elevation"].strip():
        details.append(("Elevation", f"{row['Elevation'].strip()} m"))
    if row["annual_rainfall"].strip():
        details.append(("Annual rainfall", f"{row['annual_rainfall'].strip()} mm"))
    if row["rain_days"].strip():
        details.append(("Rain days", row["rain_days"].strip()))

    items = [
        f"<li><span class=\"club-detail-label\">Coordinates</span>"
        f"<span>{esc(row['Latitude'].strip())}, {esc(row['Longitude'].strip())}</span></li>"
    ]
    for label, value in details:
        items.append(
            f"<li><span class=\"club-detail-label\">{esc(label)}</span>"
            f"<span>{esc(value)}</span></li>"
        )
    return "".join(items)


def render_club_page(page):
    canonical_url = f"{SITE_BASE_URL}/{page['rel_url']}"
    title = page_title(page)
    description = page_description(page)
    rows_html = []

    for row in page["rows"]:
        pitch = row["Pitch"].strip() or "Pitch details"
        place = row_display_place(row)
        maps_url = row["Directions"].strip() or (
            f"https://maps.google.com/?daddr={row['Latitude'].strip()},{row['Longitude'].strip()}"
        )
        twitter = row["Twitter"].strip()
        actions = [
            f"<a href=\"{esc(maps_url)}\" target=\"_blank\" rel=\"noopener noreferrer\">Google Maps Directions</a>"
        ]
        if twitter:
            actions.append(
                f"<a href=\"{esc(twitter)}\" target=\"_blank\" rel=\"noopener noreferrer\">Club Twitter</a>"
            )

        rows_html.append(
            f"""
<section class="club-entry">
  <h2>{esc(pitch)}</h2>
  <p class="club-place">{esc(place)}</p>
  <ul class="club-detail-list">
    {row_details_html(row)}
  </ul>
  <div class="club-actions">
    {"".join(actions)}
  </div>
</section>
""".strip()
        )

    body = "\n".join(rows_html)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<link rel="icon" type="image/png" href="../img/logo-icon.png">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:image" content="https://gaapitchfinder.com/img/logo-black.png">
<meta property="og:url" content="{esc(canonical_url)}">
<meta property="og:type" content="website">
<link rel="canonical" href="{esc(canonical_url)}">
<meta name="description" content="{esc(description)}">
{ga_snippet()}
<link rel="stylesheet" href="../css/style.css">
</head>
<body>

<nav class="site-nav">
  <a href="/" class="nav-logo">
    <img src="../img/logo-icon.png" alt="GAA Pitch Finder logo" width="36" height="36" style="border-radius:50%;">
    GAA Pitch Finder
  </a>
  <ul class="nav-links">
    <li><a href="/blog/">Blog</a></li>
    <li><a href="/directions.html">Directions</a></li>
    <li><a href="/about.html">About</a></li>
    <li><a href="/dataset.html">Dataset</a></li>
  </ul>
  <a href="https://www.paypal.com/paypalme/gaapitchfinder" class="nav-donate" target="_blank" rel="noopener noreferrer">Donate</a>
  <button class="nav-hamburger" id="hamburger" aria-label="Open menu">
    <span></span><span></span><span></span>
  </button>
</nav>
<div class="nav-drawer" id="nav-drawer">
  <button class="drawer-close" id="drawer-close" aria-label="Close menu">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
  </button>
  <a href="/">GAA Pitch Finder</a>
  <a href="/blog/">Blog</a>
  <a href="/directions.html">Directions</a>
  <a href="/dataset.html">Dataset</a>
  <a href="/about.html">About</a>
  <a href="https://www.paypal.com/paypalme/gaapitchfinder" target="_blank" rel="noopener noreferrer">Donate</a>
</div>

<div class="page-content">
  <p class="clubs-breadcrumb"><a href="/clubs/">Clubs</a> / {esc(page["location_label"])}</p>
  <h1>{esc(page["club"])}</h1>
  <p class="clubs-subtitle">{esc(page["location_label"])} · {esc(row_region(page["rows"][0]))}</p>
  <p>This page lists the pitch details recorded for {esc(page["club"])} on GAA Pitch Finder, including coordinates and Google Maps directions.</p>
  {body}
  <a href="/directions.html" class="back-link">Browse all directions</a>
</div>

<footer class="site-footer">
  &copy; GAA Pitch Finder &nbsp;·&nbsp; <a href="mailto:gaapitchfinder@gmail.com">gaapitchfinder@gmail.com</a>
</footer>

<script>
document.getElementById('hamburger').addEventListener('click', () => {{
  document.getElementById('nav-drawer').classList.toggle('open');
}});
document.getElementById('drawer-close').addEventListener('click', () => {{
  document.getElementById('nav-drawer').classList.remove('open');
}});
</script>
</body>
</html>
"""


def render_index_page(pages):
    groups = {}
    for page in pages:
        initial = page["club"][0].upper() if page["club"] else "#"
        if not initial.isalpha():
            initial = "#"
        groups.setdefault(initial, []).append(page)

    sections = []
    for initial in sorted(groups):
        links = []
        for page in sorted(groups[initial], key=lambda item: (item["club"].lower(), item["location_label"].lower())):
            links.append(
                f"<li><a href=\"/{page['rel_url']}\">{esc(page['club'])}</a>"
                f"<span class=\"club-directory-meta\">{esc(page['location_label'])}</span></li>"
            )
        sections.append(
            f"<section class=\"club-directory-group\" id=\"group-{initial.lower()}\">"
            f"<h2>{esc(initial)}</h2><ul>{''.join(links)}</ul></section>"
        )

    toc = "".join(
        f"<a href=\"#group-{initial.lower()}\">{esc(initial)}</a>" for initial in sorted(groups)
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GAA Club Directory – GAA Pitch Finder</title>
<link rel="icon" type="image/png" href="../img/logo-icon.png">
<meta property="og:title" content="GAA Club Directory – GAA Pitch Finder">
<meta property="og:description" content="Browse club and pitch pages for GAA clubs in Ireland and worldwide.">
<meta property="og:image" content="https://gaapitchfinder.com/img/logo-black.png">
<meta property="og:url" content="https://gaapitchfinder.com/clubs/">
<meta property="og:type" content="website">
<link rel="canonical" href="https://gaapitchfinder.com/clubs/">
<meta name="description" content="Browse club and pitch pages for GAA clubs in Ireland and worldwide.">
{ga_snippet()}
<link rel="stylesheet" href="../css/style.css">
</head>
<body>

<nav class="site-nav">
  <a href="/" class="nav-logo">
    <img src="../img/logo-icon.png" alt="GAA Pitch Finder logo" width="36" height="36" style="border-radius:50%;">
    GAA Pitch Finder
  </a>
  <ul class="nav-links">
    <li><a href="/blog/">Blog</a></li>
    <li><a href="/directions.html">Directions</a></li>
    <li><a href="/about.html">About</a></li>
    <li><a href="/dataset.html">Dataset</a></li>
  </ul>
  <a href="https://www.paypal.com/paypalme/gaapitchfinder" class="nav-donate" target="_blank" rel="noopener noreferrer">Donate</a>
  <button class="nav-hamburger" id="hamburger" aria-label="Open menu">
    <span></span><span></span><span></span>
  </button>
</nav>
<div class="nav-drawer" id="nav-drawer">
  <button class="drawer-close" id="drawer-close" aria-label="Close menu">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
  </button>
  <a href="/">GAA Pitch Finder</a>
  <a href="/blog/">Blog</a>
  <a href="/directions.html">Directions</a>
  <a href="/dataset.html">Dataset</a>
  <a href="/about.html">About</a>
  <a href="https://www.paypal.com/paypalme/gaapitchfinder" target="_blank" rel="noopener noreferrer">Donate</a>
</div>

<div class="page-content">
  <h1>Club Directory</h1>
  <p>Browse static club and pitch pages for GAA clubs in Ireland and worldwide. Each page includes the recorded pitch details, coordinates, and directions links from the GAA Pitch Finder dataset.</p>
  <div class="club-directory-toc">{toc}</div>
  {"".join(sections)}
</div>

<footer class="site-footer">
  &copy; GAA Pitch Finder &nbsp;·&nbsp; <a href="mailto:gaapitchfinder@gmail.com">gaapitchfinder@gmail.com</a>
</footer>

<script>
document.getElementById('hamburger').addEventListener('click', () => {{
  document.getElementById('nav-drawer').classList.toggle('open');
}});
document.getElementById('drawer-close').addEventListener('click', () => {{
  document.getElementById('nav-drawer').classList.remove('open');
}});
</script>
</body>
</html>
"""


def write_sitemap(pages):
    urls = []
    for path, priority in STATIC_URLS:
        urls.append((f"{SITE_BASE_URL}{path}", priority))

    blog_dir = SITE_DIR / "blog"
    for blog_file in sorted(blog_dir.glob("*.html")):
        if blog_file.name == "index.html":
            continue
        urls.append((f"{SITE_BASE_URL}/blog/{blog_file.name}", 0.6))

    urls.append((f"{SITE_BASE_URL}/clubs/", 0.8))
    for page in pages:
        urls.append((f"{SITE_BASE_URL}/{page['rel_url']}", 0.6))

    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, priority in urls:
        lines.append(f"  <url><loc>{html.escape(url)}</loc><priority>{priority:.1f}</priority></url>")
    lines.append("</urlset>")
    (SITE_DIR / "sitemap.xml").write_text("\n".join(lines) + "\n")


def main():
    rows = load_rows()
    pages, _row_to_url = build_club_page_records(rows)

    CLUBS_DIR.mkdir(parents=True, exist_ok=True)
    for old_file in CLUBS_DIR.glob("*.html"):
        old_file.unlink()

    for page in pages:
        (CLUBS_DIR / f"{page['slug']}.html").write_text(render_club_page(page))

    (CLUBS_DIR / "index.html").write_text(render_index_page(pages))
    write_sitemap(pages)

    print(f"Generated {len(pages)} club pages → {CLUBS_DIR}")
    print(f"Generated club index → {CLUBS_DIR / 'index.html'}")
    print(f"Generated sitemap → {SITE_DIR / 'sitemap.xml'}")


if __name__ == "__main__":
    main()
