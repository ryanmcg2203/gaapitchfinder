#!/usr/bin/env python3
"""
Check which GAA clubs have matching OSM pitch polygons, county by county in parallel.

Usage:
    python3 scripts/check_osm_coverage.py               # all counties
    python3 scripts/check_osm_coverage.py Monaghan      # single county
    python3 scripts/check_osm_coverage.py Monaghan Down # multiple counties
"""

import csv
import math
import sys
import time
import json
import urllib.request
import urllib.parse
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

INPUT_CSV = "gaapitchfinder_data.csv"
OVERPASS_URL = "https://overpass.openstreetmap.fr/api/interpreter"
SEARCH_RADIUS_M = 200
REQUEST_DELAY_S = 1.5
REQUEST_TIMEOUT_S = 30
MAX_RETRIES = 3
RETRY_BACKOFF_S = 5

GAA_TAGS = {"gaelic_football", "hurling", "gaelic_games"}


def build_query(lat, lon):
    return f"""[out:json][timeout:25];
(
  way["sport"~"gaelic_football"](around:{SEARCH_RADIUS_M},{lat},{lon});
  way["sport"~"hurling"](around:{SEARCH_RADIUS_M},{lat},{lon});
  way["sport"~"gaelic_games"](around:{SEARCH_RADIUS_M},{lat},{lon});
  way["leisure"="pitch"](around:{SEARCH_RADIUS_M},{lat},{lon});
);
out body;
>;
out skel qt;
"""


def query_overpass(lat, lon):
    query = build_query(lat, lon)
    data = urllib.parse.urlencode({"data": query}).encode()
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(OVERPASS_URL, data=data, headers={"User-Agent": "gaapitchfinder/1.0 (https://github.com/ryanmcg2203/gaapitchfinder)"})
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
                return json.loads(resp.read()).get("elements", [])
        except urllib.error.HTTPError as e:
            if e.code in (429, 504):
                wait = RETRY_BACKOFF_S * (2 ** attempt)
                time.sleep(wait)
                continue
            return None
        except Exception:
            wait = RETRY_BACKOFF_S * (2 ** attempt)
            time.sleep(wait)
    return None


def has_match(elements):
    """Returns (matched: bool, gaa_tagged: bool)"""
    if not elements:
        return False, False
    ways = [e for e in elements if e["type"] == "way" and "nodes" in e]
    if not ways:
        return False, False
    for way in ways:
        sport = way.get("tags", {}).get("sport", "")
        if any(tag in sport for tag in GAA_TAGS):
            return True, True
    return True, False  # matched but only via generic leisure=pitch


def check_club(club):
    try:
        lat = float(club["Latitude"])
        lon = float(club["Longitude"])
    except (ValueError, KeyError):
        return club, "no_coords", False

    time.sleep(REQUEST_DELAY_S)
    elements = query_overpass(lat, lon)

    if elements is None:
        return club, "api_error", False

    matched, gaa_tagged = has_match(elements)
    if matched and gaa_tagged:
        status = "matched_gaa"
    elif matched:
        status = "matched_generic"
    else:
        status = "no_match"

    return club, status, matched


def check_county(county, clubs):
    results = []
    total = len(clubs)
    matched = 0

    print(f"[{county}] Starting — {total} clubs")

    for i, club in enumerate(clubs, 1):
        club, status, ok = check_club(club)
        if ok:
            matched += 1
        icon = "✓" if status == "matched_gaa" else ("~" if status == "matched_generic" else "✗")
        print(f"  [{county}] {icon} {club['Club']} — {status}")
        results.append((club, status))

    print(f"[{county}] Done — {matched}/{total} matched\n")
    return county, results


def main():
    filter_counties = set(sys.argv[1:]) if len(sys.argv) > 1 else None

    clubs_by_county = defaultdict(list)
    with open(INPUT_CSV) as f:
        for row in csv.DictReader(f):
            county = row.get("County", "").strip()
            if not county:
                continue
            if filter_counties and county not in filter_counties:
                continue
            clubs_by_county[county].append(row)

    if not clubs_by_county:
        print("No matching counties found.")
        sys.exit(1)

    # Sort counties by size so small ones finish first
    ordered = sorted(clubs_by_county.items(), key=lambda x: len(x[1]))

    print(f"Checking {sum(len(v) for v in clubs_by_county.values())} clubs across {len(clubs_by_county)} counties\n")

    all_results = {}

    # Run counties in parallel (max 3 at once to be polite to Overpass)
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(check_county, county, clubs): county for county, clubs in ordered}
        for future in as_completed(futures):
            county, results = future.result()
            all_results[county] = results

    # Summary
    print("\n=== SUMMARY ===")
    print(f"{'County':<20} {'Matched':>8} {'Total':>8} {'%':>6}")
    print("-" * 46)
    grand_matched, grand_total = 0, 0
    for county, clubs in sorted(clubs_by_county.items(), key=lambda x: x[0]):
        results = all_results.get(county, [])
        total = len(results)
        matched = sum(1 for _, s in results if s.startswith("matched"))
        pct = (matched / total * 100) if total else 0
        grand_matched += matched
        grand_total += total
        print(f"{county:<20} {matched:>8} {total:>8} {pct:>5.0f}%")
    print("-" * 46)
    print(f"{'TOTAL':<20} {grand_matched:>8} {grand_total:>8} {(grand_matched/grand_total*100) if grand_total else 0:>5.0f}%")

    # Write no-match list to CSV
    output_file = "osm_coverage_report.csv"
    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Club", "County", "Province", "Latitude", "Longitude", "Status"])
        for county, results in sorted(all_results.items()):
            for club, status in results:
                writer.writerow([club["Club"], club["County"], club.get("Province", ""),
                                 club["Latitude"], club["Longitude"], status])

    print(f"\nFull results written to {output_file}")


if __name__ == "__main__":
    main()
