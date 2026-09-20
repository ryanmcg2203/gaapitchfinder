#!/usr/bin/env python3
"""
Check which GAA clubs have matching OSM pitch polygons, county by county in parallel.

Usage:
    python3 scripts/analyze_osm_coverage.py               # all counties
    python3 scripts/analyze_osm_coverage.py Monaghan      # single county
    python3 scripts/analyze_osm_coverage.py Monaghan Down # multiple counties
"""

import csv
import math
import os
import sys
import time
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import urllib.request
import urllib.parse
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

ROOT_DIR = os.path.join(os.path.dirname(__file__), "..")
INPUT_CSV = os.path.join(ROOT_DIR, "gaapitchfinder_data.csv")
OUTPUT_CSV = os.path.join(ROOT_DIR, "data", "derived", "osm_coverage_report.csv")
OVERPASS_URL = "https://overpass.openstreetmap.fr/api/interpreter"
SEARCH_RADIUS_M = 200
REQUEST_DELAY_S = 1.5
REQUEST_TIMEOUT_S = 30
MAX_RETRIES = 3
RETRY_BACKOFF_S = 5

GAA_TAGS = {"gaelic_football", "hurling", "gaelic_games"}
LEGACY_FIELDS = ("Club", "County", "Province", "Latitude", "Longitude", "Status")
REPORT_FIELDS = (*LEGACY_FIELDS, "CheckedAt")
EVALUATED_STATUSES = {"matched_gaa", "matched_generic", "no_match"}
ALL_STATUSES = EVALUATED_STATUSES | {"api_error", "no_coords"}


def load_snapshot(path):
    """Read a known report schema without dropping unknown or malformed data."""
    with open(path, encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source, strict=True)
        if tuple(reader.fieldnames or ()) not in (LEGACY_FIELDS, REPORT_FIELDS):
            raise ValueError("Unsupported OSM snapshot columns; existing report was not changed")
        rows = []
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Malformed OSM snapshot row at line {reader.line_num}")
            if not row["County"].strip() or not row["Club"].strip() or row["Status"] not in ALL_STATUSES:
                raise ValueError(f"Invalid OSM snapshot identity/status at line {reader.line_num}")
            row.setdefault("CheckedAt", "")  # Legacy check dates are unknown.
            if row["CheckedAt"]:
                checked_at = datetime.fromisoformat(row["CheckedAt"])
                if checked_at.tzinfo is None:
                    raise ValueError(f"OSM check date needs a timezone at line {reader.line_num}")
            rows.append(row)
        if not rows:
            raise ValueError("OSM snapshot has no records; run a full refresh first")
        return rows


def merge_snapshot(existing, refreshed, counties):
    """Replace complete selected county partitions; never guess club identities.

    Each county is fully evaluated before publication. Replacing its partition
    handles removed/moved records and multiple pitches with the same club name.
    Unselected records, including their original check dates, are retained.
    """
    if any(row["County"].strip() not in counties for row in refreshed):
        raise ValueError("Refresh results contain an unrequested county")
    retained = [row for row in existing if row["County"].strip() not in counties]
    return sorted(retained + refreshed, key=lambda row: tuple(row.get(key, "") for key in (
        "County", "Club", "Latitude", "Longitude", "Province"
    )))


def write_snapshot(path, rows):
    """Publish the complete merged report with one atomic replacement."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as target:
            temporary = Path(target.name)
            writer = csv.DictWriter(target, fieldnames=REPORT_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


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
    except (ValueError, KeyError, TypeError):
        return club, "no_coords", False
    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
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
        result = {field: club.get(field, "") for field in LEGACY_FIELDS}
        result["Status"] = status
        result["CheckedAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        results.append(result)

    print(f"[{county}] Done — {matched}/{total} matched\n")
    return county, results


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    filter_counties = set(arguments) if arguments else None

    clubs_by_county = defaultdict(list)
    with open(INPUT_CSV, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            county = row.get("County", "").strip()
            if not county:
                continue
            clubs_by_county[county].append(row)

    if filter_counties:
        unknown = filter_counties - clubs_by_county.keys()
        if unknown:
            raise SystemExit(f"Unknown counties: {', '.join(sorted(unknown))}. No requests made or report changed.")
        if not Path(OUTPUT_CSV).exists():
            raise SystemExit("Partial refresh requires an existing OSM report. Run without county arguments first.")
        # Validate before any requests so an unmergeable report stays untouched.
        try:
            existing = load_snapshot(OUTPUT_CSV)
        except (ValueError, csv.Error, UnicodeError) as error:
            raise SystemExit(f"Cannot refresh existing OSM report: {error}") from error
        clubs_by_county = {county: clubs for county, clubs in clubs_by_county.items() if county in filter_counties}
    else:
        existing = []

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
    print("Percentages use evaluated rows; API errors and missing coordinates are unavailable.")
    print(f"{'County':<20} {'Matched':>8} {'Evaluated':>10} {'Unavailable':>12} {'%':>6}")
    print("-" * 46)
    grand_matched, grand_evaluated, grand_unavailable = 0, 0, 0
    for county, clubs in sorted(clubs_by_county.items(), key=lambda x: x[0]):
        results = all_results.get(county, [])
        total = len(results)
        matched = sum(row["Status"].startswith("matched") for row in results)
        evaluated = sum(row["Status"] in EVALUATED_STATUSES for row in results)
        unavailable = total - evaluated
        pct = f"{matched / evaluated * 100:.0f}%" if evaluated else "N/A"
        grand_matched += matched
        grand_evaluated += evaluated
        grand_unavailable += unavailable
        print(f"{county:<20} {matched:>8} {evaluated:>10} {unavailable:>12} {pct:>6}")
    print("-" * 46)
    percentage = f"{grand_matched / grand_evaluated * 100:.0f}%" if grand_evaluated else "N/A"
    print(f"{'TOTAL':<20} {grand_matched:>8} {grand_evaluated:>10} {grand_unavailable:>12} {percentage:>6}")

    refreshed = [row for results in all_results.values() for row in results]
    merged = merge_snapshot(existing, refreshed, set(clubs_by_county))
    write_snapshot(OUTPUT_CSV, merged)
    print(f"\n{len(refreshed)} refreshed rows; {len(merged) - len(refreshed)} retained rows. Report written to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
