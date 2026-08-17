from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from dataset_contract import DatasetMetadata  # noqa: E402
from generate_data_quality import (  # noqa: E402
    build_data_quality_report,
    render_data_quality_page,
    serialize_report,
)


def source(source_id, source_type="canonical_csv", available=True):
    return {
        "source_id": source_id,
        "type": source_type,
        "path": f"data/{source_id}.csv",
        "url": f"https://example.com/{source_id}.csv" if available else None,
        "data_as_of": "2026-08-06" if available else None,
        "revision": "a" * 40 if available else None,
        "available": available,
        "limitation": None,
    }


def dataset_row(**overrides):
    row = {
        "File": "Ireland",
        "Club": "Example GAA",
        "Pitch": "Example Park",
        "Code": "Mixed",
        "Latitude": "53.0",
        "Longitude": "-7.0",
        "Province": "Leinster",
        "Country": "Ireland",
        "Division": "Example",
        "County": "Example",
        "Directions": "https://maps.google.com/?daddr=53.0,-7.0",
        "Twitter": "",
        "Elevation": "100",
        "annual_rainfall": "1000",
        "rain_days": "150",
        "Wikipedia": "https://en.wikipedia.org/wiki/Example",
    }
    row.update(overrides)
    return row


def metrics_by_id(report):
    return {metric["metric_id"]: metric for metric in report["metrics"]}


class DataQualityTests(unittest.TestCase):
    def setUp(self):
        self.metadata = DatasetMetadata(
            record_count=3,
            last_modified="2026-08-06",
            revision="b" * 40,
        )
        self.canonical_source = source("canonical_dataset")
        self.osm_source = source("osm_coverage_snapshot", "derived_csv")

    def build_report(self, rows, osm_rows=None, osm_source=None):
        return build_data_quality_report(
            rows,
            DatasetMetadata(
                record_count=len(rows),
                last_modified=self.metadata.last_modified,
                revision=self.metadata.revision,
            ),
            self.canonical_source,
            osm_source or self.osm_source,
            osm_rows,
            "c" * 40,
        )

    def test_core_metrics_separate_shared_coordinates_and_duplicate_candidates(self):
        rows = [
            dataset_row(),
            dataset_row(
                Club="Different Club",
                Pitch="Shared Ground",
                Elevation="",
                annual_rainfall="",
                rain_days="",
                Wikipedia="",
            ),
            dataset_row(
                Club=" example gaa ",
                Pitch="Example-Park",
                Latitude="53.000004",
                Directions="https://maps.google.com/?daddr=53.000004,-7.0",
            ),
        ]

        metrics = metrics_by_id(self.build_report(rows))

        self.assertEqual(metrics["record_count"]["value"], 3)
        self.assertEqual(metrics["valid_coordinates"]["percentage"], 100.0)
        self.assertEqual(metrics["shared_coordinate_groups"]["value"], 1)
        self.assertEqual(
            metrics["shared_coordinate_groups"]["details"]["affected_records"], 2
        )
        self.assertEqual(metrics["likely_duplicate_groups"]["value"], 1)
        self.assertEqual(metrics["valid_directions_links"]["value"], 3)
        self.assertEqual(metrics["elevation_coverage"]["value"], 2)
        self.assertEqual(metrics["rainfall_coverage"]["value"], 2)
        self.assertEqual(metrics["wikipedia_link_coverage"]["value"], 2)

    def test_missing_and_invalid_values_are_not_counted_as_complete(self):
        rows = [
            dataset_row(
                Latitude="",
                Directions="",
                County="",
                Elevation="not-a-number",
                annual_rainfall="",
                Wikipedia="https://example.com/not-wikipedia",
            )
        ]

        metrics = metrics_by_id(self.build_report(rows))

        self.assertEqual(metrics["valid_coordinates"]["value"], 0)
        self.assertEqual(metrics["missing_coordinates"]["value"], 1)
        self.assertEqual(metrics["missing_required_identity_location"]["value"], 1)
        self.assertEqual(metrics["valid_directions_links"]["value"], 0)
        self.assertEqual(metrics["elevation_coverage"]["value"], 0)
        self.assertEqual(metrics["rainfall_coverage"]["value"], 0)
        self.assertEqual(metrics["wikipedia_link_coverage"]["value"], 0)

    def test_osm_coverage_excludes_unavailable_rows_and_breaks_down_counties(self):
        osm_rows = [
            {"County": "Alpha", "Status": "matched_gaa"},
            {"County": "Alpha", "Status": "no_match"},
            {"County": "Beta", "Status": "matched_generic"},
            {"County": "Beta", "Status": "api_error"},
        ]

        metric = metrics_by_id(
            self.build_report([dataset_row()], osm_rows=osm_rows)
        )["osm_geometry_match_coverage"]

        self.assertEqual(metric["numerator"], 2)
        self.assertEqual(metric["denominator"], 3)
        self.assertEqual(metric["percentage"], 66.7)
        self.assertEqual(metric["status"], "review")
        self.assertEqual(metric["details"]["unavailable_records"], 1)
        self.assertEqual(
            metric["details"]["county_breakdown"],
            [
                {
                    "county": "Alpha",
                    "matched": 1,
                    "evaluated": 2,
                    "percentage": 50.0,
                    "unavailable": 0,
                },
                {
                    "county": "Beta",
                    "matched": 1,
                    "evaluated": 1,
                    "percentage": 100.0,
                    "unavailable": 1,
                },
            ],
        )

    def test_missing_osm_input_is_unavailable_instead_of_zero(self):
        unavailable_source = source(
            "osm_coverage_snapshot", "derived_csv", available=False
        )

        report = self.build_report(
            [dataset_row()], osm_rows=None, osm_source=unavailable_source
        )
        metric = metrics_by_id(report)["osm_geometry_match_coverage"]

        self.assertIsNone(metric["value"])
        self.assertIsNone(metric["percentage"])
        self.assertEqual(metric["status"], "unavailable")
        self.assertEqual(metric["details"]["county_breakdown"], [])
        self.assertIn("Unavailable", render_data_quality_page(report))

    def test_unavailable_county_rows_render_without_a_false_zero(self):
        report = self.build_report(
            [dataset_row()],
            osm_rows=[{"County": "Alpha", "Status": "api_error"}],
        )

        page = render_data_quality_page(report)

        self.assertIn('<td data-label="Coverage">Unavailable</td>', page)
        self.assertNotIn('<td data-label="Coverage">0.0%</td>', page)

    def test_contract_has_stable_provenance_fields_and_serialization(self):
        report = self.build_report([dataset_row()])

        self.assertEqual(report["contract_version"], "1.0.0")
        self.assertEqual(report["build"]["source_revision"], "c" * 40)
        self.assertEqual(set(report["sources"]), {
            "canonical_dataset",
            "osm_coverage_snapshot",
        })
        for metric in report["metrics"]:
            self.assertIn(metric["source_id"], report["sources"])
            self.assertIn("data_as_of", metric)
            self.assertIn("method", metric)
            self.assertIn("status", metric)
            self.assertIn("threshold", metric)
            self.assertIn("limitation", metric)

        serialized = serialize_report(report)
        self.assertEqual(serialized, serialize_report(report))
        page = render_data_quality_page(report)
        self.assertIn("/data-quality.json", page)
        self.assertIn("Open dataset downloads", page)
        self.assertIn("Source lineage", page)


if __name__ == "__main__":
    unittest.main()
