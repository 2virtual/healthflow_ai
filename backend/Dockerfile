# ---------- Base image ----------
FROM python:3.11-slim

# ---------- Install only required system tools + Java (for pypmml) ----------
RUN apt-get update && apt-get install -y \
    curl \
    default-jre \
    && rm -rf /var/lib/apt/lists/*

# ---------- Environment variables ----------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/home/appuser/.local/bin:$PATH"

# ---------- Create non-root user ----------
RUN useradd -m appuser
USER appuser

# ---------- Set working directory ----------
WORKDIR /app

# ---------- Copy requirements first ----------
COPY --chown=appuser:appuser requirements.txt .

# ---------- Install Python dependencies ----------
RUN pip install --no-cache-dir -r requirements.txt

# ---------- Copy app code ----------
COPY --chown=appuser:appuser ./app /app/app

# ---------- Validate symptoms.json (strict in prod) ----------
RUN python -m app.validate_symptoms

# ---------- Expose FastAPI port ----------
EXPOSE 8000

# ---------- Start Uvicorn in production mode ----------
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]







# # ---------- Base image ----------
# FROM python:3.11-slim

# # ---------- Create non-root user ----------
# RUN adduser --disabled-password --gecos '' appuser && \
#     chown -R appuser:appuser /home/appuser

# # ---------- Install system tools + Java (needed for pypmml) ----------
# RUN apt-get update && apt-get install -y \
#     curl \
#     default-jre \
#     && rm -rf /var/lib/apt/lists/*

# # ---------- Switch to non-root user ----------
# USER appuser

# # ---------- Set working directory ----------
# WORKDIR /app

# # ---------- Copy requirements first ----------
# COPY --chown=appuser:appuser requirements.txt .

# # ---------- Install Python dependencies ----------
# RUN pip install --no-cache-dir -r requirements.txt

# # ---------- Copy app code ----------
# COPY --chown=appuser:appuser ./app /app/app

# # ---------- Validate symptoms.json ----------
# RUN python -m app.validate_symptoms

# # ---------- Expose port ----------
# EXPOSE 8000

# # ---------- Start Uvicorn ----------
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]





# # # ---------- Base image ----------
# # FROM python:3.11-slim

# # # ---------- Create non-root user ----------
# # RUN adduser --disabled-password --gecos '' appuser && \
# #     chown -R appuser:appuser /home/appuser

# # # ---------- Install system tools ----------
# # RUN apt-get update && apt-get install -y \
# #     curl \
# #     && rm -rf /var/lib/apt/lists/*

# # # ---------- Switch to non-root user ----------
# # USER appuser

# # # ---------- Set working directory ----------
# # WORKDIR /app

# # # ---------- Copy requirements first ----------
# # COPY --chown=appuser:appuser requirements.txt .

# # # ---------- Install Python dependencies ----------
# # RUN pip install --no-cache-dir -r requirements.txt

# # # ---------- Copy app code ----------
# # # Make sure entire app folder is copied including endpoints/data
# # COPY --chown=appuser:appuser ./app /app/app

# # # ---------- Validate symptoms.json ----------
# # # Update the command to match the actual file location
# # RUN python -m app.validate_symptoms

# # # ---------- Expose port ----------
# # EXPOSE 8000

# # # ---------- Start Uvicorn ----------
# # CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]



