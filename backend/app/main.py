# app/main.py
from fastapi import FastAPI
from app.database import Base, engine
from app.endpoints.fetch_ed_waits import router as fetch_ed_waits_router
from app.endpoints.upload_csv import router as upload_csv_router
from app.endpoints.upload_appointments import router as upload_appointments_router
from app.endpoints.recommend import router as recommend_router
from app.endpoints.triage import router as triage_router
from app.endpoints import ws_wait_times, triage_ws
from app.startup_tasks import geocode_hospitals_on_startup  # ✅ import only the async geocoding
import asyncio

app = FastAPI(title="HealthFlow API", version="1.0.0")


@app.on_event("startup")
async def startup_event():
    # Create database tables
    Base.metadata.create_all(bind=engine)

    # Safely launch async hospital geocoding
    try:
        asyncio.create_task(geocode_hospitals_on_startup())
        print("✅ Hospital geocoding task started")
    except Exception as e:
        print("⚠️ Failed to start hospital geocoding:", e)

    # Launch WebSocket broadcasting loop safely
    try:
        asyncio.create_task(ws_wait_times.broadcast_data())
        print("✅ WebSocket broadcasting task started")
    except Exception as e:
        print("⚠️ Failed to start WebSocket broadcaster:", e)


# Include HTTP routers
app.include_router(fetch_ed_waits_router)
app.include_router(upload_csv_router)
app.include_router(upload_appointments_router)
app.include_router(recommend_router)
app.include_router(triage_router)

# Mount WebSocket endpoints
app.add_api_websocket_route("/ws/ed-waits", ws_wait_times.ws_ed_wait_times)
app.add_api_websocket_route("/ws/triage", triage_ws.ws_triage)


@app.get("/")
def root():
    return {"message": "API is running"}



# # app/main.py
# from fastapi import FastAPI
# from app.database import Base, engine
# from app.endpoints.fetch_ed_waits import router as fetch_ed_waits_router
# from app.endpoints.upload_csv import router as upload_csv_router
# from app.endpoints.upload_appointments import router as upload_appointments_router
# from app.endpoints.recommend import router as recommend_router
# from app.endpoints.triage import router as triage_router
# from app.endpoints import ws_wait_times, triage_ws  # WebSocket modules
# from app.startup_tasks import generate_hospital_coordinates, geocode_hospitals_on_startup  # import async geocoding
# import asyncio

# app = FastAPI(title="HealthFlow API", version="1.0.0")


# @app.on_event("startup")
# async def startup_event():
#     # Create database tables
#     Base.metadata.create_all(bind=engine)

#     # Safely generate hospital coordinates (sync version, if needed)
#     try:
#         generate_hospital_coordinates()
#         print("✅ Hospital coordinates generated successfully")
#     except Exception as e:
#         print("⚠️ Error generating hospital coordinates:", e)

#     # Async geocoding for actual addresses
#     try:
#         await geocode_hospitals_on_startup()
#         print("✅ Hospital geocoding complete")
#     except Exception as e:
#         print("⚠️ Error geocoding hospitals:", e)

#     # Launch WebSocket broadcasting loop safely
#     try:
#         asyncio.create_task(ws_wait_times.broadcast_data())
#         print("✅ WebSocket broadcasting task started")
#     except Exception as e:
#         print("⚠️ Failed to start WebSocket broadcaster:", e)


# # Include HTTP routers
# app.include_router(fetch_ed_waits_router)
# app.include_router(upload_csv_router)
# app.include_router(upload_appointments_router)
# app.include_router(recommend_router)
# app.include_router(triage_router)

# # Mount WebSocket endpoints (not part of APIRouter)
# app.add_api_websocket_route("/ws/ed-waits", ws_wait_times.ws_ed_wait_times)
# app.add_api_websocket_route("/ws/triage", triage_ws.ws_triage)


# @app.get("/")
# def root():
#     return {"message": "API is running"}





# # app/main.py
# from fastapi import FastAPI
# from app.database import Base, engine
# from app.endpoints.fetch_ed_waits import router as fetch_ed_waits_router
# from app.endpoints.upload_csv import router as upload_csv_router
# from app.endpoints.upload_appointments import router as upload_appointments_router
# from app.endpoints.recommend import router as recommend_router
# from app.endpoints.triage import router as triage_router  # ✅ import router object directly
# from app.endpoints import ws_wait_times, triage_ws  # WebSocket modules
# from app.startup_tasks import generate_hospital_coordinates
# import asyncio

# app = FastAPI(title="HealthFlow API", version="1.0.0")


# @app.on_event("startup")
# async def startup_event():
#     # Create database tables
#     Base.metadata.create_all(bind=engine)

#     # Safely generate hospital coordinates
#     try:
#         generate_hospital_coordinates()
#         print("✅ Hospital coordinates generated successfully")
#     except Exception as e:
#         print("⚠️ Error generating hospital coordinates:", e)

#     # Launch WebSocket broadcasting loop safely
#     try:
#         asyncio.create_task(ws_wait_times.broadcast_data())
#         print("✅ WebSocket broadcasting task started")
#     except Exception as e:
#         print("⚠️ Failed to start WebSocket broadcaster:", e)


# # Include HTTP routers
# app.include_router(fetch_ed_waits_router)
# app.include_router(upload_csv_router)
# app.include_router(upload_appointments_router)
# app.include_router(recommend_router)

# # ✅ Include triage router (human-like + rule-based combined)
# app.include_router(triage_router)

# # Mount WebSocket endpoints (not part of APIRouter)
# app.add_api_websocket_route("/ws/ed-waits", ws_wait_times.ws_ed_wait_times)

# # ✅ Mount triage WebSocket
# app.add_api_websocket_route("/ws/triage", triage_ws.ws_triage)


# @app.get("/")
# def root():
#     return {"message": "API is running"}



