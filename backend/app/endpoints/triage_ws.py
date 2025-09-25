# app/endpoints/triage_ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
import json
from app.database import get_db
from app.services.triage_service import process_triage

router = APIRouter()

@router.websocket("/ws/triage")
async def ws_triage(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    try:
        while True:
            text = await websocket.receive_text()
            try:
                payload = json.loads(text)
            except Exception:
                await websocket.send_text(json.dumps({"response": "Invalid request format"}))
                continue

            # ✅ Await async triage processing
            result = await process_triage(payload, db)
            human_response = result.get("response", "No response generated")

            # Send back humanized response along with full triage info
            await websocket.send_text(json.dumps(result))

    except WebSocketDisconnect:
        print("⚠️ WebSocket disconnected")
        return

