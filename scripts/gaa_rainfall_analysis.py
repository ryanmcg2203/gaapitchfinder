import pandas as pd
import numpy as np
from collections import defaultdict
import folium
import seaborn as sns
import matplotlib.pyplot as plt
import logging
import argparse
from typing import Dict, List, Tuple
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
DEFAULT_DATA_PATH = Path("../gaapitchfinder_data.csv")
DEFAULT_OUTPUT_DIR = Path("../output")
MAP_CENTER = [53.4129, -7.9135]  # Center of Ireland
MAP_ZOOM = 7
PLOT_FIGSIZE = (15, 10)
PLOT_DPI = 300
PLOT_POINT_SIZE = 100
PLOT_ALPHA = 0.6
MAP_MARKER_RADIUS = 8
MAP_OPACITY_NORMALIZATION = 2500  # Max rainfall for opacity calculation

def ensure_output_directories() -> None:
    """Ensure output directories exist."""
    try:
        (DEFAULT_OUTPUT_DIR / "visualizations").mkdir(parents=True, exist_ok=True)
        (DEFAULT_OUTPUT_DIR / "reports").mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create output directories: {str(e)}")
        raise

def calculate_county_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate rainfall statistics for each county.
    
    Args:
        df: DataFrame containing club data
        
    Returns:
        DataFrame with county statistics
    """
    county_stats = defaultdict(lambda: {"clubs": 0, "total_rainfall": 0, "clubs_with_data": 0})
    
    for _, row in df.iterrows():
        county = row["County"]
        rainfall = row["annual_rainfall"]
        
        county_stats[county]["clubs"] += 1
        if pd.notna(rainfall):
            county_stats[county]["total_rainfall"] += rainfall
            county_stats[county]["clubs_with_data"] += 1
    
    # Calculate averages and create rankings
    county_averages = []
    for county, stats in county_stats.items():
        if stats["clubs_with_data"] > 0:
            avg_rainfall = stats["total_rainfall"] / stats["clubs_with_data"]
            county_averages.append({
                "County": county,
                "Average Rainfall (mm)": round(avg_rainfall, 1),
                "Total Clubs": stats["clubs"],
                "Clubs with Data": stats["clubs_with_data"]
            })
    
    return pd.DataFrame(county_averages).sort_values("Average Rainfall (mm)", ascending=False)

def create_static_heatmap(df: pd.DataFrame) -> None:
    """
    Create and save static heatmap visualization.
    
    Args:
        df: DataFrame containing club data
    """
    logger.info("Generating static heatmap...")
    ireland_data = df[df['annual_rainfall'].notna()].copy()
    
    plt.figure(figsize=PLOT_FIGSIZE)
    scatter = plt.scatter(
        ireland_data['Longitude'],
        ireland_data['Latitude'],
        c=ireland_data['annual_rainfall'],
        cmap='YlOrRd',
        s=PLOT_POINT_SIZE,
        alpha=PLOT_ALPHA,
    )
    
    plt.title('GAA Club Rainfall Distribution (mm/year)', pad=20)
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.colorbar(scatter, label='Annual Rainfall (mm)')
    plt.xlim(-11, -5)
    plt.ylim(51, 56)
    
    plt.savefig(DEFAULT_OUTPUT_DIR / "visualizations/rainfall_heatmap.png", 
                dpi=PLOT_DPI, bbox_inches='tight')
    plt.close()

def create_interactive_map(df: pd.DataFrame) -> None:
    """
    Create and save interactive map visualization.
    
    Args:
        df: DataFrame containing club data
    """
    logger.info("Generating interactive heatmap...")
    ireland_data = df[df['annual_rainfall'].notna()].copy()
    
    m = folium.Map(location=MAP_CENTER, zoom_start=MAP_ZOOM)
    
    for _, row in ireland_data.iterrows():
        folium.CircleMarker(
            location=[row['Latitude'], row['Longitude']],
            radius=MAP_MARKER_RADIUS,
            color='red',
            fill=True,
            fillColor='red',
            fillOpacity=row['annual_rainfall'] / MAP_OPACITY_NORMALIZATION,
            popup=f"{row['Club']}: {row['annual_rainfall']:.1f}mm/year"
        ).add_to(m)
    
    m.save(DEFAULT_OUTPUT_DIR / "visualizations/rainfall_heatmap.html")

def generate_report(df: pd.DataFrame, county_df: pd.DataFrame) -> None:
    """
    Generate markdown report with analysis results.
    
    Args:
        df: DataFrame containing club data
        county_df: DataFrame containing county statistics
    """
    logger.info("Generating report...")
    report_path = DEFAULT_OUTPUT_DIR / "reports/gaa_rainfall_analysis.md"
    
    with open(report_path, "w") as f:
        f.write("# GAA Club Rainfall Analysis\n\n")
        
        f.write("## Overall Statistics\n")
        f.write(f"- Total Clubs Analyzed: {len(df)}\n")
        f.write(f"- Clubs with Rainfall Data: {df['annual_rainfall'].notna().sum()}\n")
        f.write(f"- Average Annual Rainfall: {df['annual_rainfall'].mean():.1f}mm\n")
        f.write(f"- Wettest Location: {df.loc[df['annual_rainfall'].idxmax(), 'Club']} ({df['annual_rainfall'].max():.1f}mm)\n")
        f.write(f"- Driest Location: {df.loc[df['annual_rainfall'].idxmin(), 'Club']} ({df['annual_rainfall'].min():.1f}mm)\n\n")
        
        f.write("## Visualizations\n")
        f.write("Two heatmap visualizations have been generated:\n")
        f.write("1. `rainfall_heatmap.html` - An interactive map showing rainfall distribution\n")
        f.write("2. `rainfall_heatmap.png` - A static heatmap showing rainfall density\n\n")
        
        f.write("## County Rankings (by Average Annual Rainfall)\n")
        f.write("| Rank | County | Average Rainfall (mm) | Total Clubs | Clubs with Data |\n")
        f.write("|------|--------|---------------------|-------------|----------------|\n")
        
        for i, row in county_df.iterrows():
            f.write(f"| {i+1} | {row['County']} | {row['Average Rainfall (mm)']} | {row['Total Clubs']} | {row['Clubs with Data']} |\n")
        
        f.write("\n## Notable Findings\n")
        f.write("1. Rainfall variation across counties\n")
        f.write(f"   - Highest county average: {county_df.iloc[0]['County']} ({county_df.iloc[0]['Average Rainfall (mm)']}mm)\n")
        f.write(f"   - Lowest county average: {county_df.iloc[-1]['County']} ({county_df.iloc[-1]['Average Rainfall (mm)']}mm)\n")
        f.write(f"   - Range: {county_df.iloc[0]['Average Rainfall (mm)'] - county_df.iloc[-1]['Average Rainfall (mm)']:.1f}mm\n\n")
        
        f.write("2. Regional patterns\n")
        f.write("   - Western counties tend to have higher rainfall\n")
        f.write("   - Eastern counties generally show lower rainfall\n")
        f.write("   - Coastal areas typically experience more rainfall than inland regions\n\n")
        
        f.write("3. Implications for GAA\n")
        f.write("   - Higher rainfall areas may need more robust drainage systems\n")
        f.write("   - Consider artificial surfaces in particularly wet regions\n")
        f.write("   - Match scheduling might need to account for regional rainfall patterns\n")

def main():
    parser = argparse.ArgumentParser(description="Analyze rainfall patterns for GAA clubs")
    parser.add_argument("--input", type=str, default=str(DEFAULT_DATA_PATH),
                      help="Path to input CSV file")
    args = parser.parse_args()
    
    logger.info("=== GAA Club Rainfall Analysis ===\n")
    
    try:
        # Ensure output directories exist
        ensure_output_directories()
        
        # Read data
        logger.info("Reading club data...")
        df = pd.read_csv(args.input)
        
        # Calculate county statistics
        logger.info("Calculating county statistics...")
        county_df = calculate_county_statistics(df)
        
        # Generate visualizations
        create_static_heatmap(df)
        create_interactive_map(df)
        
        # Generate report
        generate_report(df, county_df)
        
        logger.info("\nAnalysis complete! Results saved to:")
        logger.info(f"- {DEFAULT_OUTPUT_DIR}/reports/gaa_rainfall_analysis.md")
        logger.info(f"- {DEFAULT_OUTPUT_DIR}/visualizations/rainfall_heatmap.html")
        logger.info(f"- {DEFAULT_OUTPUT_DIR}/visualizations/rainfall_heatmap.png")
        
    except Exception as e:
        logger.error(f"Script failed: {str(e)}")
        raise

if __name__ == "__main__":
    main() 