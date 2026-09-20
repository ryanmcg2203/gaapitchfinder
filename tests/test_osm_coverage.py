import csv
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import analyze_osm_coverage as coverage


def record(club="Alpha", county="Monaghan", latitude="54.1", status="matched_gaa", checked_at="2025-01-02T12:00:00+00:00"):
    return {
        "Club": club, "County": county, "Province": "Ulster",
        "Latitude": latitude, "Longitude": "-7.2", "Status": status,
        "CheckedAt": checked_at,
    }


class OSMCoverageTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.source = self.root / "source.csv"
        self.report = self.root / "report.csv"
        self.existing = [record(), record("Beta", "Down")]
        coverage.write_snapshot(self.report, self.existing)
        self.write_source([record(latitude="54.2"), record("Beta", "Down")])
        paths = patch.multiple(coverage, INPUT_CSV=str(self.source), OUTPUT_CSV=str(self.report), REQUEST_DELAY_S=0)
        paths.start()
        self.addCleanup(paths.stop)
        self.console = io.StringIO()
        output = patch("sys.stdout", self.console)
        output.start()
        self.addCleanup(output.stop)
        # Fail any accidental live request, even in tests that do not mock a query.
        network = patch.object(coverage.urllib.request, "urlopen", side_effect=AssertionError("No live requests in tests"))
        network.start()
        self.addCleanup(network.stop)

    def write_source(self, rows):
        with self.source.open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=coverage.LEGACY_FIELDS[:-1], extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    def test_partial_refresh_preserves_other_counties_and_check_dates(self):
        with patch.object(coverage, "query_overpass", return_value=[]) as query:
            coverage.main(["Monaghan"])
        query.assert_called_once_with(54.2, -7.2)
        rows = coverage.load_snapshot(self.report)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], self.existing[1])
        self.assertEqual(rows[1]["Latitude"], "54.2")
        self.assertEqual(rows[1]["Status"], "no_match")
        self.assertNotEqual(rows[1]["CheckedAt"], self.existing[0]["CheckedAt"])
        self.assertIsNotNone(coverage.datetime.fromisoformat(rows[1]["CheckedAt"]).tzinfo)

    def test_partition_replacement_handles_removed_and_multiple_pitch_records(self):
        old = [record("Removed"), record("Multi", latitude="54.1"), record("Beta", "Down")]
        coverage.write_snapshot(self.report, old)
        self.write_source([record("Multi", latitude="54.2"), record("Multi", latitude="54.3"), record("New"), old[2]])
        with patch.object(coverage, "query_overpass", return_value=[]):
            coverage.main(["Monaghan"])
        rows = coverage.load_snapshot(self.report)
        self.assertEqual(len(rows), 4)
        self.assertEqual([row["Latitude"] for row in rows if row["Club"] == "Multi"], ["54.2", "54.3"])
        self.assertNotIn("Removed", [row["Club"] for row in rows])
        self.assertEqual(rows[0], old[2])

    def test_multiple_counties_refresh_without_duplicate_arguments_or_rows(self):
        with patch.object(coverage, "query_overpass", return_value=[]) as query:
            coverage.main(["Down", "Monaghan", "Down"])
        self.assertEqual(query.call_count, 2)
        self.assertEqual(len(coverage.load_snapshot(self.report)), 2)

    def test_api_errors_are_dated_and_not_counted_as_evaluated_misses(self):
        with patch.object(coverage, "query_overpass", return_value=None):
            coverage.main(["Monaghan"])
        rows = coverage.load_snapshot(self.report)
        self.assertEqual(rows[0], self.existing[1])
        self.assertEqual(rows[1]["Status"], "api_error")
        self.assertTrue(rows[1]["CheckedAt"])
        self.assertIn("N/A", self.console.getvalue())
        self.assertIn("Unavailable", self.console.getvalue())

    def test_unknown_county_rejects_entire_request_before_network_or_writes(self):
        before = self.report.read_bytes()
        for counties in [["Unknown"], ["Monaghan", "Unknown"]]:
            with patch.object(coverage, "query_overpass") as query:
                with self.assertRaisesRegex(SystemExit, "Unknown counties"):
                    coverage.main(counties)
                query.assert_not_called()
            self.assertEqual(self.report.read_bytes(), before)

    def test_partial_refresh_requires_existing_snapshot(self):
        self.report.unlink()
        with patch.object(coverage, "query_overpass") as query:
            with self.assertRaisesRegex(SystemExit, "existing OSM report"):
                coverage.main(["Monaghan"])
            query.assert_not_called()
        self.assertFalse(self.report.exists())

    def test_legacy_snapshot_keeps_unknown_check_dates_blank(self):
        with self.report.open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=coverage.LEGACY_FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(self.existing)
        with patch.object(coverage, "query_overpass", return_value=[]):
            coverage.main(["Monaghan"])
        rows = coverage.load_snapshot(self.report)
        self.assertEqual(rows[0], {**self.existing[1], "CheckedAt": ""})
        self.assertTrue(rows[1]["CheckedAt"])

    def test_malformed_snapshot_is_not_silently_replaced(self):
        for content in [
            ",".join(coverage.REPORT_FIELDS) + "\n",
            "Club,County,UnknownColumn\nAlpha,Monaghan,x\n",
            ",".join(coverage.REPORT_FIELDS) + "\nAlpha,Monaghan\n",
            ",".join(coverage.REPORT_FIELDS) + "\nAlpha,Monaghan,Ulster,54,-7,unexpected,\n",
            ",".join(coverage.REPORT_FIELDS) + "\nAlpha,Monaghan,Ulster,54,-7,no_match,bad-date\n",
        ]:
            with self.subTest(content=content):
                self.report.write_text(content)
                with patch.object(coverage, "query_overpass") as query:
                    with self.assertRaises(SystemExit):
                        coverage.main(["Monaghan"])
                    query.assert_not_called()
                self.assertEqual(self.report.read_text(), content)

    def test_unexpected_worker_failure_preserves_previous_report(self):
        before = self.report.read_bytes()
        with patch.object(coverage, "check_county", side_effect=RuntimeError("worker failed")):
            with self.assertRaisesRegex(RuntimeError, "worker failed"):
                coverage.main(["Monaghan"])
        self.assertEqual(self.report.read_bytes(), before)

    def test_failed_atomic_replacement_or_serialization_preserves_report(self):
        before = self.report.read_bytes()
        with patch.object(coverage.os, "replace", side_effect=OSError("interrupted")):
            with self.assertRaises(OSError):
                coverage.write_snapshot(self.report, [record("New")])
        self.assertEqual(self.report.read_bytes(), before)
        with self.assertRaises(ValueError):
            coverage.write_snapshot(self.report, [record("New"), {**record(), "unsupported": "value"}])
        self.assertEqual(self.report.read_bytes(), before)
        self.assertEqual(sorted(path.name for path in self.root.iterdir()), ["report.csv", "source.csv"])

    def test_unfiltered_run_rebuilds_from_current_source(self):
        coverage.write_snapshot(self.report, self.existing + [record("Obsolete", "Tyrone")])
        with patch.object(coverage, "query_overpass", return_value=[]) as query:
            coverage.main([])
        self.assertEqual(query.call_count, 2)
        self.assertEqual(len(coverage.load_snapshot(self.report)), 2)
        self.report.unlink()
        with patch.object(coverage, "query_overpass", return_value=[]):
            coverage.main([])
        self.assertTrue(self.report.exists())

    def test_invalid_coordinates_stay_unavailable_without_api_requests(self):
        for latitude in ["", "nan", "inf", "91"]:
            with self.subTest(latitude=latitude), patch.object(coverage, "query_overpass") as query:
                _, status, matched = coverage.check_club(record(latitude=latitude))
                self.assertEqual(status, "no_coords")
                self.assertFalse(matched)
                query.assert_not_called()

    def test_merge_order_does_not_depend_on_worker_completion(self):
        first, second = record("First"), record("Second")
        self.assertEqual(
            coverage.merge_snapshot(self.existing, [first, second], {"Monaghan"}),
            coverage.merge_snapshot(self.existing, [second, first], {"Monaghan"}),
        )
        with self.assertRaisesRegex(ValueError, "unrequested county"):
            coverage.merge_snapshot(self.existing, [record("Wrong", "Down")], {"Monaghan"})


if __name__ == "__main__":
    unittest.main()
