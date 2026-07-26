from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from generate_map_data import build_map_records  # noqa: E402
from generate_club_pages import render_club_page  # noqa: E402
from site_build_utils import (  # noqa: E402
    ALLOWED_REFERENCE_HOSTS,
    ALLOWED_SOCIAL_HOSTS,
    build_club_page_records,
    row_coordinates,
    row_maps_url,
    sanitized_external_url,
)


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
        "Code": "",
        "Twitter": "",
        "Elevation": "",
        "annual_rainfall": "",
        "rain_days": "",
        "Wikipedia": "",
    }
    row.update(overrides)
    return row


class SiteBuildUtilsTests(unittest.TestCase):
    def test_row_coordinates_rejects_missing_and_invalid_values(self):
        self.assertIsNone(row_coordinates(pitch_row(Latitude="")))
        self.assertIsNone(row_coordinates(pitch_row(Longitude="unknown")))
        self.assertIsNone(row_coordinates({}))

    def test_row_coordinates_rejects_values_outside_world_bounds(self):
        self.assertIsNone(row_coordinates(pitch_row(Latitude="90.1")))
        self.assertIsNone(row_coordinates(pitch_row(Latitude="-90.1")))
        self.assertIsNone(row_coordinates(pitch_row(Longitude="180.1")))
        self.assertIsNone(row_coordinates(pitch_row(Longitude="-180.1")))
        self.assertEqual(
            row_coordinates(pitch_row(Latitude="90", Longitude="-180")),
            (90.0, -180.0),
        )

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

    def test_map_records_skip_coordinates_outside_world_bounds(self):
        records, skipped = build_map_records(
            [
                pitch_row(Club="Impossible Latitude", Latitude="999"),
                pitch_row(Club="Impossible Longitude", Longitude="-999"),
                pitch_row(Club="Valid"),
            ]
        )

        self.assertEqual(skipped, 2)
        self.assertEqual([record["c"] for record in records], ["Valid"])

    def test_external_url_sanitization_uses_allowlists(self):
        self.assertEqual(
            sanitized_external_url(
                "https://en.wikipedia.org/wiki/Test", ALLOWED_REFERENCE_HOSTS
            ),
            "https://en.wikipedia.org/wiki/Test",
        )
        self.assertEqual(
            sanitized_external_url("https://x.com/testclub", ALLOWED_SOCIAL_HOSTS),
            "https://x.com/testclub",
        )
        self.assertEqual(
            sanitized_external_url(
                "https://example.com/wiki/Test", ALLOWED_REFERENCE_HOSTS
            ),
            "",
        )
        self.assertEqual(
            sanitized_external_url("javascript:alert(1)", ALLOWED_SOCIAL_HOSTS),
            "",
        )

    def test_club_page_records_disambiguate_slug_collisions(self):
        pages, row_to_url = build_club_page_records(
            [
                pitch_row(Club="St. John's", County="Cork"),
                pitch_row(Club="St Johns", County="Cork"),
            ]
        )

        self.assertEqual(
            sorted(page["slug"] for page in pages), ["st-john-s-cork", "st-johns-cork"]
        )
        self.assertEqual(row_to_url[0], "clubs/st-john-s-cork.html")
        self.assertEqual(row_to_url[1], "clubs/st-johns-cork.html")

    def test_generated_club_page_escapes_content_and_styles_wikipedia_action(self):
        row = pitch_row(
            Club='Test <Club>',
            Pitch='Ground "One"',
            Wikipedia="https://en.wikipedia.org/wiki/Test_Club",
            Twitter="https://twitter.com/testclub",
        )
        page = {
            "club": row["Club"].strip(),
            "location_label": "Galway",
            "slug": "test-club-galway",
            "rel_url": "clubs/test-club-galway.html",
            "rows": [row],
        }

        html = render_club_page(page, [page])

        self.assertIn("Test &lt;Club&gt;", html)
        self.assertIn("Ground &quot;One&quot;", html)
        self.assertIn('class="club-action club-action-reference"', html)
        self.assertNotIn(">Wikipedia</a>", html)


if __name__ == "__main__":
    unittest.main()
