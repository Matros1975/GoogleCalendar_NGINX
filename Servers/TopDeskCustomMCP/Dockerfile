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
# Use trusted host for CI/CD environments with certificate issues
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

# Copy application code
COPY src/ /app/src/

# Create necessary directories and set permissions
RUN mkdir -p /app/logs && \
    chown -R topdeskuser:topdeskuser /app

# Switch to non-root user
USER topdeskuser

# Expose port 3003 (TopDesk Custom MCP uses 3003, old TopDeskMCP uses 3002)
EXPOSE 3003

# Health check - verify HTTP endpoint responds
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
    CMD curl -f http://localhost:3003/health || exit 1

# Run the MCP server
CMD ["python", "-m", "src.main"]
