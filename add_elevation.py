import pandas as pd
import requests
import time
from tqdm import tqdm

def get_elevation(lat, lon):
    """
    Get elevation data from the Open-Elevation API
    """
    try:
        url = f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data['results'][0]['elevation']
        return None
    except Exception as e:
        print(f"Error fetching elevation for coordinates ({lat}, {lon}): {str(e)}")
        return None

def main():
    # Read the existing CSV file
    print("Reading CSV file...")
    df = pd.read_csv('gaapitchfinder_data.csv')
    
    # Create a new column for elevation
    df['Elevation'] = None
    
    # Process each row
    print("Fetching elevation data...")
    for idx in tqdm(df.index):
        lat = df.at[idx, 'Latitude']
        lon = df.at[idx, 'Longitude']
        elevation = get_elevation(lat, lon)
        df.at[idx, 'Elevation'] = elevation
        # Add a small delay to avoid overwhelming the API
        time.sleep(1)
    
    # Save the updated dataset
    print("Saving updated dataset...")
    df.to_csv('gaapitchfinder_data_with_elevation.csv', index=False)
    print("Done! New dataset saved as 'gaapitchfinder_data_with_elevation.csv'")

if __name__ == "__main__":
    main() 