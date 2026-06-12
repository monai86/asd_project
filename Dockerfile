FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Install system packages required for audio processing (libsndfile, ffmpeg) and git
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    libsndfile1 \
    libsndfile1-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source directories and artifacts
COPY src/ ./src/
COPY packages/ ./packages/
COPY data/ ./data/
COPY artifacts/ ./artifacts/

# Expose backend port
EXPOSE 8000

# Start FastAPI application
CMD ["uvicorn", "src.therapist_backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
