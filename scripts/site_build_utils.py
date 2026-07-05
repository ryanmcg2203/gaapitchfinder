from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT_DIR / "gaapitchfinder_data.csv"
SITE_DIR = ROOT_DIR / "site"
SITE_BASE_URL = "https://gaapitchfinder.com"

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


def load_rows():
    with DATASET_PATH.open() as f:
        return list(csv.DictReader(f))


def row_file_value(row):
    return row["File"].strip()


def row_region(row):
    return REGION_MAP.get(row_file_value(row), row_file_value(row))


def row_location_label(row):
    file_val = row_file_value(row)
    if file_val == "Ireland":
        return row["County"].strip()
    return row["Country"].strip() or row["County"].strip()


def row_display_place(row):
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


def slugify(value):
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug or "club"


def build_club_page_records(rows):
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
