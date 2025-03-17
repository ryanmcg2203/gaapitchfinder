import pandas as pd
import webbrowser
import os
from urllib.parse import quote
import time

def create_google_image_url(query):
    """Create a Google Images search URL for the given query"""
    encoded_query = quote(query)
    return f"https://www.google.com/search?q={encoded_query}&tbm=isch"

def main():
    # Create images directory if it doesn't exist
    if not os.path.exists('club_images'):
        os.makedirs('club_images')

    # Read the GAA pitches data
    df = pd.read_csv('gaapitchfinder_data.csv')
    
    # Filter for Monaghan clubs and sort by club name
    df = df[df['County'] == 'Monaghan'].sort_values('Club')
    
    print("\n=== Monaghan GAA Club Crest Search Helper ===")
    print(f"\nFound {len(df)} clubs in County Monaghan")
    print("\nFor each club:")
    print("1. A browser window will open with Google Images")
    print("2. Find a good image of the club's crest/logo")
    print("3. Save the image using EXACTLY the suggested filename shown")
    print("4. Save it in the 'club_images' folder")
    print("5. Press Enter to continue to next club, or 'q' to quit\n")
    
    for idx, row in df.iterrows():
        club = row['Club'].strip()
        county = row['County'].strip()  # Will always be Monaghan
        
        # Create search query - now looking for crests
        search_query = f"{club} {county} GAA crest"
        
        # Create suggested filename
        suggested_filename = f"Monaghan_{club.replace(' ', '_')}.jpeg"
        suggested_filename = suggested_filename.replace(',', '').replace("'", '')
        
        print(f"\nProcessing: {club}")
        print(f">>> Please save as: {suggested_filename}")
        
        # Open Google Images search
        webbrowser.open(create_google_image_url(search_query))
        
        # Wait for user input
        user_input = input("Press Enter when saved (or 'q' to quit): ")
        if user_input.lower() == 'q':
            print("\nStopping image search process.")
            break
        
        # Optional: add a small delay to prevent too many rapid browser opens
        time.sleep(1)

    print("\nAll Monaghan clubs processed!")

if __name__ == "__main__":
    main() 