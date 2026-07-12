#!/usr/bin/env python3
"""
Generate static club pages and a clubs index for SEO.

Run from repo root:
    python3 scripts/generate_club_pages.py
"""

from __future__ import annotations

import html
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from site_build_utils import (
    ALLOWED_SOCIAL_HOSTS,
    DATASET_PATH,
    SITE_BASE_URL,
    SITE_DIR,
    build_club_page_records,
    load_rows,
    row_coordinates,
    row_display_place,
    row_maps_url,
    row_region,
    sanitized_external_url,
)


CLUBS_DIR = SITE_DIR / "clubs"
COUNTIES_DIR = SITE_DIR / "counties"
STATIC_URLS = [
    ("/", 1.0),
    ("/pitch-of-the-day.html", 0.8),
    ("/directions.html", 0.9),
    ("/dataset.html", 0.8),
    ("/about.html", 0.7),
    ("/blog/", 0.8),
]
PROVINCE_ORDER = ["Connacht", "Leinster", "Munster", "Ulster"]


def esc(value):
    return html.escape(value or "")


def esc_attr(value):
    return html.escape(value or "", quote=True)


def ga_snippet():
    return """<script async src="https://www.googletagmanager.com/gtag/js?id=G-8R6YMPVNWH"></script>
<script src="/js/ga.js"></script>"""


def absolute_url(path):
    return f"{SITE_BASE_URL}/{path.lstrip('/')}"


def json_ld_script(data):
    json_text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    json_text = json_text.replace("</", "<\\/")
    return f'<script type="application/ld+json">{json_text}</script>'


def breadcrumb_schema(items):
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index,
                "name": name,
                "item": url,
            }
            for index, (name, url) in enumerate(items, start=1)
        ],
    }


def nav_html(prefix="../"):
    return f"""
<nav class="site-nav">
  <a href="/" class="nav-logo">
    <img src="{prefix}img/logo-icon.png" alt="GAA Pitch Finder logo" width="36" height="36" style="border-radius:50%;">
    GAA Pitch Finder
  </a>
  <ul class="nav-links">
    <li><a href="/clubs/">Clubs</a></li>
    <li><a href="/counties/">Counties</a></li>
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
  <a href="/clubs/">Clubs</a>
  <a href="/counties/">Counties</a>
  <a href="/blog/">Blog</a>
  <a href="/directions.html">Directions</a>
  <a href="/dataset.html">Dataset</a>
  <a href="/about.html">About</a>
  <a href="https://www.paypal.com/paypalme/gaapitchfinder" target="_blank" rel="noopener noreferrer">Donate</a>
</div>
""".strip()


def drawer_script():
    return """
<script>
document.getElementById('hamburger').addEventListener('click', () => {
  document.getElementById('nav-drawer').classList.toggle('open');
});
document.getElementById('drawer-close').addEventListener('click', () => {
  document.getElementById('nav-drawer').classList.remove('open');
});
</script>
""".strip()


def directory_search_html(input_id, placeholder, label="Search"):
    return f"""
<div class="directory-search">
  <label for="{esc_attr(input_id)}">{esc(label)}</label>
  <input id="{esc_attr(input_id)}" type="search" placeholder="{esc_attr(placeholder)}" autocomplete="off">
</div>
""".strip()


def directory_search_script(input_id, item_selector, empty_id):
    return f"""
<script>
(function() {{
  const input = document.getElementById('{input_id}');
  const empty = document.getElementById('{empty_id}');
  if (!input) return;
  const items = Array.from(document.querySelectorAll('{item_selector}'));
  function applyFilter() {{
    const query = input.value.trim().toLowerCase();
    let visible = 0;
    items.forEach((item) => {{
      const text = (item.dataset.search || item.textContent || '').toLowerCase();
      const match = !query || text.includes(query);
      item.hidden = !match;
      if (match) visible += 1;
    }});
    if (empty) empty.hidden = visible !== 0;
  }}
  input.addEventListener('input', applyFilter);
  applyFilter();
}})();
</script>
""".strip()


def back_to_top_link():
    return '<a href="#top" class="back-to-top" aria-label="Back to top">Back to top</a>'


def page_coordinates(page):
    coords = [row_coordinates(row) for row in page["rows"]]
    coords = [coord for coord in coords if coord]
    if not coords:
        return None
    return (
        sum(coord[0] for coord in coords) / len(coords),
        sum(coord[1] for coord in coords) / len(coords),
    )


def page_pitch_label(page):
    pitch_names = [row["Pitch"].strip() for row in page["rows"] if row["Pitch"].strip()]
    if pitch_names:
        label = ", ".join(pitch_names[:2])
        if len(pitch_names) > 2:
            label += f", +{len(pitch_names) - 2} more"
        return label
    coords = page_coordinates(page)
    if coords:
        return f"{coords[0]:.6f}, {coords[1]:.6f}"
    return row_display_place(page["rows"][0])


def haversine_km(origin, target):
    lat1, lon1 = origin
    lat2, lon2 = target
    radius = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def county_slug(county):
    from site_build_utils import slugify

    return slugify(county)


def county_url(county):
    return f"counties/{county_slug(county)}.html"


def ireland_county(row):
    return row["County"].strip() if row["File"].strip() == "Ireland" else ""


def place_address(row):
    address = {}
    if row["Country"].strip():
        address["addressCountry"] = row["Country"].strip()
    if row["Province"].strip() and row["File"].strip() == "Ireland":
        address["addressRegion"] = row["Province"].strip()
    locality = row["County"].strip() or row["Division"].strip()
    if locality:
        address["addressLocality"] = locality
    return address


def row_place_schema(row, page_url, index=0):
    coords = row_coordinates(row)
    name = row["Pitch"].strip() or row["Club"].strip()
    place = {
        "@type": "SportsActivityLocation",
        "@id": f"{page_url}#pitch-{index + 1}",
        "name": name,
        "url": page_url,
        "sport": ["Gaelic games", "Gaelic football", "Hurling"],
    }
    if row["Club"].strip():
        place["alternateName"] = row["Club"].strip()
    if row_display_place(row):
        place["address"] = {
            "@type": "PostalAddress",
            **place_address(row),
        }
    if coords:
        place["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": coords[0],
            "longitude": coords[1],
        }
        place["hasMap"] = row_maps_url(row)
    return place


def club_page_schema(page, title, description, canonical_url):
    first_county = ireland_county(page["rows"][0])
    breadcrumbs = [("GAA Pitch Finder", SITE_BASE_URL), ("Clubs", absolute_url("clubs/"))]
    if first_county:
        breadcrumbs.append((first_county, absolute_url(county_url(first_county))))
    breadcrumbs.append((page["club"], canonical_url))

    graph = [
        {
            "@type": "WebPage",
            "@id": canonical_url,
            "url": canonical_url,
            "name": title,
            "description": description,
            "isPartOf": {
                "@type": "WebSite",
                "@id": f"{SITE_BASE_URL}/#website",
                "name": "GAA Pitch Finder",
                "url": SITE_BASE_URL,
            },
            "about": [
                {"@id": f"{canonical_url}#pitch-{index + 1}"}
                for index, _row in enumerate(page["rows"])
            ],
        },
        breadcrumb_schema(breadcrumbs),
    ]
    graph.extend(
        row_place_schema(row, canonical_url, index)
        for index, row in enumerate(page["rows"])
    )
    return json_ld_script({"@context": "https://schema.org", "@graph": graph})


def county_index_schema(counties):
    url = absolute_url("counties/")
    return json_ld_script(
        {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "CollectionPage",
                    "@id": url,
                    "url": url,
                    "name": "GAA Pitches By County",
                    "description": "Browse GAA pitch and club pages by county in Ireland.",
                    "isPartOf": {
                        "@type": "WebSite",
                        "@id": f"{SITE_BASE_URL}/#website",
                        "name": "GAA Pitch Finder",
                        "url": SITE_BASE_URL,
                    },
                    "mainEntity": {
                        "@type": "ItemList",
                        "itemListElement": [
                            {
                                "@type": "ListItem",
                                "position": index,
                                "name": county,
                                "url": absolute_url(county_url(county)),
                            }
                            for index, county in enumerate(counties, start=1)
                        ],
                    },
                },
                breadcrumb_schema(
                    [
                        ("GAA Pitch Finder", SITE_BASE_URL),
                        ("Clubs", absolute_url("clubs/")),
                        ("Counties", url),
                    ]
                ),
            ],
        }
    )


def club_index_schema(pages):
    url = absolute_url("clubs/")
    sorted_pages = sorted(
        pages, key=lambda item: (item["club"].lower(), item["location_label"].lower())
    )
    return json_ld_script(
        {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "CollectionPage",
                    "@id": url,
                    "url": url,
                    "name": "GAA Club Directory",
                    "description": "Browse club and pitch pages for GAA clubs in Ireland and worldwide.",
                    "isPartOf": {
                        "@type": "WebSite",
                        "@id": f"{SITE_BASE_URL}/#website",
                        "name": "GAA Pitch Finder",
                        "url": SITE_BASE_URL,
                    },
                    "mainEntity": {
                        "@type": "ItemList",
                        "itemListElement": [
                            {
                                "@type": "ListItem",
                                "position": index,
                                "name": page["club"],
                                "url": absolute_url(page["rel_url"]),
                            }
                            for index, page in enumerate(sorted_pages, start=1)
                        ],
                    },
                },
                breadcrumb_schema(
                    [
                        ("GAA Pitch Finder", SITE_BASE_URL),
                        ("Clubs", url),
                    ]
                ),
            ],
        }
    )


def county_page_schema(county, pages, description):
    url = absolute_url(county_url(county))
    return json_ld_script(
        {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "CollectionPage",
                    "@id": url,
                    "url": url,
                    "name": f"GAA Pitches In {county}",
                    "description": description,
                    "isPartOf": {
                        "@type": "WebSite",
                        "@id": f"{SITE_BASE_URL}/#website",
                        "name": "GAA Pitch Finder",
                        "url": SITE_BASE_URL,
                    },
                    "mainEntity": {
                        "@type": "ItemList",
                        "itemListElement": [
                            {
                                "@type": "ListItem",
                                "position": index,
                                "name": page["club"],
                                "url": absolute_url(page["rel_url"]),
                            }
                            for index, page in enumerate(pages, start=1)
                        ],
                    },
                },
                breadcrumb_schema(
                    [
                        ("GAA Pitch Finder", SITE_BASE_URL),
                        ("Clubs", absolute_url("clubs/")),
                        ("Counties", absolute_url("counties/")),
                        (county, url),
                    ]
                ),
            ],
        }
    )


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


def map_html(row, map_id):
    coords = row_coordinates(row)
    if not coords:
        return ""
    lat, lng = coords
    label = row["Pitch"].strip() or row["Club"].strip()
    data = json.dumps({"id": map_id, "lat": lat, "lng": lng, "label": label})
    return (
        f"<div class=\"club-map\" id=\"{esc_attr(map_id)}\" "
        f"data-map='{esc_attr(data)}'></div>"
    )


def context_links(page, pages):
    current_url = page["rel_url"]
    location_label = page["location_label"]
    same_location = [
        candidate
        for candidate in pages
        if candidate["rel_url"] != current_url
        and candidate["location_label"] == location_label
        and row_region(candidate["rows"][0]) == row_region(page["rows"][0])
    ]
    same_location = sorted(
        same_location,
        key=lambda item: (item["club"].lower(), item["location_label"].lower()),
    )[:8]

    nearby = []
    current_coords = page_coordinates(page)
    if current_coords:
        for candidate in pages:
            if candidate["rel_url"] == current_url:
                continue
            candidate_coords = page_coordinates(candidate)
            if not candidate_coords:
                continue
            nearby.append((haversine_km(current_coords, candidate_coords), candidate))
        nearby = sorted(nearby, key=lambda item: item[0])[:5]

    blocks = []
    if nearby:
        links = "".join(
            f"<li><a href=\"/{candidate['rel_url']}\">{esc(candidate['club'])}</a>"
            f"<span>{distance:.1f} km</span></li>"
            for distance, candidate in nearby
        )
        blocks.append(
            f"<section class=\"club-context-block\"><h2>Nearby Pitches</h2><ul>{links}</ul></section>"
    )

    if same_location:
        heading = f"Other Clubs In {location_label}"
        county_link = ""
        county = ireland_county(page["rows"][0])
        if county:
            county_link = (
                f"<a class=\"club-context-more\" href=\"/{county_url(county)}\">"
                f"View all {esc(county)} pitches</a>"
            )
        links = "".join(
            f"<li><a href=\"/{candidate['rel_url']}\">{esc(candidate['club'])}</a>"
            f"<span>{esc(page_pitch_label(candidate))}</span></li>"
            for candidate in same_location
        )
        blocks.append(
            f"<section class=\"club-context-block\"><h2>{esc(heading)}</h2><ul>{links}</ul>{county_link}</section>"
        )

    if not blocks:
        return ""
    return f"<div class=\"club-context\">{''.join(blocks)}</div>"


def render_club_page(page, pages):
    canonical_url = f"{SITE_BASE_URL}/{page['rel_url']}"
    title = page_title(page)
    description = page_description(page)
    structured_data = club_page_schema(page, title, description, canonical_url)
    rows_html = []

    for row_index, row in enumerate(page["rows"]):
        pitch = row["Pitch"].strip() or "Pitch details"
        place = row_display_place(row)
        maps_url = row_maps_url(row)
        twitter = sanitized_external_url(row["Twitter"], ALLOWED_SOCIAL_HOSTS)
        actions = [
            f"<a href=\"{esc_attr(maps_url)}\" target=\"_blank\" rel=\"noopener noreferrer\">Google Maps Directions</a>"
        ]
        if twitter:
            actions.append(
                f"<a href=\"{esc_attr(twitter)}\" target=\"_blank\" rel=\"noopener noreferrer\">Club Social</a>"
            )

        rows_html.append(
            f"""
<section class="club-entry">
  <h2>{esc(pitch)}</h2>
  <p class="club-place">{esc(place)}</p>
  {map_html(row, f"club-map-{row_index}")}
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
    context_html = context_links(page, pages)
    first_county = ireland_county(page["rows"][0])
    breadcrumb = '<a href="/clubs/">Clubs</a>'
    if first_county:
        breadcrumb += f' / <a href="/{county_url(first_county)}">{esc(first_county)}</a>'
    else:
        breadcrumb += f" / {esc(page['location_label'])}"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<link rel="icon" type="image/png" href="../img/logo-icon.png">
<link rel="stylesheet" href="../vendor/leaflet.css">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:image" content="https://gaapitchfinder.com/img/logo-black.png">
<meta property="og:url" content="{esc(canonical_url)}">
<meta property="og:type" content="website">
<link rel="canonical" href="{esc(canonical_url)}">
<meta name="description" content="{esc(description)}">
{structured_data}
{ga_snippet()}
<link rel="stylesheet" href="../css/style.css">
</head>
<body>

{nav_html()}

<div class="page-content">
  <p class="clubs-breadcrumb">{breadcrumb}</p>
  <h1>{esc(page["club"])}</h1>
  <p class="clubs-subtitle">{esc(page["location_label"])} · {esc(row_region(page["rows"][0]))}</p>
  <p>This page lists the pitch details recorded for {esc(page["club"])} on GAA Pitch Finder, including coordinates and Google Maps directions.</p>
  {body}
  {context_html}
  <a href="/directions.html" class="back-link">Browse all directions</a>
</div>

<footer class="site-footer">
  &copy; GAA Pitch Finder &nbsp;·&nbsp; <a href="mailto:gaapitchfinder@gmail.com">gaapitchfinder@gmail.com</a>
</footer>

<script src="../vendor/leaflet.js"></script>
<script>
document.querySelectorAll('.club-map').forEach((el) => {{
  const data = JSON.parse(el.dataset.map);
  const map = L.map(el, {{ dragging: false, scrollWheelZoom: false, zoomControl: false }}).setView([data.lat, data.lng], 14);
  L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution: '&copy; OpenStreetMap contributors'
  }}).addTo(map);
  L.marker([data.lat, data.lng]).addTo(map).bindPopup(data.label);
}});
</script>
{drawer_script()}
</body>
</html>
"""


def render_index_page(pages):
    structured_data = club_index_schema(pages)
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
            search_text = f"{page['club']} {page['location_label']} {row_region(page['rows'][0])}"
            links.append(
                f"<li data-search=\"{esc_attr(search_text)}\"><a href=\"/{page['rel_url']}\">{esc(page['club'])}</a>"
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
{structured_data}
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
    <li><a href="/clubs/">Clubs</a></li>
    <li><a href="/counties/">Counties</a></li>
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
  <a href="/clubs/">Clubs</a>
  <a href="/counties/">Counties</a>
  <a href="/blog/">Blog</a>
  <a href="/directions.html">Directions</a>
  <a href="/dataset.html">Dataset</a>
  <a href="/about.html">About</a>
  <a href="https://www.paypal.com/paypalme/gaapitchfinder" target="_blank" rel="noopener noreferrer">Donate</a>
</div>

<div class="page-content" id="top">
  <h1>Club Directory</h1>
  <p>Browse static club and pitch pages for GAA clubs in Ireland and worldwide. Each page includes the recorded pitch details, coordinates, and directions links from the GAA Pitch Finder dataset.</p>
  {directory_search_html("club-directory-search", "Search clubs, counties, or countries")}
  <div class="club-directory-toc">{toc}</div>
  {"".join(sections)}
  <p class="directory-empty" id="club-directory-empty" hidden>No matching clubs found.</p>
</div>
{back_to_top_link()}

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
{directory_search_script("club-directory-search", ".club-directory-group li", "club-directory-empty")}
</body>
</html>
"""


def county_pages(pages):
    grouped = {}
    for page in pages:
        county = ireland_county(page["rows"][0])
        if county:
            grouped.setdefault(county, []).append(page)
    return {
        county: sorted(items, key=lambda item: item["club"].lower())
        for county, items in sorted(grouped.items())
    }


def counties_by_province(counties):
    grouped = {}
    for county, pages in counties.items():
        province = pages[0]["rows"][0]["Province"].strip() or "Other"
        grouped.setdefault(province, []).append((county, pages))
    return {
        province: sorted(items, key=lambda item: item[0])
        for province, items in grouped.items()
    }


def render_counties_index(counties):
    structured_data = county_index_schema(counties)
    province_groups = counties_by_province(counties)
    sections = []
    for province in PROVINCE_ORDER:
        if province not in province_groups:
            continue
        links = []
        for county, pages in province_groups[province]:
            search_text = f"{county} {province}"
            links.append(
                f"<li data-search=\"{esc_attr(search_text)}\"><a href=\"/{county_url(county)}\">{esc(county)}</a>"
                f"<span>{len(pages)} pitches</span></li>"
            )
        sections.append(
            f"<section class=\"county-province-group\" id=\"{county_slug(province)}\">"
            f"<h2>{esc(province)}</h2><ul>{''.join(links)}</ul></section>"
        )

    toc = "".join(
        f"<a href=\"#{county_slug(province)}\">{esc(province)}</a>"
        for province in PROVINCE_ORDER
        if province in province_groups
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GAA Pitches By County – GAA Pitch Finder</title>
<link rel="icon" type="image/png" href="../img/logo-icon.png">
<meta property="og:title" content="GAA Pitches By County – GAA Pitch Finder">
<meta property="og:description" content="Browse GAA pitch and club pages by county in Ireland.">
<meta property="og:image" content="https://gaapitchfinder.com/img/logo-black.png">
<meta property="og:url" content="https://gaapitchfinder.com/counties/">
<meta property="og:type" content="website">
<link rel="canonical" href="https://gaapitchfinder.com/counties/">
<meta name="description" content="Browse GAA pitch and club pages by county in Ireland.">
{structured_data}
{ga_snippet()}
<link rel="stylesheet" href="../css/style.css">
</head>
<body>

{nav_html()}

<div class="page-content" id="top">
  <p class="clubs-breadcrumb"><a href="/clubs/">Clubs</a> / Counties</p>
  <h1>GAA Pitches By County</h1>
  <p>Browse county pages for GAA clubs and pitches across Ireland, grouped by province. Each county page links through to recorded pitch coordinates and directions.</p>
  {directory_search_html("county-index-search", "Search counties or provinces")}
  <div class="club-directory-toc">{toc}</div>
  <section class="county-directory">
    {"".join(sections)}
  </section>
  <p class="directory-empty" id="county-index-empty" hidden>No matching counties found.</p>
</div>
{back_to_top_link()}

<footer class="site-footer">
  &copy; GAA Pitch Finder &nbsp;·&nbsp; <a href="mailto:gaapitchfinder@gmail.com">gaapitchfinder@gmail.com</a>
</footer>

{drawer_script()}
{directory_search_script("county-index-search", ".county-province-group li", "county-index-empty")}
</body>
</html>
"""


def render_county_page(county, pages):
    canonical_url = f"{SITE_BASE_URL}/{county_url(county)}"
    province = pages[0]["rows"][0]["Province"].strip()
    description = (
        f"Browse GAA pitches in {county}, with club pages, exact coordinates, "
        "small maps, and Google Maps directions."
    )
    structured_data = county_page_schema(county, pages, description)
    rows = []
    for page in pages:
        search_text = f"{page['club']} {page_pitch_label(page)} {county} {province}"
        rows.append(
            f"<li data-search=\"{esc_attr(search_text)}\"><a href=\"/{page['rel_url']}\">{esc(page['club'])}</a>"
            f"<span>{esc(page_pitch_label(page))}</span></li>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GAA Pitches In {esc(county)} – GAA Pitch Finder</title>
<link rel="icon" type="image/png" href="../img/logo-icon.png">
<meta property="og:title" content="GAA Pitches In {esc(county)} – GAA Pitch Finder">
<meta property="og:description" content="{esc(description)}">
<meta property="og:image" content="https://gaapitchfinder.com/img/logo-black.png">
<meta property="og:url" content="{esc(canonical_url)}">
<meta property="og:type" content="website">
<link rel="canonical" href="{esc(canonical_url)}">
<meta name="description" content="{esc(description)}">
{structured_data}
{ga_snippet()}
<link rel="stylesheet" href="../css/style.css">
</head>
<body>

{nav_html()}

<div class="page-content" id="top">
  <p class="clubs-breadcrumb"><a href="/clubs/">Clubs</a> / <a href="/counties/">Counties</a></p>
  <h1>GAA Pitches In {esc(county)}</h1>
  <p class="clubs-subtitle">{esc(province)} · Ireland</p>
  <p>{esc(description)}</p>
  {directory_search_html("county-page-search", f"Search clubs or pitches in {county}")}
  <section class="county-directory">
    <ul>{"".join(rows)}</ul>
  </section>
  <p class="directory-empty" id="county-page-empty" hidden>No matching pitches found.</p>
  <a href="/counties/" class="back-link">Browse all counties</a>
</div>
{back_to_top_link()}

<footer class="site-footer">
  &copy; GAA Pitch Finder &nbsp;·&nbsp; <a href="mailto:gaapitchfinder@gmail.com">gaapitchfinder@gmail.com</a>
</footer>

{drawer_script()}
{directory_search_script("county-page-search", ".county-directory li", "county-page-empty")}
</body>
</html>
"""


def lastmod_for_path(path):
    if path == "/":
        source_path = SITE_DIR / "index.html"
    else:
        source_path = SITE_DIR / path.lstrip("/")
    if source_path.exists():
        timestamp = source_path.stat().st_mtime
    else:
        timestamp = max(DATASET_PATH.stat().st_mtime, Path(__file__).stat().st_mtime)
    return datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()


def write_sitemap(pages, counties):
    urls = []
    for path, priority in STATIC_URLS:
        urls.append((path, f"{SITE_BASE_URL}{path}", priority))

    blog_dir = SITE_DIR / "blog"
    for blog_file in sorted(blog_dir.glob("*.html")):
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

    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, url, priority in urls:
        lines.append(
            f"  <url><loc>{html.escape(url)}</loc><lastmod>{lastmod_for_path(path)}</lastmod><priority>{priority:.1f}</priority></url>"
        )
    lines.append("</urlset>")
    (SITE_DIR / "sitemap.xml").write_text("\n".join(lines) + "\n")


def main():
    rows = load_rows()
    pages, _row_to_url = build_club_page_records(rows)
    counties = county_pages(pages)

    CLUBS_DIR.mkdir(parents=True, exist_ok=True)
    for old_file in CLUBS_DIR.glob("*.html"):
        old_file.unlink()
    COUNTIES_DIR.mkdir(parents=True, exist_ok=True)
    for old_file in COUNTIES_DIR.glob("*.html"):
        old_file.unlink()

    for page in pages:
        (CLUBS_DIR / f"{page['slug']}.html").write_text(render_club_page(page, pages))

    (CLUBS_DIR / "index.html").write_text(render_index_page(pages))
    (COUNTIES_DIR / "index.html").write_text(render_counties_index(counties))
    for county, county_page_records in counties.items():
        (COUNTIES_DIR / f"{county_slug(county)}.html").write_text(
            render_county_page(county, county_page_records)
        )
    write_sitemap(pages, counties)

    print(f"Generated {len(pages)} club pages → {CLUBS_DIR}")
    print(f"Generated club index → {CLUBS_DIR / 'index.html'}")
    print(f"Generated {len(counties)} county pages → {COUNTIES_DIR}")
    print(f"Generated sitemap → {SITE_DIR / 'sitemap.xml'}")


if __name__ == "__main__":
    main()
