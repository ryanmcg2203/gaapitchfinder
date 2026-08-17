"""HTML templates and presentation helpers for club and county pages."""

from __future__ import annotations

import json
from urllib.parse import quote

from site_builder.page_data import (
    counties_by_province,
    county_pages,
    county_slug,
    county_url,
    directory_initial,
    haversine_km,
    ireland_county,
    page_coordinates,
    page_description,
    page_pitch_label,
    page_title,
    place_address,
)
from site_builder.shared import (
    absolute_url,
    analytics_html,
    esc,
    esc_attr,
    footer_html,
    navigation_html,
    navigation_script_html,
)
from site_build_utils import (
    ALLOWED_REFERENCE_HOSTS,
    ALLOWED_SOCIAL_HOSTS,
    SITE_BASE_URL,
    row_coordinates,
    row_display_place,
    row_maps_url,
    row_region,
    sanitized_external_url,
)


PROVINCE_ORDER = ["Connacht", "Leinster", "Munster", "Ulster"]


def correction_mailto(row, page):
    pitch = row["Pitch"].strip()
    location = row_display_place(row)
    lat, lon = row_coordinates(row)
    subject = f"Correction for {page['club']}"
    body = "\n".join(
        [
            "Hi Ryan,",
            "",
            "I noticed a possible correction for this GAA Pitch Finder entry:",
            "",
            f"Club: {page['club']}",
            f"Pitch: {pitch}",
            f"Location: {location}",
            f"Coordinates: {lat:.6f}, {lon:.6f}",
            f"Page: {absolute_url(page['rel_url'])}",
            "",
            "Suggested correction:",
            "",
        ]
    )
    return f"mailto:gaapitchfinder@gmail.com?subject={quote(subject, safe='')}&body={quote(body, safe='')}"


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


def directory_search_html(input_id, placeholder, label="Search"):
    return f"""
<div class="directory-search">
  <label for="{esc_attr(input_id)}">{esc(label)}</label>
  <input id="{esc_attr(input_id)}" type="search" placeholder="{esc_attr(placeholder)}" autocomplete="off">
</div>
""".strip()


def directory_search_script(input_id, item_selector, empty_id):
    return (
        '<script src="/js/directory-search.js" defer '
        f'data-input-id="{esc_attr(input_id)}" '
        f'data-item-selector="{esc_attr(item_selector)}" '
        f'data-empty-id="{esc_attr(empty_id)}"></script>'
    )


def back_to_top_link():
    return '<a href="#top" class="back-to-top" aria-label="Back to top">Back to top</a>'


def icon_svg(name):
    icons = {
        "map": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2C8.1 2 5 5.1 5 9c0 5.2 7 13 7 13s7-7.8 7-13c0-3.9-3.1-7-7-7Zm0 9.4A2.4 2.4 0 1 1 12 6.6a2.4 2.4 0 0 1 0 4.8Z"/></svg>',
        "reference": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4.5A2.5 2.5 0 0 1 7.5 2H20v17H7.5A2.5 2.5 0 0 0 5 21.5v-17Zm2.5-.5a.5.5 0 0 0-.5.5v12.6c.2-.1.3-.1.5-.1H18V4H7.5Zm2 3H16v2H9.5V7Zm0 4H16v2H9.5v-2Z"/></svg>',
        "x": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M17.5 3h3.1l-6.8 7.8 8 10.2h-6.3l-4.9-6.3L5 21H1.9l7.3-8.3L1.5 3h6.4l4.4 5.7L17.5 3Zm-1.1 16.2h1.7L7 4.7H5.2l11.2 14.5Z"/></svg>',
        "correction": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 17.3V20h2.7L17.8 8.9l-2.7-2.7L4 17.3ZM19.7 7c.4-.4.4-1 0-1.4l-1.3-1.3a1 1 0 0 0-1.4 0l-1 1 2.7 2.7 1-1Z"/></svg>',
    }
    return icons[name]


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
    wikipedia = sanitized_external_url(row.get("Wikipedia"), ALLOWED_REFERENCE_HOSTS)
    if wikipedia:
        place["sameAs"] = [wikipedia]
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
        wikipedia = sanitized_external_url(row.get("Wikipedia"), ALLOWED_REFERENCE_HOSTS)
        actions = [
            f"<a class=\"club-action club-action-primary\" href=\"{esc_attr(maps_url)}\" target=\"_blank\" rel=\"noopener noreferrer\">{icon_svg('map')}<span>Google Maps Directions</span></a>"
        ]
        if wikipedia:
            actions.append(
                f"<a class=\"club-action club-action-reference\" href=\"{esc_attr(wikipedia)}\" target=\"_blank\" rel=\"noopener noreferrer\">{icon_svg('reference')}<span>Wikipedia</span></a>"
            )
        if twitter:
            actions.append(
                f"<a class=\"club-action\" href=\"{esc_attr(twitter)}\" target=\"_blank\" rel=\"noopener noreferrer\">{icon_svg('x')}<span>X / Twitter</span></a>"
            )
        actions.append(
            f"<a class=\"club-action club-action-muted\" href=\"{esc_attr(correction_mailto(row, page))}\">{icon_svg('correction')}<span>Report a correction</span></a>"
        )

        rows_html.append(
            f"""
<section class="club-entry">
  <h2>{esc(pitch)}</h2>
  <p class="club-place">{esc(place)}</p>
  {map_html(row, f"club-map-{row_index}")}
  <div class="club-actions">
    {"".join(actions)}
  </div>
  <ul class="club-detail-list">
    {row_details_html(row)}
  </ul>
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
{analytics_html()}
<link rel="stylesheet" href="../css/style.css">
</head>
<body>

{navigation_html("clubs")}

<div class="page-content">
  <p class="clubs-breadcrumb">{breadcrumb}</p>
  <h1>{esc(page["club"])}</h1>
  <p class="clubs-subtitle">{esc(page["location_label"])} · {esc(row_region(page["rows"][0]))}</p>
  <p>Find pitch information for {esc(page["club"])}, including location details, coordinates, and Google Maps directions from the open GAA Pitch Finder dataset.</p>
  {body}
  {context_html}
  <a href="/directions.html" class="back-link">Browse all directions</a>
</div>

{footer_html()}

<script src="../vendor/leaflet.js"></script>
<script src="/js/club-maps.js"></script>
{navigation_script_html()}
</body>
</html>
"""


def render_index_page(pages):
    structured_data = club_index_schema(pages)
    groups = {}
    for page in pages:
        initial = directory_initial(page["club"])
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
{analytics_html()}
<link rel="stylesheet" href="../css/style.css">
</head>
<body>

{navigation_html("clubs")}

<div class="page-content" id="top">
  <h1>Club Directory</h1>
  <p>Browse static GAA club and pitch pages for Ireland and the worldwide Gaelic games community. Each page includes recorded pitch details, coordinates, county or region information, and Google Maps directions from the open GAA Pitch Finder dataset.</p>
  {directory_search_html("club-directory-search", "Search clubs, counties, or countries")}
  <div class="club-directory-toc">{toc}</div>
  {"".join(sections)}
  <p class="directory-empty" id="club-directory-empty" hidden>No matching clubs found.</p>
</div>
{back_to_top_link()}

{footer_html()}

{navigation_script_html()}
{directory_search_script("club-directory-search", ".club-directory-group li", "club-directory-empty")}
</body>
</html>
"""


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
{analytics_html()}
<link rel="stylesheet" href="../css/style.css">
</head>
<body>

{navigation_html("counties")}

<div class="page-content" id="top">
  <p class="clubs-breadcrumb"><a href="/clubs/">Clubs</a> / Counties</p>
  <h1>GAA Pitches By County</h1>
  <p>Browse county pages for GAA clubs and pitches across Ireland, grouped by province. Each county page links through to club pages with recorded pitch coordinates, location details, and Google Maps directions.</p>
  {directory_search_html("county-index-search", "Search counties or provinces")}
  <div class="club-directory-toc">{toc}</div>
  <section class="county-directory">
    {"".join(sections)}
  </section>
  <p class="directory-empty" id="county-index-empty" hidden>No matching counties found.</p>
</div>
{back_to_top_link()}

{footer_html()}

{navigation_script_html()}
{directory_search_script("county-index-search", ".county-province-group li", "county-index-empty")}
</body>
</html>
"""


def render_county_page(county, pages):
    canonical_url = f"{SITE_BASE_URL}/{county_url(county)}"
    province = pages[0]["rows"][0]["Province"].strip()
    description = (
        f"Find GAA clubs and pitches in {county}, with club pages, exact coordinates, "
        "location details, small maps, and Google Maps directions."
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
{analytics_html()}
<link rel="stylesheet" href="../css/style.css">
</head>
<body>

{navigation_html("counties")}

<div class="page-content" id="top">
  <p class="clubs-breadcrumb"><a href="/clubs/">Clubs</a> / <a href="/counties/">Counties</a></p>
  <h1>GAA Pitches In {esc(county)}</h1>
  <p class="clubs-subtitle">{esc(province)} · Ireland</p>
  <p>{esc(description)} This county directory is generated from the open GAA Pitch Finder dataset.</p>
  {directory_search_html("county-page-search", f"Search clubs or pitches in {county}")}
  <section class="county-directory">
    <ul>{"".join(rows)}</ul>
  </section>
  <p class="directory-empty" id="county-page-empty" hidden>No matching pitches found.</p>
  <a href="/counties/" class="back-link">Browse all counties</a>
</div>
{back_to_top_link()}

{footer_html()}

{navigation_script_html()}
{directory_search_script("county-page-search", ".county-directory li", "county-page-empty")}
</body>
</html>
"""
