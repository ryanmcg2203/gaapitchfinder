from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from validate_dataset import EXPECTED_HEADERS, validate_dataset  # noqa: E402


def pitch_row(**overrides):
    row = {
        "File": "Ireland",
        "Club": "Test Club",
        "Pitch": "Test Ground",
        "Code": "",
        "Latitude": "53.1",
        "Longitude": "-8.2",
        "Province": "Connacht",
        "Country": "Ireland",
        "Division": "Galway",
        "County": "Galway",
        "Directions": "https://maps.google.com/?daddr=53.1,-8.2",
        "Twitter": "",
        "Elevation": "20",
        "annual_rainfall": "1200.5",
        "rain_days": "210",
        "Wikipedia": "",
    }
    row.update(overrides)
    if "Directions" not in overrides and (
        "Latitude" in overrides or "Longitude" in overrides
    ):
        row["Directions"] = (
            "https://maps.google.com/?daddr="
            f"{row['Latitude']},{row['Longitude']}"
        )
    return row


class DatasetValidationTests(unittest.TestCase):
    def setUp(self):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.path = Path(temporary_directory.name) / "dataset.csv"

    def write_dataset(self, rows, headers=EXPECTED_HEADERS):
        with self.path.open("w", encoding="utf-8", newline="") as dataset_file:
            writer = csv.writer(dataset_file)
            writer.writerow(headers)
            for row in rows:
                if isinstance(row, dict):
                    writer.writerow([row.get(header, "") for header in headers])
                else:
                    writer.writerow(row)

    def test_valid_dataset_accepts_optional_blanks_and_allowed_url_hosts(self):
        self.write_dataset(
            [
                pitch_row(
                    Pitch="",
                    Code="",
                    Twitter="https://www.instagram.com/testclub/",
                    Elevation="-3",
                    annual_rainfall="",
                    rain_days="",
                    Wikipedia="https://ga.wikipedia.org/wiki/Test",
                )
            ]
        )

        result = validate_dataset(self.path)

        self.assertTrue(result.is_valid, result.errors)
        self.assertEqual(result.row_count, 1)

    def test_headers_must_match_exact_names_and_order(self):
        headers = list(EXPECTED_HEADERS)
        headers[0], headers[1] = headers[1], headers[0]
        self.write_dataset([pitch_row()], headers)

        result = validate_dataset(self.path)

        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].line_number, 1)
        self.assertIn("headers must be", result.errors[0].message)

    def test_required_fields_and_coordinate_numbers_are_validated(self):
        self.write_dataset(
            [
                pitch_row(Club=""),
                pitch_row(
                    Club="Not Finite",
                    Latitude="nan",
                    Directions="https://maps.google.com/?daddr=53.2,-8.2",
                ),
                pitch_row(
                    Club="Out of Bounds",
                    Latitude="53.3",
                    Longitude="181",
                    Directions="https://maps.google.com/?daddr=53.3,-8.3",
                ),
            ]
        )

        result = validate_dataset(self.path)
        errors = [(error.line_number, error.message) for error in result.errors]

        self.assertTrue(
            any(line == 2 and "Club is required" in msg for line, msg in errors)
        )
        self.assertTrue(
            any(
                line == 3 and "Latitude must be a finite" in msg
                for line, msg in errors
            )
        )
        self.assertTrue(
            any(
                line == 4 and "Longitude must be between" in msg
                for line, msg in errors
            )
        )

    def test_optional_metrics_must_be_finite_and_within_ranges(self):
        self.write_dataset(
            [
                pitch_row(Elevation="high"),
                pitch_row(Club="Dry Club", Latitude="53.2", annual_rainfall="-0.1"),
                pitch_row(Club="Wet Club", Latitude="53.3", rain_days="367"),
            ]
        )

        result = validate_dataset(self.path)
        messages = [error.message for error in result.errors]

        self.assertTrue(
            any("Elevation must be a finite number" in msg for msg in messages)
        )
        self.assertTrue(
            any(
                "annual_rainfall must be between 0 and 12000" in msg
                for msg in messages
            )
        )
        self.assertTrue(
            any("rain_days must be between 0 and 366" in msg for msg in messages)
        )

    def test_url_schemes_and_hosts_are_allowlisted_by_column(self):
        self.write_dataset(
            [
                pitch_row(Directions="ttps://maps.google.com/?daddr=53.1,-8.2"),
                pitch_row(
                    Club="Social Club",
                    Latitude="53.2",
                    Directions="https://maps.google.com/?daddr=53.2,-8.2",
                    Twitter="https://example.com/testclub",
                ),
                pitch_row(
                    Club="Reference Club",
                    Latitude="53.3",
                    Directions="https://maps.google.com/?daddr=53.3,-8.2",
                    Wikipedia="javascript:alert(1)",
                ),
            ]
        )

        result = validate_dataset(self.path)
        errors = [(error.line_number, error.message) for error in result.errors]

        self.assertTrue(
            any(
                line == 2 and "Directions URL scheme" in msg
                for line, msg in errors
            )
        )
        self.assertTrue(
            any(line == 3 and "Twitter URL host" in msg for line, msg in errors)
        )
        self.assertTrue(
            any(
                line == 4 and "Wikipedia URL scheme" in msg
                for line, msg in errors
            )
        )

    def test_directions_coordinates_use_documented_tolerance(self):
        self.write_dataset(
            [
                pitch_row(
                    Club="Within Tolerance",
                    Directions="https://maps.google.com/?daddr=53.100009,-8.2",
                ),
                pitch_row(
                    Club="Outside Tolerance",
                    Latitude="53.2",
                    Directions="https://maps.google.com/?daddr=53.20002,-8.2",
                ),
            ]
        )

        result = validate_dataset(self.path)
        mismatch_errors = [
            error for error in result.errors if "do not match" in error.message
        ]

        self.assertEqual(len(mismatch_errors), 1)
        self.assertEqual(mismatch_errors[0].line_number, 3)
        self.assertIn("1e-05 degrees", mismatch_errors[0].message)

    def test_directions_requires_one_bounded_daddr_pair(self):
        self.write_dataset(
            [
                pitch_row(Directions="https://maps.google.com/"),
                pitch_row(
                    Club="Impossible Destination",
                    Latitude="53.2",
                    Directions="https://maps.google.com/?daddr=91,-8.2",
                ),
            ]
        )

        result = validate_dataset(self.path)
        messages = [error.message for error in result.errors]

        self.assertTrue(any("exactly one daddr" in msg for msg in messages))
        self.assertTrue(
            any("daddr latitude must be between" in msg for msg in messages)
        )

    def test_exact_duplicates_fail_with_first_and_duplicate_line_numbers(self):
        row = pitch_row()
        self.write_dataset([row, row])

        result = validate_dataset(self.path)

        duplicate_errors = [
            error for error in result.errors if "exact duplicate" in error.message
        ]
        self.assertEqual(len(duplicate_errors), 1)
        self.assertEqual(duplicate_errors[0].line_number, 3)
        self.assertIn("CSV line 2", duplicate_errors[0].message)

    def test_shared_coordinates_are_informational_and_non_failing(self):
        self.write_dataset(
            [
                pitch_row(Club="Home Club"),
                pitch_row(Club="Tenant Club", Pitch="Shared Ground"),
            ]
        )

        result = validate_dataset(self.path)

        self.assertTrue(result.is_valid, result.errors)
        self.assertEqual(len(result.information), 1)
        self.assertEqual(result.information[0].severity, "info")
        self.assertIn("CSV lines 2, 3", result.information[0].message)

    def test_diagnostics_use_physical_lines_after_multiline_records(self):
        self.write_dataset(
            [
                pitch_row(Club="Club with\nmultiline name"),
                pitch_row(
                    Club="Bad URL Club",
                    Latitude="53.2",
                    Directions="https://maps.google.com/?daddr=53.2,-8.2",
                    Twitter="https://example.com/bad",
                ),
            ]
        )

        result = validate_dataset(self.path)
        twitter_errors = [
            error for error in result.errors if "Twitter URL" in error.message
        ]

        self.assertEqual(len(twitter_errors), 1)
        self.assertEqual(twitter_errors[0].line_number, 4)

    def test_wrong_column_count_reports_its_csv_line(self):
        self.write_dataset([["too", "short"]])

        result = validate_dataset(self.path)

        self.assertEqual(result.errors[0].line_number, 2)
        self.assertIn("expected 16 columns; found 2", result.errors[0].message)


if __name__ == "__main__":
    unittest.main()
