import json
import re
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timezone

from app.models.triage_models import TriageReqModel, TriageResult  # import Pydantic models

# For PMML model
try:
    from pypmml import Model
except ImportError:
    Model = None

# -------------------------------
# Load ML model (PMML)
# -------------------------------
ML_MODEL_PATH = Path(__file__).parent / "data" / "triage_model.pmml"
ml_model = None
if Model and ML_MODEL_PATH.exists():
    try:
        ml_model = Model.load(str(ML_MODEL_PATH))
        print(f"✅ Loaded ML model from {ML_MODEL_PATH}")
    except Exception as e:
        print(f"❌ Failed to load ML model: {e}")
else:
    print("⚠️ No ML model available, fallback to rules only")

# -------------------------------
# Load symptom rules from JSON
# File: app/endpoints/data/symptoms.json
# -------------------------------
DATA_DIR = Path(__file__).parent / "data"
SYMPTOMS_JSON_PATH = DATA_DIR / "symptoms.json"

def load_symptom_rules() -> List[Dict[str, Any]]:
    if not SYMPTOMS_JSON_PATH.exists():
        raise RuntimeError(
            f"❌ Critical: Symptoms file not found at {SYMPTOMS_JSON_PATH}.\n"
            "Did you include 'app/endpoints/data/symptoms.json' in your Docker build?\n"
            "This is required for triage logic to function."
        )
    with open(SYMPTOMS_JSON_PATH, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            print(f"✅ Successfully loaded {len(data)} symptom rules")
            return data
        except json.JSONDecodeError as e:
            raise RuntimeError(f"❌ Invalid JSON in {SYMPTOMS_JSON_PATH}: {e}")

SYMPTOM_RULES = load_symptom_rules()

WEIGHTS = {"red": 50, "urgent": 30, "primary": 10, "pharmacy": 5}

# -------------------------------
# Helper Functions
# -------------------------------
def _is_negated(term: str, text: str, window=15) -> bool:
    negations = r"\b(not|no|without|denies|denying|negating|free of)\b"
    start = max(0, text.lower().find(term) - window)
    end = start + len(term) + window
    context = text[start:end]
    return bool(re.search(negations, context, re.IGNORECASE))

def _detect_symptoms(text: str) -> List[Dict[str, Any]]:
    if not text.strip():
        return []
    found = []
    text_lower = text.lower()
    for rule in SYMPTOM_RULES:
        matched_terms = []
        for kw in rule["keywords"]:
            if kw in text_lower and not _is_negated(kw, text):
                matched_terms.append(kw)
        for pattern in rule.get("patterns", []):
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                term = m if isinstance(m, str) else text[
                    re.search(pattern, text, re.IGNORECASE).start():re.search(pattern, text, re.IGNORECASE).end()
                ]
                if not _is_negated(term, text):
                    matched_terms.append(term)
        if matched_terms:
            found.append({
                "rule": rule,
                "matched_terms": list(set(matched_terms))
            })
    return found

# -------------------------------
# Rule-based fallback
# -------------------------------
def _compose_response(level: str, score: int, reasons: List[str], req: TriageReqModel) -> TriageResult:
    actions = {
        "Emergency": "Call emergency services or go to the nearest Emergency Department immediately.",
        "Urgent": "Seek urgent care within a few hours. If symptoms worsen, go to the ER.",
        "PrimaryCare": "Book with your primary care provider or virtual care within 24–72 hours.",
        "Pharmacy": "Visit a pharmacy for advice or OTC remedies.",
        "SelfCare": "Self-care at home; seek care if condition gets worse."
    }
    return TriageResult(
        recommended_level=level,
        score=min(score, 100),
        reasons=reasons,
        suggested_action=actions.get(level, actions["PrimaryCare"]),
        hospital_recommendation=None,
        meta={
            "original_symptoms": req.symptoms,
            "age": req.age,
            "known_conditions": req.known_conditions or [],
            "detected_count": len(reasons),
            "model_used": "Rules"
        }
    )

def _triage_logic_fallback(req: TriageReqModel) -> TriageResult:
    text = req.symptoms or ""
    reasons = []
    score = 0
    detected = _detect_symptoms(text)
    if not detected:
        reasons.append("No recognized symptoms detected")
        return _compose_response("SelfCare", 20, reasons, req)
    categories = {}
    for item in detected:
        cat = item["rule"]["category"]
        categories.setdefault(cat, []).append(item)
    if categories.get("red"):
        score += WEIGHTS["red"] + 20
        reasons += [f"🚨 Emergency: {item['rule']['id']} ({', '.join(item['matched_terms'])})"
                    for item in categories["red"]]
        level = "Emergency"
    elif categories.get("urgent"):
        score += WEIGHTS["urgent"] * len(categories["urgent"])
        reasons += [f"⚠️ Urgent: {item['rule']['id']}" for item in categories["urgent"]]
        if req.age and req.age >= 65:
            reasons.append("Age ≥ 65 increases urgency")
            score += 10
        if req.known_conditions:
            reasons.append(f"Known condition(s): {', '.join(req.known_conditions)} increase risk")
            score += 10
        level = "Urgent"
    elif categories.get("primary"):
        score += WEIGHTS["primary"] * len(categories["primary"])
        reasons += [f"🩺 Primary-care: {item['rule']['id']}" for item in categories["primary"]]
        level = "PrimaryCare"
    elif categories.get("pharmacy"):
        score += WEIGHTS["pharmacy"] * len(categories["pharmacy"])
        reasons += [f"💊 Pharmacy: {item['rule']['id']}" for item in categories["pharmacy"]]
        level = "Pharmacy"
    else:
        reasons.append("Input unclear; defaulting to primary care")
        level = "PrimaryCare"
        score += 20
    return _compose_response(level, score, reasons, req)

# -------------------------------
# Hybrid Logic (ML → fallback)
# -------------------------------
def triage_logic(req: TriageReqModel) -> TriageResult:
    if ml_model is None:
        return _triage_logic_fallback(req)
    try:
        # Prepare features for ML model (must match R column order!)
        features = {
            "Age": req.age or 45,
            "Sex": 1,
            "SBP": 120,
            "DBP": 80,
            "HR": 85,
            "RR": 18,
            "BT": 37.0,
            "Saturation": 98,
            "Pain": "1",
            "Mental": "1",
        }
        input_data = {
            "Age": features["Age"],
            "Sex": features["Sex"],
            "SBP": features["SBP"],
            "DBP": features["DBP"],
            "HR": features["HR"],
            "RR": features["RR"],
            "BT": features["BT"],
            "Saturation": features["Saturation"],
            "Pain": features["Pain"],
            "Mental": features["Mental"],
        }
        pred = ml_model.predict(input_data)
        pred_level = str(pred.get("predicted_KTAS") or pred.get("prediction") or "3")
        level_map = {
            "1": "Emergency",
            "2": "Emergency",
            "3": "Urgent",
            "4": "PrimaryCare",
            "5": "Pharmacy",
        }
        recommended_level = level_map.get(pred_level, "PrimaryCare")
        score = 100 - int(pred_level) * 15
        reasons = [f"AI predicted KTAS Level {pred_level}"]
        if req.age and req.age >= 65:
            reasons.append("Age ≥ 65 increases risk")
            score += 10
        if req.known_conditions:
            reasons.append(f"Known conditions: {', '.join(req.known_conditions)} increase risk")
            score += 10
        return TriageResult(
            recommended_level=recommended_level,
            score=min(score, 100),
            reasons=reasons,
            suggested_action=None,
            hospital_recommendation=None,
            meta={
                "original_symptoms": req.symptoms,
                "age": req.age,
                "known_conditions": req.known_conditions or [],
                "predicted_ktas": pred_level,
                "model_used": "ML"
            }
        )
    except Exception as e:
        print(f"⚠️ ML model failed, fallback to rules: {e}")
        return _triage_logic_fallback(req)







# # app/endpoints/triage_logic.py
# import json
# import re
# from pathlib import Path
# from typing import List, Dict, Any
# from datetime import datetime, timezone

# from app.models.triage_models import TriageReqModel, TriageResult  # import Pydantic models

# # -------------------------------
# # Load symptom rules from JSON
# # File: app/endpoints/data/symptoms.json
# # -------------------------------
# DATA_DIR = Path(__file__).parent / "data"
# SYMPTOMS_JSON_PATH = DATA_DIR / "symptoms.json"

# def load_symptom_rules() -> List[Dict[str, Any]]:
#     """
#     Load symptom rules from JSON file.
#     Raises RuntimeError if file is missing or invalid.
#     """
#     if not SYMPTOMS_JSON_PATH.exists():
#         raise RuntimeError(
#             f"❌ Critical: Symptoms file not found at {SYMPTOMS_JSON_PATH}.\n"
#             "Did you include 'app/endpoints/data/symptoms.json' in your Docker build?\n"
#             "This is required for triage logic to function."
#         )

#     with open(SYMPTOMS_JSON_PATH, 'r', encoding='utf-8') as f:
#         try:
#             data = json.load(f)
#             print(f"✅ Successfully loaded {len(data)} symptom rules from {SYMPTOMS_JSON_PATH}")
#             return data
#         except json.JSONDecodeError as e:
#             raise RuntimeError(f"❌ Invalid JSON in {SYMPTOMS_JSON_PATH}: {e}")

# # Load rules
# SYMPTOM_RULES = load_symptom_rules()

# # Scoring weights
# WEIGHTS = {"red": 50, "urgent": 30, "primary": 10, "pharmacy": 5}

# # -------------------------------
# # Helper Functions
# # -------------------------------
# def _is_negated(term: str, text: str, window=15) -> bool:
#     """
#     Check if a symptom is negated (e.g., "no chest pain")
#     """
#     negations = r"\b(not|no|without|denies|denying|negating|free of)\b"
#     start = max(0, text.lower().find(term) - window)
#     end = start + len(term) + window
#     context = text[start:end]
#     return bool(re.search(negations, context, re.IGNORECASE))


# def _detect_symptoms(text: str) -> List[Dict[str, Any]]:
#     """
#     Detect all matching symptoms using keywords, patterns, and negation checks.
#     Returns list of matched rules with metadata.
#     """
#     if not text.strip():
#         return []

#     found = []
#     text_lower = text.lower()

#     for rule in SYMPTOM_RULES:
#         matched_terms = []

#         # 1. Keyword match
#         for kw in rule["keywords"]:
#             if kw in text_lower and not _is_negated(kw, text):
#                 matched_terms.append(kw)

#         # 2. Regex pattern match
#         for pattern in rule.get("patterns", []):
#             matches = re.findall(pattern, text, re.IGNORECASE)
#             for m in matches:
#                 term = m if isinstance(m, str) else text[
#                     re.search(pattern, text, re.IGNORECASE).start():re.search(pattern, text, re.IGNORECASE).end()
#                 ]
#                 if not _is_negated(term, text):
#                     matched_terms.append(term)

#         if matched_terms:
#             found.append({
#                 "rule": rule,
#                 "matched_terms": list(set(matched_terms))
#             })

#     return found

# # -------------------------------
# # Main Triage Logic
# # -------------------------------
# def _compose_response(level: str, score: int, reasons: List[str], req: TriageReqModel) -> TriageResult:
#     actions = {
#         "Emergency": "Call emergency services or go to the nearest Emergency Department immediately.",
#         "Urgent": "Seek urgent care within a few hours. If symptoms worsen, go to the ER.",
#         "PrimaryCare": "Book with your primary care provider or virtual care within 24–72 hours.",
#         "Pharmacy": "Visit a pharmacy for advice or OTC remedies.",
#         "SelfCare": "Self-care at home; seek care if condition gets worse."
#     }

#     return TriageResult(
#         recommended_level=level,
#         score=min(score, 100),
#         reasons=reasons,
#         suggested_action=actions.get(level, actions["PrimaryCare"]),
#         hospital_recommendation=None,
#         meta={
#             "original_symptoms": req.symptoms,
#             "age": req.age,
#             "known_conditions": req.known_conditions or [],
#             "detected_count": len(reasons)
#         }
#     )


# def triage_logic(req: TriageReqModel) -> TriageResult:
#     text = req.symptoms or ""
#     reasons = []
#     score = 0
#     detected = _detect_symptoms(text)

#     if not detected:
#         reasons.append("No recognized symptoms detected")
#         return _compose_response("SelfCare", 20, reasons, req)

#     # Group by category
#     categories = {}
#     for item in detected:
#         cat = item["rule"]["category"]
#         categories.setdefault(cat, []).append(item)

#     # Determine highest priority level
#     if categories.get("red"):
#         score += WEIGHTS["red"] + 20
#         reasons += [f"🚨 Emergency: {item['rule']['id']} ({', '.join(item['matched_terms'])})"
#                     for item in categories["red"]]
#         level = "Emergency"

#     elif categories.get("urgent"):
#         score += WEIGHTS["urgent"] * len(categories["urgent"])
#         reasons += [f"⚠️ Urgent: {item['rule']['id']}" for item in categories["urgent"]]
#         if req.age and req.age >= 65:
#             reasons.append("Age ≥ 65 increases urgency")
#             score += 10
#         if req.known_conditions:
#             reasons.append(f"Known condition(s): {', '.join(req.known_conditions)} increase risk")
#             score += 10
#         level = "Urgent"

#     elif categories.get("primary"):
#         score += WEIGHTS["primary"] * len(categories["primary"])
#         reasons += [f"🩺 Primary-care: {item['rule']['id']}" for item in categories["primary"]]
#         level = "PrimaryCare"

#     elif categories.get("pharmacy"):
#         score += WEIGHTS["pharmacy"] * len(categories["pharmacy"])
#         reasons += [f"💊 Pharmacy: {item['rule']['id']}" for item in categories["pharmacy"]]
#         level = "Pharmacy"

#     else:
#         reasons.append("Input unclear; defaulting to primary care")
#         level = "PrimaryCare"
#         score += 20

#     return _compose_response(level, score, reasons, req)



