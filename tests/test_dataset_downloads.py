from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from audit_site import geojson_structure_errors  # noqa: E402
from dataset_contract import (  # noqa: E402
    FIELD_DEFINITIONS,
    SCHEMA_VERSION,
    DatasetMetadata,
    build_geojson,
    build_schema,
)
from generate_dataset_downloads import generate_downloads  # noqa: E402
from validate_dataset import EXPECTED_HEADERS  # noqa: E402


def pitch_row(**overrides):
    row = {
        "File": "Ireland",
        "Club": "Test Club",
        "Pitch": "",
        "Code": "Mixed",
        "Latitude": "53.1",
        "Longitude": "-8.2",
        "Province": "Connacht",
        "Country": "Ireland",
        "Division": "Galway",
        "County": "Galway",
        "Directions": "https://maps.google.com/?daddr=53.1,-8.2",
        "Twitter": "",
        "Elevation": "42.5",
        "annual_rainfall": "1200",
        "rain_days": "",
        "Wikipedia": "https://en.wikipedia.org/wiki/Test",
    }
    row.update(overrides)
    return row


class DatasetDownloadTests(unittest.TestCase):
    def setUp(self):
        self.metadata = DatasetMetadata(1, "2026-08-06", "a" * 40)

    def test_geojson_keeps_all_fields_and_uses_lon_lat_point_order(self):
        geojson = build_geojson([pitch_row()], self.metadata)

        self.assertEqual(geojson["type"], "FeatureCollection")
        self.assertEqual(geojson["feature_count"], 1)
        self.assertEqual(
            geojson["features"][0]["geometry"]["coordinates"], [-8.2, 53.1]
        )
        properties = geojson["features"][0]["properties"]
        self.assertEqual(tuple(properties), EXPECTED_HEADERS)
        self.assertEqual(properties["Elevation"], 42.5)
        self.assertIsNone(properties["Pitch"])
        self.assertIsNone(properties["rain_days"])

    def test_geojson_rejects_metadata_count_drift(self):
        with self.assertRaisesRegex(ValueError, "feature count"):
            build_geojson([pitch_row()], DatasetMetadata(2, "2026-08-06", "a" * 40))

    def test_schema_documents_every_field_and_release_property(self):
        schema = build_schema(self.metadata)

        self.assertEqual(schema["schema_version"], SCHEMA_VERSION)
        self.assertEqual(schema["dataset_version"], "2026.08.06")
        self.assertEqual(schema["coordinate_reference_system"]["identifier"], "EPSG:4326")
        self.assertEqual(
            tuple(field["name"] for field in schema["fields"]), EXPECTED_HEADERS
        )
        for field in schema["fields"]:
            self.assertTrue(
                {"name", "type", "nullable", "units", "description"}.issubset(field)
            )
        code_field = next(field for field in schema["fields"] if field["name"] == "Code")
        self.assertEqual(
            code_field["controlled_values"], ["Football", "Hurling", "Mixed"]
        )
        self.assertIn("breaking_changes", schema["compatibility"])

    def test_generator_publishes_stable_files_and_exact_csv_bytes(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.csv"
            source.write_bytes(b"canonical,csv\r\nexact,bytes\r\n")
            output = root / "downloads"

            generate_downloads(
                [pitch_row()], self.metadata, dataset_path=source, downloads_dir=output
            )

            self.assertEqual(
                (output / "gaapitchfinder.csv").read_bytes(), source.read_bytes()
            )
            self.assertEqual(
                json.loads((output / "gaapitchfinder.geojson").read_text())["feature_count"],
                1,
            )
            self.assertEqual(
                json.loads((output / "schema.json").read_text())["schema_version"],
                SCHEMA_VERSION,
            )

    def test_geojson_audit_rejects_wrong_root_and_feature_count(self):
        self.assertEqual(
            geojson_structure_errors({"type": "Feature", "features": []}, 1),
            ["GeoJSON root must be a FeatureCollection object"],
        )
        errors = geojson_structure_errors(
            {"type": "FeatureCollection", "feature_count": 0, "features": []}, 1
        )
        self.assertTrue(any("feature count" in error for error in errors))

    def test_contract_order_matches_canonical_csv(self):
        self.assertEqual(tuple(field.name for field in FIELD_DEFINITIONS), EXPECTED_HEADERS)


if __name__ == "__main__":
    unittest.main()
