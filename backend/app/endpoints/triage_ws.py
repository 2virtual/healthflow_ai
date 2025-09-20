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



# # app/endpoints/triage_ws.py
# from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
# from sqlalchemy.orm import Session
# import json
# from app.database import get_db
# from app.services.triage_service import process_triage

# # ✅ ML model import
# from pypmml import Model

# router = APIRouter()

# # ✅ Load PMML model once on startup
# pmml_model = None
# try:
#     pmml_model = Model.load("app/models/triage_model.pmml")  # ✅ updated path
#     print("✅ PMML model loaded successfully in triage_ws")
# except Exception as e:
#     print(f"⚠️ Could not load PMML model: {e}")


# @router.websocket("/ws/triage")
# async def ws_triage(websocket: WebSocket, db: Session = Depends(get_db)):
#     await websocket.accept()
#     try:
#         while True:
#             text = await websocket.receive_text()
#             try:
#                 payload = json.loads(text)
#             except Exception:
#                 await websocket.send_text(json.dumps({"response": "Invalid request format"}))
#                 continue

#             symptoms = payload.get("symptoms", "").strip()
#             response = None

#             if pmml_model and symptoms:
#                 try:
#                     # ✅ Example: run ML model prediction
#                     prediction = pmml_model.predict(payload)
#                     response = f"ML prediction: {prediction}"
#                 except Exception as e:
#                     print(f"⚠️ ML model prediction failed: {e}")

#             # ✅ Fallback to rule-based / existing service
#             if not response:
#                 result = process_triage(payload, db)
#                 response = result.get("response", "No response generated")

#             await websocket.send_text(json.dumps({"response": response}))

#     except WebSocketDisconnect:
#         return

