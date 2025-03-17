# GAA Pitch Finder

A comprehensive dataset and analysis tool for GAA pitches across Ireland, including rainfall patterns, elevation data, and club information.

## Project Structure

```
gaapitchfinder/
├── gaapitchfinder_data.csv    # Main dataset
├── additional_data/           # Supplementary data
│   └── club_images/          # Club crest images
├── output/                    # Generated content
│   ├── visualizations/       # Maps and charts
│   └── reports/              # Analysis reports
├── scripts/                   # Python analysis scripts
│   ├── gaa_rainfall_analysis.py    # Rainfall analysis and visualization
│   ├── cleanup_rainfall.py         # Data cleanup and API fetching
│   ├── merge_data.py              # Data merging utilities
│   ├── link_crest_images.py       # Club crest image processing
│   └── search_club_images.py      # Image search utilities
├── venv/                      # Python virtual environment
├── requirements.txt           # Python dependencies
├── LICENSE                    # MIT License
└── README.md                  # This file
```

## Features

- Comprehensive GAA pitch location database
- County-level rainfall statistics and analysis
- Interactive and static rainfall visualizations
- Elevation data for each pitch location
- Club crest image collection and processing
- Detailed statistical analysis reports

## Data Sources

- GAA club locations and information
- Open-Meteo API for rainfall data
- OpenStreetMap elevation data
- Club crest images from official sources

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/gaapitchfinder.git
cd gaapitchfinder
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Rainfall Analysis

```bash
python scripts/gaa_rainfall_analysis.py
```

This will generate:
- Interactive rainfall heatmap (`output/visualizations/rainfall_heatmap.html`)
- Static rainfall visualization (`output/visualizations/rainfall_heatmap.png`)
- Analysis report (`output/reports/gaa_rainfall_analysis.md`)

### Data Cleanup

```bash
python scripts/cleanup_rainfall.py
```

This script will:
- Identify clubs missing rainfall data
- Fetch missing data from the Open-Meteo API
- Update the main dataset

## Dataset Description

The main dataset (`gaapitchfinder_data.csv`) contains the following columns:

- `File`: Source file identifier
- `Club`: Name of the GAA club
- `Pitch`: Name of the pitch/ground
- `Code`: Club code (if available)
- `Latitude`: Decimal degrees (WGS84)
- `Longitude`: Decimal degrees (WGS84)
- `Province`: Irish province (Connacht, Leinster, Munster, Ulster)
- `Country`: Country (Ireland)
- `Division`: GAA division
- `County`: County where the club is located
- `Directions`: Google Maps link to the pitch
- `Twitter`: Club's Twitter handle
- `Elevation`: Height above sea level in meters
- `annual_rainfall`: Total annual rainfall in millimeters
- `rain_days`: Number of days with precipitation

## Output Files

### Visualizations
- `output/visualizations/rainfall_heatmap.html`: Interactive map showing rainfall patterns
- `output/visualizations/rainfall_heatmap.png`: Static visualization of rainfall distribution

### Reports
- `output/reports/gaa_rainfall_analysis.md`: Detailed analysis of rainfall patterns

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


