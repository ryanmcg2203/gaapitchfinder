from __future__ import annotations

import html
from pathlib import Path


SITE_NAME = "GAA Pitch Finder"
CONTACT_EMAIL = "gaapitchfinder@gmail.com"
REPOSITORY_URL = "https://github.com/ryanmcg2203/gaapitchfinder"
SITE_BASE_URL = "https://gaapitchfinder.com"

NAV_ITEMS = (
    ("map", "Map", "/"),
    ("clubs", "Clubs", "/clubs/"),
    ("counties", "Counties", "/counties/"),
    ("directions", "Directions", "/directions.html"),
    ("daily-pitch", "Daily Pitch", "/pitch-of-the-day.html"),
    ("blog", "Blog", "/blog/"),
    ("dataset", "Dataset", "/dataset.html"),
    ("about", "About", "/about.html"),
)

STATIC_TEMPLATE_TOKENS = {
    "analytics",
    "footer",
    "navigation",
    "navigation_script",
}


def esc(value: object) -> str:
    return html.escape(str(value or ""))


def esc_attr(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def absolute_url(path: str) -> str:
    return f"{SITE_BASE_URL}/{path.lstrip('/')}"


def analytics_html() -> str:
    return '<script src="/js/ga.js" defer></script>'


def navigation_script_html() -> str:
    return '<script src="/js/navigation.js" defer></script>'


def navigation_html(active: str | None = None) -> str:
    desktop_links = []
    drawer_links = []
    for key, label, url in NAV_ITEMS:
        active_attribute = ' class="active"' if key == active else ""
        desktop_links.append(
            f'    <li><a href="{url}"{active_attribute}>{label}</a></li>'
        )
        drawer_links.append(f'  <a href="{url}">{label}</a>')

    return f"""<nav class="site-nav">
  <a href="/" class="nav-logo">
    <img src="/img/logo-icon.png" alt="GAA Pitch Finder logo" width="36" height="36" style="border-radius:50%;">
    GAA Pitch Finder
  </a>
  <ul class="nav-links">
{chr(10).join(desktop_links)}
  </ul>
  <a href="/donate.html" class="nav-donate">Donate</a>
  <button class="nav-hamburger" id="hamburger" type="button" aria-label="Open menu" aria-expanded="false" aria-controls="nav-drawer">
    <span></span><span></span><span></span>
  </button>
</nav>
<div class="nav-drawer" id="nav-drawer" aria-hidden="true" inert>
  <button class="drawer-close" id="drawer-close" type="button" aria-label="Close menu">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
  </button>
{chr(10).join(drawer_links)}
  <a href="/privacy.html">Privacy</a>
  <a href="/donate.html">Donate</a>
</div>"""


def footer_html() -> str:
    return f"""<footer class="site-footer">
  &copy; {SITE_NAME} &nbsp;&middot;&nbsp; <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a> &nbsp;&middot;&nbsp; <a href="/dataset.html">Dataset</a> &nbsp;&middot;&nbsp; <a href="{REPOSITORY_URL}" target="_blank" rel="noopener noreferrer">GitHub</a> &nbsp;&middot;&nbsp; <a href="/privacy.html">Privacy</a>
</footer>"""


def active_navigation_for_path(relative_path: Path | str) -> str | None:
    path = Path(relative_path).as_posix().lstrip("/")
    if path == "index.html":
        return "map"
    if path.startswith("clubs/"):
        return "clubs"
    if path.startswith("counties/"):
        return "counties"
    if path == "directions.html":
        return "directions"
    if path == "pitch-of-the-day.html":
        return "daily-pitch"
    if path.startswith("blog/"):
        return "blog"
    if path in {"dataset.html", "data-quality.html"}:
        return "dataset"
    if path == "about.html":
        return "about"
    return None


def render_static_template(template: str, relative_path: Path | str) -> str:
    replacements = {
        "analytics": analytics_html(),
        "footer": footer_html(),
        "navigation": navigation_html(active_navigation_for_path(relative_path)),
        "navigation_script": navigation_script_html(),
    }
    rendered = template
    for token, value in replacements.items():
        rendered = rendered.replace(f"{{{{ {token} }}}}", value)

    unresolved = [
        token for token in STATIC_TEMPLATE_TOKENS if f"{{{{ {token} }}}}" in rendered
    ]
    if unresolved:
        raise ValueError(f"Unresolved shared template tokens: {', '.join(unresolved)}")
    return rendered
