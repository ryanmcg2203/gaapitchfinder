from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
STATIC_TEMPLATE_SOURCES = tuple(
    path.relative_to(ROOT_DIR).as_posix()
    for path in sorted((ROOT_DIR / "templates" / "static").rglob("*.html"))
)
BUILD_SOURCES = (
    "README.md",
    "gaapitchfinder_data.csv",
    "scripts/build_metadata.py",
    "scripts/dataset_contract.py",
    "scripts/generate_club_pages.py",
    "scripts/generate_dataset_downloads.py",
    "scripts/generate_data_quality.py",
    "scripts/generate_map_data.py",
    "scripts/generate_public_metadata.py",
    "scripts/generate_static_pages.py",
    "scripts/site_build_utils.py",
    "scripts/site_builder/__init__.py",
    "scripts/site_builder/build.py",
    "scripts/site_builder/page_data.py",
    "scripts/site_builder/pages.py",
    "scripts/site_builder/shared.py",
    "scripts/site_builder/sitemap.py",
    "scripts/validate_dataset.py",
    "data/derived/osm_coverage_report.csv",
) + STATIC_TEMPLATE_SOURCES
COMMIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "Build Test",
    "GIT_AUTHOR_EMAIL": "build-test@example.com",
    "GIT_COMMITTER_NAME": "Build Test",
    "GIT_COMMITTER_EMAIL": "build-test@example.com",
}


def run(command, cwd, env=None):
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        command_text = " ".join(str(part) for part in command)
        raise AssertionError(
            f"Command failed ({command_text}):\n{result.stdout}{result.stderr}"
        )


def commit(repository, message, timestamp):
    env = os.environ.copy()
    env.update(COMMIT_IDENTITY)
    env["GIT_AUTHOR_DATE"] = timestamp
    env["GIT_COMMITTER_DATE"] = timestamp
    run(["git", "add", "--all"], repository, env)
    run(["git", "commit", "-q", "-m", message], repository, env)


def site_manifest(repository):
    site_dir = repository / "site"
    return {
        path.relative_to(site_dir).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in sorted(site_dir.rglob("*"))
        if path.is_file()
    }


def sitemap_dates(repository):
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    root = ET.parse(repository / "site/sitemap.xml").getroot()
    return {
        url.findtext("sm:loc", namespaces=namespace): url.findtext(
            "sm:lastmod", namespaces=namespace
        )
        for url in root.findall("sm:url", namespace)
    }


class DeterministicBuildTests(unittest.TestCase):
    def test_repeated_builds_follow_source_history_and_ignore_mtimes(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = Path(temporary_directory)
            for relative_path in BUILD_SOURCES:
                destination = repository / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT_DIR / relative_path, destination)

            tracked_site_files = subprocess.run(
                ["git", "ls-files", "site"],
                cwd=ROOT_DIR,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.splitlines()
            for relative_path in tracked_site_files:
                destination = repository / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT_DIR / relative_path, destination)

            run(["git", "init", "-q"], repository)
            commit(repository, "Initial sources", "2024-01-02T12:00:00+0000")

            with (repository / "templates/static/about.html").open("a") as output:
                output.write("\n")
            commit(repository, "Update about page", "2024-02-03T12:00:00+0000")

            with (repository / "scripts/site_builder/pages.py").open("a") as output:
                output.write("\n")
            commit(repository, "Update page generator", "2024-03-04T12:00:00+0000")

            (repository / "UNRELATED.md").write_text("Unrelated change\n")
            commit(repository, "Unrelated change", "2024-04-05T12:00:00+0000")

            build_commands = (
                [sys.executable, "scripts/generate_static_pages.py"],
                [sys.executable, "scripts/generate_map_data.py"],
                [sys.executable, "scripts/generate_dataset_downloads.py"],
                [sys.executable, "scripts/generate_public_metadata.py"],
                [sys.executable, "scripts/generate_data_quality.py"],
                [sys.executable, "scripts/generate_club_pages.py"],
            )
            for command in build_commands:
                run(command, repository)

            first_manifest = site_manifest(repository)
            dates = sitemap_dates(repository)
            self.assertEqual(dates["https://gaapitchfinder.com/"], "2024-01-02")
            self.assertEqual(
                dates["https://gaapitchfinder.com/about.html"], "2024-02-03"
            )
            self.assertEqual(
                dates["https://gaapitchfinder.com/clubs/"], "2024-03-04"
            )
            self.assertEqual(
                dates["https://gaapitchfinder.com/counties/"], "2024-03-04"
            )

            future_timestamp = 2524608000
            for path in repository.rglob("*"):
                if path.is_file() and ".git" not in path.parts:
                    os.utime(path, (future_timestamp, future_timestamp))

            for command in build_commands:
                run(command, repository)

            self.assertEqual(site_manifest(repository), first_manifest)


if __name__ == "__main__":
    unittest.main()
