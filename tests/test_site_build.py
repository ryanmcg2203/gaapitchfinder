from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from generate_map_data import build_map_records  # noqa: E402
from site_build_utils import row_coordinates, row_maps_url  # noqa: E402


def pitch_row(**overrides):
    row = {
        "File": "Ireland",
        "Club": "Test Club",
        "Pitch": "Test Ground",
        "Latitude": "53.1",
        "Longitude": "-8.2",
        "County": "Galway",
        "Country": "Ireland",
        "Province": "Connacht",
        "Division": "",
        "Directions": "",
    }
    row.update(overrides)
    return row


class SiteBuildUtilsTests(unittest.TestCase):
    def test_row_coordinates_rejects_missing_and_invalid_values(self):
        self.assertIsNone(row_coordinates(pitch_row(Latitude="")))
        self.assertIsNone(row_coordinates(pitch_row(Longitude="unknown")))
        self.assertIsNone(row_coordinates({}))

    def test_maps_url_rejects_untrusted_hosts_and_uses_coordinates(self):
        row = pitch_row(Directions="https://example.com/redirect")
        self.assertEqual(
            row_maps_url(row), "https://maps.google.com/?daddr=53.1,-8.2"
        )

    def test_map_records_skip_invalid_coordinates_and_keep_page_links_aligned(self):
        rows = [
            pitch_row(Club="Invalid", Latitude="bad"),
            pitch_row(Club="Valid"),
        ]

        records, skipped = build_map_records(rows)

        self.assertEqual(skipped, 1)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["c"], "Valid")
        self.assertEqual(records[0]["u"], "clubs/valid-galway.html")


if __name__ == "__main__":
    unittest.main()
