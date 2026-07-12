"""
Convert gaapitchfinder_data.csv to site/data.json for the Leaflet map.
Run from repo root: python3 scripts/generate_map_data.py
"""
import json
from site_build_utils import (
    ALLOWED_DIRECTIONS_HOSTS,
    SITE_DIR,
    build_club_page_records,
    load_rows,
    row_file_value,
    row_region,
    sanitized_external_url,
)

clubs = []
skipped = 0

rows = load_rows()
_page_records, row_to_url = build_club_page_records(rows)

for index, row in enumerate(rows):
    lat = row["Latitude"].strip()
    lng = row["Longitude"].strip()
    if not lat or not lng:
        skipped += 1
        continue
    try:
        lat = float(lat)
        lng = float(lng)
    except ValueError:
        skipped += 1
        continue

    file_val = row_file_value(row)
    county = row["County"].strip() if file_val == "Ireland" else row["Country"].strip()
    directions_url = sanitized_external_url(row["Directions"], ALLOWED_DIRECTIONS_HOSTS)
    if not directions_url:
        directions_url = f"https://maps.google.com/?daddr={lat},{lng}"

    clubs.append({
        "c": row["Club"].strip(),
        "p": row["Pitch"].strip(),
        "r": row_region(row),
        "k": county,
        "la": lat,
        "lo": lng,
        "d": directions_url,
        "u": row_to_url[index],
    })

SITE_DIR.mkdir(parents=True, exist_ok=True)
out_path = SITE_DIR / "data.json"
with out_path.open("w") as f:
    json.dump(clubs, f, separators=(',', ':'))

print(f'Generated {len(clubs)} clubs → {out_path}')
if skipped:
    print(f'Skipped {skipped} rows (missing coordinates)')
