#!/usr/bin/env python3
"""Generate stable public CSV, GeoJSON, and schema downloads."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from build_metadata import GitBuildMetadata
from dataset_contract import build_dataset_metadata, build_geojson, build_schema
from site_build_utils import DATASET_PATH, ROOT_DIR, SITE_DIR, load_rows


DOWNLOADS_DIR = SITE_DIR / "downloads"
CSV_OUTPUT_PATH = DOWNLOADS_DIR / "gaapitchfinder.csv"
GEOJSON_OUTPUT_PATH = DOWNLOADS_DIR / "gaapitchfinder.geojson"
SCHEMA_OUTPUT_PATH = DOWNLOADS_DIR / "schema.json"


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def generate_downloads(
    rows,
    metadata,
    dataset_path: Path = DATASET_PATH,
    downloads_dir: Path = DOWNLOADS_DIR,
) -> None:
    downloads_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(dataset_path, downloads_dir / CSV_OUTPUT_PATH.name)
    write_json(downloads_dir / GEOJSON_OUTPUT_PATH.name, build_geojson(rows, metadata))
    write_json(downloads_dir / SCHEMA_OUTPUT_PATH.name, build_schema(metadata))


def main() -> int:
    rows = load_rows()
    metadata = build_dataset_metadata(rows, GitBuildMetadata(ROOT_DIR))
    generate_downloads(rows, metadata)
    print(
        f"Generated CSV, GeoJSON, and schema downloads for "
        f"{metadata.record_count:,} records at dataset version {metadata.version} "
        f"({metadata.short_revision})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
