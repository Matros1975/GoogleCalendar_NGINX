# TopDesk MCP Server - Python-based Dockerfile
# syntax=docker/dockerfile:1

FROM python:3.11-alpine

# Create app user for security
RUN addgroup -g 1001 -S appuser && \
    adduser -S -u 1001 -G appuser appuser

# Set working directory
WORKDIR /app

# Install dependencies
RUN apk add --no-cache \
    wget \
    curl \
    && rm -rf /var/cache/apk/*

# Install topdesk-mcp package
RUN pip install --no-cache-dir topdesk-mcp==0.8.1

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/data && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port for HTTP mode
EXPOSE 3030

# Health check script
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
    CMD wget --no-verbose --tries=1 --spider http://0.0.0.0:3030/health || exit 1

# Run the MCP server
CMD ["python", "-m", "topdesk_mcp.main"]
