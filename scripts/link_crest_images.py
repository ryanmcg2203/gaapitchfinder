import pandas as pd
import os
from pathlib import Path

def main():
    print("=== Linking Crest Images to Club Data ===")
    
    # Check if images directory exists
    if not os.path.exists('club_images'):
        print("Error: club_images directory not found!")
        return
        
    # Get list of image files
    image_files = list(Path('club_images').glob('*.jpeg'))
    print(f"\nFound {len(image_files)} crest images")
    
    # Read the CSV file
    print("\nReading CSV data...")
    df = pd.read_csv('gaapitchfinder_data.csv')
    
    # Add crest_image column if it doesn't exist
    if 'crest_image' not in df.columns:
        df['crest_image'] = None
    
    # Counter for matches
    matches = 0
    
    print("\nLinking images to clubs...")
    # For each club in Monaghan
    monaghan_clubs = df[df['County'] == 'Monaghan']
    for idx, row in monaghan_clubs.iterrows():
        club = row['Club'].strip()
        # Create expected filename
        expected_filename = f"Monaghan_{club.replace(' ', '_')}.jpeg"
        expected_filename = expected_filename.replace(',', '').replace("'", '')
        
        # Check if file exists
        if os.path.exists(os.path.join('club_images', expected_filename)):
            df.loc[idx, 'crest_image'] = expected_filename
            matches += 1
    
    print(f"\nFound matches for {matches} clubs")
    
    # Show preview of changes
    print("\nPreview of updates:")
    preview = df[df['crest_image'].notna()][['Club', 'County', 'crest_image']].head()
    print(preview)
    
    # Ask for confirmation
    response = input("\nWould you like to save these changes to the CSV? (y/n): ")
    if response.lower() == 'y':

        # Save updated file
        print("Saving updated CSV...")
        df.to_csv('gaapitchfinder_data.csv', index=False)
        print("Done!")
    else:
        print("\nChanges not saved.")

if __name__ == "__main__":
    main() 