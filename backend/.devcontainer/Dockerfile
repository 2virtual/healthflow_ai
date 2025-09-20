FROM python:3.11

WORKDIR /workspace

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install other tools if needed (e.g., git, linting tools)
RUN apt-get update && apt-get install -y git