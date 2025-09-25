# app/services/hospital_service.py
import redis
import json
from typing import List, Dict

# ---------------- Redis Client ----------------
redis_client = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)

def get_all_hospitals_from_redis():
    keys = redis_client.keys("hospital:*")
    hospitals = []
    for key in keys:
        # Skip non-hospital keys like "hospital:count"
        if key == "hospital:count":
            continue
        try:
            data = json.loads(redis_client.get(key))
            # Optional: validate it's a dict with 'name'
            if isinstance(data, dict) and "name" in data:
                hospitals.append(data)
        except (TypeError, json.JSONDecodeError):
            continue  # skip invalid entries
    hospitals.sort(key=lambda x: x.get("name", ""))
    return hospitals