from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Mapping

from build_metadata import GitBuildMetadata
from site_build_utils import DATASET_PATH, SITE_BASE_URL
from validate_dataset import EXPECTED_HEADERS, REQUIRED_CORE_FIELDS


SCHEMA_VERSION = "1.0.0"
CSV_DOWNLOAD_PATH = "/downloads/gaapitchfinder.csv"
GEOJSON_DOWNLOAD_PATH = "/downloads/gaapitchfinder.geojson"
SCHEMA_DOWNLOAD_PATH = "/downloads/schema.json"
LICENSE_NAME = "Creative Commons Attribution 4.0 International (CC BY 4.0)"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
ATTRIBUTION = "GAA Pitch Finder by Ryan McGuinness (https://gaapitchfinder.com)"


@dataclass(frozen=True)
class DatasetMetadata:
    record_count: int
    last_modified: str
    revision: str

    @property
    def version(self) -> str:
        return self.last_modified.replace("-", ".")

    @property
    def short_revision(self) -> str:
        return self.revision[:8]


@dataclass(frozen=True)
class FieldDefinition:
    name: str
    data_type: str
    nullable: bool
    description: str
    units: str | None = None
    controlled_values: tuple[str, ...] = ()
    value_format: str | None = None
    minimum: float | None = None
    maximum: float | None = None

    def as_dictionary(self) -> dict:
        field = {
            "name": self.name,
            "type": self.data_type,
            "nullable": self.nullable,
            "units": self.units,
            "description": self.description,
        }
        if self.value_format:
            field["format"] = self.value_format
        if self.controlled_values:
            field["controlled_values"] = list(self.controlled_values)
        constraints = {}
        if self.minimum is not None:
            constraints["minimum"] = self.minimum
        if self.maximum is not None:
            constraints["maximum"] = self.maximum
        if constraints:
            field["constraints"] = constraints
        return field


FIELD_DEFINITIONS = (
    FieldDefinition(
        "File",
        "string",
        False,
        "Top-level coverage region used to partition the source dataset.",
        controlled_values=(
            "Asia",
            "Australasia",
            "Canada",
            "Europe",
            "Great Britain",
            "Ireland",
            "Middle East",
            "South America",
            "USA",
        ),
    ),
    FieldDefinition("Club", "string", False, "Club or team name."),
    FieldDefinition(
        "Pitch", "string", True, "Pitch, ground, or community field name."
    ),
    FieldDefinition(
        "Code",
        "string",
        True,
        "Primary Gaelic games code where it is known.",
        controlled_values=("Football", "Hurling", "Mixed"),
    ),
    FieldDefinition(
        "Latitude",
        "number",
        False,
        "Latitude of the pitch point in WGS 84 decimal degrees.",
        units="decimal degrees",
        minimum=-90,
        maximum=90,
    ),
    FieldDefinition(
        "Longitude",
        "number",
        False,
        "Longitude of the pitch point in WGS 84 decimal degrees.",
        units="decimal degrees",
        minimum=-180,
        maximum=180,
    ),
    FieldDefinition(
        "Province",
        "string",
        False,
        "Province or comparable broad regional grouping.",
    ),
    FieldDefinition("Country", "string", False, "Country name."),
    FieldDefinition(
        "Division",
        "string",
        False,
        "GAA division, county board, or overseas administrative grouping.",
    ),
    FieldDefinition(
        "County",
        "string",
        False,
        "County, state, division, or local grouping used for browsing.",
    ),
    FieldDefinition(
        "Directions",
        "string",
        False,
        "Google Maps directions URL for the canonical pitch coordinates.",
        value_format="uri",
    ),
    FieldDefinition(
        "Twitter",
        "string",
        True,
        "Club social profile URL; legacy records may contain X or Instagram URLs.",
        value_format="uri",
    ),
    FieldDefinition(
        "Elevation",
        "number",
        True,
        "Estimated pitch elevation above mean sea level.",
        units="metres",
        minimum=-500,
        maximum=9000,
    ),
    FieldDefinition(
        "annual_rainfall",
        "number",
        True,
        "Estimated mean annual rainfall at the pitch location.",
        units="millimetres per year",
        minimum=0,
        maximum=12000,
    ),
    FieldDefinition(
        "rain_days",
        "number",
        True,
        "Estimated annual number of days with precipitation.",
        units="days per year",
        minimum=0,
        maximum=366,
    ),
    FieldDefinition(
        "Wikipedia",
        "string",
        True,
        "Reviewed Wikipedia URL for the club where available.",
        value_format="uri",
    ),
)

if tuple(field.name for field in FIELD_DEFINITIONS) != EXPECTED_HEADERS:
    raise RuntimeError("Dataset contract fields do not match canonical CSV headers")
if {field.name for field in FIELD_DEFINITIONS if not field.nullable} != set(
    REQUIRED_CORE_FIELDS
):
    raise RuntimeError("Dataset contract nullability does not match CSV validation")


def build_dataset_metadata(
    rows: Iterable[Mapping[str, str]], build_metadata: GitBuildMetadata
) -> DatasetMetadata:
    return DatasetMetadata(
        record_count=sum(1 for _row in rows),
        last_modified=build_metadata.last_modified_date(DATASET_PATH),
        revision=build_metadata.last_modified_commit(DATASET_PATH),
    )


def _typed_value(field: FieldDefinition, raw_value: str | None):
    value = (raw_value or "").strip()
    if not value:
        if field.nullable:
            return None
        raise ValueError(f"Required field {field.name} is blank")
    if field.data_type == "number":
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"Field {field.name} is not finite: {value!r}")
        return number
    return value


def build_geojson(
    rows: Iterable[Mapping[str, str]], metadata: DatasetMetadata
) -> dict:
    features = []
    latitudes = []
    longitudes = []
    for index, row in enumerate(rows, start=2):
        try:
            properties = {
                field.name: _typed_value(field, row.get(field.name))
                for field in FIELD_DEFINITIONS
            }
        except (TypeError, ValueError) as error:
            raise ValueError(f"CSV line {index}: {error}") from error
        latitude = properties["Latitude"]
        longitude = properties["Longitude"]
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ValueError(f"CSV line {index}: coordinates are outside world bounds")
        latitudes.append(latitude)
        longitudes.append(longitude)
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [longitude, latitude],
                },
                "properties": properties,
            }
        )

    if len(features) != metadata.record_count:
        raise ValueError(
            "GeoJSON feature count does not match release metadata: "
            f"{len(features)} != {metadata.record_count}"
        )

    bbox = []
    if features:
        bbox = [
            min(longitudes),
            min(latitudes),
            max(longitudes),
            max(latitudes),
        ]
    return {
        "type": "FeatureCollection",
        "name": "GAA Pitch Finder Dataset",
        "dataset_version": metadata.version,
        "dataset_revision": metadata.revision,
        "schema_version": SCHEMA_VERSION,
        "generation_date": metadata.last_modified,
        "feature_count": metadata.record_count,
        "license": LICENSE_URL,
        "attribution": ATTRIBUTION,
        "schema": f"{SITE_BASE_URL}{SCHEMA_DOWNLOAD_PATH}",
        "bbox": bbox,
        "features": features,
    }


def build_schema(metadata: DatasetMetadata) -> dict:
    return {
        "name": "GAA Pitch Finder Dataset",
        "schema_version": SCHEMA_VERSION,
        "dataset_version": metadata.version,
        "dataset_revision": metadata.revision,
        "generation_date": metadata.last_modified,
        "generation_date_basis": (
            "Commit date of the latest revision that changed the canonical CSV"
        ),
        "record_count": metadata.record_count,
        "license": {"name": LICENSE_NAME, "url": LICENSE_URL},
        "attribution": ATTRIBUTION,
        "coordinate_reference_system": {
            "name": "World Geodetic System 1984",
            "identifier": "EPSG:4326",
            "csv_axis_order": ["latitude", "longitude"],
            "geojson_axis_order": ["longitude", "latitude"],
            "geojson_standard": "RFC 7946",
        },
        "distributions": [
            {
                "format": "CSV",
                "media_type": "text/csv",
                "url": f"{SITE_BASE_URL}{CSV_DOWNLOAD_PATH}",
                "representation": (
                    "UTF-8 CSV with the exact canonical column order; blank optional "
                    "values are empty strings"
                ),
            },
            {
                "format": "GeoJSON",
                "media_type": "application/geo+json",
                "url": f"{SITE_BASE_URL}{GEOJSON_DOWNLOAD_PATH}",
                "representation": (
                    "FeatureCollection of Point features; numeric fields are JSON "
                    "numbers and blank optional values are null"
                ),
            },
        ],
        "fields": [field.as_dictionary() for field in FIELD_DEFINITIONS],
        "compatibility": {
            "versioning": "Semantic versioning for schema_version",
            "stable_latest_urls": True,
            "backward_compatible_changes": [
                "Adding an optional field",
                "Adding a controlled vocabulary value",
                "Clarifying descriptions or units without changing interpretation",
            ],
            "breaking_changes": [
                "Removing or renaming a field",
                "Changing a field type or making a nullable field required",
                "Changing coordinate reference system or GeoJSON geometry type",
            ],
            "consumer_guidance": (
                "Ignore unknown fields and do not assume controlled vocabularies are "
                "closed. Breaking changes increment the schema major version."
            ),
        },
    }
