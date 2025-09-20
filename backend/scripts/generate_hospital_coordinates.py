# scripts/generate_hospital_coordinates.py

import os
import json
import requests
import time
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

# ---------------------------
# Config
# ---------------------------
AHS_ENDPOINT = "http://backend:8000/ed-waits"  # change if running differently
COORDS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "hospital_coordinates.json")

FALLBACK_HOSPITALS = [
    "Foothills Medical Centre",
    "Peter Lougheed Centre",
    "Rockyview General Hospital",
    "South Health Campus",
    "Alberta Children's Hospital",
    "University of Alberta Hospital",
    "Royal Alexandra Hospital",
    "Grey Nuns Community Hospital",
    "Misericordia Community Hospital",
    "Sturgeon Community Hospital",
]

# ---------------------------
# Helper functions
# ---------------------------
def fetch_hospital_names():
    """Fetch hospital names from /ed-waits endpoint and flatten nested data."""
    try:
        response = requests.get(AHS_ENDPOINT, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        hospitals = []
        if isinstance(data, list):
            # already flat list
            hospitals = [h.get("name") for h in data if h.get("name")]
        elif isinstance(data, dict):
            # nested dictionary
            for region, categories in data.items():
                for category, hospital_list in categories.items():
                    for hospital in hospital_list:
                        name = hospital.get("Name") or hospital.get("name")
                        if name:
                            hospitals.append(name)
        else:
            print("⚠️ Unexpected data format from /ed-waits")
        
        if not hospitals:
            print("⚠️ No hospitals fetched, using fallback list.")
            hospitals = FALLBACK_HOSPITALS
        
        return list(set(hospitals))  # unique
    except Exception as e:
        print(f"❌ Error fetching hospitals: {e}")
        print("⚠️ Using fallback hospital list.")
        return FALLBACK_HOSPITALS

def geocode_hospitals(hospitals):
    """Geocode hospital names into coordinates."""
    geolocator = Nominatim(user_agent="ahs_hospital_locator")
    coords = {}

    for name in hospitals:
        try:
            print(f"🌍 Geocoding: {name} ...")
            location = geolocator.geocode(f"{name}, Alberta, Canada")
            if location:
                coords[name] = {"lat": location.latitude, "lng": location.longitude}
                print(f"✅ Found: {coords[name]}")
            else:
                print(f"⚠️ No result for {name}")
        except GeocoderTimedOut:
            print(f"⏳ Timeout, retrying for {name}...")
            time.sleep(2)
            continue
        except Exception as e:
            print(f"❌ Error geocoding {name}: {e}")
        time.sleep(1)  # respect Nominatim rate limit

    return coords

def main():
    """Generate hospital_coordinates.json"""
    hospitals = fetch_hospital_names()
    if not hospitals:
        print("❌ No hospitals available. Exiting.")
        return

    coords = geocode_hospitals(hospitals)

    with open(COORDS_FILE, "w") as f:
        json.dump(coords, f, indent=2)

    print(f"✅ Saved {len(coords)} hospital coordinates to {COORDS_FILE}")

if __name__ == "__main__":
    main()
