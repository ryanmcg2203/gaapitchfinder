"""
Convert gaapitchfinder_data.csv to site/data.json for the Leaflet map.
Run from repo root: python3 scripts/generate_map_data.py
"""
import json
from site_build_utils import (
    SITE_DIR,
    build_club_page_records,
    load_rows,
    row_coordinates,
    row_file_value,
    row_maps_url,
    row_region,
    sanitized_external_url,
    ALLOWED_REFERENCE_HOSTS,
)


def build_map_records(rows):
    """Build the compact map payload without performing filesystem writes."""
    rows = list(rows)
    _page_records, row_to_url = build_club_page_records(rows)
    clubs = []
    skipped = 0

    for index, row in enumerate(rows):
        coordinates = row_coordinates(row)
        if not coordinates:
            skipped += 1
            continue

        latitude, longitude = coordinates
        file_value = row_file_value(row)
        location = (
            row["County"].strip()
            if file_value == "Ireland"
            else row["Country"].strip()
        )
        clubs.append(
            {
                "c": row["Club"].strip(),
                "p": row["Pitch"].strip(),
                "r": row_region(row),
                "k": location,
                "la": latitude,
                "lo": longitude,
                "d": row_maps_url(row),
                "u": row_to_url[index],
                "w": sanitized_external_url(row.get("Wikipedia"), ALLOWED_REFERENCE_HOSTS),
            }
        )

    return clubs, skipped


def main():
    clubs, skipped = build_map_records(load_rows())
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SITE_DIR / "data.json"
    with out_path.open("w") as output_file:
        json.dump(clubs, output_file, separators=(",", ":"))

    print(f"Generated {len(clubs)} clubs → {out_path}")
    if skipped:
        print(f"Skipped {skipped} rows (missing or invalid coordinates)")


if __name__ == "__main__":
    main()
