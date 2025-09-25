import redis
import json
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def set_hospital_data(data: dict, expire_sec: int = 300):
    """Save hospital data with TTL (default 5 minutes)."""
    r.set("hospital_data", json.dumps(data), ex=expire_sec)

def get_hospital_data() -> dict:
    """Fetch hospital data from Redis."""
    data = r.get("hospital_data")
    return json.loads(data) if data else {}
