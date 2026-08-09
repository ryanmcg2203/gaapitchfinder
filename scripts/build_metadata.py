from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path


class BuildMetadataError(RuntimeError):
    """Raised when deterministic build metadata cannot be read from Git."""


class GitBuildMetadata:
    """Resolve source modification dates from the repository's commit history."""

    def __init__(self, repository_root: Path):
        self.repository_root = repository_root.resolve()
        self._date_cache: dict[tuple[str, ...], str] = {}

    def last_modified_date(self, *source_paths: str | Path) -> str:
        relative_paths = tuple(
            sorted({self._relative_path(path) for path in source_paths})
        )
        if not relative_paths:
            raise ValueError("At least one source path is required")
        if relative_paths not in self._date_cache:
            self._date_cache[relative_paths] = self._read_git_date(relative_paths)
        return self._date_cache[relative_paths]

    def _relative_path(self, source_path: str | Path) -> str:
        path = Path(source_path)
        if path.is_absolute():
            try:
                path = path.resolve().relative_to(self.repository_root)
            except ValueError as error:
                raise ValueError(
                    f"Source path is outside the repository: {source_path}"
                ) from error
        return path.as_posix()

    def _read_git_date(self, relative_paths: tuple[str, ...]) -> str:
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%cs", "--", *relative_paths],
                cwd=self.repository_root,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as error:
            raise BuildMetadataError(
                f"Unable to read Git build metadata: {error}"
            ) from error
        value = result.stdout.strip()
        if result.returncode != 0 or not value:
            detail = result.stderr.strip() or "no matching commit was found"
            paths = ", ".join(relative_paths)
            raise BuildMetadataError(
                f"Unable to determine a Git date for {paths}: {detail}"
            )
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError as error:
            raise BuildMetadataError(
                f"Git returned an invalid date for {', '.join(relative_paths)}: {value}"
            ) from error
