"""Page-level data shaping for club and county templates."""

from __future__ import annotations

import math
import unicodedata

from site_build_utils import row_coordinates, row_display_place, slugify


def directory_initial(value):
    if not value:
        return "#"
    normalized = unicodedata.normalize("NFKD", value[0])
    ascii_initial = normalized.encode("ascii", "ignore").decode("ascii").upper()
    if ascii_initial and ascii_initial[0].isalpha():
        return ascii_initial[0]
    return "#"


def page_coordinates(page):
    coordinates = [row_coordinates(row) for row in page["rows"]]
    coordinates = [coordinate for coordinate in coordinates if coordinate]
    if not coordinates:
        return None
    return (
        sum(coordinate[0] for coordinate in coordinates) / len(coordinates),
        sum(coordinate[1] for coordinate in coordinates) / len(coordinates),
    )


def page_pitch_label(page):
    pitch_names = [
        row["Pitch"].strip() for row in page["rows"] if row["Pitch"].strip()
    ]
    if pitch_names:
        label = ", ".join(pitch_names[:2])
        if len(pitch_names) > 2:
            label += f", +{len(pitch_names) - 2} more"
        return label
    coordinates = page_coordinates(page)
    if coordinates:
        return f"{coordinates[0]:.6f}, {coordinates[1]:.6f}"
    return row_display_place(page["rows"][0])


def haversine_km(origin, target):
    lat1, lon1 = origin
    lat2, lon2 = target
    radius = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    value = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def county_slug(county):
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
            "coordinates, and Google Maps directions."
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
