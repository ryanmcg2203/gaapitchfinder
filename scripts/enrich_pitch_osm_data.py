#!/usr/bin/env python3
"""
Enrich GAA pitch centroid data with polygon geometry from OpenStreetMap.

Queries the Overpass API for each pitch centroid, extracts polygon corners,
and calculates pitch dimensions and orientation. Supports checkpoint/resume
so it can be re-run without re-querying already-processed rows.
"""

import csv
import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
INPUT_CSV = os.path.join(os.path.dirname(__file__), "..", "gaapitchfinder_data.csv")
OUTPUT_CSV = os.path.join(os.path.dirname(__file__), "..", "gaapitchfinder_data_with_geometry.csv")
CHECKPOINT_FILE = os.path.join(os.path.dirname(__file__), "..", ".osm_enrichment_checkpoint.json")

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
SEARCH_RADIUS_M = 200
REQUEST_DELAY_S = 1.5  # polite delay between API calls
REQUEST_TIMEOUT_S = 30
MAX_RETRIES = 3
RETRY_BACKOFF_S = 5

# New columns to add
NEW_COLUMNS = [
    "osm_way_id",
    "corner_nw_lat", "corner_nw_lon",
    "corner_ne_lat", "corner_ne_lon",
    "corner_se_lat", "corner_se_lon",
    "corner_sw_lat", "corner_sw_lon",
    "pitch_length_m", "pitch_width_m",
    "orientation_degrees",
    "geometry_source", "geometry_verified",
]


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    """Return distance in metres between two lat/lon points."""
    R = 6_371_000  # Earth radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def bearing(lat1, lon1, lat2, lon2):
    """Return initial bearing in degrees from point 1 to point 2."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlam = math.radians(lon2 - lon1)
    x = math.sin(dlam) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlam)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def oriented_bounding_box(coords):
    """
    Compute the minimum-area oriented bounding box for a set of 2-D points.

    Uses rotating calipers on the convex hull. Returns the 4 corner coords
    (as lat/lon pairs) of the OBB and the rotation angle.
    """
    pts = np.array(coords)

    # Approximate metres so the OBB works in metric space
    lat_center = pts[:, 0].mean()
    lon_scale = math.cos(math.radians(lat_center))
    scaled = np.column_stack([
        pts[:, 0] * 111_320,            # lat -> m (approx)
        pts[:, 1] * 111_320 * lon_scale  # lon -> m (approx)
    ])

    # Convex hull via gift-wrapping is fine for small point sets
    from scipy.spatial import ConvexHull  # noqa: local import to keep top-level light
    try:
        hull = ConvexHull(scaled)
    except Exception:
        return None
    hull_pts = scaled[hull.vertices]

    # Rotating calipers: test each edge angle
    best_area = float("inf")
    best_box = None
    best_angle = 0

    edges = np.diff(np.vstack([hull_pts, hull_pts[0:1]]), axis=0)
    for edge in edges:
        angle = math.atan2(edge[1], edge[0])
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        rot = np.array([[cos_a, sin_a], [-sin_a, cos_a]])
        rotated = hull_pts @ rot.T
        min_xy = rotated.min(axis=0)
        max_xy = rotated.max(axis=0)
        area = (max_xy[0] - min_xy[0]) * (max_xy[1] - min_xy[1])
        if area < best_area:
            best_area = area
            best_angle = angle
            # corners in rotated frame
            corners_rot = np.array([
                [min_xy[0], min_xy[1]],
                [max_xy[0], min_xy[1]],
                [max_xy[0], max_xy[1]],
                [min_xy[0], max_xy[1]],
            ])
            # rotate back
            inv_rot = np.array([[cos_a, -sin_a], [sin_a, cos_a]])
            best_box = corners_rot @ inv_rot.T

    if best_box is None:
        return None

    # Convert back to lat/lon
    box_latlon = np.column_stack([
        best_box[:, 0] / 111_320,
        best_box[:, 1] / (111_320 * lon_scale),
    ])

    return box_latlon, best_angle


def classify_corners(box_latlon):
    """
    Given 4 lat/lon corners, label them NW / NE / SE / SW.
    Returns dict with keys nw, ne, se, sw, each a (lat, lon) tuple.
    """
    pts = list(map(tuple, box_latlon))
    # Sort by latitude descending (north first), then by longitude
    north = sorted(pts, key=lambda p: -p[0])[:2]
    south = sorted(pts, key=lambda p: p[0])[:2]
    nw = min(north, key=lambda p: p[1])
    ne = max(north, key=lambda p: p[1])
    sw = min(south, key=lambda p: p[1])
    se = max(south, key=lambda p: p[1])
    return {"nw": nw, "ne": ne, "se": se, "sw": sw}


def compute_pitch_metrics(corners):
    """Return (length_m, width_m, orientation_degrees)."""
    nw, ne, se, sw = corners["nw"], corners["ne"], corners["se"], corners["sw"]
    side_north = haversine(*nw, *ne)
    side_east = haversine(*ne, *se)

    length = max(side_north, side_east)
    width = min(side_north, side_east)

    # Orientation = bearing along the long axis
    if side_north >= side_east:
        orient = bearing(*nw, *ne)
    else:
        orient = bearing(*ne, *se)

    return round(length, 1), round(width, 1), round(orient, 1)


def bbox_corners(coords):
    """Axis-aligned bounding box from a list of (lat, lon) coords."""
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    return [
        (max(lats), min(lons)),  # NW
        (max(lats), max(lons)),  # NE
        (min(lats), max(lons)),  # SE
        (min(lats), min(lons)),  # SW
    ]


# ---------------------------------------------------------------------------
# Overpass API query
# ---------------------------------------------------------------------------
def build_overpass_query(lat, lon, radius=SEARCH_RADIUS_M):
    """Build an Overpass QL query for GAA-related pitches near a point."""
    return f"""
[out:json][timeout:25];
(
  way["sport"="gaelic_football"](around:{radius},{lat},{lon});
  way["sport"="hurling"](around:{radius},{lat},{lon});
  way["sport"="gaelic_games"](around:{radius},{lat},{lon});
  way["leisure"="pitch"](around:{radius},{lat},{lon});
  relation["sport"="gaelic_football"](around:{radius},{lat},{lon});
  relation["sport"="hurling"](around:{radius},{lat},{lon});
  relation["sport"="gaelic_games"](around:{radius},{lat},{lon});
  relation["leisure"="pitch"](around:{radius},{lat},{lon});
);
out body;
>;
out skel qt;
"""


def query_overpass(lat, lon):
    """
    Query Overpass API. Returns list of elements or None on failure.
    Retries with exponential back-off on transient errors.
    """
    query = build_overpass_query(lat, lon)
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(
                OVERPASS_URL,
                data={"data": query},
                timeout=REQUEST_TIMEOUT_S,
            )
            if resp.status_code == 429:
                wait = RETRY_BACKOFF_S * (2 ** attempt)
                print(f"    Rate limited, waiting {wait}s …")
                time.sleep(wait)
                continue
            if resp.status_code == 504:
                wait = RETRY_BACKOFF_S * (2 ** attempt)
                print(f"    Gateway timeout, retrying in {wait}s …")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json().get("elements", [])
        except requests.exceptions.Timeout:
            wait = RETRY_BACKOFF_S * (2 ** attempt)
            print(f"    Timeout (attempt {attempt + 1}/{MAX_RETRIES}), retrying in {wait}s …")
            time.sleep(wait)
        except requests.exceptions.RequestException as exc:
            wait = RETRY_BACKOFF_S * (2 ** attempt)
            print(f"    Request error: {exc} (attempt {attempt + 1}/{MAX_RETRIES}), retrying in {wait}s …")
            time.sleep(wait)
    return None


def pick_best_element(elements, centroid_lat, centroid_lon):
    """
    From Overpass results, pick the way/relation whose centroid is closest
    to our known centroid. Prefer GAA-specific sport tags over generic
    leisure=pitch. Returns (element, node_lookup) or (None, None).
    """
    if not elements:
        return None, None

    node_lookup = {}
    ways = []
    for el in elements:
        if el["type"] == "node":
            node_lookup[el["id"]] = (el["lat"], el["lon"])
        elif el["type"] == "way" and "nodes" in el:
            ways.append(el)

    if not ways:
        return None, None

    gaa_tags = {"gaelic_football", "hurling", "gaelic_games"}

    def score(way):
        """Lower is better. GAA-specific tags get priority, then distance."""
        tags = way.get("tags", {})
        sport = tags.get("sport", "")
        is_gaa = sport in gaa_tags
        # Compute centroid of way nodes
        coords = [node_lookup[nid] for nid in way["nodes"] if nid in node_lookup]
        if not coords:
            return (1, 1e9)
        avg_lat = sum(c[0] for c in coords) / len(coords)
        avg_lon = sum(c[1] for c in coords) / len(coords)
        dist = haversine(centroid_lat, centroid_lon, avg_lat, avg_lon)
        return (0 if is_gaa else 1, dist)

    ways.sort(key=score)
    return ways[0], node_lookup


def extract_geometry(way, node_lookup):
    """
    Extract corner coordinates from a way. Returns (corners_dict, source)
    where source is 'osm_polygon' (OBB from polygon nodes) or 'osm_bbox'.
    """
    coords = [(node_lookup[nid][0], node_lookup[nid][1])
              for nid in way["nodes"] if nid in node_lookup]

    if len(coords) < 3:
        return None, "not_found"

    # Try oriented bounding box first
    try:
        result = oriented_bounding_box(coords)
        if result is not None:
            box_latlon, _ = result
            corners = classify_corners(box_latlon)
            return corners, "osm_polygon"
    except Exception:
        pass

    # Fall back to axis-aligned bounding box
    bbox = bbox_corners(coords)
    box_arr = np.array(bbox)
    corners = classify_corners(box_arr)
    return corners, "osm_bbox"


# ---------------------------------------------------------------------------
# Checkpoint logic
# ---------------------------------------------------------------------------
def load_checkpoint():
    """Load set of already-processed row indices."""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            data = json.load(f)
            return set(data.get("processed_indices", []))
    return set()


def save_checkpoint(processed_indices):
    """Persist processed row indices."""
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump({"processed_indices": sorted(processed_indices)}, f)


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------
def main():
    # Ensure scipy is available (needed for ConvexHull)
    try:
        from scipy.spatial import ConvexHull  # noqa
    except ImportError:
        print("Installing scipy …")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "scipy", "-q"])

    print("Loading input data …")
    df = pd.read_csv(INPUT_CSV)
    total = len(df)
    print(f"  {total} pitches loaded.")

    # If output file already exists, load it to preserve previous results
    if os.path.exists(OUTPUT_CSV):
        df_out = pd.read_csv(OUTPUT_CSV)
        # Ensure all new columns exist
        for col in NEW_COLUMNS:
            if col not in df_out.columns:
                df_out[col] = ""
        print(f"  Resuming from existing output file ({len(df_out)} rows).")
    else:
        df_out = df.copy()
        for col in NEW_COLUMNS:
            df_out[col] = ""

    processed = load_checkpoint()
    remaining = [i for i in range(total) if i not in processed]
    print(f"  {len(processed)} already processed, {len(remaining)} remaining.\n")

    matched = 0
    not_found = 0
    errors = 0

    # Count previously processed results
    for i in processed:
        src = df_out.at[i, "geometry_source"] if i < len(df_out) else ""
        if src in ("osm_polygon", "osm_bbox"):
            matched += 1
        else:
            not_found += 1

    for count, idx in enumerate(remaining, 1):
        row = df.iloc[idx]
        club = row.get("Club", "")
        county = row.get("County", "")
        lat = row.get("Latitude")
        lon = row.get("Longitude")

        print(f"[{count}/{len(remaining)}] {club} ({county}) …", end=" ", flush=True)

        # Skip rows without coordinates
        if pd.isna(lat) or pd.isna(lon):
            print("SKIP (no coordinates)")
            df_out.at[idx, "geometry_source"] = "not_found"
            df_out.at[idx, "geometry_verified"] = False
            processed.add(idx)
            not_found += 1
            if count % 10 == 0:
                save_checkpoint(processed)
                df_out.to_csv(OUTPUT_CSV, index=False)
            continue

        lat, lon = float(lat), float(lon)

        # Query Overpass
        elements = query_overpass(lat, lon)
        if elements is None:
            print("ERROR (API failure)")
            errors += 1
            # Don't mark as processed so it can be retried
            time.sleep(REQUEST_DELAY_S)
            continue

        way, node_lookup = pick_best_element(elements, lat, lon)
        if way is None:
            print("not found")
            df_out.at[idx, "geometry_source"] = "not_found"
            df_out.at[idx, "geometry_verified"] = False
            processed.add(idx)
            not_found += 1
        else:
            corners, source = extract_geometry(way, node_lookup)
            if corners is None:
                print("not found (bad geometry)")
                df_out.at[idx, "geometry_source"] = "not_found"
                df_out.at[idx, "geometry_verified"] = False
                processed.add(idx)
                not_found += 1
            else:
                length, width, orient = compute_pitch_metrics(corners)
                df_out.at[idx, "osm_way_id"] = way["id"]
                df_out.at[idx, "corner_nw_lat"] = round(corners["nw"][0], 7)
                df_out.at[idx, "corner_nw_lon"] = round(corners["nw"][1], 7)
                df_out.at[idx, "corner_ne_lat"] = round(corners["ne"][0], 7)
                df_out.at[idx, "corner_ne_lon"] = round(corners["ne"][1], 7)
                df_out.at[idx, "corner_se_lat"] = round(corners["se"][0], 7)
                df_out.at[idx, "corner_se_lon"] = round(corners["se"][1], 7)
                df_out.at[idx, "corner_sw_lat"] = round(corners["sw"][0], 7)
                df_out.at[idx, "corner_sw_lon"] = round(corners["sw"][1], 7)
                df_out.at[idx, "pitch_length_m"] = length
                df_out.at[idx, "pitch_width_m"] = width
                df_out.at[idx, "orientation_degrees"] = orient
                df_out.at[idx, "geometry_source"] = source
                df_out.at[idx, "geometry_verified"] = False
                processed.add(idx)
                matched += 1
                print(f"OK ({source}, {length}x{width}m, {orient}°)")

        # Periodic save
        if count % 10 == 0:
            save_checkpoint(processed)
            df_out.to_csv(OUTPUT_CSV, index=False)

        # Polite delay
        time.sleep(REQUEST_DELAY_S)

    # Final save
    save_checkpoint(processed)
    df_out.to_csv(OUTPUT_CSV, index=False)

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------
    total_processed = matched + not_found
    match_rate = (matched / total_processed * 100) if total_processed > 0 else 0

    print("\n" + "=" * 60)
    print("ENRICHMENT SUMMARY")
    print("=" * 60)
    print(f"  Total pitches:       {total}")
    print(f"  Processed:           {total_processed}")
    print(f"  Matched (OSM):       {matched}")
    print(f"  Not found:           {not_found}")
    print(f"  API errors (retry):  {errors}")
    print(f"  Match rate:          {match_rate:.1f}%")
    print(f"\n  Output: {os.path.abspath(OUTPUT_CSV)}")
    if errors > 0:
        print(f"\n  ⚠ {errors} rows had API errors and were NOT marked processed.")
        print("    Re-run the script to retry them.")
    print("=" * 60)


if __name__ == "__main__":
    main()
