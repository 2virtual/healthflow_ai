# app/endpoints/ws_wait_times.py
import asyncio
import json
import logging
import requests
from fastapi import WebSocket, WebSocketDisconnect

# Shared across broadcast and websocket handler
clients = set()
latest_data = []

logger = logging.getLogger("wait_times_ws")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def fetch_wait_times():
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
                    "note": hospital.get("Note"),
                })
    return results


async def broadcast_data():
    global latest_data
    while True:
        latest_data = fetch_wait_times()
        logger.info(f"📡 Broadcasting {len(latest_data)} records to {len(clients)} clients.")
        for ws in list(clients):
            try:
                await ws.send_text(json.dumps(latest_data))
            except Exception as e:
                clients.remove(ws)
                logger.warning(f"⚠️ Removed client {id(ws)} due to error: {e}")
        await asyncio.sleep(30)


async def ws_ed_wait_times(websocket: WebSocket):
    """Handle WebSocket connections and share the same clients set."""
    await websocket.accept()
    clients.add(websocket)
    logger.info(f"✅ Client {id(websocket)} connected. Total: {len(clients)}")
    try:
        if latest_data:
            await websocket.send_text(json.dumps(latest_data))
        while True:
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        clients.remove(websocket)
        logger.info(f"🔌 Client {id(websocket)} disconnected. Total: {len(clients)}")
