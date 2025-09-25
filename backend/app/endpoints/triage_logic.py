import json
import re
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timezone

from app.models.triage_models import TriageReqModel, TriageResult  # import Pydantic models

# For NLP model
import joblib
from scipy.sparse import hstack
import os

# -------------------------------
# Load NLP Model (Symptom Text Classifier)
# -------------------------------
NLP_MODEL_PATH = Path(__file__).parent.parent / "models" / "triage_nlp_model.joblib"
nlp_model_data = None

try:
    if NLP_MODEL_PATH.exists():
        nlp_model_data = joblib.load(NLP_MODEL_PATH)
        print(f"✅ Loaded NLP triage model from {NLP_MODEL_PATH}")
    else:
        print(f"⚠️ NLP model not found at {NLP_MODEL_PATH}")
except Exception as e:
    print(f"❌ Failed to load NLP model: {e}")

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
# NLP Helper Functions
# -------------------------------
def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)  # Keep letters, numbers, spaces
    text = re.sub(r'\s+', ' ', text)             # Normalize whitespace
    return text.strip()

def predict_from_text(symptoms_text: str, age: int, sex: int = 1) -> str:
    """Predict triage level from symptom text using NLP model"""
    if not nlp_model_data:  # ✅ Fixed: use the actual variable that holds tfidf + model
        return None
    try:
        tfidf = nlp_model_data['tfidf']
        model = nlp_model_data['model']
        
        clean = clean_text(symptoms_text)
        if not clean:
            return None
            
        X_tfidf = tfidf.transform([clean])
        X_meta = [[age, sex]]
        X_full = hstack([X_tfidf, X_meta])
        
        pred = model.predict(X_full)[0]
        level_map = {
            1: "Emergency",
            2: "Emergency",
            3: "Urgent",
            4: "PrimaryCare",
            5: "Pharmacy"
        }
        return level_map.get(pred, "PrimaryCare")
    except Exception as e:
        print(f"⚠️ NLP prediction error: {e}")
        return None

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
# Hybrid Logic (NLP → Rules)
# -------------------------------
def triage_logic(req: TriageReqModel) -> TriageResult:
    # ➤ STEP 1: Try NLP model if symptoms provided
    if nlp_model_data and req.symptoms:
        predicted_level = predict_from_text(
            req.symptoms,
            req.age or 45,  # fallback age
            1  # default sex=1 if not provided
        )
        if predicted_level:
            # Scoring based on level
            score_map = {
                "Emergency": 100,
                "Urgent": 90,
                "PrimaryCare": 80,
                "Pharmacy": 60,
                "SelfCare": 20   # ← Keep SelfCare low
            }
            score = score_map.get(predicted_level, 80)

            # Boost score for high-risk factors
            if req.age and req.age >= 65:
                score = min(score + 10, 100)
            if req.known_conditions:
                score = min(score + 10, 100)

            reasons = [f"NLP model prediction based on: '{req.symptoms}'"]
            if req.age and req.age >= 65:
                reasons.append("Age ≥ 65 increases risk")
            if req.known_conditions:
                reasons.append(f"Known conditions: {', '.join(req.known_conditions)} increase risk")
                

            # ✅ Use _compose_response to generate valid suggested_action string
            composed = _compose_response(predicted_level, score, reasons, req)
            return TriageResult(
                recommended_level=predicted_level,
                score=score,
                reasons=reasons,
                suggested_action=composed.suggested_action,
                hospital_recommendation=None,
                meta={
                    "original_symptoms": req.symptoms,
                    "age": req.age,
                    "known_conditions": req.known_conditions or [],
                    "model_used": "NLP"
                }
            )

    # ➤ STEP 2: Final fallback to rule-based engine
    return _triage_logic_fallback(req)