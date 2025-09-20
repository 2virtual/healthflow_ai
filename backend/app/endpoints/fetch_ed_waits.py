# src/api/ws_wait_times.py
import asyncio
import json
import requests
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# Router for both WebSocket + HTTP
router = APIRouter(prefix="/ed-waits", tags=["ED Waits"])

# Keep track of connected clients
clients = set()
latest_data = []


def fetch_wait_times():
    """Fetch and flatten Alberta wait times from AHS API."""
    url = "https://www.albertahealthservices.ca/WebApps/WaitTimes/api/WaitTimes"
    r = requests.get(url, timeout=10)
    data = r.json()

    results = []
    for region, categories in data.items():
        for category, hospitals in categories.items():
            for hospital in hospitals:
                results.append({
                    "region": region,
                    "category": category,
                    "name": hospital.get("Name"),
                    "wait_time": hospital.get("WaitTime"),
                    "note": hospital.get("Note")
                })
    return results


@router.get("/", summary="Get latest ED wait times (HTTP)")
def get_latest_wait_times():
    """
    Returns the most recent cached wait times (or fetches fresh if empty).
    Useful for Swagger testing and non-realtime clients.
    """
    global latest_data
    if not latest_data:
        latest_data = fetch_wait_times()
    return latest_data


async def broadcast_data():
    """Background task to fetch & broadcast wait times to all WebSocket clients."""
    global latest_data
    while True:
        try:
            latest_data = fetch_wait_times()
            # Send JSON to all connected WebSocket clients
            for ws in list(clients):
                try:
                    await ws.send_text(json.dumps(latest_data))
                except Exception:
                    clients.remove(ws)
        except Exception as e:
            print(f"Error fetching/broadcasting: {e}")
        await asyncio.sleep(30)  # fetch every 30s


@router.websocket("/ws")
async def ws_ed_wait_times(websocket: WebSocket):
    """
    WebSocket endpoint for live ED wait times.
    Clients will receive updates every 30s.
    """
    await websocket.accept()
    clients.add(websocket)
    try:
        # Send latest data immediately after connection
        if latest_data:
            await websocket.send_text(json.dumps(latest_data))

        while True:
            await asyncio.sleep(30)  # keep connection alive
    except WebSocketDisconnect:
        clients.remove(websocket)
