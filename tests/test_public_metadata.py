from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from generate_public_metadata import (  # noqa: E402
    DATASET_HEAD_END,
    DATASET_HEAD_START,
    DATASET_SUMMARY_END,
    DATASET_SUMMARY_START,
    README_END,
    README_START,
    DatasetMetadata,
    replace_generated_block,
    update_dataset_page,
    update_readme,
)


class PublicMetadataTests(unittest.TestCase):
    def setUp(self):
        self.metadata = DatasetMetadata(
            record_count=1989,
            last_modified="2026-08-06",
        )

    def test_generated_metadata_updates_readme_and_dataset_page(self):
        readme = f"Before\n{README_START}\nstale\n{README_END}\nAfter\n"
        dataset_page = (
            f"<head>{DATASET_HEAD_START}\nstale\n{DATASET_HEAD_END}</head>"
            f"<body>{DATASET_SUMMARY_START}\nstale\n{DATASET_SUMMARY_END}</body>"
        )

        updated_readme = update_readme(readme, self.metadata)
        updated_dataset = update_dataset_page(dataset_page, self.metadata)

        self.assertIn("1,989 pitch records", updated_readme)
        self.assertIn("As of 6 August 2026", updated_readme)
        self.assertIn('content="1989"', updated_dataset)
        self.assertIn('datetime="2026-08-06"', updated_dataset)

        schema_match = re.search(
            r'<script type="application/ld\+json">(.*?)</script>', updated_dataset
        )
        self.assertIsNotNone(schema_match)
        schema = json.loads(schema_match.group(1))
        dataset = schema["@graph"][1]
        self.assertEqual(dataset["dateModified"], "2026-08-06")
        self.assertEqual(dataset["additionalProperty"]["value"], 1989)

    def test_generated_block_requires_exactly_one_marker_pair(self):
        with self.assertRaisesRegex(ValueError, "found 0"):
            replace_generated_block("no markers", "start", "end", "replacement")

        duplicated = "start old end start old end"
        with self.assertRaisesRegex(ValueError, "found 2"):
            replace_generated_block(duplicated, "start", "end", "replacement")


if __name__ == "__main__":
    unittest.main()
