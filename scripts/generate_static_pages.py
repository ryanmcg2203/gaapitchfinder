#!/usr/bin/env python3
"""Render hand-authored static page templates into the deployable site tree."""

from __future__ import annotations

from pathlib import Path

from site_build_utils import SITE_DIR
from site_builder.shared import render_static_template


ROOT_DIR = SITE_DIR.parent
TEMPLATE_DIR = ROOT_DIR / "templates" / "static"


def render_static_pages(
    template_dir: Path = TEMPLATE_DIR, output_dir: Path = SITE_DIR
) -> list[Path]:
    outputs = []
    for template_path in sorted(template_dir.rglob("*.html")):
        relative_path = template_path.relative_to(template_dir)
        output_path = output_dir / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            render_static_template(template_path.read_text(), relative_path)
        )
        outputs.append(output_path)
    return outputs


def main() -> None:
    outputs = render_static_pages()
    print(f"Generated {len(outputs)} static pages from {TEMPLATE_DIR}")


if __name__ == "__main__":
    main()
