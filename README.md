# GAA Pitch Finder

A comprehensive dataset and analysis tool for GAA pitches across Ireland, including rainfall patterns, elevation data, and club information.

## Project Structure

```
gaapitchfinder/
├── gaapitchfinder_data.csv    # Main dataset containing club information
├── additional_data/          # Supplementary data files
│   └── club_images/         # Club crest images
├── output/                   # Generated content
│   ├── visualizations/      # Maps and charts
│   └── reports/            # Analysis reports
├── scripts/                 # Python analysis scripts
├── requirements.txt         # Project dependencies
└── venv/                   # Python virtual environment
```

## Features

- Comprehensive GAA club database with geographical coordinates
- Rainfall analysis and visualization
- Interactive maps with club locations
- County-level statistics and analysis

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
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Rainfall Analysis

To generate rainfall analysis and visualizations:
```bash
python scripts/gaa_rainfall_analysis.py
```

This will create:
- `output/visualizations/rainfall_heatmap.png`: Static map showing rainfall patterns
- `output/visualizations/rainfall_heatmap.html`: Interactive map with detailed information
- `output/reports/gaa_rainfall_analysis.md`: Detailed analysis report

### Elevation Analysis

To analyze pitch elevations:
```bash
python scripts/analyze_elevation.py
```

This will generate:
- `output/visualizations/elevation_heatmap.png`: Static map showing elevation patterns
- `output/visualizations/elevation_heatmap.html`: Interactive map with pitch details
- `output/reports/elevation_analysis.md`: Statistical analysis of pitch elevations

## Output Files

### Visualizations
- `rainfall_heatmap.png`: Static map showing rainfall distribution across Ireland
- `rainfall_heatmap.html`: Interactive map with clickable points showing club details
- `elevation_heatmap.png`: Static map showing elevation distribution
- `elevation_heatmap.html`: Interactive map with pitch elevation details

### Reports
- `gaa_rainfall_analysis.md`: Comprehensive analysis of rainfall patterns by county
- `elevation_analysis.md`: Analysis of pitch elevations and terrain patterns

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

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


