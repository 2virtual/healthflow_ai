# app/models/triage_models.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

class TriageReqModel(BaseModel):
    symptoms: str
    age: Optional[int] = None
    known_conditions: Optional[List[str]] = None

class TriageResult(BaseModel):
    recommended_level: str
    score: int
    reasons: List[str]
    suggested_action: str
    hospital_recommendation: Optional[Dict[str, Any]] = None
    received_at: datetime = datetime.now(timezone.utc)
    meta: Optional[Dict[str, Any]] = None
