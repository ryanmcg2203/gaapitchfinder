#!/usr/bin/env python3
"""Generate public dataset counts and dates from canonical sources."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Mapping

from build_metadata import GitBuildMetadata
from site_build_utils import DATASET_PATH, ROOT_DIR, SITE_DIR, load_rows


README_PATH = ROOT_DIR / "README.md"
DATASET_PAGE_PATH = SITE_DIR / "dataset.html"
README_START = "<!-- dataset-summary:start -->"
README_END = "<!-- dataset-summary:end -->"
DATASET_HEAD_START = "<!-- dataset-metadata:start -->"
DATASET_HEAD_END = "<!-- dataset-metadata:end -->"
DATASET_SUMMARY_START = "<!-- dataset-summary:start -->"
DATASET_SUMMARY_END = "<!-- dataset-summary:end -->"


@dataclass(frozen=True)
class DatasetMetadata:
    record_count: int
    last_modified: str

    @property
    def formatted_count(self) -> str:
        return f"{self.record_count:,}"

    @property
    def formatted_date(self) -> str:
        return format_iso_date(self.last_modified)


def format_iso_date(value: str) -> str:
    parsed = date.fromisoformat(value)
    return f"{parsed.day} {parsed.strftime('%B %Y')}"


def build_dataset_metadata(
    rows: Iterable[Mapping[str, str]], build_metadata: GitBuildMetadata
) -> DatasetMetadata:
    return DatasetMetadata(
        record_count=sum(1 for _row in rows),
        last_modified=build_metadata.last_modified_date(DATASET_PATH),
    )


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
        f"As of {metadata.formatted_date}, the main dataset contains "
        f"{metadata.formatted_count} pitch records with coordinates, elevation, "
        "rainfall data, club details, and directions links."
    )


def dataset_schema(metadata: DatasetMetadata) -> dict:
    description = (
        f"Open dataset of {metadata.formatted_count} GAA club and pitch locations "
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
                "additionalProperty": {
                    "@type": "PropertyValue",
                    "name": "Record count",
                    "value": metadata.record_count,
                },
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
                "variableMeasured": [
                    "Club",
                    "Pitch",
                    "Latitude",
                    "Longitude",
                    "Province",
                    "Country",
                    "Division",
                    "County",
                    "Directions",
                    "Twitter",
                    "Wikipedia",
                    "Elevation",
                    "annual_rainfall",
                    "rain_days",
                ],
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
                        "contentUrl": "https://raw.githubusercontent.com/ryanmcg2203/gaapitchfinder/main/gaapitchfinder_data.csv",
                    },
                    {
                        "@type": "DataDownload",
                        "name": "GAA Pitch Finder GitHub repository",
                        "encodingFormat": "text/html",
                        "contentUrl": "https://github.com/ryanmcg2203/gaapitchfinder",
                    },
                ],
            },
        ],
    }


def render_dataset_head(metadata: DatasetMetadata) -> str:
    description = (
        f"Open GAA club and pitch locations dataset with {metadata.formatted_count} "
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
<script type="application/ld+json">{schema}</script>"""


def render_dataset_summary(metadata: DatasetMetadata) -> str:
    return f"""  <p>GAA Pitch Finder publishes an open GAA club and pitch locations dataset maintained by Ryan McGuinness. It contains <strong>{metadata.formatted_count} GAA pitch records</strong> worldwide, including club names, pitch names, coordinates, directions, elevation, rainfall data, and regional groupings.</p>
  <p>Dataset last updated: <time datetime="{metadata.last_modified}">{metadata.formatted_date}</time>.</p>"""


def update_readme(content: str, metadata: DatasetMetadata) -> str:
    return replace_generated_block(
        content, README_START, README_END, render_readme_summary(metadata)
    )


def update_dataset_page(content: str, metadata: DatasetMetadata) -> str:
    content = replace_generated_block(
        content, DATASET_HEAD_START, DATASET_HEAD_END, render_dataset_head(metadata)
    )
    return replace_generated_block(
        content,
        DATASET_SUMMARY_START,
        DATASET_SUMMARY_END,
        render_dataset_summary(metadata),
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
        f"Generated public metadata for {metadata.formatted_count} records "
        f"updated {metadata.last_modified}: {outputs}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
