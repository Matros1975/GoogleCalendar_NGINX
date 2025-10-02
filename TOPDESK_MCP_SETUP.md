# TopDesk MCP Server Setup Guide

This document describes the TopDesk MCP server that has been added to the multi-MCP deployment.

## Overview

The TopDesk MCP server provides access to the TopDesk API via the Model Context Protocol (MCP). It runs as a containerized Python service alongside the existing Google Calendar MCP server, both behind an NGINX reverse proxy.

## Architecture

```
┌─────────────────────────────────────────┐
│         NGINX Reverse Proxy             │
│  (Authentication & SSL Termination)     │
└─────────┬───────────────────────┬───────┘
          │                       │
          ├─ /topdesk/            ├─ / (calendar)
          │                       │
┌─────────▼────────┐    ┌────────▼────────────┐
│  TopDesk MCP     │    │  Calendar MCP       │
│  Port: 3030      │    │  Port: 3000         │
│  Transport: HTTP │    │  Transport: HTTP    │
└──────────────────┘    └─────────────────────┘
```

## Configuration

### Environment Variables

Add these to your `.env` file or set them in `docker-compose.yml`:

```bash
# TopDesk API Configuration
TOPDESK_URL=https://yourcompany.topdesk.net
TOPDESK_USERNAME=your_api_username
TOPDESK_PASSWORD=your_api_token

# Transport Configuration (already set in docker-compose.yml)
TOPDESK_MCP_TRANSPORT=streamable-http
TOPDESK_MCP_HOST=0.0.0.0
TOPDESK_MCP_PORT=3030
```

### Docker Compose Service

The TopDesk MCP service is defined in `docker-compose.yml`:

```yaml
topdesk-mcp:
  build: ./Servers/TopDeskMCP
  container_name: topdesk-mcp
  restart: unless-stopped
  networks:
    - mcp-internal
  environment:
    - TOPDESK_MCP_TRANSPORT=streamable-http
    - TOPDESK_MCP_HOST=0.0.0.0
    - TOPDESK_MCP_PORT=3030
    - TOPDESK_URL=${TOPDESK_URL:-https://example.topdesk.net}
    - TOPDESK_USERNAME=${TOPDESK_USERNAME:-example_user}
    - TOPDESK_PASSWORD=${TOPDESK_PASSWORD:-example_password}
  volumes:
    - topdesk-data:/app/data
  # Security and resource limits...
```

## Deployment

### 1. Configure Credentials

Edit your `.env` file or set environment variables:

```bash
export TOPDESK_URL="https://yourcompany.topdesk.net"
export TOPDESK_USERNAME="your_username"
export TOPDESK_PASSWORD="your_api_token"
```

### 2. Build and Start Services

```bash
# Build the TopDesk MCP container
docker compose build topdesk-mcp

# Start all services (or just TopDesk)
docker compose up -d

# Or start only TopDesk MCP
docker compose up -d topdesk-mcp
```

### 3. Verify Deployment

```bash
# Check container status
docker ps | grep topdesk

# Check container health
docker inspect topdesk-mcp --format='{{.State.Health.Status}}'

# View logs
docker logs topdesk-mcp

# Run TopDesk-specific tests
./tests/infrastructure/07-topdesk-mcp-test.sh
```

## NGINX Routing

The TopDesk MCP server is accessible through NGINX at the `/topdesk/` path:

```
https://yourdomain.com/topdesk/  -> topdesk-mcp:3030/mcp
```

### Security

The TopDesk endpoint uses the same security measures as the Calendar MCP:

1. **IP Allowlist**: Configure allowed IPs in `nginx/conf.d/mcp-proxy.conf`
2. **Bearer Token Authentication**: Required for all API calls
3. **TLS/SSL**: HTTPS enforced via Let's Encrypt certificates

## Available Tools

The TopDesk MCP server exposes the following tools via the MCP protocol:

### Incident Management
- `topdesk_get_incident` - Get incident by UUID or number
- `topdesk_get_incidents_by_fiql_query` - Query incidents with FIQL
- `topdesk_create_incident` - Create new incident
- `topdesk_archive_incident` / `topdesk_unarchive_incident`
- `topdesk_escalate_incident` / `topdesk_deescalate_incident`
- `topdesk_add_action_to_incident` - Add comments/replies
- `topdesk_get_incident_actions` - Get all actions
- `topdesk_get_complete_incident_overview` - Full incident details

### Time Tracking
- `topdesk_get_timespent_on_incident`
- `topdesk_register_timespent_on_incident`

### Attachments
- `topdesk_get_incident_attachments`
- `topdesk_get_incident_attachments_as_markdown` - With document conversion

### Operators
- `topdesk_get_operator` - Get operator by ID
- `topdesk_get_operators_by_fiql_query`
- `topdesk_get_operatorgroups_of_operator`

### Persons
- `topdesk_get_person` - Get person by ID
- `topdesk_get_person_by_query`
- `topdesk_create_person` / `topdesk_update_person`
- `topdesk_archive_person` / `topdesk_unarchive_person`

### Utilities
- `topdesk_get_fiql_query_howto` - FIQL query help
- `topdesk_get_object_schemas` - Schema documentation

## Testing

### Run TopDesk Tests

```bash
# Run TopDesk-specific tests
./tests/infrastructure/07-topdesk-mcp-test.sh

# Run all infrastructure tests
./tests/infrastructure/run-all-tests.sh
```

### Test Results

The TopDesk test suite validates:

1. ✅ Container is running
2. ✅ Health status is healthy
3. ✅ MCP process is active
4. ✅ Logs are clean
5. ✅ NGINX routing (when NGINX is running)
6. ✅ Network connectivity
7. ✅ Resource usage within limits
8. ✅ Network configuration
9. ✅ Security settings (read-only filesystem, no-new-privileges)

## Security Features

The TopDesk MCP container implements the same security measures as the Calendar MCP:

### Container Security
- **Read-only root filesystem**: Prevents runtime modifications
- **No-new-privileges**: Blocks privilege escalation
- **Non-root user**: Runs as `appuser` (UID 1001)
- **Capability dropping**: All capabilities dropped except `NET_BIND_SERVICE`
- **Temporary filesystems**: Writable areas limited to `/tmp` and `/app/logs`

### Resource Limits
```yaml
memory: 512M (limit), 256M (reservation)
cpus: 1.0 (limit), 0.5 (reservation)
```

### Network Isolation
- Connected only to `mcp-internal` network
- No direct port exposure to host
- All access through NGINX proxy

## Troubleshooting

### Container Won't Start

Check logs:
```bash
docker logs topdesk-mcp
```

Common issues:
- Missing credentials (TOPDESK_URL, TOPDESK_USERNAME, TOPDESK_PASSWORD)
- Invalid TopDesk URL
- Network connectivity issues

### Health Check Failing

```bash
# Check health status
docker inspect topdesk-mcp --format='{{json .State.Health}}' | jq

# Test health check manually
docker exec topdesk-mcp ps aux | grep topdesk_mcp.main
```

### NGINX Cannot Reach TopDesk

```bash
# Test network connectivity
docker exec nginx-proxy ping topdesk-mcp

# Check NGINX logs
docker logs nginx-proxy | grep topdesk

# Verify service is on correct network
docker inspect topdesk-mcp --format='{{json .NetworkSettings.Networks}}'
```

### Authentication Issues

Verify credentials:
```bash
docker exec topdesk-mcp env | grep TOPDESK
```

Test TopDesk API directly:
```bash
curl -u "${TOPDESK_USERNAME}:${TOPDESK_PASSWORD}" \
  "${TOPDESK_URL}/tas/api/incidents?pageSize=1"
```

## Maintenance

### Updating TopDesk MCP Version

```bash
# Update version in Dockerfile
cd Servers/TopDeskMCP
# Edit Dockerfile: pip install topdesk-mcp==X.Y.Z

# Rebuild
docker compose build topdesk-mcp

# Recreate container
docker compose up -d --force-recreate topdesk-mcp
```

### Viewing Logs

```bash
# Real-time logs
docker logs -f topdesk-mcp

# Last 100 lines
docker logs --tail 100 topdesk-mcp
```

### Restarting Service

```bash
# Restart TopDesk MCP only
docker compose restart topdesk-mcp

# Restart all services
docker compose restart
```

## Integration with Existing Setup

The TopDesk MCP integrates seamlessly with the existing infrastructure:

1. **Same Security Model**: IP allowlist + bearer token authentication
2. **Consistent Patterns**: Follows the same deployment patterns as Calendar MCP
3. **Shared NGINX**: Uses the same reverse proxy for routing
4. **Network Isolation**: Connected to the same internal network
5. **Monitoring**: Same health check patterns
6. **Testing**: Integrated into the existing test suite

## References

- [TopDesk MCP Package (PyPI)](https://pypi.org/project/topdesk-mcp/)
- [TopDesk API Documentation](https://developers.topdesk.com/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [FastMCP Framework](https://github.com/jlowin/fastmcp)

## Support

For issues specific to:
- **TopDesk MCP package**: Check [topdesk-mcp on PyPI](https://pypi.org/project/topdesk-mcp/)
- **Deployment/Infrastructure**: See main project README and REFACTOR.md
- **TopDesk API**: Refer to [TopDesk Developer Portal](https://developers.topdesk.com/)
