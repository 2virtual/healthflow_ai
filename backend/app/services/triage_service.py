import os
import logging
import re
import random
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
import redis
import json
from geopy.distance import geodesic

from app.services.hospital_service import get_all_hospitals_from_redis
from app.endpoints.triage_logic import triage_logic
from app.models.triage import TriageAudit, TriageMessage
from app.models.triage_models import TriageReqModel

# ------------------------------- Logging -------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------- Redis -------------------------------
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = 6379
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

# ------------------------------- Default Coordinates -------------------------------
DEFAULT_COORDS = (51.089, -114.071)

# ------------------------------- Greeting -------------------------------
_greetings_variations = {
    "hi": ["Hi there! How are you feeling today?", "Hey! How’s your day going?", "Hello! What’s on your mind health-wise?"],
    "hello": ["Hello! I’m here to listen. What symptoms would you like to share?", "Hi there! How are you doing?", "Hello! How can I support you today?"],
    "thanks": ["You're very welcome! Take care of yourself.", "Happy to help! Stay healthy.", "No problem at all. Wishing you good health!"],
    "thank you": ["Glad I could help. How are you feeling now?", "Anytime! Take care of yourself.", "Of course! Wishing you a speedy recovery."],
    "what's up": ["Not much, just here to support you with health advice.", "I’m here for you! What’s happening with your health?", "Just ready to listen. How are you doing?"],
    "how are you": ["I'm doing well, thank you! How can I help with your health concerns today?", "Pretty good, thanks! How are you feeling today?", "I’m good! Hope you are too. What’s troubling you?"],
    "good morning": ["Good morning! How are you doing today?", "Morning! How’s your health feeling today?", "Good morning! Hope you’re doing well."],
    "good afternoon": ["Good afternoon! What health concerns are on your mind?", "Afternoon! How are you feeling?", "Good afternoon! How’s your day going?"],
    "good evening": ["Good evening! How are you feeling tonight?", "Evening! What health concerns would you like to share?", "Good evening! How was your day? Any symptoms bothering you?"],
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

# ------------------------------- Clinical Safety Override -------------------------------
def _apply_clinical_safety_override(symptoms: str, age: Optional[int], known_conditions: list) -> Optional[dict]:
    danger_keywords = [
        "shortness of breath", "difficulty breathing", "can't breathe", "unable to breathe",
        "chest pain", "pressure in chest", "unconscious", "fainting", "passed out",
        "seizure", "stroke", "suicidal", "homicidal", "major trauma", "bleeding uncontrollably",
        "nose bleed", "heavy bleeding", "bleeding won't stop", "dizzy from bleeding","heart attack",
          "anaphylaxis", "allergic reaction swelling throat","cardiac arrest", "myocardial infarction"
    ]
    text_lower = symptoms.lower()
    for kw in danger_keywords:
        if kw in text_lower:
            reasons = [f"🚨 SAFETY OVERRIDE: Critical symptom '{kw}' detected"]
            if age and age >= 65:
                reasons.append("❗ Age ≥ 65 — higher risk")
            if known_conditions:
                reasons.append(f"❗ Known conditions: {', '.join(known_conditions)} — higher risk")
            return {
                "recommended_level": "Emergency",
                "score": 100,
                "reasons": reasons,
                "suggested_action": "Call 911 or go to nearest Emergency Department IMMEDIATELY.",
                "meta": {"model_used": "Clinical Safety Override"}
            }
    return None

# ------------------------------- Humanize Response -------------------------------
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
            wait = h.get('wait_time', 'N/A')
            note = h.get('note', 'No additional info')
            dist = h.get('distance_km', '?')
            message += f"{idx}. {h['name']} ({h['category']}) — {wait}, {dist} km away. Note: {note}\n"
    return message.strip()



# ------------------------------- Get Hospital Recommendations -------------------------------
def _get_hospital_recommendations(level: str, lat: Optional[float], lng: Optional[float]) -> List[Dict]:
    if level not in ["Emergency", "Urgent", "PrimaryCare"]:
        return []

    patient_coords = (lat or DEFAULT_COORDS[0], lng or DEFAULT_COORDS[1])
    hospitals = get_all_hospitals_from_redis()

    # Compute distances
    for hosp in hospitals:
        if hosp.get("lat") and hosp.get("lng"):
            hosp["distance_km"] = round(geodesic(patient_coords, (hosp["lat"], hosp["lng"])).km, 1)
        else:
            hosp["distance_km"] = None

    # Filter by category
    if level == "Emergency":
        filtered = [h for h in hospitals if h.get("category") == "Emergency"]
    elif level == "Urgent":
        filtered = [h for h in hospitals if h.get("category") == "Urgent"]
    else:  # PrimaryCare
        filtered = [h for h in hospitals if h.get("category") == "PrimaryCare"]

    # Sort by distance, exclude missing coords, return top 3
    valid = [h for h in filtered if h["distance_km"] is not None]
    return sorted(valid, key=lambda x: x["distance_km"])[:3]

# ------------------------------- Main Triage Pipeline -------------------------------
async def process_triage(payload: dict, db: Session):
    logger.info("=== Incoming Triage Payload ===")
    for key, value in payload.items():
        logger.info(f"{key}: {value}")
    logger.info("================================")

    user_msg_text = payload.get("symptoms", "").strip()
    if not user_msg_text:
        return {"response": "No symptoms provided"}

    # Greeting
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
            "meta": {"type": "greeting"}
        }

    # Initialize variables
    recommended_level = None
    score = 0
    reasons = []
    suggested_action = ""
    meta = {}

    # Clinical Safety Override
    safety_override = _apply_clinical_safety_override(
        user_msg_text,
        payload.get("age"),
        payload.get("known_conditions", []),
    )
    if safety_override:
        recommended_level = safety_override["recommended_level"]
        score = safety_override["score"]
        reasons = safety_override["reasons"]
        suggested_action = safety_override["suggested_action"]
        meta = safety_override["meta"]
    else:
        # Normal triage logic
        try:
            req = TriageReqModel(
                symptoms=user_msg_text,
                age=payload.get("age"),
                known_conditions=payload.get("known_conditions") or []
            )
        except Exception as e:
            logger.error(f"❌ Input validation failed: {e}")
            return {
                "response": "Unable to process symptoms. Please try again.",
                "recommended_level": "Error",
                "score": 0,
                "reasons": ["Invalid input format"],
                "suggested_action": "Ensure symptoms are text and age is a number.",
                "hospital_recommendation": None,
                "received_at": datetime.utcnow().isoformat(),
                "meta": {"error": str(e)}
            }

        result = triage_logic(req)
        recommended_level = result.recommended_level
        score = result.score
        reasons = result.reasons
        suggested_action = result.suggested_action
        meta = result.meta

    # ✅ Unified hospital recommendation logic — works for safety override AND normal triage
        # 🔍 DIAGNOSTIC LOGS — ADD THESE TWO LINES HERE
    logger.info(f"🔍 Getting hospitals for level: {recommended_level}")
    logger.info(f"📍 Patient coords: {payload.get('lat')}, {payload.get('lng')}")
    hospital_reco = _get_hospital_recommendations(
        recommended_level,
        payload.get("lat"),
        payload.get("lng")
    )

    # Humanize response
    human_response = humanize_response(suggested_action, recommended_level, hospital_reco)

    # Save audit & messages
    audit = TriageAudit(
        received_at=datetime.utcnow(),
        symptoms=user_msg_text,
        age=payload.get("age"),
        known_conditions=payload.get("known_conditions", []),
        recommended_level=recommended_level,
        score=score,
        reasons=reasons,
        suggested_action=suggested_action,
        hospital_recommendation=json.dumps(hospital_reco),
        meta={"human_like": True, **meta},
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)

    db.add(TriageMessage(audit_id=audit.id, direction="user", text=user_msg_text))
    db.commit()
    db.add(TriageMessage(audit_id=audit.id, direction="bot", text=json.dumps({
        "response": human_response,
        "recommended_level": recommended_level,
        "score": score,
        "reasons": reasons,
        "suggested_action": suggested_action,
        "hospital_recommendation": hospital_reco,
        "received_at": audit.received_at.isoformat(),
        "meta": audit.meta,
    })))
    db.commit()

    logger.info("=== Triage Bot Response ===")
    logger.info(f"response: {human_response}")
    logger.info(f"recommended_level: {recommended_level}")
    logger.info(f"score: {score}")
    logger.info(f"reasons: {reasons}")
    logger.info(f"suggested_action: {suggested_action}")
    logger.info(f"hospital_recommendation: {hospital_reco}")
    logger.info("===========================")

    return {
        "response": human_response,
        "recommended_level": recommended_level,
        "score": score,
        "reasons": reasons,
        "suggested_action": suggested_action,
        "hospital_recommendation": hospital_reco,
        "received_at": audit.received_at.isoformat(),
        "meta": audit.meta,
    }






# import os
# import logging
# import re
# import random
# from datetime import datetime
# from sqlalchemy.orm import Session
# from typing import Optional, List, Dict
# import redis
# import json
# from geopy.distance import geodesic

# from app.services.hospital_service import get_all_hospitals_from_redis
# from app.endpoints.triage_logic import triage_logic
# from app.models.triage import TriageAudit, TriageMessage

# # ------------------------------- Logging -------------------------------
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # ------------------------------- Redis -------------------------------
# REDIS_HOST = os.getenv("REDIS_HOST", "redis")
# REDIS_PORT = 6379
# redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

# # ------------------------------- Default Coordinates -------------------------------
# # Fallback coordinates near Alberta Children's Hospital
# DEFAULT_COORDS = (51.089, -114.071)

# # ------------------------------- Greeting -------------------------------
# _greetings_variations = {
#     "hi": ["Hi there! How are you feeling today?", "Hey! How’s your day going?", "Hello! What’s on your mind health-wise?"],
#     "hello": ["Hello! I’m here to listen. What symptoms would you like to share?", "Hi there! How are you doing?", "Hello! How can I support you today?"],
#     "thanks": ["You're very welcome! Take care of yourself.", "Happy to help! Stay healthy.", "No problem at all. Wishing you good health!"],
#     "thank you": ["Glad I could help. How are you feeling now?", "Anytime! Take care of yourself.", "Of course! Wishing you a speedy recovery."],
#     "what's up": ["Not much, just here to support you with health advice.", "I’m here for you! What’s happening with your health?", "Just ready to listen. How are you doing?"],
#     "how are you": ["I'm doing well, thank you! How can I help with your health concerns today?", "Pretty good, thanks! How are you feeling today?", "I’m good! Hope you are too. What’s troubling you?"],
#     "good morning": ["Good morning! How are you doing today?", "Morning! How’s your health feeling today?", "Good morning! Hope you’re doing well."],
#     "good afternoon": ["Good afternoon! What health concerns are on your mind?", "Afternoon! How are you feeling?", "Good afternoon! How’s your day going?"],
#     "good evening": ["Good evening! How are you feeling tonight?", "Evening! What health concerns would you like to share?", "Good evening! How was your day? Any symptoms bothering you?"],
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

# # ------------------------------- Clinical Safety Override -------------------------------
# def _apply_clinical_safety_override(symptoms: str, age: Optional[int], known_conditions: list) -> Optional[dict]:
#     danger_keywords = [
#         "shortness of breath", "difficulty breathing", "can't breathe", "unable to breathe",
#         "chest pain", "pressure in chest", "unconscious", "fainting", "passed out",
#         "seizure", "stroke", "suicidal", "homicidal", "major trauma", "bleeding uncontrollably",
#         "nose bleed", "heavy bleeding", "bleeding won't stop", "dizzy from bleeding"
#     ]
#     text_lower = symptoms.lower()
#     for kw in danger_keywords:
#         if kw in text_lower:
#             reasons = [f"🚨 SAFETY OVERRIDE: Critical symptom '{kw}' detected"]
#             if age and age >= 65:
#                 reasons.append("❗ Age ≥ 65 — higher risk")
#             if known_conditions:
#                 reasons.append(f"❗ Known conditions: {', '.join(known_conditions)} — higher risk")
#             return {
#                 "recommended_level": "Emergency",
#                 "score": 100,
#                 "reasons": reasons,
#                 "suggested_action": "CALLTYPE 911 or go to nearest Emergency Department IMMEDIATELY.",
#                 "meta": {"model_used": "Clinical Safety Override"}
#             }
#     return None

# # ------------------------------- Humanize Response -------------------------------
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
#             message += (
#                 f"{idx}. {h['name']} ({h['category']}) — {h.get('wait_time', 'N/A')}, "
#                 f"{h.get('distance_km', '?')} km away. Note: {h.get('note', 'No additional info')}\n"
#             )
#     return message.strip()

# # ------------------------------- Main Triage Pipeline -------------------------------
# async def process_triage(payload: dict, db: Session):
#     logger.info("=== Incoming Triage Payload ===")
#     for key, value in payload.items():
#         logger.info(f"{key}: {value}")
#     logger.info("================================")

#     user_msg_text = payload.get("symptoms", "").strip()
#     if not user_msg_text:
#         return {"response": "No symptoms provided"}

#     # Greeting
#     greeting_reply = handle_greetings(user_msg_text)
#     if greeting_reply:
#         return {"response": greeting_reply, "recommended_level": "None", "score": None, "reasons": [], "suggested_action": None, "hospital_recommendation": None, "received_at": datetime.utcnow().isoformat(), "meta": {"type": "greeting"}}

#     # Clinical Safety Override
#     safety_override = _apply_clinical_safety_override(
#         user_msg_text,
#         payload.get("age"),
#         payload.get("known_conditions", []),
#     )
#     if safety_override:
#         response_text = safety_override["suggested_action"]
#         recommended_level = safety_override["recommended_level"]
#         score = safety_override["score"]
#         reasons = safety_override["reasons"]
#         suggested_action = safety_override["suggested_action"]
#         meta = safety_override["meta"]
#     else:
#         # NLP Triage
#         req_model = triage_logic({
#             "symptoms": user_msg_text,
#             "age": payload.get("age"),
#             "known_conditions": payload.get("known_conditions", []),
#         })
#         response_text = req_model["suggested_action"]
#         recommended_level = req_model["recommended_level"]
#         score = req_model["score"]
#         reasons = req_model["reasons"]
#         suggested_action = req_model["suggested_action"]
#         meta = req_model.get("meta", {})

#     # ---------------- Hospital Recommendations ----------------
#     hospital_reco = []
#     LEVEL_MAPPING = {"red": "Emergency", "yellow": "Urgent", "green": "PrimaryCare", "blue": "SelfCare"}
#     mapped_level = LEVEL_MAPPING.get(recommended_level.lower(), recommended_level)

#     if mapped_level in ["Emergency", "Urgent", "PrimaryCare"]:
#         patient_coords = (
#             payload.get("lat", DEFAULT_COORDS[0]),
#             payload.get("lng", DEFAULT_COORDS[1])
#         )
#         hospitals = get_all_hospitals_from_redis()

#         for hosp in hospitals:
#             hosp["distance_km"] = (
#                 round(geodesic(patient_coords, (hosp.get("lat"), hosp.get("lng"))).km, 1)
#                 if hosp.get("lat") and hosp.get("lng")
#                 else None
#             )

#         # Filter by category
#         if mapped_level == "Emergency":
#             hospitals = [h for h in hospitals if h.get("category") == "Emergency"]
#         elif mapped_level == "Urgent":
#             hospitals = [h for h in hospitals if h.get("category") == "Urgent"]
#         elif mapped_level == "PrimaryCare":
#             hospitals = [h for h in hospitals if h.get("category") == "PrimaryCare"]

#         # Sort by distance and take top 3
#         hospital_reco = sorted(
#             [h for h in hospitals if h["distance_km"] is not None],
#             key=lambda x: x["distance_km"]
#         )[:3]

#     # Humanize response
#     human_response = humanize_response(response_text, recommended_level, hospital_reco)

#     # Save audit & messages
#     audit = TriageAudit(
#         received_at=datetime.utcnow(),
#         symptoms=user_msg_text,
#         age=payload.get("age"),
#         known_conditions=payload.get("known_conditions", []),
#         recommended_level=recommended_level,
#         score=score,
#         reasons=reasons,
#         suggested_action=suggested_action,
#         hospital_recommendation=json.dumps(hospital_reco),
#         meta={"human_like": True, **meta},
#     )
#     db.add(audit)
#     db.commit()
#     db.refresh(audit)

#     db.add(TriageMessage(audit_id=audit.id, direction="user", text=user_msg_text))
#     db.commit()
#     db.add(TriageMessage(audit_id=audit.id, direction="bot", text=json.dumps({
#         "response": human_response,
#         "recommended_level": recommended_level,
#         "score": score,
#         "reasons": reasons,
#         "suggested_action": suggested_action,
#         "hospital_recommendation": hospital_reco,
#         "received_at": audit.received_at.isoformat(),
#         "meta": audit.meta,
#     })))
#     db.commit()

#     logger.info("=== Triage Bot Response ===")
#     logger.info(f"response: {human_response}")
#     logger.info(f"recommended_level: {recommended_level}")
#     logger.info(f"score: {score}")
#     logger.info(f"reasons: {reasons}")
#     logger.info(f"suggested_action: {suggested_action}")
#     logger.info(f"hospital_recommendation: {hospital_reco}")
#     logger.info("===========================")

#     return {
#         "response": human_response,
#         "recommended_level": recommended_level,
#         "score": score,
#         "reasons": reasons,
#         "suggested_action": suggested_action,
#         "hospital_recommendation": hospital_reco,
#         "received_at": audit.received_at.isoformat(),
#         "meta": audit.meta,
#     }
