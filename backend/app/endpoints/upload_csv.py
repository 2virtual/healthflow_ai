from fastapi import APIRouter, UploadFile, File, HTTPException
import pandas as pd

router = APIRouter()

@router.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload a CSV file and return its content as JSON.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")
    
    try:
        df = pd.read_csv(file.file)
        data = df.to_dict(orient="records")
        return {"filename": file.filename, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process CSV: {e}")







# from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
# import pandas as pd
# from sqlalchemy.orm import Session
# from app.database import get_db
# from app import models

# router = APIRouter()

# @router.post("/upload-csv")
# async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
#     df = pd.read_csv(file.file)

#     required_cols = {"hospital_name", "wait_time_minutes"}
#     if not required_cols.issubset(df.columns):
#         raise HTTPException(status_code=400, detail=f"CSV must contain columns: {required_cols}")

#     for _, row in df.iterrows():
#         entry = models.EdWaitTime(
#             hospital_name=row["hospital_name"],
#             wait_time_minutes=row["wait_time_minutes"],
#         )
#         db.add(entry)

#     db.commit()
#     return {"message": f"Uploaded {len(df)} rows successfully"}
