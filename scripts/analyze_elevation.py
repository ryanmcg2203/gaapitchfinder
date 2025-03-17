import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Read the data
df = pd.read_csv('gaapitchfinder_data_with_elevation.csv')

# Basic statistics
stats = df['Elevation'].describe()
print("\nElevation Statistics (in meters):")
print(stats)

# Create a figure with two subplots
plt.figure(figsize=(15, 6))

# Histogram
plt.subplot(1, 2, 1)
sns.histplot(data=df, x='Elevation', bins=30)
plt.title('Distribution of GAA Pitch Elevations')
plt.xlabel('Elevation (meters)')
plt.ylabel('Count')

# Box plot
plt.subplot(1, 2, 2)
sns.boxplot(y=df['Elevation'])
plt.title('Box Plot of GAA Pitch Elevations')
plt.ylabel('Elevation (meters)')

# Adjust layout and save
plt.tight_layout()
plt.savefig('elevation_distribution.png')

# Find some interesting insights
print("\nInteresting Insights:")
print(f"Lowest elevation pitch: {df.loc[df['Elevation'].idxmin()][['Club', 'County', 'Elevation']].to_dict()}")
print(f"Highest elevation pitch: {df.loc[df['Elevation'].idxmax()][['Club', 'County', 'Elevation']].to_dict()}")

# Group by county and get mean elevation
county_elevations = df.groupby('County')['Elevation'].agg(['mean', 'count']).sort_values('mean', ascending=False)
print("\nAverage Elevation by County (top 5):")
print(county_elevations.head()) 