#!/usr/bin/env python3
"""Generate club pages, county directories, redirects, and the sitemap."""

from site_builder.build import main
from site_builder.pages import directory_initial, render_club_page
from site_builder.shared import analytics_html as ga_snippet


__all__ = ["directory_initial", "ga_snippet", "main", "render_club_page"]


if __name__ == "__main__":
    main()
