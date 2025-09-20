# app/services/triage_service.py

import os
import json
import logging
import pandas as pd
import re
import random
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional
from geopy.distance import geodesic  # pip install geopy

from app.endpoints.triage_logic import (
    triage_logic,
    TriageReqModel,
    _compose_response,
    _detect_symptoms,
)
from app.endpoints.recommend import recommend_gps  # ✅ direct import
from app.models.triage import TriageAudit, TriageMessage

# -------------------------------
# Load Hospital Coordinates JSON
# -------------------------------
HOSPITAL_COORDS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "hospital_coordinates.json"
)
with open(HOSPITAL_COORDS_PATH, "r", encoding="utf-8") as f:
    HOSPITAL_COORDS = json.load(f)

# -------------------------------
# Configure logging
# -------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------------
# Load ML model (PMML)
# -------------------------------
try:
    from pypmml import Model

    triage_model = Model.load("app/models/triage_model.pmml")
    use_ml = True
    logger.info("[INFO] PMML triage model loaded for triage service")
except Exception as e:
    logger.warning(f"[Warning] Could not load PMML model: {e}")
    triage_model = None
    use_ml = False

# -------------------------------
# Greeting Handler
# -------------------------------
_greetings_variations = {
    "hi": ["Hi there! How are you feeling today?", "Hey! How’s your day going?", "Hello! What’s on your mind health-wise?"],
    "hello": ["Hello! I’m here to listen. What symptoms would you like to share?", "Hi there! How are you doing?", "Hello! How can I support you today?"],
    "thanks": ["You're very welcome! Take care of yourself.", "Happy to help! Stay healthy.", "No problem at all. Wishing you good health!"],
    "thank you": ["Glad I could help. How are you feeling now?", "Anytime! Take care of yourself.", "Of course! Wishing you a speedy recovery."],
    "what's up": ["Not much, just here to support you with health advice.", "I’m here for you! What’s happening with your health?", "Just ready to listen. How are you doing?"],
    "how are you": ["I'm doing well, thank you! How can I help with your health concerns today?", "Pretty good, thanks! How are you feeling today?", "I’m good! Hope you are too. What’s troubling you?"],
    "how are you doing": ["I'm good, thanks! How are you feeling today?", "Doing well! How about you?", "I’m fine, thank you. How are you doing today?"],
    "good morning": ["Good morning! How are you doing today?", "Morning! How’s your health feeling today?", "Good morning! Hope you’re doing well."],
    "good afternoon": ["Good afternoon! What health concerns are on your mind?", "Afternoon! How are you feeling?", "Good afternoon! How’s your day going?"],
    "good evening": ["Good evening! How are you feeling tonight?", "Evening! What health concerns would you like to share?", "Good evening! How was your day? Any symptoms bothering you?"],
    "yo": ["Hey there! What health concerns can I help with?", "Yo! How are you feeling today?", "Hi! What’s up with your health?"],
    "sup": ["Hi! How are you feeling today?", "Sup! Any health issues bothering you?", "Hey! Want to tell me how you’re doing?"],
}


def handle_greetings(user_msg: str) -> Optional[str]:
    text = user_msg.lower().strip()
    matched = []
    for phrase, responses in _greetings_variations.items():
        if re.search(rf"\b{re.escape(phrase)}\b", text):
            matched.append((phrase, responses))
    if not matched:
        return None
    phrase, responses = max(matched, key=lambda x: len(x[0]))
    return random.choice(responses)


# -------------------------------
# Humanize Response
# -------------------------------
def humanize_response(raw_text: str, recommended_level: str, hospitals: list = None) -> str:
    if not raw_text:
        raw_text = "Please monitor your symptoms and seek care if they worsen."
    level_prefix = {
        "Emergency": "⚠️ Emergency: ",
        "Urgent": "🚨 Urgent attention recommended: ",
        "PrimaryCare": "🏥 Visit a primary care clinic: ",
        "SelfCare": "🩹 Self-care may be sufficient: ",
    }.get(recommended_level, "")
    message = f"{level_prefix}{raw_text}"
    if hospitals:
        message += "\n\nClosest hospitals for you:\n"
        for idx, h in enumerate(hospitals, 1):
            message += (
                f"{idx}. {h['name']} ({h['category']}) — {h.get('wait_time', 'N/A')}, "
                f"{h.get('distance_km', '?')} km away. Note: {h.get('note', 'No additional info')}\n"
            )
    return message.strip()


# -------------------------------
# Fallback & ML
# -------------------------------
def _fallback_triage(payload: dict) -> str:
    SBP = payload.get("SBP", 120)
    HR = payload.get("HR", 75)
    RR = payload.get("RR", 18)
    BT = payload.get("BT", 37.0)
    if SBP < 90 or HR > 120:
        return "Emergency"
    elif SBP < 100 or RR > 20 or BT > 39:
        return "Urgent"
    elif SBP < 110:
        return "PrimaryCare"
    else:
        return "SelfCare"


def _ml_or_rules(payload: dict):
    if use_ml and triage_model:
        try:
            df = pd.DataFrame([payload])
            result = triage_model.predict(df)
            predicted = str(result.at[0, "predicted_KTAS_expert"])
            return predicted, "ML"
        except Exception as e:
            logger.warning(f"[Error] ML prediction failed: {e}")
    return _fallback_triage(payload), "Rules"


def _force_english(text_or_obj):
    if isinstance(text_or_obj, dict):
        return text_or_obj.get("en") or next(iter(text_or_obj.values()), "")
    return text_or_obj or ""


# -------------------------------
# Main Triage Pipeline
# -------------------------------
async def process_triage(payload: dict, db: Session):
    logger.info("=== Incoming Triage Payload ===")
    for key, value in payload.items():
        logger.info(f"{key}: {value}")
    logger.info("================================")

    user_msg_text = payload.get("symptoms", "").strip()
    if not user_msg_text:
        return {"response": "No symptoms provided"}

    # --- Greeting check ---
    greeting_reply = handle_greetings(user_msg_text)
    if greeting_reply:
        return {
            "response": greeting_reply,
            "recommended_level": "None",
            "score": None,
            "reasons": [],
            "suggested_action": None,
            "hospital_recommendation": None,
            "received_at": datetime.utcnow().isoformat(),
            "meta": {"type": "greeting"},
        }

    # --- Rule or ML classification ---
    detected = _detect_symptoms(user_msg_text)
    response_text = recommended_level = score = reasons = suggested_action = None

    if detected:
        best_match = max(detected, key=lambda x: len(x["matched_terms"]))
        response_text = _force_english(best_match["rule"]["response"])
        recommended_level = best_match["rule"].get("category", "PrimaryCare")
        score = 100 if recommended_level == "Emergency" else 50
        reasons = [f"🚨 {recommended_level}: {best_match['rule']['id']} ({', '.join(best_match['matched_terms'])})"]
        suggested_action = _compose_response(
            recommended_level, score, reasons, TriageReqModel(symptoms=user_msg_text)
        ).suggested_action
    else:
        predicted_level, source = _ml_or_rules(payload)
        recommended_level = predicted_level
        req_model = TriageReqModel(
            symptoms=user_msg_text,
            age=payload.get("age"),
            known_conditions=payload.get("known_conditions", []),
        )
        result = triage_logic(req_model)
        response_text = _force_english(result.suggested_action)
        score = result.score
        reasons = result.reasons
        suggested_action = _force_english(result.suggested_action)

    # --- Hospital recommendations ---
    hospital_reco = []
    LEVEL_MAPPING = {"red": "Emergency", "yellow": "Urgent", "green": "PrimaryCare", "blue": "SelfCare"}
    mapped_level = LEVEL_MAPPING.get(recommended_level.lower(), recommended_level)

    if mapped_level in ["Emergency", "Urgent", "PrimaryCare"]:
        try:
            result = await recommend_gps(
                lat=payload.get("lat", 51.0447),
                lng=payload.get("lng", -114.0719),
            )
            fetched_hospitals = result.get("top_recommendations", [])
            fetched_lookup = {h["hospital"].lower(): h for h in fetched_hospitals}

            patient_coords = (payload.get("lat", 51.0447), payload.get("lng", -114.0719))
            merged_hospitals = []
            for hosp_name, coords in HOSPITAL_COORDS.items():
                distance_km = round(geodesic(patient_coords, (coords["lat"], coords["lng"])).km, 1)
                info = fetched_lookup.get(hosp_name.lower(), {})
                merged_hospitals.append(
                    {
                        "name": hosp_name,
                        "category": info.get("category", "Unknown"),
                        "region": info.get("region", "Unknown"),
                        "wait_time": info.get("wait_time", "N/A"),
                        "distance_km": distance_km,
                        "score": info.get("score", 0),
                        "status": info.get("status", ""),
                        "recommendation": info.get("recommendation", ""),
                        "note": info.get("note", "No additional info"),
                    }
                )
            hospital_reco = sorted(merged_hospitals, key=lambda x: x["distance_km"])[:3]
        except Exception as e:
            logger.warning(f"[Hospital Recommendation Error] {e}")
            hospital_reco = []

    # --- Humanized response ---
    human_response = humanize_response(response_text, recommended_level, hospital_reco)

    # --- Save audit (dump hospital_reco to JSON string) ---
    audit = TriageAudit(
        received_at=datetime.utcnow(),
        symptoms=user_msg_text,
        age=payload.get("age"),
        known_conditions=payload.get("known_conditions", []),
        recommended_level=recommended_level,
        score=score,
        reasons=reasons,
        suggested_action=suggested_action,
        hospital_recommendation=json.dumps(hospital_reco),  # ✅ dump here
        meta={"human_like": True},
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)

    # --- Save messages ---
    db.add(TriageMessage(audit_id=audit.id, direction="user", text=user_msg_text))
    db.commit()

    bot_payload = {
        "response": human_response,
        "recommended_level": recommended_level,
        "score": score,
        "reasons": reasons,
        "suggested_action": suggested_action,
        "hospital_recommendation": hospital_reco,  # ✅ return as dict/list
        "received_at": audit.received_at.isoformat(),
        "meta": audit.meta,
    }

    db.add(TriageMessage(audit_id=audit.id, direction="bot", text=json.dumps(bot_payload)))
    db.commit()

    logger.info("=== Triage Bot Response ===")
    for key, value in bot_payload.items():
        logger.info(f"{key}: {value}")
    logger.info("===========================")

    return bot_payload




# # app/services/triage_service.py
# import json
# import logging
# import pandas as pd
# import requests
# from datetime import datetime
# from sqlalchemy.orm import Session
# import re
# import random
# from typing import Optional
# from geopy.distance import geodesic  # pip install geopy

# from app.endpoints.triage_logic import triage_logic, TriageReqModel, _compose_response, _detect_symptoms
# from app.models.triage import TriageAudit, TriageMessage


# # Configure logging
# # ---------------------------
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)


# # --- Load ML model (PMML) ---
# try:
#     from pypmml import Model
#     triage_model = Model.load("app/models/triage_model.pmml")
#     use_ml = True
#     print("[INFO] PMML triage model loaded for triage service")
# except Exception as e:
#     print(f"[Warning] Could not load PMML model: {e}")
#     triage_model = None
#     use_ml = False

# # ------------------- Greeting Handler -------------------
# _greetings_variations = {
#     "hi": ["Hi there! How are you feeling today?", "Hey! How’s your day going?", "Hello! What’s on your mind health-wise?"],
#     "hello": ["Hello! I’m here to listen. What symptoms would you like to share?", "Hi there! How are you doing?", "Hello! How can I support you today?"],
#     "thanks": ["You're very welcome! Take care of yourself.", "Happy to help! Stay healthy.", "No problem at all. Wishing you good health!"],
#     "thank you": ["Glad I could help. How are you feeling now?", "Anytime! Take care of yourself.", "Of course! Wishing you a speedy recovery."],
#     "what's up": ["Not much, just here to support you with health advice.", "I’m here for you! What’s happening with your health?", "Just ready to listen. How are you doing?"],
#     "how are you": ["I'm doing well, thank you! How can I help with your health concerns today?", "Pretty good, thanks! How are you feeling today?", "I’m good! Hope you are too. What’s troubling you?"],
#     "how are you doing": ["I'm good, thanks! How are you feeling today?", "Doing well! How about you?", "I’m fine, thank you. How are you doing today?"],
#     "good morning": ["Good morning! How are you doing today?", "Morning! How’s your health feeling today?", "Good morning! Hope you’re doing well."],
#     "good afternoon": ["Good afternoon! What health concerns are on your mind?", "Afternoon! How are you feeling?", "Good afternoon! How’s your day going?"],
#     "good evening": ["Good evening! How are you feeling tonight?", "Evening! What health concerns would you like to share?", "Good evening! How was your day? Any symptoms bothering you?"],
#     "yo": ["Hey there! What health concerns can I help with?", "Yo! How are you feeling today?", "Hi! What’s up with your health?"],
#     "sup": ["Hi! How are you feeling today?", "Sup! Any health issues bothering you?", "Hey! Want to tell me how you’re doing?"]
# }

# def handle_greetings(user_msg: str) -> Optional[str]:
#     text = user_msg.lower().strip()
#     matched = []
#     for phrase, responses in _greetings_variations.items():
#         if re.search(rf"\b{re.escape(phrase)}\b", text):
#             matched.append((phrase, responses))
#     if not matched:
#         return None
#     phrase, responses = max(matched, key=lambda x: len(x[0]))
#     return random.choice(responses)

# # ------------------- Humanizer -------------------
# def humanize_response(raw_text: str, recommended_level: str, hospitals: list = None) -> str:
#     if not raw_text:
#         raw_text = "Please monitor your symptoms and seek care if they worsen."
#     level_prefix = {
#         "Emergency": "⚠️ Emergency: ",
#         "Urgent": "🚨 Urgent attention recommended: ",
#         "PrimaryCare": "🏥 Visit a primary care clinic: ",
#         "SelfCare": "🩹 Self-care may be sufficient: ",
#     }.get(recommended_level, "")
#     message = f"{level_prefix}{raw_text}"
#     if hospitals:
#         message += "\n\nClosest hospitals for you:\n"
#         for idx, h in enumerate(hospitals, 1):
#             message += f"{idx}. {h['name']} ({h['category']}) — {h.get('wait_time', 'N/A')}, {h.get('distance_km', '?')} km away. Note: {h.get('note', 'No additional info')}\n"
#     return message.strip()

# # ------------------- Fallback & ML -------------------
# def _fallback_triage(payload: dict) -> str:
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
#     if use_ml and triage_model:
#         try:
#             df = pd.DataFrame([payload])
#             result = triage_model.predict(df)
#             predicted = str(result.at[0, "predicted_KTAS_expert"])
#             return predicted, "ML"
#         except Exception as e:
#             print(f"[Error] ML prediction failed: {e}")
#     return _fallback_triage(payload), "Rules"

# def _force_english(text_or_obj):
#     if isinstance(text_or_obj, dict):
#         return text_or_obj.get("en") or next(iter(text_or_obj.values()), "")
#     return text_or_obj or ""

# # ------------------- Main Triage Pipeline -------------------
# def process_triage(payload: dict, db: Session):
#     # --- Log incoming payload ---
#     logger.info("=== Incoming Triage Payload ===")
#     for key, value in payload.items():
#         logger.info(f"{key}: {value}")
#     logger.info("================================")

#     user_msg_text = payload.get("symptoms", "").strip()
#     if not user_msg_text:
#         response = {"response": "No symptoms provided"}
#         logger.info(f"[Triage Response] {json.dumps(response, ensure_ascii=False)}")
#         return response

#     # --- Greeting check ---
#     greeting_reply = handle_greetings(user_msg_text)
#     if greeting_reply:
#         response = {
#             "response": greeting_reply,
#             "recommended_level": "None",
#             "score": None,
#             "reasons": [],
#             "suggested_action": None,
#             "hospital_recommendation": None,
#             "received_at": datetime.utcnow().isoformat(),
#             "meta": {"type": "greeting"}
#         }
#         logger.info(f"[Triage Response - Greeting] {json.dumps(response, ensure_ascii=False)}")
#         return response

#     # --- Rest of triage logic ---
#     detected = _detect_symptoms(user_msg_text)
#     response_text = None
#     recommended_level = score = reasons = suggested_action = hospital_reco = None

#     if detected:
#         best_match = max(detected, key=lambda x: len(x["matched_terms"]))
#         response_text = _force_english(best_match["rule"]["response"])
#         recommended_level = best_match["rule"].get("category", "PrimaryCare")
#         score = 100 if recommended_level == "Emergency" else 50
#         reasons = [f"🚨 {recommended_level}: {best_match['rule']['id']} ({', '.join(best_match['matched_terms'])})"]
#         suggested_action = _compose_response(recommended_level, score, reasons, TriageReqModel(symptoms=user_msg_text)).suggested_action
#     else:
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

#     # --- Hospital recommendations ---
#     hospital_reco = []
#     # Map triage levels for fetching hospitals
#     LEVEL_MAPPING = {
#         "red": "Emergency",
#         "yellow": "Urgent",
#         "green": "PrimaryCare",
#         "blue": "SelfCare"
#     }
#     mapped_level = LEVEL_MAPPING.get(recommended_level.lower(), recommended_level)

#     if mapped_level in ["Emergency", "Urgent", "PrimaryCare"]:
#         try:
#             r = requests.get(
#                 "http://localhost:8000/recommend/gps",
#                 timeout=3,
#                 params={
#                     "lat": payload.get("lat", 51.0447),
#                     "lng": payload.get("lng", -114.0719)
#                 },
#             )
#             r.raise_for_status()
#             data = r.json()
#             hospitals = data.get("top_recommendations", [])
#             # Round distances if present
#             for h in hospitals:
#                 if h.get("distance_km") is not None:
#                     h["distance_km"] = round(h["distance_km"], 1)
#                 else:
#                     h["distance_km"] = None
#             hospital_reco = hospitals[:3]  # top 3
#         except requests.RequestException as e:
#             logger.warning(f"[Hospital Recommendation Error] {e}")
#             hospital_reco = []

#     # --- Humanized response ---
#     human_response = humanize_response(response_text, recommended_level, hospital_reco)

#     # --- Save audit ---
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
#         meta={"human_like": True},
#     )
#     db.add(audit)
#     db.commit()
#     db.refresh(audit)

#     # --- Save messages ---
#     db.add(TriageMessage(audit_id=audit.id, direction="user", text=user_msg_text))
#     db.commit()

#     bot_payload = {
#         "response": human_response,
#         "recommended_level": recommended_level,
#         "score": score,
#         "reasons": reasons,
#         "suggested_action": suggested_action,
#         "hospital_recommendation": hospital_reco,
#         "received_at": audit.received_at.isoformat(),
#         "meta": audit.meta,
#     }

#     db.add(TriageMessage(audit_id=audit.id, direction="bot", text=json.dumps(bot_payload)))
#     db.commit()

#     # --- Log final bot response ---
#     logger.info("=== Triage Bot Response ===")
#     for key, value in bot_payload.items():
#         logger.info(f"{key}: {value}")
#     logger.info("===========================")

#     return bot_payload





# # app/services/triage_service.py
# import json
# import pandas as pd
# import requests
# from datetime import datetime
# from sqlalchemy.orm import Session
# import re
# import random
# from typing import Optional
# from app.endpoints.triage_logic import triage_logic, TriageReqModel, _compose_response


# from app.models.triage import TriageAudit, TriageMessage
# from app.endpoints.triage_logic import triage_logic, TriageReqModel, _detect_symptoms

# # --- Load ML model (PMML) ---
# try:
#     from pypmml import Model
#     triage_model = Model.load("app/models/triage_model.pmml")  # ✅ updated path
#     use_ml = True
#     print("[INFO] PMML triage model loaded for triage service")
# except Exception as e:
#     print(f"[Warning] Could not load PMML model: {e}")
#     triage_model = None
#     use_ml = False


# # ------------------- Greeting Handler -------------------
# _greetings_variations = {
#     "hi": [
#         "Hi there! How are you feeling today?",
#         "Hey! How’s your day going?",
#         "Hello! What’s on your mind health-wise?"
#     ],
#     "hello": [
#         "Hello! I’m here to listen. What symptoms would you like to share?",
#         "Hi there! How are you doing?",
#         "Hello! How can I support you today?"
#     ],
#     "thanks": [
#         "You're very welcome! Take care of yourself.",
#         "Happy to help! Stay healthy.",
#         "No problem at all. Wishing you good health!"
#     ],
#     "thank you": [
#         "Glad I could help. How are you feeling now?",
#         "Anytime! Take care of yourself.",
#         "Of course! Wishing you a speedy recovery."
#     ],
#     "what's up": [
#         "Not much, just here to support you with health advice.",
#         "I’m here for you! What’s happening with your health?",
#         "Just ready to listen. How are you doing?"
#     ],
#     "how are you": [
#         "I'm doing well, thank you for asking! How can I help with your health concerns today?",
#         "Pretty good, thanks! How are you feeling today?",
#         "I’m good! Hope you are too. What’s troubling you?"
#     ],
#     "how are you doing": [
#         "I'm good, thanks! How are you feeling today?",
#         "Doing well! How about you?",
#         "I’m fine, thank you. How are you doing today?"
#     ],
#     "good morning": [
#         "Good morning! How are you doing today?",
#         "Morning! How’s your health feeling today?",
#         "Good morning! Hope you’re doing well."
#     ],
#     "good afternoon": [
#         "Good afternoon! What health concerns are on your mind?",
#         "Afternoon! How are you feeling?",
#         "Good afternoon! How’s your day going?"
#     ],
#     "good evening": [
#         "Good evening! How are you feeling tonight?",
#         "Evening! What health concerns would you like to share?",
#         "Good evening! How was your day? Any symptoms bothering you?"
#     ],
#     "yo": [
#         "Hey there! What health concerns can I help with?",
#         "Yo! How are you feeling today?",
#         "Hi! What’s up with your health?"
#     ],
#     "sup": [
#         "Hi! How are you feeling today?",
#         "Sup! Any health issues bothering you?",
#         "Hey! Want to tell me how you’re doing?"
#     ]
# }


# def handle_greetings(user_msg: str) -> Optional[str]:
#     """
#     Return a friendly response if the user is just greeting.
#     Picks a random variation from _greetings_variations.
#     """
#     text = user_msg.lower().strip()
#     matched = []

#     for phrase, responses in _greetings_variations.items():
#         if re.search(rf"\b{re.escape(phrase)}\b", text):
#             matched.append((phrase, responses))

#     if not matched:
#         return None

#     # Pick the longest match for specificity, then random response
#     phrase, responses = max(matched, key=lambda x: len(x[0]))
#     return random.choice(responses)


# # ------------------- Humanizer -------------------
# def humanize_response(raw_text: str, recommended_level: str) -> str:
#     """
#     Convert a raw triage response into a more human-friendly message.
#     """
#     if not raw_text:
#         raw_text = "Please monitor your symptoms and seek care if they worsen."

#     # Add human-friendly context based on level
#     level_prefix = {
#         "Emergency": "⚠️ Emergency: ",
#         "Urgent": "🚨 Urgent attention recommended: ",
#         "PrimaryCare": "🏥 Visit a primary care clinic: ",
#         "SelfCare": "🩹 Self-care may be sufficient: ",
#     }.get(recommended_level, "")

#     # Clean up text and combine
#     clean_text = raw_text.replace("\n", " ").strip()
#     return f"{level_prefix}{clean_text}"


# # ------------------- Fallback Rules -------------------
# def _fallback_triage(payload: dict) -> str:
#     """Very simple backup triage rules."""
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
#     """Try ML first, fallback to rules."""
#     if use_ml and triage_model:
#         try:
#             df = pd.DataFrame([payload])
#             result = triage_model.predict(df)
#             predicted = str(result.at[0, "predicted_KTAS_expert"])
#             return predicted, "ML"
#         except Exception as e:
#             print(f"[Error] ML prediction failed: {e}")
#     return _fallback_triage(payload), "Rules"


# def _force_english(text_or_obj):
#     """Ensure we get an English string."""
#     if isinstance(text_or_obj, dict):
#         return text_or_obj.get("en") or next(iter(text_or_obj.values()), "")
#     return text_or_obj or ""


# # ------------------- Main Triage Pipeline -------------------
# def process_triage(payload: dict, db: Session):
#     """
#     Shared triage pipeline for REST + WebSocket.
#     Handles greetings → ML → rules fallback, humanizer, hospital reco, audit logging.
#     """
#     user_msg_text = payload.get("symptoms", "").strip()
#     if not user_msg_text:
#         return {"response": "No symptoms provided"}

#     # --- Greeting handler ---
#     greeting_reply = handle_greetings(user_msg_text)
#     if greeting_reply:
#         return {
#             "response": greeting_reply,
#             "recommended_level": "None",
#             "score": None,
#             "reasons": [],
#             "suggested_action": None,
#             "hospital_recommendation": None,
#             "received_at": datetime.utcnow().isoformat(),
#             "meta": {"type": "greeting"}
#         }

#     detected = _detect_symptoms(user_msg_text)
#     response_text = None
#     recommended_level = score = reasons = suggested_action = hospital_reco = None

#     triage_category_map = {
#         # Map your rule IDs to triage levels
#         "chest_pain_rule_id": "Emergency",
#         "shortness_of_breath": "Emergency",
#         "high_fever": "Urgent",
#         # add more mappings as needed
#     }

#     if detected:
#         # Rule-based NLP match (safety-net rules)
#         best_match = max(detected, key=lambda x: len(x["matched_terms"]))
#         response_text = _force_english(best_match["rule"]["response"])
#         rule_id = best_match["rule"]["id"]
#         recommended_level = triage_category_map.get(rule_id, "PrimaryCare")
#         score = 100 if recommended_level == "Emergency" else 50
#         reasons = [f"🚨 {recommended_level}: {rule_id} ({', '.join(best_match['matched_terms'])})"]
#         suggested_action = _compose_response(recommended_level, score, reasons, TriageReqModel(symptoms=user_msg_text)).suggested_action
#         meta_flag = {"human_like": True, "matched_rule": rule_id}

#         # --- Hospital recommendation for rules ---
#         if recommended_level in ["Emergency", "Urgent", "PrimaryCare"]:
#             try:
#                 r = requests.get(
#                     "http://localhost:8000/recommend/gps",
#                     timeout=2,
#                     params={
#                         "lat": payload.get("lat", 51.0447),   # fallback Calgary downtown
#                         "lng": payload.get("lng", -114.0719)
#                     },
#                 )
#                 if r.status_code == 200:
#                     hospital_reco = r.json()
#             except Exception:
#                 hospital_reco = None

#     else:
#         # ML or rules fallback
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

#         # --- Hospital recommendation already exists in ML branch ---
#         if recommended_level in ["Emergency", "Urgent", "PrimaryCare"]:
#             try:
#                 r = requests.get(
#                     "http://localhost:8000/recommend/gps",
#                     timeout=2,
#                     params={
#                         "lat": payload.get("lat", 51.0447),
#                         "lng": payload.get("lng", -114.0719)
#                     },
#                 )
#                 if r.status_code == 200:
#                     hospital_reco = r.json()
#             except Exception:
#                 hospital_reco = None

#     # ------------------- Humanizer -------------------
#     human_response = humanize_response(response_text, recommended_level)

#     # ------------------- Save audit -------------------
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

#     # Save messages
#     user_msg = TriageMessage(audit_id=audit.id, direction="user", text=user_msg_text)
#     db.add(user_msg)
#     db.commit()

#     bot_payload = {
#         "response": human_response,
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

