"""Atomic geometry snapshots; the CSV is an export, not resume state."""

import csv
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile


class ResumeError(ValueError):
    """Existing results cannot safely be associated with this run."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, text):
    """Replace a file only after its complete UTF-8 contents are flushed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as target:
            temporary = Path(target.name)
            target.write(text)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class GeometryCheckpoint:
    """Bind positional results to the exact source bytes and method fingerprint.

    A single atomic JSON snapshot stores both results and completion state.
    An interrupted CSV export can therefore be repaired on the next load.
    """

    def __init__(self, checkpoint_path, output_path, source_bytes, method):
        self.path = Path(checkpoint_path)
        self.output_path = Path(output_path)
        self.source_digest = digest(source_bytes)
        self.method = method
        self.source_rows = list(csv.reader(io.StringIO(source_bytes.decode("utf-8"))))
        self.row_count = len(self.source_rows) - 1

    def _error(self, reason):
        return ResumeError(
            f"Cannot safely resume geometry enrichment: {reason}. "
            f"Archive both {self.path} and {self.output_path}, then rerun to start "
            "fresh. Existing files have not been reset."
        )

    def _validate_results(self, csv_text, processed):
        if not isinstance(csv_text, str) or not isinstance(processed, list):
            raise self._error("invalid result or completion state")
        if any(type(i) is not int or not 0 <= i < self.row_count for i in processed):
            raise self._error("invalid processed row indices")
        if len(set(processed)) != len(processed):
            raise self._error("duplicate processed row indices")
        rows = list(csv.reader(io.StringIO(csv_text), strict=True))
        if len(rows) != len(self.source_rows) or not rows:
            raise self._error("result row count does not match source")
        source_width = len(self.source_rows[0])
        if any(row[:source_width] != original for row, original in zip(rows, self.source_rows)):
            raise self._error("result identities or source values do not match input")
        if "geometry_source" not in rows[0] or any(len(row) != len(rows[0]) for row in rows):
            raise self._error("invalid result columns")
        status_column = rows[0].index("geometry_source")
        for i in processed:
            if rows[i + 1][status_column] not in {"osm_polygon", "osm_bbox", "not_found"}:
                raise self._error("completed row has no durable result")

    def load(self):
        if not self.path.exists():
            if self.output_path.exists():
                raise self._error("CSV exists without a verifiable snapshot")
            return None, set()
        try:
            state = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(state, dict) or state.get("version") != 1:
                raise self._error("legacy or unsupported checkpoint")
            if state.get("source_sha256") != self.source_digest:
                raise self._error("source dataset changed")
            if state.get("method") != self.method:
                raise self._error("enrichment method changed")
            csv_text = state["csv"]
            processed = state["processed_indices"]
            if not isinstance(csv_text, str) or digest(csv_text.encode("utf-8")) != state["csv_sha256"]:
                raise self._error("result checksum mismatch")
            self._validate_results(csv_text, processed)
        except (KeyError, UnicodeError, json.JSONDecodeError, csv.Error) as error:
            raise self._error("malformed snapshot") from error
        # Recover a missing, stale, or interrupted export from committed results.
        atomic_write(self.output_path, csv_text)
        return csv_text, set(processed)

    def save(self, csv_text, processed):
        processed = sorted(processed)
        self._validate_results(csv_text, processed)
        state = {
            "version": 1,
            "source_sha256": self.source_digest,
            "method": self.method,
            "csv": csv_text,
            "csv_sha256": digest(csv_text.encode("utf-8")),
            "processed_indices": processed,
        }
        # Results and completion markers become durable in the same replacement.
        atomic_write(self.path, json.dumps(state, ensure_ascii=False) + "\n")
        atomic_write(self.output_path, csv_text)
