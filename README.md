# GAA Pitch Finder

GAA Pitch Finder is a static website and open dataset for GAA pitches in Ireland and around the world. It includes an interactive Leaflet map, Google Maps directions, blog/content pages, and analysis scripts for rainfall, elevation, and OpenStreetMap coverage.

<!-- dataset-summary:start -->
As of 6 August 2026, the main dataset contains 1,989 pitch records with coordinates, elevation, rainfall data, club details, and directions links.
<!-- dataset-summary:end -->

`gaapitchfinder_data.csv` is the canonical base dataset. Scripts should treat it as read-only input and write durable enrichments to `data/derived/`, with reports and charts going to `output/` and site assets going to `site/`.

## Project Structure

```text
gaapitchfinder/
├── site/                         # Public GitHub Pages website
│   ├── index.html                # Main Leaflet pitch map
│   ├── pitch-of-the-day.html     # Daily featured pitch page
│   ├── directions.html           # Browseable directions page
│   ├── clubs/                    # Generated club pages
│   ├── counties/                 # Generated county pages
│   ├── downloads/                # Generated CSV, GeoJSON, and schema downloads
│   ├── data-quality.html          # Generated data health and provenance dashboard
│   ├── data-quality.json          # Machine-readable quality metric contract
│   ├── blog/                     # Generated static blog posts
│   ├── css/                      # Shared site styles
│   ├── img/                      # Logo and image assets
│   └── vendor/                   # Vendored Leaflet assets
├── templates/
│   └── static/                   # Hand-authored page content and metadata
├── data/
│   └── derived/                  # Durable generated datasets and coverage reports
├── scripts/                      # Data generation and analysis scripts
│   ├── site_build_utils.py       # Shared helpers for generators and tests
│   ├── enrich_club_wikipedia.py  # Review-first Wikipedia/Wikidata suggestions
│   ├── generate_map_data.py      # Builds site/data.json
│   ├── generate_dataset_downloads.py # Builds stable public data downloads
│   ├── dataset_contract.py       # Shared fields, schema, and GeoJSON contract
│   ├── generate_public_metadata.py # Syncs public dataset counts and dates
│   ├── generate_data_quality.py  # Builds the public health report and JSON contract
│   ├── generate_static_pages.py  # Renders shared chrome into hand-authored pages
│   ├── site_builder/              # Shared templates and generated-page build modules
│   └── generate_club_pages.py    # Builds club/county pages and sitemap
├── tests/                        # Unit tests for site build helpers
├── .github/workflows/deploy.yml  # PR validation and GitHub Pages deployment
├── output/
│   ├── reports/                  # Generated analysis reports
│   └── visualizations/           # Generated maps and charts
├── additional_data/              # Supplementary assets and source data
├── ATTRIBUTION.md                # Suggested dataset attribution wording
├── gaapitchfinder_data.csv       # Main pitch dataset
└── requirements.txt              # Python dependencies
```

## Data Flow

```text
gaapitchfinder_data.csv
  -> data/derived/               # durable enriched datasets and coverage outputs
  -> site/data.json              # generated site payload
  -> site/downloads/             # canonical CSV, GeoJSON, and JSON schema
  -> output/reports/             # markdown analysis output
  -> output/visualizations/      # charts and HTML maps
```

## Website

The public site lives in `site/` and is deployed to GitHub Pages.

The Leaflet pages and Pitch of the Day load a generated `site/data.json` file. Hand-authored pages live in `templates/static/` and are rendered with the shared navigation, footer, analytics hook, and drawer behavior. Static club and county pages are generated into `site/clubs/` and `site/counties/`. The data-backed outputs are intentionally ignored by git and are created from the main CSV:

```bash
python3 scripts/generate_map_data.py
python3 scripts/generate_dataset_downloads.py
python3 scripts/generate_static_pages.py
python3 scripts/generate_public_metadata.py
python3 scripts/generate_data_quality.py
python3 scripts/generate_club_pages.py
```

GitHub Actions runs this generator automatically before deploying `site/`, so production builds do not need `site/data.json` committed.

For local static testing over plain HTTP, generate the data file and serve the site directory:

```bash
python3 scripts/generate_map_data.py
python3 scripts/generate_dataset_downloads.py
python3 scripts/generate_static_pages.py
python3 scripts/generate_public_metadata.py
python3 scripts/generate_data_quality.py
python3 scripts/generate_club_pages.py
python3 scripts/audit_site.py
python3 -m http.server 8000 --directory site
```

Then open `http://localhost:8000`. HTTPS is provided by the production host, not the local Python server.

### CARTO Basemap Key

The homepage map uses CARTO raster basemaps when `site/js/config.js` defines a
`cartoBasemapKey`. The committed config file is intentionally empty, so local
development falls back to standard OpenStreetMap tiles without secrets.

For local CARTO testing, temporarily set `cartoBasemapKey` in `site/js/config.js`
and do not commit that key.

For production, add the key as a GitHub Actions repository secret named
`CARTO_BASEMAP_KEY`. The deploy workflow writes `site/js/config.js` from that
secret immediately before uploading the GitHub Pages artifact.

## Setup

```bash
git clone https://github.com/ryanmcg2203/gaapitchfinder.git
cd gaapitchfinder
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Common Tasks

### Generate Map Data

```bash
python3 scripts/generate_map_data.py
```

Creates `site/data.json` from `gaapitchfinder_data.csv`.

### Generate Static Pages

```bash
python3 scripts/generate_static_pages.py
```

Renders the templates in `templates/static/` into `site/`. Shared page chrome is owned by `scripts/site_builder/shared.py`; generated output should not be edited directly.

### Generate Club And County Pages

```bash
python3 scripts/generate_club_pages.py
```

Creates static SEO-focused club pages in `site/clubs/`, county pages in `site/counties/`, and regenerates `site/sitemap.xml`.
Sitemap modification dates come from Git history, so run this command from a Git checkout with the relevant history available.

### Generate Dataset Downloads

```bash
python3 scripts/generate_dataset_downloads.py
```

Copies the canonical CSV to its stable public URL and generates the GeoJSON and versioned JSON data dictionary in `site/downloads/`. Release dates and revisions come from the latest Git commit that changed the canonical CSV, keeping repeated builds reproducible.

### Generate Public Dataset Metadata

```bash
python3 scripts/generate_public_metadata.py
```

Synchronizes the exact CSV record count and Git-derived dataset date in this README and the public dataset page. Run it after committing dataset changes so the published date reflects the source commit.

### Generate Dataset Health Report

```bash
python3 scripts/generate_data_quality.py
```

Builds the deterministic `site/data-quality.json` metric contract and the public `site/data-quality.html` dashboard from the canonical CSV, Git history, and the optional checked-in OSM coverage snapshot. Missing optional sources are published as unavailable rather than zero.

### Audit Generated Site

```bash
python3 scripts/audit_site.py
```

Checks generated HTML links, shared template consistency, required SEO tags, sitemap freshness metadata, unsafe directions URLs in `site/data.json`, and the structure, feature count, and freshness of all dataset downloads.

### Run Tests

```bash
python3 -m unittest discover -s tests
```

Runs the unit tests for shared site-build helpers and map-data generation behavior.

### Wikipedia Link Enrichment

```bash
python3 scripts/enrich_club_wikipedia.py --limit 25
python3 scripts/enrich_club_wikipedia.py --county Leitrim --county Monaghan
python3 scripts/enrich_club_wikipedia.py --club "Portobello GAA"
```

Writes review-first Wikipedia/Wikidata link suggestions to `data/derived/club_wikipedia_links*.csv`. Suggested links should be reviewed before being copied into the public dataset. See `data/derived/README.md` for the full workflow and output statuses.

### Rainfall Analysis

```bash
python3 scripts/analyze_pitch_rainfall.py
```

Creates:

- `output/visualizations/rainfall_heatmap.png`
- `output/visualizations/rainfall_heatmap.html`
- `output/reports/gaa_rainfall_analysis.md`

### Elevation Analysis

```bash
python3 scripts/analyze_pitch_elevation.py
```

Creates:

- `output/visualizations/elevation_distribution.png`
- `output/reports/gaa_elevation_analysis.md`

### OpenStreetMap Coverage Check

```bash
python3 scripts/analyze_osm_coverage.py
```

Checks nearby OSM pitch polygons for each club and writes `data/derived/osm_coverage_report.csv`.

You can limit the check to one or more counties:

```bash
python3 scripts/analyze_osm_coverage.py Monaghan Down
```

### OpenStreetMap Geometry Enrichment

```bash
python3 scripts/enrich_pitch_geometry.py
```

Attempts to match each pitch to OSM geometry and write pitch dimensions, orientation, corner coordinates, and source metadata to `data/derived/pitch_geometry.csv`.

This script uses the Overpass API, includes request delays, and supports checkpoint/resume with `data/derived/.pitch_geometry_checkpoint.json`.

## Script Roles

- `generate_map_data.py`: builds the compact JSON payload used by the public site
- `generate_dataset_downloads.py`: publishes the stable CSV, GeoJSON, and schema downloads
- `dataset_contract.py`: defines field metadata, release versioning, and GeoJSON conversion
- `generate_public_metadata.py`: synchronizes public dataset counts and last-updated dates
- `generate_data_quality.py`: publishes deterministic quality metrics, source lineage, freshness, and known limitations
- `generate_static_pages.py`: renders hand-authored templates with the shared site chrome
- `generate_club_pages.py`: builds static club pages, county pages, directories, and sitemap entries
- `site_builder/`: owns shared HTML, page templates, build orchestration, and sitemap behavior
- `audit_site.py`: checks generated site output for link safety and SEO regressions
- `site_build_utils.py`: shared parsing, URL-safety, slug, and grouping helpers used by site generators
- `enrich_club_wikipedia.py`: creates review-first Wikipedia/Wikidata link suggestions in `data/derived/`
- `analyze_pitch_rainfall.py`: creates rainfall reports and visualizations
- `analyze_pitch_elevation.py`: creates elevation reports and visualizations
- `analyze_osm_coverage.py`: produces an OSM coverage report in `data/derived/`
- `enrich_pitch_geometry.py`: creates a reusable geometry-enriched derivative dataset

## Dataset Columns

`gaapitchfinder_data.csv` contains:

- `File`: Source region identifier
- `Club`: Club name
- `Pitch`: Pitch or ground name
- `Code`: Club code or sport code, where available
- `Latitude`: Decimal latitude (WGS84)
- `Longitude`: Decimal longitude (WGS84)
- `Province`: Irish province, where applicable
- `Country`: Country
- `Division`: GAA division or county grouping
- `County`: County, division, state, or local grouping
- `Directions`: Google Maps directions link
- `Twitter`: Club Twitter/X URL, where available
- `Wikipedia`: Reviewed club Wikipedia URL, where available
- `Elevation`: Elevation in meters
- `annual_rainfall`: Annual rainfall in millimeters
- `rain_days`: Number of days with precipitation

The public [dataset page](https://gaapitchfinder.com/dataset.html) and machine-readable `site/downloads/schema.json` define logical types, units, nullability, controlled values, WGS 84 axis order, and compatibility expectations. Stable latest-version URLs are:

- `https://gaapitchfinder.com/downloads/gaapitchfinder.csv`
- `https://gaapitchfinder.com/downloads/gaapitchfinder.geojson`
- `https://gaapitchfinder.com/downloads/schema.json`

## Data Sources

- GAA club and pitch locations collected and verified over time
- Open-Meteo rainfall data
- Elevation data
- OpenStreetMap pitch geometry and coverage checks
- Club images and supplementary assets in `additional_data/`

## Deployment

Deployment is handled by `.github/workflows/deploy.yml`. Pull requests and pushes run validation; deployment only runs for `main`, including manual workflow dispatches from that branch. The workflow:

1. Checks out the repository.
2. Sets up pinned Python and Node versions.
3. Validates the canonical dataset and runs the Python and JavaScript tests.
4. Generates map data, club pages, county pages, redirects, and the sitemap once.
5. Audits the generated site.
6. Uploads that exact audited `site/` directory as the GitHub Pages artifact.
7. Deploys the previously uploaded artifact without checking out or rebuilding it.

## License

The website code is licensed under the MIT License. See `LICENSE`.

The dataset in `gaapitchfinder_data.csv` is licensed under the Creative Commons Attribution 4.0 International License (CC BY 4.0). If you use the dataset, please credit GAA Pitch Finder by Ryan McGuinness and link to `https://gaapitchfinder.com`.

See `ATTRIBUTION.md` for suggested wording.
