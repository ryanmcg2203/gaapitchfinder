import csv
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from geometry_checkpoint import GeometryCheckpoint, ResumeError


SOURCE = b"Club,Latitude,Longitude\nAlpha,53.100,-8.200\nBeta,54.1,-7.2\n"


def results(source=SOURCE, statuses=("osm_polygon", "")):
    rows = list(csv.reader(io.StringIO(source.decode())))
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(rows[0] + ["geometry_source"])
    for row, status in zip(rows[1:], statuses):
        writer.writerow(row + [status])
    return output.getvalue()


class GeometryCheckpointTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.path = self.directory / "checkpoint.json"
        self.output = self.directory / "geometry.csv"
        self.store = self.make_store()

    def make_store(self, source=SOURCE, method="method-v1"):
        return GeometryCheckpoint(self.path, self.output, source, method)

    def test_unchanged_run_retains_results_and_only_completed_indices(self):
        self.assertEqual(self.store.load(), (None, set()))
        self.store.save(results(), {0})
        self.assertEqual(self.store.load(), (results(), {0}))
        self.assertEqual(self.output.read_bytes(), results().encode())

    def test_changed_source_is_rejected_without_modifying_saved_files(self):
        self.store.save(results(), {0})
        original_files = (self.path.read_bytes(), self.output.read_bytes())
        header, alpha, beta = SOURCE.splitlines(keepends=True)
        variants = {
            "reordered": header + beta + alpha,
            "inserted": SOURCE + b"Gamma,52.1,-6.2\n",
            "deleted": header + alpha,
            "moved": SOURCE.replace(b"53.100", b"53.101"),
            "renamed": SOURCE.replace(b"Alpha", b"Renamed"),
        }
        for kind, source in variants.items():
            with self.subTest(kind=kind), self.assertRaisesRegex(ResumeError, "dataset changed"):
                self.make_store(source).load()
            self.assertEqual(original_files, (self.path.read_bytes(), self.output.read_bytes()))

    def test_changed_method_is_rejected(self):
        self.store.save(results(), {0})
        with self.assertRaisesRegex(ResumeError, "method changed"):
            self.make_store(method="method-v2").load()

    def test_legacy_checkpoint_and_orphan_csv_are_not_trusted(self):
        self.path.write_text('{"processed_indices": [0]}')
        with self.assertRaisesRegex(ResumeError, "legacy"):
            self.store.load()
        self.path.unlink()
        self.output.write_text(results())
        with self.assertRaisesRegex(ResumeError, "without a verifiable snapshot"):
            self.store.load()

    def test_failed_snapshot_replace_preserves_previous_committed_state(self):
        self.store.save(results(), {0})
        before = (self.path.read_bytes(), self.output.read_bytes())
        with patch("geometry_checkpoint.os.replace", side_effect=OSError("interrupted")):
            with self.assertRaises(OSError):
                self.store.save(results(statuses=("osm_polygon", "not_found")), {0, 1})
        self.assertEqual(before, (self.path.read_bytes(), self.output.read_bytes()))
        self.assertEqual(self.store.load(), (results(), {0}))
        self.assertEqual(sorted(p.name for p in self.directory.iterdir()), ["checkpoint.json", "geometry.csv"])

    def test_export_failure_recovers_results_and_completion_together(self):
        from geometry_checkpoint import atomic_write

        self.store.save(results(), {0})
        completed = results(statuses=("osm_polygon", "not_found"))

        def fail_export(path, text):
            if Path(path) == self.output:
                raise OSError("export interrupted")
            atomic_write(path, text)

        with patch("geometry_checkpoint.atomic_write", side_effect=fail_export):
            with self.assertRaises(OSError):
                self.store.save(completed, {0, 1})
        self.assertEqual(self.store.load(), (completed, {0, 1}))
        self.assertEqual(self.output.read_bytes(), completed.encode())
        self.output.unlink()
        self.assertEqual(self.store.load(), (completed, {0, 1}))
        self.assertTrue(self.output.exists())

    def test_malformed_and_corrupt_snapshots_fail_without_overwriting_export(self):
        for corrupt in ["{", "[]", '{"version":1}']:
            with self.subTest(corrupt=corrupt):
                self.path.write_text(corrupt)
                with self.assertRaises(ResumeError):
                    self.store.load()
        self.store.save(results(), {0})
        state = json.loads(self.path.read_text())
        state["csv"] = state["csv"].replace("Alpha", "Wrong")
        self.path.write_text(json.dumps(state))
        with self.assertRaisesRegex(ResumeError, "checksum"):
            self.store.load()
        self.assertEqual(self.output.read_bytes(), results().encode())

    def test_cannot_commit_missing_results_bad_indices_or_wrong_identity(self):
        for processed in [{1}, {2}, {-1}, {True}]:
            with self.subTest(processed=processed), self.assertRaises(ResumeError):
                self.store.save(results(), processed)
        with self.assertRaisesRegex(ResumeError, "identities"):
            self.store.save(results().replace("Alpha", "Wrong"), {0})
        self.assertFalse(self.path.exists())


HAS_ANALYSIS_DEPENDENCIES = all(
    importlib.util.find_spec(name) is not None
    for name in ("numpy", "pandas", "requests", "scipy")
)


@unittest.skipUnless(HAS_ANALYSIS_DEPENDENCIES, "requires optional analysis dependencies")
class GeometryResumeIntegrationTests(unittest.TestCase):
    def test_retry_api_failure_without_requerying_success_and_reject_edits(self):
        import enrich_pitch_geometry as geometry

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.csv"
            output = root / "output.csv"
            checkpoint = root / "checkpoint.json"
            source.write_bytes(SOURCE)
            corners = {"nw": (53.101, -8.201), "ne": (53.101, -8.2),
                       "se": (53.1, -8.2), "sw": (53.1, -8.201)}
            with (
                patch.multiple(geometry, INPUT_CSV=str(source), OUTPUT_CSV=str(output),
                               CHECKPOINT_FILE=str(checkpoint), REQUEST_DELAY_S=0),
                patch("sys.stdout", new_callable=io.StringIO),
                patch.object(geometry, "query_overpass", side_effect=[[{"id": 42}], None]) as query,
                patch.object(geometry, "pick_best_element", return_value=({"id": 42}, {})),
                patch.object(geometry, "extract_geometry", return_value=(corners, "osm_polygon")),
            ):
                geometry.main()
                self.assertEqual(query.call_count, 2)
                state = json.loads(checkpoint.read_text())
                self.assertEqual(state["processed_indices"], [0])
                query.reset_mock(side_effect=True)
                query.return_value = []
                # A successful empty response is a completed no-match, not an API error.
                with patch.object(geometry, "pick_best_element", return_value=(None, None)):
                    geometry.main()
                query.assert_called_once_with(54.1, -7.2)
                rows = list(csv.DictReader(io.StringIO(output.read_text())))
                self.assertEqual(rows[0]["Latitude"], "53.100")
                self.assertEqual(rows[0]["geometry_source"], "osm_polygon")
                self.assertEqual(rows[1]["geometry_source"], "not_found")
                query.reset_mock()
                geometry.main()
                query.assert_not_called()
                source.write_bytes(SOURCE.replace(b"Alpha", b"Changed"))
                with self.assertRaisesRegex(SystemExit, "dataset changed"):
                    geometry.main()
                query.assert_not_called()


if __name__ == "__main__":
    unittest.main()
