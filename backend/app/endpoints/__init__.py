# app/endpoints/__init__.py

# Import routers from each endpoint file
from .fetch_ed_waits import router as fetch_ed_waits
from .upload_csv import router as upload_csv
from .upload_appointments import router as upload_appointments

# Optional: expose them all in __all__ for clarity
__all__ = ["fetch_ed_waits", "upload_csv", "upload_appointments"]
