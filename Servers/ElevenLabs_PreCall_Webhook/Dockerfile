# ElevenLabs Pre-Call Webhook Service
FROM python:3.11-slim

# Install system dependencies for audio processing
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -g 1001 precalluser && \
    useradd -u 1001 -g precalluser -s /bin/bash -m precalluser

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

# Copy application code
COPY src/ /app/src/

# Create directories
RUN mkdir -p /app/logs /app/storage/voice_samples /var/log/mcp-services && \
    chown -R precalluser:precalluser /app /var/log/mcp-services

USER precalluser

EXPOSE 3005

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
    CMD curl -f http://localhost:3005/health || exit 1

CMD ["python", "-m", "src.main"]
