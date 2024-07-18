# gaapitchfinder
Contains the underlying dataset for the GAA Pitch Finder website.

## Description
This dataset provides detailed information about various GAA Pitches, including their respective clubs, names, locations (latitude and longitude), provinces, countries, divisions, and counties. It also includes specific data such as the name of the pitch (where available), directions (via a Google Maps URL), and the club's Twitter handle (where available).

## Dataset Structure
The dataset currently consists of 1973 rows and 12 columns, detailed as follows:

- **File**: The region identifier.
- **Club**: The name of the GAA club.
- **Pitch**: The name of the GAA club's pitch (some entries may be missing).
- **Code**: The GAA sports that the clubs partake in e.g. Football, Hurling, Camoige, Mixed.
- **Latitude**: The latitude coordinate of the club's location.
- **Longitude**: The longitude coordinate of the club's location.
- **Province**: The province where the club is located.
- **Country**: The country where the club is located.
- **Division**: The division the club belongs to. In Ireland this is the same as the County. Used for international pitches which have a different hierarchy.
- **County**: The county where the club is located.
- **Directions**: A URL to Google Maps directions for the club's location.
- **Twitter**: The Twitter handle of the club (some entries may be missing).

## Usage
This dataset is intended for research, analysis, and educational purposes. Users are encouraged to explore the geographical distribution of GAA clubs, suggest amendments, or develop location-based services for sports enthusiasts.

## Citation
If you use this dataset in your research or project, please cite it as follows:

GAA Pitch Finder. (2024). Retrieved from the [GAA Pitch Finder GitHub repo](https://github.com/ryanmcg2203/gaapitchfinder)


