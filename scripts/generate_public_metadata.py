#!/usr/bin/env python3
"""Generate public dataset counts and dates from canonical sources."""

from __future__ import annotations

import json
import re
from datetime import date
from html import escape
from pathlib import Path

from build_metadata import GitBuildMetadata
from dataset_contract import (
    ATTRIBUTION,
    CSV_DOWNLOAD_PATH,
    FIELD_DEFINITIONS,
    GEOJSON_DOWNLOAD_PATH,
    LICENSE_NAME,
    LICENSE_URL,
    SCHEMA_DOWNLOAD_PATH,
    SCHEMA_VERSION,
    DatasetMetadata,
    build_dataset_metadata,
)
from site_build_utils import ROOT_DIR, SITE_BASE_URL, SITE_DIR, load_rows


README_PATH = ROOT_DIR / "README.md"
DATASET_PAGE_PATH = SITE_DIR / "dataset.html"
README_START = "<!-- dataset-summary:start -->"
README_END = "<!-- dataset-summary:end -->"
DATASET_HEAD_START = "<!-- dataset-metadata:start -->"
DATASET_HEAD_END = "<!-- dataset-metadata:end -->"
DATASET_SUMMARY_START = "<!-- dataset-summary:start -->"
DATASET_SUMMARY_END = "<!-- dataset-summary:end -->"
DATASET_CONTRACT_START = "<!-- dataset-contract:start -->"
DATASET_CONTRACT_END = "<!-- dataset-contract:end -->"


def format_iso_date(value: str) -> str:
    parsed = date.fromisoformat(value)
    return f"{parsed.day} {parsed.strftime('%B %Y')}"


def replace_generated_block(content: str, start: str, end: str, body: str) -> str:
    pattern = re.compile(f"{re.escape(start)}.*?{re.escape(end)}", re.DOTALL)
    replacement = f"{start}\n{body.rstrip()}\n{end}"
    updated, replacements = pattern.subn(lambda _match: replacement, content)
    if replacements != 1:
        raise ValueError(
            f"Expected exactly one generated block from {start!r} to {end!r}; "
            f"found {replacements}"
        )
    return updated


def render_readme_summary(metadata: DatasetMetadata) -> str:
    return (
        f"As of {format_iso_date(metadata.last_modified)}, the main dataset contains "
        f"{metadata.record_count:,} pitch records with coordinates, elevation, "
        "rainfall data, club details, and directions links."
    )


def dataset_schema(metadata: DatasetMetadata) -> dict:
    description = (
        f"Open dataset of {metadata.record_count:,} GAA club and pitch locations "
        "worldwide, including club names, pitch names, coordinates, region, county, "
        "country, elevation, rainfall data, Google Maps directions links, and "
        "reviewed Wikipedia links where available."
    )
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "@id": "https://gaapitchfinder.com/dataset.html#webpage",
                "url": "https://gaapitchfinder.com/dataset.html",
                "name": "Open GAA Pitch Dataset - GAA Pitch Finder",
                "description": description,
                "isPartOf": {"@id": "https://gaapitchfinder.com/#website"},
                "about": {"@id": "https://gaapitchfinder.com/dataset.html#dataset"},
            },
            {
                "@type": "Dataset",
                "@id": "https://gaapitchfinder.com/dataset.html#dataset",
                "name": "GAA Pitch Finder Dataset",
                "alternateName": [
                    "GAA pitch dataset",
                    "GAA club locations dataset",
                    "GAA pitch locations",
                ],
                "description": description,
                "url": "https://gaapitchfinder.com/dataset.html",
                "sameAs": [
                    "https://github.com/ryanmcg2203/gaapitchfinder",
                    "https://github.com/ryanmcg2203/gaapitchfinder/blob/main/gaapitchfinder_data.csv",
                ],
                "creator": {
                    "@type": "Person",
                    "name": "Ryan McGuinness",
                    "url": "https://gaapitchfinder.com/about.html",
                },
                "publisher": {
                    "@type": "Organization",
                    "name": "GAA Pitch Finder",
                    "url": "https://gaapitchfinder.com/",
                    "logo": "https://gaapitchfinder.com/img/logo-black.png",
                    "email": "gaapitchfinder@gmail.com",
                },
                "license": "https://creativecommons.org/licenses/by/4.0/",
                "isAccessibleForFree": True,
                "inLanguage": "en",
                "dateModified": metadata.last_modified,
                "version": metadata.version,
                "identifier": metadata.revision,
                "additionalProperty": [
                    {
                        "@type": "PropertyValue",
                        "name": "Record count",
                        "value": metadata.record_count,
                    },
                    {
                        "@type": "PropertyValue",
                        "name": "Schema version",
                        "value": SCHEMA_VERSION,
                    },
                    {
                        "@type": "PropertyValue",
                        "name": "Coordinate reference system",
                        "value": "EPSG:4326",
                    },
                ],
                "keywords": [
                    "GAA pitch finder",
                    "GAA club finder",
                    "GAA pitch dataset",
                    "GAA club locations",
                    "Gaelic games",
                    "GAA directions",
                    "open sports data",
                    "Ireland sports data",
                ],
                "spatialCoverage": [
                    {"@type": "Country", "name": "Ireland"},
                    {"@type": "Place", "name": "Great Britain"},
                    {"@type": "Place", "name": "North America"},
                    {"@type": "Place", "name": "Europe"},
                    {"@type": "Place", "name": "Australasia"},
                    {"@type": "Place", "name": "Asia"},
                    {"@type": "Place", "name": "Middle East"},
                    {"@type": "Place", "name": "South America"},
                ],
                "temporalCoverage": "2017/..",
                "variableMeasured": [field.name for field in FIELD_DEFINITIONS],
                "measurementTechnique": [
                    "Manual verification",
                    "Satellite imagery cross-reference",
                    "Club website cross-reference",
                    "Open-Meteo rainfall data",
                    "Elevation data",
                ],
                "distribution": [
                    {
                        "@type": "DataDownload",
                        "name": "GAA Pitch Finder CSV dataset",
                        "encodingFormat": "text/csv",
                        "contentUrl": f"{SITE_BASE_URL}{CSV_DOWNLOAD_PATH}",
                    },
                    {
                        "@type": "DataDownload",
                        "name": "GAA Pitch Finder GeoJSON dataset",
                        "encodingFormat": "application/geo+json",
                        "contentUrl": f"{SITE_BASE_URL}{GEOJSON_DOWNLOAD_PATH}",
                    },
                    {
                        "@type": "DataDownload",
                        "name": "GAA Pitch Finder dataset schema",
                        "encodingFormat": "application/json",
                        "contentUrl": f"{SITE_BASE_URL}{SCHEMA_DOWNLOAD_PATH}",
                    },
                ],
            },
        ],
    }


def render_dataset_head(metadata: DatasetMetadata) -> str:
    description = (
        f"Open GAA club and pitch locations dataset with {metadata.record_count:,} "
        "records worldwide, including coordinates, directions, elevation, rainfall "
        "data and reviewed Wikipedia links."
    )
    schema = json.dumps(dataset_schema(metadata), separators=(",", ":"))
    return f"""<meta property="og:description" content="{description}">
<meta property="og:image" content="https://gaapitchfinder.com/img/logo-black.png">
<meta property="og:url" content="https://gaapitchfinder.com/dataset.html">
<meta property="og:type" content="website">
<link rel="canonical" href="https://gaapitchfinder.com/dataset.html">
<meta name="description" content="{description}">
<meta name="gaa-dataset-record-count" content="{metadata.record_count}">
<meta name="gaa-dataset-last-modified" content="{metadata.last_modified}">
<meta name="gaa-dataset-version" content="{metadata.version}">
<meta name="gaa-dataset-revision" content="{metadata.revision}">
<script type="application/ld+json">{schema}</script>"""


def render_dataset_summary(metadata: DatasetMetadata) -> str:
    return f"""  <p>GAA Pitch Finder publishes an open GAA club and pitch locations dataset maintained by Ryan McGuinness. It contains <strong>{metadata.record_count:,} GAA pitch records</strong> worldwide, including club names, pitch names, coordinates, directions, elevation, rainfall data, and regional groupings.</p>
  <p>Dataset generated from the canonical data revision dated <time datetime="{metadata.last_modified}">{format_iso_date(metadata.last_modified)}</time>.</p>
  <p><a href="/data-quality.html">View current dataset health, provenance, and known limitations</a>.</p>"""


def _field_details(field) -> str:
    details = []
    if field.value_format:
        details.append(field.value_format.upper())
    if field.units:
        details.append(field.units)
    if field.controlled_values:
        values = ", ".join(escape(value) for value in field.controlled_values)
        details.append(f"Values: {values}")
    if field.minimum is not None or field.maximum is not None:
        details.append(f"Range: {field.minimum:g} to {field.maximum:g}")
    return "<br>".join(details) or "&mdash;"


def render_dataset_contract(metadata: DatasetMetadata) -> str:
    field_rows = "\n".join(
        f"""      <tr>
        <th scope="row"><code>{escape(field.name)}</code></th>
        <td data-label="Type">{escape(field.data_type)}</td>
        <td data-label="Nullability">{"Optional" if field.nullable else "Required"}</td>
        <td data-label="Units or values">{_field_details(field)}</td>
        <td data-label="Description">{escape(field.description)}</td>
      </tr>"""
        for field in FIELD_DEFINITIONS
    )
    return f"""  <section class="dataset-download-section" aria-labelledby="dataset-downloads-heading">
    <h2 id="dataset-downloads-heading">Downloads</h2>
    <p>These stable URLs always serve the latest published dataset version.</p>
    <div class="dataset-download-actions">
      <a class="dataset-download dataset-download-primary" href="{CSV_DOWNLOAD_PATH}" download>
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v11m0 0 4-4m-4 4-4-4M5 18v3h14v-3"/></svg>
        <span><strong>Download CSV</strong><small>Canonical table</small></span>
      </a>
      <a class="dataset-download" href="{GEOJSON_DOWNLOAD_PATH}" download>
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-18c2.2 2.5 3.3 5.5 3.3 9S14.2 18.5 12 21M12 3C9.8 5.5 8.7 8.5 8.7 12s1.1 6.5 3.3 9M3 12h18"/></svg>
        <span><strong>Download GeoJSON</strong><small>WGS 84 points</small></span>
      </a>
      <a class="dataset-download" href="{SCHEMA_DOWNLOAD_PATH}">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m8 8-4 4 4 4m8-8 4 4-4 4m-2-11-4 14"/></svg>
        <span><strong>View schema</strong><small>JSON data dictionary</small></span>
      </a>
    </div>
  </section>

  <section aria-labelledby="dataset-details-heading">
    <h2 id="dataset-details-heading">Dataset details</h2>
    <dl class="dataset-facts">
      <div><dt>Records</dt><dd>{metadata.record_count:,}</dd></div>
      <div><dt>Dataset version</dt><dd>{metadata.version}</dd></div>
      <div><dt>Schema version</dt><dd>{SCHEMA_VERSION}</dd></div>
      <div><dt>Generation date</dt><dd><time datetime="{metadata.last_modified}">{format_iso_date(metadata.last_modified)}</time></dd></div>
      <div><dt>Revision</dt><dd><a href="https://github.com/ryanmcg2203/gaapitchfinder/commit/{metadata.revision}"><code>{metadata.revision}</code></a></dd></div>
      <div><dt>Coordinates</dt><dd>WGS 84 (EPSG:4326)</dd></div>
      <div><dt>License</dt><dd><a href="{LICENSE_URL}">{LICENSE_NAME}</a></dd></div>
      <div><dt>Attribution</dt><dd>{escape(ATTRIBUTION)}</dd></div>
    </dl>
  </section>

  <section aria-labelledby="dataset-fields-heading">
    <h2 id="dataset-fields-heading">Field reference</h2>
    <p>The CSV stores blank optional values as empty strings. GeoJSON uses JSON numbers for numeric fields and <code>null</code> for blank optional values; every feature is a Point with coordinates ordered longitude, latitude.</p>
    <div class="dataset-table-wrap" tabindex="0" role="region" aria-label="Dataset field reference table">
      <table class="dataset-table" aria-label="Dataset field reference table">
        <thead><tr><th scope="col">Field</th><th scope="col">Type</th><th scope="col">Nullability</th><th scope="col">Units or values</th><th scope="col">Description</th></tr></thead>
        <tbody>
{field_rows}
        </tbody>
      </table>
    </div>
  </section>"""


def update_readme(content: str, metadata: DatasetMetadata) -> str:
    return replace_generated_block(
        content, README_START, README_END, render_readme_summary(metadata)
    )


def update_dataset_page(content: str, metadata: DatasetMetadata) -> str:
    content = replace_generated_block(
        content, DATASET_HEAD_START, DATASET_HEAD_END, render_dataset_head(metadata)
    )
    content = replace_generated_block(
        content,
        DATASET_SUMMARY_START,
        DATASET_SUMMARY_END,
        render_dataset_summary(metadata),
    )
    return replace_generated_block(
        content,
        DATASET_CONTRACT_START,
        DATASET_CONTRACT_END,
        render_dataset_contract(metadata),
    )


def write_if_changed(path: Path, content: str) -> bool:
    if path.read_text() == content:
        return False
    path.write_text(content)
    return True


def main() -> int:
    metadata = build_dataset_metadata(
        load_rows(), GitBuildMetadata(ROOT_DIR)
    )
    changed = []
    if write_if_changed(
        README_PATH, update_readme(README_PATH.read_text(), metadata)
    ):
        changed.append(README_PATH.relative_to(ROOT_DIR).as_posix())
    if write_if_changed(
        DATASET_PAGE_PATH,
        update_dataset_page(DATASET_PAGE_PATH.read_text(), metadata),
    ):
        changed.append(DATASET_PAGE_PATH.relative_to(ROOT_DIR).as_posix())

    outputs = ", ".join(changed) if changed else "no files (already current)"
    print(
        f"Generated public metadata for {metadata.record_count:,} records "
        f"updated {metadata.last_modified}: {outputs}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
