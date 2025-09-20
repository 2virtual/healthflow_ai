from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query
import httpx
import time
import random
import asyncio
import json
from math import radians, cos, sin, asin, sqrt
from pathlib import Path
from rapidfuzz import process  # fuzzy matching

router = APIRouter()

# ---------------------------
# Cache settings
# ---------------------------
CACHE_TTL = 300  # 5 minutes
cached_data = None
last_fetch_time = 0

# ---------------------------
# Config
# ---------------------------
AHS_API_URL = "https://www.albertahealthservices.ca/WebApps/WaitTimes/api/WaitTimes"
WAIT_TIME_THRESHOLD = 120  # minutes
HOSPITAL_COORDS_FILE = Path("hospital_coordinates.json")  # precomputed lat/lng

# ---------------------------
# Load Coordinates
# ---------------------------
def load_hospital_coords():
    if not HOSPITAL_COORDS_FILE.exists():
        print("⚠️ hospital_coordinates.json not found. Returning empty dict.")
        return {}
    try:
        with open(HOSPITAL_COORDS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Failed to load hospital_coordinates.json: {e}")
        return {}

HOSPITAL_COORDS = load_hospital_coords()

# ---------------------------
# Helper functions
# ---------------------------
async def fetch_ahs_data():
    """Fetch data from Alberta Health Services API (with caching)."""
    global cached_data, last_fetch_time
    now = time.time()
    if cached_data and (now - last_fetch_time) < CACHE_TTL:
        return cached_data
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            response = await client.get(AHS_API_URL)
            response.raise_for_status()
            data = response.json()
            cached_data = data
            last_fetch_time = now
            return data
    except Exception as e:
        print(f"⚠️ Error fetching AHS data: {e}")
        return None

def parse_wait_time(wait_str: str) -> int:
    """Convert wait time string like '2 hr 30 min' to total minutes."""
    if not wait_str:
        return 0
    wait_str = wait_str.lower()
    hours, minutes = 0, 0
    if "hr" in wait_str:
        parts = wait_str.split("hr")
        try:
            hours = int(parts[0].strip())
        except ValueError:
            hours = 0
        if "min" in parts[1]:
            try:
                minutes = int(parts[1].replace("min", "").strip())
            except ValueError:
                minutes = 0
    elif "min" in wait_str:
        try:
            minutes = int(wait_str.replace("min", "").strip())
        except ValueError:
            minutes = 0
    return hours * 60 + minutes

def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance (km) between two lat/lng points."""
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c

def ai_predict_fallback():
    """Mock AI fallback (replace with ML model)."""
    return {
        "hospital": "AI-Predicted Hospital",
        "predicted_wait_time": random.randint(30, 150),
        "note": "Fallback AI prediction due to stale/unavailable live data."
    }

# ---------------------------
# REST Endpoint (region-based)
# ---------------------------
@router.get("/recommend")
async def recommend(location: str = "Calgary"):
    """Recommend best hospital using region filter + wait time only."""
    ahs_data = await fetch_ahs_data()
    if not ahs_data or not isinstance(ahs_data, list):
        return ai_predict_fallback()

    nearby_hospitals = [
        h for h in ahs_data
        if isinstance(h, dict) and location.lower() in h.get("region", "").lower()
    ]

    if not nearby_hospitals:
        raise HTTPException(status_code=404, detail="No hospitals found for this location.")

    best_hospital = min(
        nearby_hospitals,
        key=lambda x: parse_wait_time(x.get("wait_time", "0"))
    )
    wait_time = parse_wait_time(best_hospital.get("wait_time", "0"))
    status = "✅ Recommended" if wait_time <= WAIT_TIME_THRESHOLD else "⚠️ Long wait"

    return {
        "hospital": best_hospital.get("name"),
        "wait_time": best_hospital.get("wait_time"),
        "status": status,
        "recommendation": "Best option in region based on current data."
    }

# ---------------------------
# REST Endpoint (GPS-based, normalized & flattened with fuzzy matching)
# ---------------------------
@router.get("/recommend/gps")
async def recommend_gps(lat: float = Query(...), lng: float = Query(...)):
    """Recommend top 3 hospitals using patient GPS + wait time + distance with robust matching."""
    ahs_data = await fetch_ahs_data()
    if not ahs_data or not isinstance(ahs_data, dict):
        return ai_predict_fallback()

    # Flatten hospitals
    flattened_hospitals = []
    for region, categories in ahs_data.items():
        for category, hospitals in categories.items():
            for h in hospitals:
                name = h.get("Name") or h.get("name")
                wait_time = h.get("WaitTime") or h.get("wait_time") or "0"
                flattened_hospitals.append({
                    "name": name.strip() if name else "",
                    "wait_time": wait_time,
                    "category": category,
                    "region": region
                })

    if not flattened_hospitals:
        return ai_predict_fallback()

    # Normalize hospital coordinates keys
    HOSPITAL_COORDS_NORMALIZED = {k.lower().strip(): v for k, v in HOSPITAL_COORDS.items()}

    recommendations = []
    for h in flattened_hospitals:
        hospital_name = h["name"]
        wait_str = h["wait_time"]
        wait_minutes = parse_wait_time(wait_str)
        coords = None

        # Fuzzy match hospital name to coordinates
        if HOSPITAL_COORDS_NORMALIZED:
            match_name, score, _ = process.extractOne(
                hospital_name.lower(),
                HOSPITAL_COORDS_NORMALIZED.keys()
            )
            if score >= 80:
                coords = HOSPITAL_COORDS_NORMALIZED[match_name]

        if coords:
            distance_km = haversine(lat, lng, coords["lat"], coords["lng"])
        else:
            distance_km = None  # fallback if no coordinates found

        score_metric = wait_minutes + (distance_km * 2 if distance_km else 0)
        recommendations.append({
            "hospital": hospital_name,
            "wait_time": wait_str,
            "category": h["category"],
            "region": h["region"],
            "distance_km": round(distance_km, 1) if distance_km else None,
            "score": round(score_metric, 1)
        })

    if not recommendations:
        raise HTTPException(status_code=404, detail="No hospitals available for recommendation.")

    # Sort by score (wait + distance) and pick top 3
    sorted_recommendations = sorted(recommendations, key=lambda x: x["score"])[:3]

    for idx, r in enumerate(sorted_recommendations):
        r["status"] = "✅ Recommended" if parse_wait_time(r["wait_time"]) <= WAIT_TIME_THRESHOLD else "⚠️ Long wait"
        r["recommendation"] = "Balanced choice (wait time + distance)" if idx == 0 else "Alternative option"

    return {
        "patient_location": {"lat": lat, "lng": lng},
        "top_recommendations": sorted_recommendations
    }

# ---------------------------
# WebSocket Endpoint
# ---------------------------
@router.websocket("/ws/recommend")
async def websocket_recommend(websocket: WebSocket):
    """Stream live AHS wait times to WebSocket clients."""
    await websocket.accept()
    try:
        while True:
            ahs_data = await fetch_ahs_data()
            update = ahs_data if ahs_data else ai_predict_fallback()
            await websocket.send_json(update)
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        print("❌ WebSocket client disconnected")




# from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query
# import httpx
# import time
# import random
# import asyncio
# import json
# from math import radians, cos, sin, asin, sqrt
# from pathlib import Path

# router = APIRouter()

# # ---------------------------
# # Cache settings
# # ---------------------------
# CACHE_TTL = 300  # 5 minutes
# cached_data = None
# last_fetch_time = 0

# # ---------------------------
# # Config
# # ---------------------------
# AHS_API_URL = "https://www.albertahealthservices.ca/WebApps/WaitTimes/api/WaitTimes"
# WAIT_TIME_THRESHOLD = 120  # minutes
# HOSPITAL_COORDS_FILE = Path("hospital_coordinates.json")  # precomputed lat/lng


# # ---------------------------
# # Load Coordinates (no subprocess)
# # ---------------------------
# def load_hospital_coords():
#     if not HOSPITAL_COORDS_FILE.exists():
#         print("⚠️ hospital_coordinates.json not found. Returning empty dict.")
#         return {}
#     try:
#         with open(HOSPITAL_COORDS_FILE, "r") as f:
#             return json.load(f)
#     except Exception as e:
#         print(f"❌ Failed to load hospital_coordinates.json: {e}")
#         return {}


# HOSPITAL_COORDS = load_hospital_coords()

# # ---------------------------
# # Helper functions
# # ---------------------------
# async def fetch_ahs_data():
#     """Fetch data from Alberta Health Services API (with caching)."""
#     global cached_data, last_fetch_time
#     now = time.time()

#     if cached_data and (now - last_fetch_time) < CACHE_TTL:
#         return cached_data

#     try:
#         async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
#             response = await client.get(AHS_API_URL)
#             response.raise_for_status()
#             data = response.json()
#             cached_data = data
#             last_fetch_time = now
#             return data
#     except Exception as e:
#         print(f"⚠️ Error fetching AHS data: {e}")
#         return None


# def parse_wait_time(wait_str: str) -> int:
#     """Convert wait time string like '2 hr 30 min' to total minutes."""
#     if not wait_str:
#         return 0
#     wait_str = wait_str.lower()
#     hours, minutes = 0, 0
#     if "hr" in wait_str:
#         parts = wait_str.split("hr")
#         try:
#             hours = int(parts[0].strip())
#         except ValueError:
#             hours = 0
#         if "min" in parts[1]:
#             try:
#                 minutes = int(parts[1].replace("min", "").strip())
#             except ValueError:
#                 minutes = 0
#     elif "min" in wait_str:
#         try:
#             minutes = int(wait_str.replace("min", "").strip())
#         except ValueError:
#             minutes = 0
#     return hours * 60 + minutes


# def haversine(lat1, lon1, lat2, lon2):
#     """Calculate distance (km) between two lat/lng points."""
#     R = 6371
#     dlat = radians(lat2 - lat1)
#     dlon = radians(lon2 - lon1)
#     a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
#     c = 2 * asin(sqrt(a))
#     return R * c


# def ai_predict_fallback():
#     """Mock AI fallback (replace with ML model)."""
#     return {
#         "hospital": "AI-Predicted Hospital",
#         "predicted_wait_time": random.randint(30, 150),
#         "note": "Fallback AI prediction due to stale/unavailable live data."
#     }


# # ---------------------------
# # REST Endpoint (region-based)
# # ---------------------------
# @router.get("/recommend")
# async def recommend(location: str = "Calgary"):
#     """Recommend best hospital using region filter + wait time only."""
#     ahs_data = await fetch_ahs_data()
#     if not ahs_data or not isinstance(ahs_data, list):
#         return ai_predict_fallback()

#     nearby_hospitals = [
#         h for h in ahs_data
#         if isinstance(h, dict) and location.lower() in h.get("region", "").lower()
#     ]

#     if not nearby_hospitals:
#         raise HTTPException(status_code=404, detail="No hospitals found for this location.")

#     best_hospital = min(
#         nearby_hospitals,
#         key=lambda x: parse_wait_time(x.get("wait_time", "0"))
#     )
#     wait_time = parse_wait_time(best_hospital.get("wait_time", "0"))

#     status = "✅ Recommended" if wait_time <= WAIT_TIME_THRESHOLD else "⚠️ Long wait"
#     return {
#         "hospital": best_hospital.get("name"),
#         "wait_time": best_hospital.get("wait_time"),
#         "status": status,
#         "recommendation": "Best option in region based on current data."
#     }


# # --------------------------- 
# # REST Endpoint (GPS-based, normalized & flattened)
# # ---------------------------
# @router.get("/recommend/gps")
# async def recommend_gps(
#     lat: float = Query(..., description="Patient latitude"),
#     lng: float = Query(..., description="Patient longitude")
# ):
#     """Recommend top 3 hospitals using patient GPS + wait time + distance with name normalization."""
#     ahs_data = await fetch_ahs_data()
#     if not ahs_data or not isinstance(ahs_data, dict):
#         return ai_predict_fallback()

#     # Flatten the nested AHS data: region -> category -> hospitals
#     flattened_hospitals = []
#     for region, categories in ahs_data.items():
#         for category, hospitals in categories.items():
#             for hospital in hospitals:
#                 flattened_hospitals.append({
#                     "region": region,
#                     "category": category,
#                     "name": hospital.get("Name") or hospital.get("name"),
#                     "wait_time": hospital.get("WaitTime") or hospital.get("wait_time"),
#                     "note": hospital.get("Note") or hospital.get("note")
#                 })

#     if not flattened_hospitals:
#         return ai_predict_fallback()

#     # Normalize hospital coordinates dict
#     HOSPITAL_COORDS_NORMALIZED = {k.lower().strip(): v for k, v in HOSPITAL_COORDS.items()}

#     recommendations = []
#     for h in flattened_hospitals:
#         name = h.get("name", "")
#         wait_str = h.get("wait_time", "0")
#         wait_time = parse_wait_time(wait_str)

#         # Normalize the name to match coordinates
#         coords = HOSPITAL_COORDS_NORMALIZED.get(name.lower().strip())
#         if not coords:
#             continue

#         distance_km = haversine(lat, lng, coords["lat"], coords["lng"])
#         score = wait_time + (distance_km * 2)  # weight distance lightly

#         recommendations.append({
#             "hospital": name,
#             "wait_time": wait_str,
#             "distance_km": round(distance_km, 1),
#             "score": round(score, 1),
#         })

#     if not recommendations:
#         raise HTTPException(status_code=404, detail="No hospitals with coordinates available.")

#     # Sort by score and take top 3
#     sorted_recommendations = sorted(recommendations, key=lambda x: x["score"])[:3]

#     # Add status + recommendation message
#     for r in sorted_recommendations:
#         r["status"] = "✅ Recommended" if parse_wait_time(r["wait_time"]) <= WAIT_TIME_THRESHOLD else "⚠️ Long wait"
#         r["recommendation"] = (
#             "Balanced choice (wait time + distance)"
#             if r == sorted_recommendations[0]
#             else "Alternative option"
#         )

#     return {
#         "patient_location": {"lat": lat, "lng": lng},
#         "top_recommendations": sorted_recommendations
#     }


# # ---------------------------
# # WebSocket Endpoint
# # ---------------------------
# @router.websocket("/ws/recommend")
# async def websocket_recommend(websocket: WebSocket):
#     await websocket.accept()
#     try:
#         while True:
#             ahs_data = await fetch_ahs_data()
#             update = ahs_data if ahs_data else ai_predict_fallback()
#             await websocket.send_json(update)
#             await asyncio.sleep(60)
#     except WebSocketDisconnect:
#         print("❌ WebSocket client disconnected")

