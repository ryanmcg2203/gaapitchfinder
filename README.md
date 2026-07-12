# GAA Pitch Finder

GAA Pitch Finder is a static website and open dataset for GAA pitches in Ireland and around the world. It includes an interactive Leaflet map, Google Maps directions, blog/content pages, and analysis scripts for rainfall, elevation, and OpenStreetMap coverage.

The main dataset currently contains 1,988 pitch records with coordinates, elevation, rainfall data, club details, and directions links.

`gaapitchfinder_data.csv` is the canonical base dataset. Scripts should treat it as read-only input and write durable enrichments to `data/derived/`, with reports and charts going to `output/` and site assets going to `site/`.

## Project Structure

```text
gaapitchfinder/
├── site/                         # Public GitHub Pages website
│   ├── index.html                # Main Leaflet pitch map
│   ├── pitch-of-the-day.html     # Daily featured pitch page
│   ├── directions.html           # Browseable directions page
│   ├── blog/                     # Static blog posts
│   ├── css/                      # Shared site styles
│   ├── img/                      # Logo and image assets
│   └── vendor/                   # Vendored Leaflet assets
├── map/                          # Standalone/legacy Leaflet map
├── data/
│   └── derived/                  # Durable generated datasets and coverage reports
├── scripts/                      # Data generation and analysis scripts
├── output/
│   ├── reports/                  # Generated analysis reports
│   └── visualizations/           # Generated maps and charts
├── additional_data/              # Supplementary assets and source data
├── gaapitchfinder_data.csv       # Main pitch dataset
└── requirements.txt              # Python dependencies
```

## Data Flow

```text
gaapitchfinder_data.csv
  -> data/derived/               # durable enriched datasets and coverage outputs
  -> site/data.json              # generated site payload
  -> output/reports/             # markdown analysis output
  -> output/visualizations/      # charts and HTML maps
```

## Website

The public site lives in `site/` and is deployed to GitHub Pages.

The Leaflet pages and Pitch of the Day load a generated `site/data.json` file. Static club and county pages are generated into `site/clubs/` and `site/counties/`. These generated outputs are intentionally ignored by git and are created from the main CSV:

```bash
python3 scripts/generate_map_data.py
python3 scripts/generate_club_pages.py
```

GitHub Actions runs this generator automatically before deploying `site/`, so production builds do not need `site/data.json` committed.

For local static testing, generate the data file and serve the site directory:

```bash
python3 scripts/generate_map_data.py
python3 scripts/generate_club_pages.py
python3 -m http.server 8000 --directory site
```

Then open `http://localhost:8000`.

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

### Generate Club And County Pages

```bash
python3 scripts/generate_club_pages.py
```

Creates static SEO-focused club pages in `site/clubs/`, county pages in `site/counties/`, and regenerates `site/sitemap.xml`.

### Audit Generated Site

```bash
python3 scripts/audit_site.py
```

Checks generated HTML links, required SEO tags, sitemap freshness metadata, and unsafe directions URLs in `site/data.json`.

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
- `generate_club_pages.py`: builds static club pages, county pages, directories, and sitemap entries
- `audit_site.py`: checks generated site output for link safety and SEO regressions
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
- `Elevation`: Elevation in meters
- `annual_rainfall`: Annual rainfall in millimeters
- `rain_days`: Number of days with precipitation

## Data Sources

- GAA club and pitch locations collected and verified over time
- Open-Meteo rainfall data
- Elevation data
- OpenStreetMap pitch geometry and coverage checks
- Club images and supplementary assets in `additional_data/`

## Deployment

Deployment is handled by `.github/workflows/deploy.yml` on pushes to `main` or manual workflow dispatch. The workflow:

1. Checks out the repository.
2. Sets up Python.
3. Runs `scripts/generate_map_data.py`.
4. Runs `scripts/generate_club_pages.py`.
5. Uploads `site/` as the GitHub Pages artifact.
6. Deploys to GitHub Pages.

## License

The website code is licensed under the MIT License. See `LICENSE`.

The dataset in `gaapitchfinder_data.csv` is licensed under the Creative Commons Attribution 4.0 International License (CC BY 4.0). If you use the dataset, please credit GAA Pitch Finder by Ryan McGuinness and link to `https://gaapitchfinder.com`.

See `ATTRIBUTION.md` for suggested wording.
