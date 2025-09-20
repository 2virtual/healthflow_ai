from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base  # This comes from SQLAlchemy engine setup

class Facility(Base):
    __tablename__ = "facilities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    region = Column(String, nullable=False)
    modality = Column(String)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    appointments = relationship("Appointment", back_populates="facility")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("facilities.id", ondelete="CASCADE"))
    patient_id = Column(String)  # hashed or anonymized
    modality = Column(String, nullable=False)
    scheduled_time = Column(TIMESTAMP(timezone=True), nullable=False)
    status = Column(String, nullable=False)
    urgency = Column(String)
    referrer = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    facility = relationship("Facility", back_populates="appointments")
