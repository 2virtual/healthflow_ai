# app/startup_tasks.py
from geopy.geocoders import Nominatim
import asyncio
import json
import re
from pathlib import Path

# Path to hospital coordinates JSON
HOSPITAL_COORDS_FILE = Path("hospital_coordinates.json")
HOSPITAL_COORDS = {}

# Load existing coordinates
if HOSPITAL_COORDS_FILE.exists():
    with open(HOSPITAL_COORDS_FILE, "r") as f:
        HOSPITAL_COORDS = json.load(f)

async def fetch_ahs_data():
    """
    Placeholder for your async function that fetches hospital data from AHS.
    Must return a dict of hospitals by region/category.
    """
    # TODO: implement real fetching
    return {}

async def geocode_hospitals_on_startup():
    """Pre-fetch hospital coordinates and update JSON file."""
    global HOSPITAL_COORDS
    ahs_data = await fetch_ahs_data()

    if not ahs_data or not isinstance(ahs_data, dict):
        print("⚠️ No AHS data available on startup.")
        return

    # Flatten AHS data
    flattened_hospitals = []
    for region, categories in ahs_data.items():
        for category, hospitals in categories.items():
            for hospital in hospitals:
                flattened_hospitals.append({
                    "name": hospital.get("Name") or hospital.get("name"),
                    "address": hospital.get("Address") or "",
                })

    geolocator = Nominatim(user_agent="healthflow_ai")
    updated_coords = {}

    for h in flattened_hospitals:
        name = h["name"]
        address = h["address"]

        # Skip hospitals that already have coordinates
        if not name or name in HOSPITAL_COORDS:
            continue

        # Clean address
        address = re.sub(r"[^\w\s,.-]", "", address)

        success = False
        for attempt in range(3):
            try:
                loc = geolocator.geocode(address, timeout=10)
                if loc:
                    coords = {"lat": loc.latitude, "lng": loc.longitude}
                    HOSPITAL_COORDS[name] = coords
                    updated_coords[name] = coords
                    print(f"✅ {name}: {coords}")
                    success = True
                    break
                else:
                    print(f"⚠️ Could not geocode {name} on attempt {attempt+1}")
            except Exception as e:
                print(f"❌ Error geocoding {name} on attempt {attempt+1}: {e}")
            await asyncio.sleep(1)  # wait 1s before retry

        if not success:
            print(f"⚠️ Failed to geocode {name} after 3 attempts")

    # Save updated coordinates to JSON
    if updated_coords:
        with open(HOSPITAL_COORDS_FILE, "w") as f:
            json.dump(HOSPITAL_COORDS, f, indent=2)
        print(f"✅ Saved {len(updated_coords)} new hospital coordinates to {HOSPITAL_COORDS_FILE}")

# Example of usage in main.py:
# asyncio.run(geocode_hospitals_on_startup())







# # app/startup_tasks.py
# from geopy.geocoders import Nominatim
# import asyncio
# import json
# import re
# from pathlib import Path
# import httpx  # async HTTP client

# # Path to hospital coordinates JSON
# HOSPITAL_COORDS_FILE = Path("hospital_coordinates.json")
# HOSPITAL_COORDS = {}

# if HOSPITAL_COORDS_FILE.exists():
#     with open(HOSPITAL_COORDS_FILE, "r") as f:
#         HOSPITAL_COORDS = json.load(f)


# async def fetch_ahs_data():
#     """
#     Fetch hospital wait times from Alberta Health Services API.
#     Returns a dict of hospitals with name and address.
#     """
#     url = "https://www.albertahealthservices.ca/WebApps/WaitTimes/api/WaitTimes"
#     async with httpx.AsyncClient(timeout=10.0) as client:
#         try:
#             resp = await client.get(url)
#             resp.raise_for_status()
#             data = resp.json()
#         except Exception as e:
#             print(f"⚠️ Error fetching AHS data: {e}")
#             return {}

#     hospitals_by_region = {}

#     for region_name, region_data in data.items():
#         hospitals_by_region[region_name] = {}
#         for category_name, hospitals in region_data.items():
#             hospitals_by_region[region_name][category_name] = []
#             for h in hospitals:
#                 # Only include name & address
#                 hospitals_by_region[region_name][category_name].append({
#                     "Name": h.get("Name") or h.get("name"),
#                     "Address": h.get("Address") or h.get("address") or ""
#                 })
#     return hospitals_by_region


# async def geocode_hospitals_on_startup():
#     """Pre-fetch hospital coordinates and update JSON file."""
#     global HOSPITAL_COORDS
#     ahs_data = await fetch_ahs_data()

#     if not ahs_data or not isinstance(ahs_data, dict):
#         print("⚠️ No AHS data available on startup.")
#         return

#     # Flatten AHS data
#     flattened_hospitals = []
#     for region, categories in ahs_data.items():
#         for category, hospitals in categories.items():
#             for hospital in hospitals:
#                 flattened_hospitals.append({
#                     "name": hospital.get("Name") or hospital.get("name"),
#                     "address": hospital.get("Address") or "",
#                 })

#     geolocator = Nominatim(user_agent="healthflow_ai")
#     updated_coords = {}

#     for h in flattened_hospitals:
#         name = h["name"]
#         address = h["address"]

#         if not name or name in HOSPITAL_COORDS:
#             continue

#         # Clean address
#         address = re.sub(r"[^\w\s,.-]", "", address)

#         success = False
#         for attempt in range(3):
#             try:
#                 loc = geolocator.geocode(address, timeout=10)
#                 if loc:
#                     coords = {"lat": loc.latitude, "lng": loc.longitude}
#                     HOSPITAL_COORDS[name] = coords
#                     updated_coords[name] = coords
#                     print(f"✅ {name}: {coords}")
#                     success = True
#                     break
#                 else:
#                     print(f"⚠️ Could not geocode {name} on attempt {attempt+1}")
#             except Exception as e:
#                 print(f"❌ Error geocoding {name} on attempt {attempt+1}: {e}")
#             await asyncio.sleep(1)  # wait 1s before retry

#         if not success:
#             print(f"⚠️ Failed to geocode {name} after 3 attempts")

#     # Save updated coordinates to JSON
#     if updated_coords:
#         with open(HOSPITAL_COORDS_FILE, "w") as f:
#             json.dump(HOSPITAL_COORDS, f, indent=2)
#         print(f"✅ Saved {len(updated_coords)} hospital coordinates to {HOSPITAL_COORDS_FILE}")

#     print("✅ Async hospital geocoding complete")



