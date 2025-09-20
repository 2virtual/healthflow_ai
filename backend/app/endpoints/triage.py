# app/endpoints/triage.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.triage_service import process_triage

router = APIRouter()

@router.post("/triage")
def triage(payload: dict, db: Session = Depends(get_db)):
    return process_triage(payload, db)





# # app/endpoints/triage.py
# import json
# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session
# from datetime import datetime
# import requests
# import pandas as pd

# from app.database import get_db
# from app.models.triage import TriageAudit, TriageMessage
# from app.endpoints.triage_logic import triage_logic, TriageReqModel, _detect_symptoms

# # Load PMML model
# try:
#     from pypmml import Model
#     triage_model = Model.load("models/triage_model.pmml")
#     use_ml = True
#     print("[INFO] PMML triage model loaded for REST triage")
# except Exception as e:
#     print(f"[Warning] Could not load PMML model for REST: {e}")
#     triage_model = None
#     use_ml = False

# router = APIRouter()

# def _force_english(text_or_obj):
#     if isinstance(text_or_obj, dict):
#         return text_or_obj.get("en") or next(iter(text_or_obj.values()), "")
#     return text_or_obj or ""

# def _fallback_triage(payload: dict) -> str:
#     """Simple rules if ML not available."""
#     SBP = payload.get("SBP", 120)
#     HR = payload.get("HR", 75)
#     RR = payload.get("RR", 18)
#     BT = payload.get("BT", 37.0)

#     if SBP < 90 or HR > 120:
#         return "Emergency"
#     elif SBP < 100 or RR > 20 or BT > 39:
#         return "Urgent"
#     elif SBP < 110:
#         return "PrimaryCare"
#     else:
#         return "SelfCare"

# def _ml_or_rules(payload: dict):
#     """Try ML first, else rules."""
#     if use_ml and triage_model:
#         try:
#             df = pd.DataFrame([payload])
#             result = triage_model.predict(df)
#             predicted = str(result.at[0, "predicted_KTAS_expert"])
#             return predicted, "ML"
#         except Exception as e:
#             print(f"[Error] ML prediction failed in REST: {e}")
#     return _fallback_triage(payload), "Rules"

# @router.post("/triage")
# def triage(payload: dict, db: Session = Depends(get_db)):
#     user_msg_text = payload.get("symptoms", "").strip()
#     if not user_msg_text:
#         raise HTTPException(status_code=400, detail="No symptoms provided")

#     detected = _detect_symptoms(user_msg_text)
#     response_text = None
#     recommended_level = score = reasons = suggested_action = hospital_reco = None

#     if detected:
#         # Rule-based NLP match
#         best_match = max(detected, key=lambda x: len(x["matched_terms"]))
#         response_text = _force_english(best_match["rule"]["response"])
#         recommended_level = best_match["rule"]["id"]
#         meta_flag = {"human_like": True, "matched_rule": best_match["rule"]["id"]}
#     else:
#         # Try ML or rules
#         predicted_level, source = _ml_or_rules(payload)
#         recommended_level = predicted_level

#         req_model = TriageReqModel(
#             symptoms=user_msg_text,
#             age=payload.get("age"),
#             known_conditions=payload.get("known_conditions", []),
#         )
#         result = triage_logic(req_model)

#         response_text = _force_english(result.suggested_action)
#         score = result.score
#         reasons = result.reasons
#         suggested_action = _force_english(result.suggested_action)
#         meta_flag = {"source": source, **result.meta}

#     # Fetch hospital recommendation if urgent
#     if recommended_level in ["Emergency", "Urgent", "PrimaryCare"]:
#         try:
#             r = requests.get(
#                 "http://localhost:8000/recommend/gps",
#                 timeout=2,
#                 params={"lat": payload.get("lat"), "lng": payload.get("lng")},
#             )
#             if r.status_code == 200:
#                 hospital_reco = r.json()
#         except Exception:
#             hospital_reco = None

#     # Save audit record
#     audit = TriageAudit(
#         received_at=datetime.utcnow(),
#         symptoms=user_msg_text,
#         age=payload.get("age"),
#         known_conditions=payload.get("known_conditions", []),
#         recommended_level=recommended_level,
#         score=score,
#         reasons=reasons,
#         suggested_action=suggested_action,
#         hospital_recommendation=hospital_reco,
#         meta=meta_flag,
#     )
#     db.add(audit)
#     db.commit()
#     db.refresh(audit)

#     # Save user + bot messages
#     user_msg = TriageMessage(audit_id=audit.id, direction="user", text=user_msg_text)
#     db.add(user_msg)
#     db.commit()

#     bot_payload = {
#         "response": response_text,
#         "recommended_level": recommended_level,
#         "score": score,
#         "reasons": reasons,
#         "suggested_action": suggested_action,
#         "hospital_recommendation": hospital_reco,
#         "received_at": audit.received_at.isoformat(),
#         "meta": audit.meta,
#     }
#     bot_msg = TriageMessage(audit_id=audit.id, direction="bot", text=json.dumps(bot_payload))
#     db.add(bot_msg)
#     db.commit()

#     return bot_payload







# # app/endpoints/triage.py
# from datetime import datetime
# from fastapi import APIRouter, Depends
# from pydantic import BaseModel
# from typing import List, Optional, Dict, Any
# import requests
# from sqlalchemy.orm import Session

# from app.database import get_db
# from app.models.triage import TriageAudit
# from app.endpoints.triage_logic import triage_logic
# from app.models.triage_models import TriageReqModel  # Updated import

# # ✅ Define router
# router = APIRouter(prefix="/triage", tags=["Triage"])

# # ---------------------------
# # Request and Response Models
# # ---------------------------
# class TriageRequestOut(BaseModel):
#     message: str
#     age: Optional[int] = None
#     known_conditions: Optional[List[str]] = None
#     language: Optional[str] = "en"

# class TriageResultOut(BaseModel):
#     response: str
#     recommended_level: Optional[str] = None
#     score: Optional[int] = None
#     reasons: Optional[List[str]] = None
#     suggested_action: Optional[str] = None
#     hospital_recommendation: Optional[Any] = None
#     received_at: datetime
#     meta: Optional[Dict[str, Any]] = None

# # ---------------------------
# # Triage Endpoint
# # ---------------------------
# @router.post("/", response_model=TriageResultOut)
# def triage_endpoint(req: TriageRequestOut, db: Session = Depends(get_db)):

#     msg = req.message.lower().strip()

#     # --- Human-like casual responses ---
#     if "thank" in msg:
#         response_text = "You're very welcome! I'm glad I could help. 💙"
#         recommended_level = score = reasons = suggested_action = hospital_reco = None

#     elif "headache" in msg and "stomach" in msg:
#         response_text = (
#             "I'm sorry you're not feeling well 😔. Since you have both a headache and stomach upset, "
#             "it might be best to rest, drink fluids, and monitor your symptoms. "
#             "If it worsens, please consider seeing a doctor."
#         )
#         recommended_level = score = reasons = suggested_action = hospital_reco = None

#     elif "headache" in msg:
#         response_text = (
#             "It sounds like you have a headache. Try resting, staying hydrated, "
#             "and avoiding screen time. If it's severe or persistent, get medical advice."
#         )
#         recommended_level = score = reasons = suggested_action = hospital_reco = None

#     elif "stomach" in msg or "upset" in msg:
#         response_text = (
#             "Stomach upset can sometimes improve with rest and fluids. "
#             "Avoid heavy meals for a while. If you have severe pain, vomiting, or fever, consult a doctor."
#         )
#         recommended_level = score = reasons = suggested_action = hospital_reco = None

#     else:
#         # --- Structured triage logic ---
#         result = triage_logic(TriageReqModel(
#             symptoms=req.message,
#             age=req.age,
#             known_conditions=req.known_conditions
#         ))

#         response_text = "Here’s your triage assessment."
#         recommended_level = result.recommended_level
#         score = result.score
#         reasons = result.reasons
#         suggested_action = result.suggested_action

#         # Optional hospital recommendation via local /recommend endpoint
#         hospital_reco = None
#         try:
#             r = requests.get(
#                 "http://localhost:8000/recommend",
#                 timeout=3,
#                 params={"symptoms": req.message},
#             )
#             if r.status_code == 200:
#                 hospital_reco = r.json()
#         except Exception:
#             hospital_reco = None

#     # Persist audit record in DB
#     audit = TriageAudit(
#         received_at=datetime.utcnow(),
#         symptoms=req.message,
#         age=req.age,
#         known_conditions=req.known_conditions,
#         recommended_level=recommended_level,
#         score=score,
#         reasons=reasons,
#         suggested_action=suggested_action,
#         hospital_recommendation=hospital_reco,
#         meta={"human_like": recommended_level is None},
#     )
#     db.add(audit)
#     db.commit()
#     db.refresh(audit)

#     # Return structured response
#     return {
#         "response": response_text,
#         "recommended_level": recommended_level,
#         "score": score,
#         "reasons": reasons,
#         "suggested_action": suggested_action,
#         "hospital_recommendation": hospital_reco,
#         "received_at": audit.received_at,
#         "meta": audit.meta,
#     }





# # app/endpoints/triage.py
# from datetime import datetime
# from fastapi import APIRouter, Depends
# from pydantic import BaseModel
# from typing import List, Optional, Dict, Any
# import requests
# from sqlalchemy.orm import Session
# from app.database import get_db
# from app.models.triage import TriageAudit
# from app.endpoints.triage_logic import triage_logic, TriageRequest, TriageResult

# # ✅ Define router
# router = APIRouter(prefix="/triage", tags=["Triage"])

# # ---------------------------
# # Request and Response Models
# # ---------------------------
# class TriageRequestOut(BaseModel):
#     message: str
#     age: Optional[int] = None
#     known_conditions: Optional[List[str]] = None
#     language: Optional[str] = "en"

# class TriageResultOut(BaseModel):
#     response: str
#     recommended_level: Optional[str] = None
#     score: Optional[int] = None
#     reasons: Optional[List[str]] = None
#     suggested_action: Optional[str] = None
#     hospital_recommendation: Optional[Any] = None
#     received_at: datetime
#     meta: Optional[Dict[str, Any]] = None

# # ---------------------------
# # Triage Endpoint
# # ---------------------------
# @router.post("/", response_model=TriageResultOut)
# def triage_endpoint(req: TriageRequestOut, db: Session = Depends(get_db)):

#     msg = req.message.lower().strip()

#     # --- Human-like casual responses ---
#     if "thank" in msg:
#         response_text = "You're very welcome! I'm glad I could help. 💙"
#         recommended_level = score = reasons = suggested_action = hospital_reco = None

#     elif "headache" in msg and "stomach" in msg:
#         response_text = (
#             "I'm sorry you're not feeling well 😔. Since you have both a headache and stomach upset, "
#             "it might be best to rest, drink fluids, and monitor your symptoms. "
#             "If it worsens, please consider seeing a doctor."
#         )
#         recommended_level = score = reasons = suggested_action = hospital_reco = None

#     elif "headache" in msg:
#         response_text = (
#             "It sounds like you have a headache. Try resting, staying hydrated, "
#             "and avoiding screen time. If it's severe or persistent, get medical advice."
#         )
#         recommended_level = score = reasons = suggested_action = hospital_reco = None

#     elif "stomach" in msg or "upset" in msg:
#         response_text = (
#             "Stomach upset can sometimes improve with rest and fluids. "
#             "Avoid heavy meals for a while. If you have severe pain, vomiting, or fever, consult a doctor."
#         )
#         recommended_level = score = reasons = suggested_action = hospital_reco = None

#     else:
#         # --- Structured triage logic ---
#         result: TriageResult = triage_logic(TriageRequest(**req.dict()))
#         response_text = "Here’s your triage assessment."
#         recommended_level = result.recommended_level
#         score = result.score
#         reasons = result.reasons
#         suggested_action = result.suggested_action

#         # Optional hospital recommendation
#         hospital_reco = None
#         try:
#             r = requests.get(
#                 "http://localhost:8000/recommend",
#                 timeout=3,
#                 params={"symptoms": req.message},
#             )
#             if r.status_code == 200:
#                 hospital_reco = r.json()
#         except Exception:
#             hospital_reco = None

#     # Persist audit record
#     audit = TriageAudit(
#         received_at=datetime.utcnow(),
#         symptoms=req.message,
#         age=req.age,
#         known_conditions=req.known_conditions,
#         recommended_level=recommended_level,
#         score=score,
#         reasons=reasons,
#         suggested_action=suggested_action,
#         hospital_recommendation=hospital_reco,
#         meta={"human_like": recommended_level is None},
#     )
#     db.add(audit)
#     db.commit()
#     db.refresh(audit)

#     # Return combined response
#     return {
#         "response": response_text,
#         "recommended_level": recommended_level,
#         "score": score,
#         "reasons": reasons,
#         "suggested_action": suggested_action,
#         "hospital_recommendation": hospital_reco,
#         "received_at": audit.received_at,
#         "meta": audit.meta,
#     }
