"""
Convert gaapitchfinder_data.csv to map/data.json for the Leaflet map.
Run from repo root: python scripts/generate_map_data.py
"""
import csv
import json
import os

REGION_MAP = {
    'Ireland': 'Ireland',
    'Great Britain': 'Great Britain',
    'USA': 'North America',
    'Canada': 'North America',
    'Europe': 'Rest of Europe',
    'Australasia': 'Australasia',
    'Asia': 'Asia',
    'Middle East': 'Middle East',
    'South America': 'South America',
}

clubs = []
skipped = 0

with open('gaapitchfinder_data.csv') as f:
    for row in csv.DictReader(f):
        lat = row['Latitude'].strip()
        lng = row['Longitude'].strip()
        if not lat or not lng:
            skipped += 1
            continue
        try:
            lat = float(lat)
            lng = float(lng)
        except ValueError:
            skipped += 1
            continue

        file_val = row['File'].strip()
        region = REGION_MAP.get(file_val, file_val)

        # County/Country filter: use County for Ireland, Country for overseas
        county = row['County'].strip() if file_val == 'Ireland' else row['Country'].strip()

        clubs.append({
            'c': row['Club'].strip(),
            'p': row['Pitch'].strip(),
            'r': region,
            'k': county,
            'la': lat,
            'lo': lng,
            'd': row['Directions'].strip(),
        })

os.makedirs('map', exist_ok=True)
out_path = 'map/data.json'
with open(out_path, 'w') as f:
    json.dump(clubs, f, separators=(',', ':'))

print(f'Generated {len(clubs)} clubs → {out_path}')
if skipped:
    print(f'Skipped {skipped} rows (missing coordinates)')
