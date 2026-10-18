#!/usr/bin/env python3
"""Build the Jekyll-owned blog pages into the existing site tree."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
JEKYLL_DIR = ROOT_DIR / "jekyll"
SITE_BLOG_DIR = ROOT_DIR / "site" / "blog"


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="gaapitchfinder-jekyll-") as temp_dir:
        destination = Path(temp_dir) / "blog"
        subprocess.run(
            [
                "bundle",
                "exec",
                "jekyll",
                "build",
                "--source",
                str(JEKYLL_DIR),
                "--destination",
                str(destination),
                "--config",
                str(JEKYLL_DIR / "_config.yml"),
            ],
            cwd=ROOT_DIR,
            check=True,
        )
        for relative_path in ("index.html", "r-package.html"):
            source = destination / relative_path
            if not source.exists():
                raise FileNotFoundError(f"Jekyll did not generate {source}")
            shutil.copy2(source, SITE_BLOG_DIR / relative_path)

    print("Generated Jekyll blog pages ->", SITE_BLOG_DIR)


if __name__ == "__main__":
    main()
