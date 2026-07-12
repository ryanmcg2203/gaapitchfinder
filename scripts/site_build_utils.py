from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Mapping
from urllib.parse import urlparse


ROOT_DIR = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT_DIR / "gaapitchfinder_data.csv"
SITE_DIR = ROOT_DIR / "site"
SITE_BASE_URL = "https://gaapitchfinder.com"
ALLOWED_DIRECTIONS_HOSTS = {"maps.google.com"}
ALLOWED_SOCIAL_HOSTS = {
    "twitter.com",
    "www.twitter.com",
    "x.com",
    "www.x.com",
    "instagram.com",
    "www.instagram.com",
}

REGION_MAP = {
    "Ireland": "Ireland",
    "Great Britain": "Great Britain",
    "USA": "North America",
    "Canada": "North America",
    "Europe": "Rest of Europe",
    "Australasia": "Australasia",
    "Asia": "Asia",
    "Middle East": "Middle East",
    "South America": "South America",
}


def load_rows() -> list[dict[str, str]]:
    with DATASET_PATH.open() as f:
        return list(csv.DictReader(f))


def row_file_value(row: Mapping[str, str]) -> str:
    return row["File"].strip()


def row_region(row: Mapping[str, str]) -> str:
    return REGION_MAP.get(row_file_value(row), row_file_value(row))


def row_location_label(row: Mapping[str, str]) -> str:
    file_val = row_file_value(row)
    if file_val == "Ireland":
        return row["County"].strip()
    return row["Country"].strip() or row["County"].strip()


def row_display_place(row: Mapping[str, str]) -> str:
    file_val = row_file_value(row)
    county = row["County"].strip()
    province = row["Province"].strip()
    country = row["Country"].strip()
    if file_val == "Ireland":
        parts = [part for part in [county, province, country] if part]
    else:
        division = row["Division"].strip()
        parts = [part for part in [country, division or county] if part]
    return ", ".join(dict.fromkeys(parts))


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug or "club"


def sanitized_external_url(value: str | None, allowed_hosts: set[str]) -> str:
    url = (value or "").strip()
    if not url:
        return ""

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return ""
    if not parsed.hostname or parsed.hostname.lower() not in allowed_hosts:
        return ""
    return url


def row_coordinates(row: Mapping[str, str]) -> tuple[float, float] | None:
    """Return valid numeric coordinates, or ``None`` for incomplete rows."""
    try:
        latitude = row["Latitude"].strip()
        longitude = row["Longitude"].strip()
        if not latitude or not longitude:
            return None
        return float(latitude), float(longitude)
    except (KeyError, AttributeError, ValueError):
        return None


def row_maps_url(row: Mapping[str, str]) -> str:
    """Return a safe directions URL, falling back to coordinates when possible."""
    directions_url = sanitized_external_url(
        row.get("Directions"), ALLOWED_DIRECTIONS_HOSTS
    )
    if directions_url:
        return directions_url

    coordinates = row_coordinates(row)
    if coordinates:
        return f"https://maps.google.com/?daddr={coordinates[0]},{coordinates[1]}"
    return "https://maps.google.com/"


def build_club_page_records(rows: Iterable[dict[str, str]]):
    grouped_rows = defaultdict(list)
    for index, row in enumerate(rows):
        key = (row["Club"].strip(), row_file_value(row), row_location_label(row))
        grouped_rows[key].append((index, row))

    used_slugs = set()
    page_records = []
    row_to_url = {}

    for key in sorted(grouped_rows):
        club, _file_val, location_label = key
        members = grouped_rows[key]
        slug_base = slugify(f"{club}-{location_label}")
        slug = slug_base
        suffix = 2
        while slug in used_slugs:
            slug = f"{slug_base}-{suffix}"
            suffix += 1
        used_slugs.add(slug)

        rel_url = f"clubs/{slug}.html"
        page_records.append(
            {
                "club": club,
                "location_label": location_label,
                "slug": slug,
                "rel_url": rel_url,
                "rows": [row for _, row in members],
            }
        )

        for row_index, _row in members:
            row_to_url[row_index] = rel_url

    return page_records, row_to_url
