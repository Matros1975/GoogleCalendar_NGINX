# TopDesk Custom MCP Server - Direct Python Implementation
# syntax=docker/dockerfile:1

FROM python:3.11-slim

# Install curl for health checks
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Create app user for security (non-root)
RUN groupadd -g 1001 topdeskuser && \
    useradd -u 1001 -g topdeskuser -s /bin/bash -m topdeskuser

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ /app/src/

# Create necessary directories and set permissions
RUN mkdir -p /app/logs && \
    chown -R topdeskuser:topdeskuser /app

# Switch to non-root user
USER topdeskuser

# Expose port 3002
EXPOSE 3002

# Health check - verify HTTP endpoint responds
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
    CMD curl -f http://localhost:3002/health || exit 1

# Run the MCP server
CMD ["python", "-m", "src.main"]
