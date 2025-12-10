# Voice Clone Pre-Call Service - Docker Image
# syntax=docker/dockerfile:1

FROM python:3.11-slim

# Install curl for health checks
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Create app user for security (non-root)
RUN groupadd -g 1001 voicecloneuser && \
    useradd -u 1001 -g voicecloneuser -s /bin/bash -m voicecloneuser

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
# Use trusted host for CI/CD environments with certificate issues
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

# Copy application code
COPY src/ /app/src/
COPY migrations/ /app/migrations/
COPY alembic.ini /app/

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/storage /app/data/voices /var/log/mcp-services && \
    chown -R voicecloneuser:voicecloneuser /app /var/log/mcp-services

# Switch to non-root user
USER voicecloneuser

# Expose port 3006
EXPOSE 3006

# Health check - verify HTTP endpoint responds
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
    CMD curl -f http://localhost:3006/health || exit 1

# Run the service
CMD ["python", "-m", "src.main"]
