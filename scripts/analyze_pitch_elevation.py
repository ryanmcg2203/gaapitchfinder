#!/usr/bin/env python3
"""
Analyze pitch elevations from the main GAA Pitch Finder dataset.

Run from the repo root:
    python3 scripts/analyze_pitch_elevation.py
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = ROOT_DIR / "gaapitchfinder_data.csv"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "output"


def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "Elevation" not in df.columns:
        raise ValueError(f"{path} does not contain an Elevation column")

    df = df.copy()
    df["Elevation"] = pd.to_numeric(df["Elevation"], errors="coerce")
    return df[df["Elevation"].notna()]


def create_distribution_chart(df: pd.DataFrame, output_dir: Path) -> Path:
    visualizations_dir = output_dir / "visualizations"
    visualizations_dir.mkdir(parents=True, exist_ok=True)

    chart_path = visualizations_dir / "elevation_distribution.png"

    plt.figure(figsize=(15, 6))

    plt.subplot(1, 2, 1)
    sns.histplot(data=df, x="Elevation", bins=30)
    plt.title("Distribution of GAA Pitch Elevations")
    plt.xlabel("Elevation (meters)")
    plt.ylabel("Count")

    plt.subplot(1, 2, 2)
    sns.boxplot(y=df["Elevation"])
    plt.title("Box Plot of GAA Pitch Elevations")
    plt.ylabel("Elevation (meters)")

    plt.tight_layout()
    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close()

    return chart_path


def write_report(df: pd.DataFrame, output_dir: Path) -> Path:
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    report_path = reports_dir / "gaa_elevation_analysis.md"
    stats = df["Elevation"].describe()
    lowest = df.loc[df["Elevation"].idxmin()]
    highest = df.loc[df["Elevation"].idxmax()]
    county_elevations = (
        df.groupby("County")["Elevation"]
        .agg(["mean", "count"])
        .sort_values("mean", ascending=False)
        .head(10)
    )

    with report_path.open("w") as f:
        f.write("# GAA Pitch Elevation Analysis\n\n")
        f.write("## Overall Statistics\n")
        f.write(f"- Total pitches analyzed: {len(df)}\n")
        f.write(f"- Average elevation: {stats['mean']:.1f}m\n")
        f.write(f"- Median elevation: {stats['50%']:.1f}m\n")
        f.write(f"- Minimum elevation: {stats['min']:.1f}m\n")
        f.write(f"- Maximum elevation: {stats['max']:.1f}m\n\n")

        f.write("## Extremes\n")
        f.write(
            f"- Lowest pitch: {lowest['Club']} ({lowest.get('County', 'Unknown')}, "
            f"{lowest['Elevation']:.1f}m)\n"
        )
        f.write(
            f"- Highest pitch: {highest['Club']} ({highest.get('County', 'Unknown')}, "
            f"{highest['Elevation']:.1f}m)\n\n"
        )

        f.write("## Highest Average Elevation Areas\n")
        f.write("| Area | Average Elevation (m) | Pitches |\n")
        f.write("|------|-----------------------|---------|\n")
        for area, row in county_elevations.iterrows():
            f.write(f"| {area} | {row['mean']:.1f} | {int(row['count'])} |\n")

        f.write("\n## Visualization\n")
        f.write("- `output/visualizations/elevation_distribution.png`\n")

    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze pitch elevation data")
    parser.add_argument("--input", type=Path, default=DEFAULT_DATA_PATH, help="Path to input CSV file")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for generated outputs")
    args = parser.parse_args()

    df = load_data(args.input)
    stats = df["Elevation"].describe()
    chart_path = create_distribution_chart(df, args.output_dir)
    report_path = write_report(df, args.output_dir)

    print("Elevation Statistics (in meters):")
    print(stats)
    print(f"\nChart written to {chart_path}")
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
