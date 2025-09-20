# app/models/triage.py
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base  # uses your existing Base

class TriageAudit(Base):
    __tablename__ = "triage_audit"
    id = Column(Integer, primary_key=True, index=True)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    symptoms = Column(Text, nullable=False)
    age = Column(Integer, nullable=True)
    known_conditions = Column(JSON, nullable=True)
    recommended_level = Column(String(50), nullable=True)
    score = Column(Integer, nullable=True)
    reasons = Column(JSON, nullable=True)
    suggested_action = Column(Text, nullable=True)
    hospital_recommendation = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True)

    # optional relationship to chat messages
    messages = relationship("TriageMessage", back_populates="audit", cascade="all, delete-orphan")

class TriageMessage(Base):
    __tablename__ = "triage_message"
    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(Integer, ForeignKey("triage_audit.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    direction = Column(String(10), nullable=False)  # "user" or "bot"
    text = Column(Text, nullable=False)
    meta = Column(JSON, nullable=True)

    audit = relationship("TriageAudit", back_populates="messages")
