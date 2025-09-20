from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

# Example Pydantic model for appointments
class Appointment(BaseModel):
    patient_name: str
    hospital: str
    appointment_time: datetime

# In-memory storage (replace with DB later)
appointments = []

@router.post("/upload-appointments")
async def upload_appointments(appointment: Appointment):
    """
    Upload a single appointment.
    """
    appointments.append(appointment.dict())
    return {"message": "Appointment uploaded successfully", "appointment": appointment.dict()}

@router.get("/appointments")
async def list_appointments():
    """
    Get all uploaded appointments.
    """
    return appointments








# # app/endpoints/upload_appointments.py
# from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
# from sqlalchemy.orm import Session
# import csv
# from io import StringIO

# from app.database import get_db
# from app import models

# router = APIRouter()

# @router.post("/upload-appointments")
# async def upload_appointments(file: UploadFile = File(...), db: Session = Depends(get_db)):
#     if not file.filename.endswith(".csv"):
#         raise HTTPException(status_code=400, detail="Please upload a CSV file.")

#     try:
#         # Decode uploaded CSV
#         contents = await file.read()
#         decoded = contents.decode("utf-8")
#         reader = csv.DictReader(StringIO(decoded))

#         required_cols = {"facility_name", "patient_id", "modality", "scheduled_time", "status"}
#         if not required_cols.issubset(reader.fieldnames):
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"CSV must contain columns: {required_cols}"
#             )

#         added_count = 0
#         for row in reader:
#             # --- Ensure Facility exists ---
#             facility = db.query(models.Facility).filter_by(name=row["facility_name"]).first()
#             if not facility:
#                 facility = models.Facility(
#                     name=row["facility_name"],
#                     region=row.get("region", "Unknown"),
#                     modality=row.get("modality", None),
#                 )
#                 db.add(facility)
#                 db.commit()
#                 db.refresh(facility)

#             # --- Insert Appointment ---
#             appointment = models.Appointment(
#                 facility_id=facility.id,
#                 patient_id=row["patient_id"],
#                 modality=row["modality"],
#                 scheduled_time=row["scheduled_time"],  # Must be ISO datetime string in CSV
#                 status=row["status"],
#                 urgency=row.get("urgency", None),
#                 referrer=row.get("referrer", None),
#             )
#             db.add(appointment)
#             added_count += 1

#         db.commit()
#         return {"message": f"Uploaded {added_count} appointments successfully."}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
