# tests/test_triage_service.py
import pytest
from app.services.triage_service import process_triage, use_ml

def test_fallback_rules_path(db_session):
    """Should use rules fallback when ML disabled or model missing."""
    payload = {
        "symptoms": "mild cough and headache",
        "age": 25,
        "SBP": 125,
        "HR": 80,
        "RR": 16,
        "BT": 37.2,
    }

    result = process_triage(payload, db_session)

    assert "response" in result
    assert result["recommended_level"] in ["Emergency", "Urgent", "PrimaryCare", "SelfCare"]
    assert result["meta"]["source"] == "Rules"

def test_ml_or_rules_path(db_session):
    """If ML is available, should return ML as source."""
    payload = {
        "symptoms": "chest pain and shortness of breath",
        "age": 65,
        "SBP": 85,
        "HR": 130,
        "RR": 25,
        "BT": 39.5,
    }

    result = process_triage(payload, db_session)

    assert "response" in result
    assert result["recommended_level"] is not None
    if use_ml:
        assert result["meta"]["source"] == "ML"
    else:
        assert result["meta"]["source"] == "Rules"

def test_audit_and_messages_persist(db_session):
    """Verify audit and messages are stored in DB."""
    payload = {
        "symptoms": "severe headache and dizziness",
        "age": 40,
        "SBP": 100,
        "HR": 95,
        "RR": 22,
        "BT": 38.0,
    }

    result = process_triage(payload, db_session)

    # Check DB contents
    from app.models.triage import TriageAudit, TriageMessage

    audits = db_session.query(TriageAudit).all()
    messages = db_session.query(TriageMessage).all()

    assert len(audits) == 1
    assert audits[0].symptoms == "severe headache and dizziness"
    assert len(messages) == 2  # user + bot
    assert any("response" in m.text for m in messages if m.direction == "bot")
