# app/services/update_hospital_data.py
import os
import json
import time
import logging
import requests
import redis
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# Full hospital coordinates (keep your existing 29 entries)
HOSPITAL_COORDS = {
    "Alberta Children's Hospital": {"lat": 51.0706, "lng": -114.1593},
    "Foothills Medical Centre": {"lat": 51.0651, "lng": -114.1302},
    "Peter Lougheed Centre": {"lat": 51.0736, "lng": -113.9574},
    "Rockyview General Hospital": {"lat": 50.9839, "lng": -114.0975},
    "South Health Campus": {"lat": 50.8849, "lng": -113.9581},
    "Airdrie Community Health Centre": {"lat": 51.2917, "lng": -114.0144},
    "Cochrane Community Health Centre": {"lat": 51.1894, "lng": -114.4677},
    "Okotoks Health and Wellness Centre": {"lat": 50.7256, "lng": -113.9749},
    "Sheldon M. Chumir Centre": {"lat": 51.0425, "lng": -114.0647},
    "South Calgary Health Centre": {"lat": 50.9306, "lng": -114.0427},
    "Devon General Hospital": {"lat": 53.3652, "lng": -113.7353},
    "Fort Sask Community Hospital": {"lat": 53.7180, "lng": -113.2094},
    "Grey Nuns Community Hospital": {"lat": 53.4840, "lng": -113.4439},
    "Leduc Community Hospital": {"lat": 53.2590, "lng": -113.5448},
    "Misericordia Community Hospital": {"lat": 53.5265, "lng": -113.5561},
    "Northeast Community Health Centre": {"lat": 53.6020, "lng": -113.4411},
    "Royal Alexandra Hospital": {"lat": 53.5491, "lng": -113.4965},
    "Stollery Children's Hospital": {"lat": 53.5215, "lng": -113.5266},
    "Strathcona Community Hospital": {"lat": 53.6071, "lng": -113.3046},
    "Sturgeon Community Hospital": {"lat": 53.6731, "lng": -113.6229},
    "University of Alberta Hospital": {"lat": 53.5225, "lng": -113.5301},
    "WestView Health Centre": {"lat": 53.5283, "lng": -114.0089},
    "Red Deer Regional Hospital": {"lat": 52.2690, "lng": -113.8112},
    "Innisfail Health Centre": {"lat": 52.0336, "lng": -113.9589},
    "Lacombe Hospital and Care Centre": {"lat": 52.4673, "lng": -113.7366},
    "Chinook Regional Hospital": {"lat": 49.6935, "lng": -112.8418},
    "Medicine Hat Regional Hospital": {"lat": 50.0290, "lng": -110.7034},
    "Grande Prairie Regional Hospital": {"lat": 55.1700, "lng": -118.7947},
    "Northern Lights Regional Health Centre": {"lat": 56.7266, "lng": -111.3810},
}

def fetch_wait_times():
    url = "https://www.albertahealthservices.ca/WebApps/WaitTimes/api/WaitTimes"
    headers = {
        "User-Agent": "Mozilla/5.0 (HealthFlow AI; +https://github.com/yourname/healthflow)"
    }
    try:
        logger.info("📡 Fetching AHS wait times...")
        r = requests.get(url, headers=headers, timeout=10)
        logger.info(f"✅ HTTP {r.status_code}, Content-Type: {r.headers.get('content-type', 'N/A')}")
        
        if r.status_code == 200:
            # Try to parse JSON
            data = r.json()
            logger.info(f"✅ Parsed {sum(len(hospitals) for cats in data.values() for hospitals in cats.values())} hospitals")
            return data
        else:
            logger.error(f"❌ HTTP error: {r.status_code} - {r.text[:200]}")
            return None
    except Exception as e:
        logger.exception(f"❌ Failed to fetch or parse AHS data: {e}")
        return None 
      
def flatten_hospitals(raw_data: Dict) -> List[Dict]:
    hospitals = []
    for region_name, categories in raw_data.items():
        for category_type, sites in categories.items():
            for site in sites:
                # Map category
                if site["Category"] == "Emergency":
                    internal_category = "Emergency"
                elif "Urgent" in site["Category"]:
                    internal_category = "Urgent"
                else:
                    internal_category = "PrimaryCare"

                hospitals.append({
                    "name": site["Name"],
                    "category": internal_category,
                    "wait_time": site["WaitTime"],
                    "note": site["Note"],
                    "address": site["Address"],
                    "url": site["URL"],
                    "region": region_name,
                    "split_facility": site.get("SplitFacility"),
                    "lat": None,
                    "lng": None,
                })
    return hospitals

def update_redis(hospitals):
    for idx, hosp in enumerate(hospitals, start=1):
        coord = HOSPITAL_COORDS.get(hosp["name"], {"lat": None, "lng": None})
        hosp["lat"] = coord["lat"]
        hosp["lng"] = coord["lng"]
        redis_client.set(f"hospital:{idx}", json.dumps(hosp, ensure_ascii=False))
    redis_client.set("hospital:count", len(hospitals))
    logger.info(f"✅ Updated {len(hospitals)} hospitals in Redis")

if __name__ == "__main__":
    logger.info("🏥 Starting hospital data updater (every 5 minutes)")
    while True:
        raw = fetch_wait_times()
        if raw:
            try:
                flattened = flatten_hospitals(raw)
                update_redis(flattened)
            except Exception as e:
                logger.exception(f"❌ Error processing data: {e}")
        else:
            logger.warning("⚠️ No data — skipping Redis update")
        time.sleep(300)


# # app/services/update_hospital_data.py

# import os
# import json
# import redis
# import requests
# from typing import List, Dict

# # ✅ Connect to Redis (works in Docker or locally)
# REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
# redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# # ✅ Coordinates mapped by hospital index (1..N)
# # TODO: Fill this with actual hospital coordinates
# # ✅ Coordinates mapped by hospital ID (1..29)
# HOSPITAL_COORDS = {
#     1: {"lat": 51.0706, "lng": -114.1593},  # Alberta Children's Hospital
#     2: {"lat": 51.0651, "lng": -114.1302},  # Foothills Medical Centre
#     3: {"lat": 51.0736, "lng": -113.9574},  # Peter Lougheed Centre
#     4: {"lat": 50.9839, "lng": -114.0975},  # Rockyview General Hospital
#     5: {"lat": 50.8849, "lng": -113.9581},  # South Health Campus
#     6: {"lat": 51.2917, "lng": -114.0144},  # Airdrie Community Health Centre
#     7: {"lat": 51.1894, "lng": -114.4677},  # Cochrane Community Health Centre
#     8: {"lat": 50.7256, "lng": -113.9749},  # Okotoks Health and Wellness Centre
#     9: {"lat": 51.0425, "lng": -114.0647},  # Sheldon M. Chumir Centre
#     10: {"lat": 50.9306, "lng": -114.0427}, # South Calgary Health Centre
#     11: {"lat": 53.3652, "lng": -113.7353}, # Devon General Hospital
#     12: {"lat": 53.7180, "lng": -113.2094}, # Fort Sask Community Hospital
#     13: {"lat": 53.4840, "lng": -113.4439}, # Grey Nuns Community Hospital
#     14: {"lat": 53.2590, "lng": -113.5448}, # Leduc Community Hospital
#     15: {"lat": 53.5265, "lng": -113.5561}, # Misericordia Community Hospital
#     16: {"lat": 53.6020, "lng": -113.4411}, # Northeast Community Health Centre
#     17: {"lat": 53.5491, "lng": -113.4965}, # Royal Alexandra Hospital
#     18: {"lat": 53.5215, "lng": -113.5266}, # Stollery Children's Hospital
#     19: {"lat": 53.6071, "lng": -113.3046}, # Strathcona Community Hospital
#     20: {"lat": 53.6731, "lng": -113.6229}, # Sturgeon Community Hospital
#     21: {"lat": 53.5225, "lng": -113.5301}, # University of Alberta Hospital
#     22: {"lat": 53.5283, "lng": -114.0089}, # WestView Health Centre
#     23: {"lat": 52.2690, "lng": -113.8112}, # Red Deer Regional Hospital
#     24: {"lat": 52.0336, "lng": -113.9589}, # Innisfail Health Centre
#     25: {"lat": 52.4673, "lng": -113.7366}, # Lacombe Hospital and Care Centre
#     26: {"lat": 49.6935, "lng": -112.8418}, # Chinook Regional Hospital
#     27: {"lat": 50.0290, "lng": -110.7034}, # Medicine Hat Regional Hospital
#     28: {"lat": 55.1700, "lng": -118.7947}, # Grande Prairie Regional Hospital
#     29: {"lat": 56.7266, "lng": -111.3810}, # Northern Lights Regional Health Centre
# }


# def fetch_wait_times() -> List[Dict]:
#     """Fetch and flatten Alberta ED wait times from AHS API."""
#     url = "https://www.albertahealthservices.ca/WebApps/WaitTimes/api/WaitTimes"
#     try:
#         r = requests.get(url, timeout=10)
#         r.raise_for_status()
#         data = r.json()

#         results = []
#         for region, categories in data.items():
#             for category, hospitals in categories.items():
#                 for hospital in hospitals:
#                     results.append({
#                         "region": region,
#                         "category": category,
#                         "name": hospital.get("Name"),
#                         "wait_time": hospital.get("WaitTime"),
#                         "note": hospital.get("Note")
#                     })
#         return results

#     except requests.exceptions.RequestException as e:
#         print(f"[ERROR] Could not fetch wait times: {e}")
#         return []
#     except ValueError:
#         print("[ERROR] Invalid JSON received from AHS API")
#         return []


# def enrich_hospitals(raw_data: List[Dict]) -> List[Dict]:
#     """Make sure all hospitals have lat/lng fields."""
#     enriched = []
#     for hosp in raw_data:
#         if isinstance(hosp, str):
#             try:
#                 hosp = json.loads(hosp)
#             except Exception:
#                 continue
#         enriched.append(hosp)
#     return enriched


# def update_redis(hospitals: List[Dict]):
#     """Update Redis keys hospital:1..N with enriched data."""
#     for idx, hosp in enumerate(hospitals, start=1):
#         if not hosp.get("name"):
#             continue

#         coord = HOSPITAL_COORDS.get(idx, {"lat": None, "lng": None})
#         hosp["lat"] = coord["lat"]
#         hosp["lng"] = coord["lng"]

#         key = f"hospital:{idx}"
#         redis_client.set(key, json.dumps(hosp))

#     print(f"[INFO] Updated {len(hospitals)} hospital records in Redis.")


# if __name__ == "__main__":
#     print("[INFO] Fetching hospital wait times...")
#     raw_hospitals = fetch_wait_times()   # ✅ FIXED name
#     enriched = enrich_hospitals(raw_hospitals)
#     update_redis(enriched)
#     print("[DONE] Hospital data sync complete.")
