# ============================================================
# ASD Assessment Dashboard — production container
#
# Build:    docker build -t asd-dashboard .
# Run:      docker run -p 8501:8501 asd-dashboard
# Open:     http://localhost:8501
# ============================================================
FROM python:3.11-slim

# System libs required by librosa / soundfile / faster-whisper
# default-jre-headless is for the optional TalkBank CHATTER validator
# (drop chatter.jar at /opt/chatter.jar and set CHATTER_JAR=/opt/chatter.jar
# to enable strict validation; pipeline gracefully skips if absent).
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ffmpeg \
        libsndfile1 \
        libgomp1 \
        default-jre-headless \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better Docker cache)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Streamlit configuration
ENV STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    PYTHONUNBUFFERED=1

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app/dashboard_unified.py"]
