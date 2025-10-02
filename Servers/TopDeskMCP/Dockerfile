# TopDesk MCP Server - Python-based Dockerfile
# syntax=docker/dockerfile:1

FROM python:3.11-slim

# Install procps for ps command (needed for health check)
RUN apt-get update && apt-get install -y --no-install-recommends procps && rm -rf /var/lib/apt/lists/*

# Create app user for security
RUN groupadd -g 1001 appuser && \
    useradd -u 1001 -g appuser -s /bin/bash -m appuser

# Set working directory
WORKDIR /app

# Install topdesk-mcp package
# Use trusted host for CI/CD environments with certificate issues
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org topdesk-mcp==0.8.1

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/data && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port for HTTP mode
EXPOSE 3030

# Health check - verify the process is running
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
    CMD ps aux | grep -v grep | grep "topdesk_mcp.main" > /dev/null || exit 1

# Run the MCP server
CMD ["python", "-m", "topdesk_mcp.main"]
