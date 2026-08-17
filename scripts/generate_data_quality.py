#!/usr/bin/env python3
"""Generate the public dataset health and provenance report."""

from __future__ import annotations

import csv
import html
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Mapping

from build_metadata import GitBuildMetadata
from dataset_contract import DatasetMetadata, build_dataset_metadata
from site_builder.shared import (
    REPOSITORY_URL,
    analytics_html,
    footer_html,
    navigation_html,
    navigation_script_html,
)
from site_build_utils import DATASET_PATH, ROOT_DIR, SITE_DIR, load_rows
from validate_dataset import (
    ALLOWED_DIRECTIONS_HOSTS,
    ALLOWED_WIKIPEDIA_HOSTS,
    DIRECTIONS_COORDINATE_TOLERANCE,
    OPTIONAL_NUMERIC_RULES,
    parse_directions_coordinates,
    parse_finite_number,
    validate_url,
)


CONTRACT_VERSION = "1.0.0"
METHOD_VERSION = "1.0.0"
OSM_COVERAGE_PATH = ROOT_DIR / "data" / "derived" / "osm_coverage_report.csv"
REPORT_JSON_PATH = SITE_DIR / "data-quality.json"
REPORT_HTML_PATH = SITE_DIR / "data-quality.html"
REQUIRED_IDENTITY_LOCATION_FIELDS = (
    "File",
    "Club",
    "Province",
    "Country",
    "Division",
    "County",
)
OSM_MATCHED_STATUSES = {"matched_gaa", "matched_generic"}
OSM_EVALUATED_STATUSES = {*OSM_MATCHED_STATUSES, "no_match"}


def _percentage(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator * 100, 1)


def _metric(
    metric_id: str,
    label: str,
    value: int | float | None,
    unit: str,
    status: str,
    source_id: str,
    data_as_of: str | None,
    method: str,
    summary: str,
    *,
    numerator: int | None = None,
    denominator: int | None = None,
    threshold: dict | None = None,
    limitation: str | None = None,
    details: dict | None = None,
) -> dict:
    return {
        "metric_id": metric_id,
        "label": label,
        "value": value,
        "unit": unit,
        "numerator": numerator,
        "denominator": denominator,
        "percentage": (
            _percentage(numerator, denominator)
            if numerator is not None and denominator is not None
            else None
        ),
        "status": status,
        "threshold": threshold,
        "source_id": source_id,
        "data_as_of": data_as_of,
        "method": method,
        "summary": summary,
        "limitation": limitation,
        "details": details or {},
    }


def _source_url(revision: str, path: str) -> str:
    return f"{REPOSITORY_URL}/blob/{revision}/{path}"


def _source(
    source_id: str,
    source_type: str,
    path: str,
    data_as_of: str | None,
    revision: str | None,
    *,
    available: bool,
    limitation: str | None = None,
) -> dict:
    return {
        "source_id": source_id,
        "type": source_type,
        "path": path,
        "url": _source_url(revision, path) if revision else None,
        "data_as_of": data_as_of,
        "revision": revision,
        "available": available,
        "limitation": limitation,
    }


def _valid_coordinates(row: Mapping[str, str]) -> tuple[float, float] | None:
    try:
        latitude = parse_finite_number((row.get("Latitude") or "").strip())
        longitude = parse_finite_number((row.get("Longitude") or "").strip())
    except ValueError:
        return None
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return None
    return latitude, longitude


def _directions_are_valid(row: Mapping[str, str]) -> bool:
    directions = (row.get("Directions") or "").strip()
    coordinates = _valid_coordinates(row)
    if not directions or coordinates is None:
        return False
    if validate_url(directions, ALLOWED_DIRECTIONS_HOSTS):
        return False
    try:
        directions_coordinates = parse_directions_coordinates(directions)
    except ValueError:
        return False
    return all(
        abs(link_value - row_value) <= DIRECTIONS_COORDINATE_TOLERANCE
        for link_value, row_value in zip(directions_coordinates, coordinates)
    )


def _valid_optional_number(row: Mapping[str, str], field_name: str) -> bool:
    raw_value = (row.get(field_name) or "").strip()
    if not raw_value:
        return False
    try:
        value = parse_finite_number(raw_value)
    except ValueError:
        return False
    rule = OPTIONAL_NUMERIC_RULES[field_name]
    return rule.minimum <= value <= rule.maximum


def _valid_wikipedia_url(row: Mapping[str, str]) -> bool:
    value = (row.get("Wikipedia") or "").strip()
    return bool(value) and validate_url(value, ALLOWED_WIKIPEDIA_HOSTS) is None


def _normalize_identity(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").casefold()
    return re.sub(r"[^a-z0-9]+", "", ascii_text)


def _coordinate_groups(rows: Iterable[Mapping[str, str]]) -> list[list[int]]:
    groups: dict[tuple[float, float], list[int]] = defaultdict(list)
    for index, row in enumerate(rows, start=2):
        coordinates = _valid_coordinates(row)
        if coordinates is not None:
            groups[coordinates].append(index)
    return [line_numbers for line_numbers in groups.values() if len(line_numbers) > 1]


def _likely_duplicate_groups(rows: Iterable[Mapping[str, str]]) -> list[list[int]]:
    groups: dict[tuple, list[int]] = defaultdict(list)
    for index, row in enumerate(rows, start=2):
        coordinates = _valid_coordinates(row)
        if coordinates is None:
            continue
        key = (
            _normalize_identity(row.get("Club") or ""),
            _normalize_identity(row.get("Pitch") or ""),
            _normalize_identity(row.get("County") or ""),
            _normalize_identity(row.get("Country") or ""),
            round(coordinates[0], 5),
            round(coordinates[1], 5),
        )
        groups[key].append(index)
    return [line_numbers for line_numbers in groups.values() if len(line_numbers) > 1]


def _threshold_status(
    numerator: int, denominator: int, minimum_percentage: float
) -> str:
    percentage = _percentage(numerator, denominator)
    return "pass" if percentage is not None and percentage >= minimum_percentage else "review"


def _build_core_metrics(
    rows: list[dict[str, str]], metadata: DatasetMetadata
) -> list[dict]:
    total = len(rows)
    valid_coordinates = sum(_valid_coordinates(row) is not None for row in rows)
    missing_coordinates = sum(
        not (row.get("Latitude") or "").strip()
        or not (row.get("Longitude") or "").strip()
        for row in rows
    )
    invalid_coordinates = total - valid_coordinates - missing_coordinates
    missing_required = sum(
        any(not (row.get(field_name) or "").strip() for field_name in REQUIRED_IDENTITY_LOCATION_FIELDS)
        for row in rows
    )
    shared_groups = _coordinate_groups(rows)
    duplicate_groups = _likely_duplicate_groups(rows)
    valid_directions = sum(_directions_are_valid(row) for row in rows)
    elevation_complete = sum(
        _valid_optional_number(row, "Elevation") for row in rows
    )
    rainfall_complete = sum(
        _valid_optional_number(row, "annual_rainfall")
        and _valid_optional_number(row, "rain_days")
        for row in rows
    )
    wikipedia_complete = sum(_valid_wikipedia_url(row) for row in rows)
    data_as_of = metadata.last_modified
    source_id = "canonical_dataset"

    return [
        _metric(
            "record_count",
            "Pitch records",
            total,
            "records",
            "informational",
            source_id,
            data_as_of,
            "Count data rows in the canonical CSV, excluding the header.",
            f"{total:,} pitch records are published in the current dataset.",
        ),
        _metric(
            "valid_coordinates",
            "Valid coordinates",
            valid_coordinates,
            "records",
            "pass" if valid_coordinates == total else "review",
            source_id,
            data_as_of,
            "Parse finite WGS 84 latitude and longitude values and enforce world bounds.",
            f"{valid_coordinates:,} of {total:,} records have valid coordinate pairs.",
            numerator=valid_coordinates,
            denominator=total,
            threshold={"operator": "gte", "value": 100, "unit": "percent"},
            details={"missing_records": missing_coordinates, "invalid_records": invalid_coordinates},
        ),
        _metric(
            "missing_coordinates",
            "Missing coordinates",
            missing_coordinates,
            "records",
            "pass" if missing_coordinates == 0 else "review",
            source_id,
            data_as_of,
            "Count rows where latitude or longitude is blank.",
            f"{missing_coordinates:,} records have a blank latitude or longitude.",
            threshold={"operator": "eq", "value": 0, "unit": "records"},
            limitation="Malformed nonblank coordinates are reported under valid coordinates rather than this metric.",
        ),
        _metric(
            "missing_required_identity_location",
            "Missing required identity or location",
            missing_required,
            "records",
            "pass" if missing_required == 0 else "review",
            source_id,
            data_as_of,
            "Count rows missing any required identity or location field: File, Club, Province, Country, Division, or County.",
            f"{missing_required:,} records are missing a required identity or location field.",
            threshold={"operator": "eq", "value": 0, "unit": "records"},
            limitation="Pitch name is intentionally optional and is not included in this metric.",
        ),
        _metric(
            "shared_coordinate_groups",
            "Shared coordinate groups",
            len(shared_groups),
            "groups",
            "review" if shared_groups else "pass",
            source_id,
            data_as_of,
            "Group records that have exactly equal numeric latitude and longitude values.",
            f"{len(shared_groups):,} coordinate groups are shared by more than one record.",
            threshold={"operator": "review_above", "value": 0, "unit": "groups"},
            limitation="Shared coordinates are review prompts, not errors; multiple clubs can legitimately use one ground.",
            details={"affected_records": sum(len(group) for group in shared_groups)},
        ),
        _metric(
            "likely_duplicate_groups",
            "Likely duplicate groups",
            len(duplicate_groups),
            "groups",
            "review" if duplicate_groups else "pass",
            source_id,
            data_as_of,
            "Group normalized club, pitch, county, and country names at coordinates rounded to five decimal places.",
            f"{len(duplicate_groups):,} groups match the duplicate-candidate rule.",
            threshold={"operator": "review_above", "value": 0, "unit": "groups"},
            limitation="Candidates require human review because a club can have multiple records at one complex.",
            details={"affected_records": sum(len(group) for group in duplicate_groups)},
        ),
        _metric(
            "valid_directions_links",
            "Valid directions links",
            valid_directions,
            "records",
            "pass" if valid_directions == total else "review",
            source_id,
            data_as_of,
            "Require an allowed Google Maps host, one finite daddr pair, and coordinates matching the canonical point within 0.00001 degrees.",
            f"{valid_directions:,} of {total:,} directions links are valid and coordinate-aligned.",
            numerator=valid_directions,
            denominator=total,
            threshold={"operator": "gte", "value": 100, "unit": "percent"},
        ),
        _metric(
            "elevation_coverage",
            "Elevation coverage",
            elevation_complete,
            "records",
            _threshold_status(elevation_complete, total, 95),
            source_id,
            data_as_of,
            "Count nonblank finite elevation values between -500 and 9,000 metres.",
            f"{elevation_complete:,} of {total:,} records include a valid elevation value.",
            numerator=elevation_complete,
            denominator=total,
            threshold={"operator": "gte", "value": 95, "unit": "percent"},
            limitation="Elevation values are enrichment estimates and are not surveyed ground heights.",
        ),
        _metric(
            "rainfall_coverage",
            "Rainfall coverage",
            rainfall_complete,
            "records",
            _threshold_status(rainfall_complete, total, 95),
            source_id,
            data_as_of,
            "Count rows with valid annual rainfall and rain-days values within the published schema ranges.",
            f"{rainfall_complete:,} of {total:,} records include both rainfall fields.",
            numerator=rainfall_complete,
            denominator=total,
            threshold={"operator": "gte", "value": 95, "unit": "percent"},
            limitation="Rainfall fields are modelled annual estimates rather than observations at each pitch.",
        ),
        _metric(
            "wikipedia_link_coverage",
            "Reviewed Wikipedia links",
            wikipedia_complete,
            "records",
            "informational",
            source_id,
            data_as_of,
            "Count nonblank Wikipedia URLs that use an allowed Wikipedia hostname.",
            f"{wikipedia_complete:,} of {total:,} records include a reviewed Wikipedia link.",
            numerator=wikipedia_complete,
            denominator=total,
            limitation="Not every club has a suitable Wikipedia article, so no completeness target is applied.",
        ),
    ]


def _osm_breakdown(rows: list[dict[str, str]]) -> list[dict]:
    county_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        county_rows[(row.get("County") or "Unknown").strip() or "Unknown"].append(row)

    breakdown = []
    for county, matches in sorted(county_rows.items()):
        evaluated = [row for row in matches if row.get("Status") in OSM_EVALUATED_STATUSES]
        matched = sum(row.get("Status") in OSM_MATCHED_STATUSES for row in evaluated)
        breakdown.append(
            {
                "county": county,
                "matched": matched,
                "evaluated": len(evaluated),
                "percentage": _percentage(matched, len(evaluated)),
                "unavailable": len(matches) - len(evaluated),
            }
        )
    return breakdown


def _build_osm_metric(
    osm_rows: list[dict[str, str]] | None,
    source: dict,
    ireland_record_count: int,
) -> dict:
    if osm_rows is None:
        return _metric(
            "osm_geometry_match_coverage",
            "OSM geometry-match coverage",
            None,
            "percent",
            "unavailable",
            source["source_id"],
            None,
            "Aggregate evaluated rows from the optional checked-in OSM coverage snapshot.",
            "OSM geometry-match coverage is unavailable because no derived snapshot was found.",
            limitation="Unavailable inputs are never interpreted as zero coverage.",
            details={"county_breakdown": []},
        )

    evaluated = [row for row in osm_rows if row.get("Status") in OSM_EVALUATED_STATUSES]
    matched = sum(row.get("Status") in OSM_MATCHED_STATUSES for row in evaluated)
    unavailable = len(osm_rows) - len(evaluated)
    percentage = _percentage(matched, len(evaluated))
    snapshot_gap = ireland_record_count - len(osm_rows)
    limitation_parts = [
        "This is a historical proximity check against OSM pitch geometry, not proof that every match is correctly tagged."
    ]
    if snapshot_gap:
        limitation_parts.append(
            f"The snapshot contains {len(osm_rows):,} rows while the current canonical dataset contains {ireland_record_count:,} Ireland records."
        )
    if unavailable:
        limitation_parts.append(
            f"{unavailable:,} snapshot rows were unavailable and excluded from the percentage denominator."
        )

    return _metric(
        "osm_geometry_match_coverage",
        "OSM geometry-match coverage",
        percentage,
        "percent",
        "informational" if not unavailable else "review",
        source["source_id"],
        source["data_as_of"],
        "Treat matched_gaa and matched_generic as matches, no_match as evaluated nonmatches, and exclude unavailable statuses from the denominator.",
        f"{matched:,} of {len(evaluated):,} evaluated snapshot rows have a nearby OSM pitch match.",
        numerator=matched,
        denominator=len(evaluated),
        limitation=" ".join(limitation_parts),
        details={
            "snapshot_records": len(osm_rows),
            "current_ireland_records": ireland_record_count,
            "unavailable_records": unavailable,
            "county_breakdown": _osm_breakdown(osm_rows),
        },
    )


def build_data_quality_report(
    rows: list[dict[str, str]],
    metadata: DatasetMetadata,
    canonical_source: dict,
    osm_source: dict,
    osm_rows: list[dict[str, str]] | None,
    source_revision: str,
) -> dict:
    metrics = _build_core_metrics(rows, metadata)
    ireland_record_count = sum((row.get("File") or "").strip() == "Ireland" for row in rows)
    metrics.append(_build_osm_metric(osm_rows, osm_source, ireland_record_count))
    return {
        "contract_version": CONTRACT_VERSION,
        "build": {
            "method_version": METHOD_VERSION,
            "source_revision": source_revision,
            "generator": "scripts/generate_data_quality.py",
        },
        "dataset": {
            "record_count": metadata.record_count,
            "data_as_of": metadata.last_modified,
            "version": metadata.version,
            "revision": metadata.revision,
        },
        "sources": {
            canonical_source["source_id"]: canonical_source,
            osm_source["source_id"]: osm_source,
        },
        "metrics": metrics,
    }


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source_file:
        return list(csv.DictReader(source_file))


def build_current_report() -> dict:
    git_metadata = GitBuildMetadata(ROOT_DIR)
    rows = load_rows()
    metadata = build_dataset_metadata(rows, git_metadata)
    canonical_path = DATASET_PATH.relative_to(ROOT_DIR).as_posix()
    canonical_source = _source(
        "canonical_dataset",
        "canonical_csv",
        canonical_path,
        metadata.last_modified,
        metadata.revision,
        available=True,
    )

    osm_relative_path = OSM_COVERAGE_PATH.relative_to(ROOT_DIR).as_posix()
    if OSM_COVERAGE_PATH.exists():
        osm_date = git_metadata.last_modified_date(osm_relative_path)
        osm_revision = git_metadata.last_modified_commit(osm_relative_path)
        osm_rows = _load_csv(OSM_COVERAGE_PATH)
        osm_source = _source(
            "osm_coverage_snapshot",
            "derived_csv",
            osm_relative_path,
            osm_date,
            osm_revision,
            available=True,
            limitation="The snapshot is refreshed manually and can predate the canonical dataset.",
        )
        source_paths = (canonical_path, osm_relative_path)
    else:
        osm_rows = None
        osm_source = _source(
            "osm_coverage_snapshot",
            "derived_csv",
            osm_relative_path,
            None,
            None,
            available=False,
            limitation="No checked-in OSM coverage snapshot was available at build time.",
        )
        source_paths = (canonical_path,)

    source_revision = git_metadata.last_modified_commit(*source_paths)
    return build_data_quality_report(
        rows,
        metadata,
        canonical_source,
        osm_source,
        osm_rows,
        source_revision,
    )


def _format_value(metric: dict) -> str:
    if metric["value"] is None:
        return "Unavailable"
    if metric["unit"] == "percent":
        return f'{metric["value"]:.1f}%'
    if metric["percentage"] is not None and metric["metric_id"] in {
        "valid_coordinates",
        "valid_directions_links",
        "elevation_coverage",
        "rainfall_coverage",
        "wikipedia_link_coverage",
    }:
        return f'{metric["percentage"]:.1f}%'
    return f'{metric["value"]:,}'


def _render_status(status: str) -> str:
    labels = {
        "pass": "Pass",
        "review": "Review",
        "informational": "Information",
        "unavailable": "Unavailable",
    }
    return labels[status]


def _render_metric(metric: dict) -> str:
    limitation = ""
    if metric["limitation"]:
        limitation = f'\n          <p><strong>Known limitation:</strong> {html.escape(metric["limitation"])}</p>'
    return f"""      <article class="data-quality-metric" data-metric-id="{html.escape(metric['metric_id'])}">
        <div class="data-quality-metric-heading">
          <h3>{html.escape(metric['label'])}</h3>
          <span class="data-quality-status data-quality-status-{html.escape(metric['status'])}">{_render_status(metric['status'])}</span>
        </div>
        <p class="data-quality-value">{_format_value(metric)}</p>
        <p class="data-quality-summary">{html.escape(metric['summary'])}</p>
        <details>
          <summary>Method and provenance</summary>
          <p><strong>Method:</strong> {html.escape(metric['method'])}</p>
          <p><strong>Source:</strong> <code>{html.escape(metric['source_id'])}</code></p>
          <p><strong>Data as of:</strong> {html.escape(metric['data_as_of'] or 'Unavailable')}</p>{limitation}
        </details>
      </article>"""


def _render_osm_table(metric: dict) -> str:
    rows = metric["details"].get("county_breakdown", [])
    if not rows:
        return '<p class="data-quality-unavailable">County breakdown unavailable.</p>'
    body_rows = []
    for row in rows:
        coverage = (
            f'{row["percentage"]:.1f}%'
            if row["percentage"] is not None
            else "Unavailable"
        )
        body_rows.append(
            f"""          <tr>
            <th scope="row">{html.escape(row['county'])}</th>
            <td data-label="Matched">{row['matched']:,}</td>
            <td data-label="Evaluated">{row['evaluated']:,}</td>
            <td data-label="Coverage">{coverage}</td>
            <td data-label="Unavailable">{row['unavailable']:,}</td>
          </tr>"""
        )
    body = "\n".join(body_rows)
    return f"""<div class="dataset-table-wrap" tabindex="0" role="region" aria-label="OSM coverage by county">
        <table class="dataset-table data-quality-table" aria-label="OSM coverage by county">
          <thead><tr><th scope="col">County</th><th scope="col">Matched</th><th scope="col">Evaluated</th><th scope="col">Coverage</th><th scope="col">Unavailable</th></tr></thead>
          <tbody>
{body}
          </tbody>
        </table>
      </div>"""


def render_data_quality_page(report: dict) -> str:
    dataset = report["dataset"]
    metrics = {metric["metric_id"]: metric for metric in report["metrics"]}
    integrity_ids = (
        "record_count",
        "valid_coordinates",
        "missing_coordinates",
        "missing_required_identity_location",
        "shared_coordinate_groups",
        "likely_duplicate_groups",
        "valid_directions_links",
    )
    enrichment_ids = (
        "elevation_coverage",
        "rainfall_coverage",
        "wikipedia_link_coverage",
        "osm_geometry_match_coverage",
    )
    integrity = "\n".join(_render_metric(metrics[metric_id]) for metric_id in integrity_ids)
    enrichment = "\n".join(_render_metric(metrics[metric_id]) for metric_id in enrichment_ids)
    osm_metric = metrics["osm_geometry_match_coverage"]
    source_rows = []
    for source in report["sources"].values():
        source_link = (
            f'<a href="{html.escape(source["url"])}" target="_blank" rel="noopener noreferrer"><code>{html.escape(source["path"])}</code></a>'
            if source["url"]
            else f'<code>{html.escape(source["path"])}</code>'
        )
        source_rows.append(
            f"""          <tr>
            <th scope="row">{html.escape(source['source_id'])}</th>
            <td data-label="Type">{html.escape(source['type'])}</td>
            <td data-label="Source">{source_link}</td>
            <td data-label="Data as of">{html.escape(source['data_as_of'] or 'Unavailable')}</td>
            <td data-label="Available">{'Yes' if source['available'] else 'No'}</td>
          </tr>"""
        )

    description = "Public quality metrics, provenance, freshness, and known limitations for the open GAA Pitch Finder dataset."
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dataset Health and Provenance - GAA Pitch Finder</title>
<link rel="icon" type="image/png" href="img/logo-icon.png">
<meta property="og:title" content="Dataset Health and Provenance - GAA Pitch Finder">
<meta property="og:description" content="{description}">
<meta property="og:image" content="https://gaapitchfinder.com/img/logo-black.png">
<meta property="og:url" content="https://gaapitchfinder.com/data-quality.html">
<meta property="og:type" content="website">
<link rel="canonical" href="https://gaapitchfinder.com/data-quality.html">
<meta name="description" content="{description}">
<meta name="gaa-data-quality-source-revision" content="{html.escape(report['build']['source_revision'])}">
{analytics_html()}
<link rel="stylesheet" href="css/style.css">
</head>
<body>

{navigation_html("dataset")}

<main class="page-content data-quality-page">
  <header class="data-quality-header">
    <p class="data-quality-eyebrow">Open dataset monitoring</p>
    <h1>Dataset health and provenance</h1>
    <p>This report publishes the checks behind GAA Pitch Finder as individual metrics. It deliberately avoids a single quality score so gaps and limitations remain visible.</p>
    <dl class="data-quality-snapshot">
      <div><dt>Records</dt><dd>{dataset['record_count']:,}</dd></div>
      <div><dt>Data as of</dt><dd><time datetime="{html.escape(dataset['data_as_of'])}">{html.escape(dataset['data_as_of'])}</time></dd></div>
      <div><dt>Dataset version</dt><dd>{html.escape(dataset['version'])}</dd></div>
      <div><dt>Source revision</dt><dd><a href="{REPOSITORY_URL}/commit/{html.escape(report['build']['source_revision'])}"><code>{html.escape(report['build']['source_revision'][:10])}</code></a></dd></div>
    </dl>
    <div class="data-quality-actions">
      <a href="/dataset.html">Open dataset downloads</a>
      <a href="/data-quality.json">View metric JSON</a>
      <a href="{REPOSITORY_URL}/blob/main/scripts/generate_data_quality.py" target="_blank" rel="noopener noreferrer">Read methodology code</a>
    </div>
  </header>

  <section class="data-quality-section" aria-labelledby="integrity-heading">
    <div class="data-quality-section-heading">
      <h2 id="integrity-heading">Core integrity</h2>
      <p>Checks for coordinates, identity fields, duplicate candidates, and directions links in the canonical CSV.</p>
    </div>
    <div class="data-quality-grid">
{integrity}
    </div>
  </section>

  <section class="data-quality-section" aria-labelledby="enrichment-heading">
    <div class="data-quality-section-heading">
      <h2 id="enrichment-heading">Enrichment coverage</h2>
      <p>Completeness of optional context fields and the separately dated OpenStreetMap geometry snapshot.</p>
    </div>
    <div class="data-quality-grid">
{enrichment}
    </div>
  </section>

  <section class="data-quality-section" aria-labelledby="osm-heading">
    <div class="data-quality-section-heading">
      <h2 id="osm-heading">OSM coverage by county</h2>
      <p>The denominator contains only evaluated snapshot rows. API errors and unavailable checks are shown separately rather than counted as misses.</p>
    </div>
    {_render_osm_table(osm_metric)}
  </section>

  <section class="data-quality-section" aria-labelledby="sources-heading">
    <div class="data-quality-section-heading">
      <h2 id="sources-heading">Source lineage</h2>
      <p>Each metric references one of these versioned repository sources.</p>
    </div>
    <div class="dataset-table-wrap" tabindex="0" role="region" aria-label="Data quality source lineage">
      <table class="dataset-table data-quality-table" aria-label="Data quality source lineage">
        <thead><tr><th scope="col">Source ID</th><th scope="col">Type</th><th scope="col">Source</th><th scope="col">Data as of</th><th scope="col">Available</th></tr></thead>
        <tbody>
{chr(10).join(source_rows)}
        </tbody>
      </table>
    </div>
  </section>
</main>

{footer_html()}

{navigation_script_html()}
</body>
</html>
"""


def serialize_report(report: dict) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2) + "\n"


def write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def main() -> int:
    report = build_current_report()
    changed = []
    if write_if_changed(REPORT_JSON_PATH, serialize_report(report)):
        changed.append(REPORT_JSON_PATH.relative_to(ROOT_DIR).as_posix())
    if write_if_changed(REPORT_HTML_PATH, render_data_quality_page(report)):
        changed.append(REPORT_HTML_PATH.relative_to(ROOT_DIR).as_posix())
    outputs = ", ".join(changed) if changed else "no files (already current)"
    print(
        f"Generated {len(report['metrics'])} data quality metrics from "
        f"source revision {report['build']['source_revision'][:10]}: {outputs}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
