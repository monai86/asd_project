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

# Install research/runtime dependencies plus the active API dependencies.
COPY requirements.txt /tmp/root-requirements.txt
COPY apps/api/requirements.txt /tmp/api-requirements.txt
RUN pip install --no-cache-dir \
    -r /tmp/root-requirements.txt \
    -r /tmp/api-requirements.txt

# Copy the canonical Therapist App v2 API and research assets used by providers.
COPY apps/api/app/ ./app/
COPY src/ ./src/
COPY packages/ ./packages/
COPY data/ ./data/
COPY artifacts/ ./artifacts/

# Expose backend port
EXPOSE 8000

# Start the canonical Therapist App v2 API.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
