# TopDesk Custom MCP - Deployment Guide

This guide covers deploying the TopDesk Custom MCP server in the existing multi-MCP infrastructure.

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose installed
- Access to TopDesk instance with API credentials
- Bearer token for authentication

### 2. Configuration

Create `.env` file in the root directory with:

```bash
# TopDesk Custom MCP Configuration
TOPDESK_BASE_URL=https://your-instance.topdesk.net/tas/api
TOPDESK_CUSTOM_USERNAME=your_username
TOPDESK_CUSTOM_PASSWORD=your_password
TOPDESK_CUSTOM_BEARER_TOKENS=["your-bearer-token-here"]
```

### 3. Build and Start

```bash
# Build the TopDesk Custom MCP container
docker-compose build topdesk-custom-mcp

# Start the service
docker-compose up -d topdesk-custom-mcp

# Check logs
docker-compose logs -f topdesk-custom-mcp

# Verify health
curl http://localhost:3003/health
```

## Integration Points

### Docker Compose

The service is defined in `docker-compose.yml`:

```yaml
topdesk-custom-mcp:
  build: ./Servers/TopDeskCustomMCP
  container_name: topdesk-custom-mcp
  ports:
    - "3003:3003"  # Internal port only
  networks:
    - mcp-internal
  environment:
    - TOPDESK_BASE_URL
    - TOPDESK_USERNAME
    - TOPDESK_PASSWORD
    - BEARER_TOKENS
```

### NGINX Routing

The service is accessible through NGINX at:

```
https://yourdomain.com/topdesk-custom/
```

NGINX configuration in `nginx/conf.d/mcp-proxy.conf`:
- Bearer token authentication required
- IP allowlist enforced
- Standard JSON-RPC timeouts (30s connect, 60s read)

## Testing

### Local Testing

```bash
# Run unit tests
cd Servers/TopDeskCustomMCP
pip install -r requirements.txt
pytest tests/unit/ -v

# Run integration tests
pytest tests/integration/ -v

# Run end-to-end test
python test_e2e.py http://localhost:3003 your-bearer-token
```

### Docker Testing

```bash
# Build test image
docker build -t topdesk-custom-mcp:test Servers/TopDeskCustomMCP/

# Run test container
docker run --rm -d \
  --name topdesk-test \
  -p 3003:3003 \
  -e TOPDESK_BASE_URL=https://test.topdesk.net/tas/api \
  -e TOPDESK_USERNAME=test_user \
  -e TOPDESK_PASSWORD=test_pass \
  -e BEARER_TOKENS='["test-token"]' \
  topdesk-custom-mcp:test

# Test health endpoint
curl http://localhost:3003/health

# Test MCP initialization
curl -X POST http://localhost:3003 \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {"name": "test", "version": "1.0"}
    }
  }'

# Stop test container
docker stop topdesk-test
```

### NGINX Testing

```bash
# Test through NGINX (requires full deployment)
curl -X POST https://yourdomain.com/topdesk-custom/ \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'
```

## MCP Protocol Usage

### Initialize Session

```json
POST /topdesk-custom/
Authorization: Bearer your-token

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {
      "name": "your-client",
      "version": "1.0.0"
    }
  }
}
```

### List Available Tools

```json
POST /topdesk-custom/
Authorization: Bearer your-token

{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list",
  "params": {}
}
```

### Create Incident

```json
POST /topdesk-custom/
Authorization: Bearer your-token

{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "topdesk_create_incident",
    "arguments": {
      "caller_id": "d34b277f-e6a2-534c-a96b-23bf383cb4a1",
      "brief_description": "Cannot login to Windows",
      "request": "User cannot login. Error message shown.",
      "category": "Core applicaties",
      "priority": "P1 (I&A)"
    }
  }
}
```

## Monitoring

### Health Check

```bash
# Direct health check
curl http://localhost:3003/health

# Through NGINX (if configured)
curl https://yourdomain.com/topdesk-custom/health
```

Expected response:
```json
{
  "status": "healthy",
  "server": "TopDeskCustomMCP",
  "version": "1.0.0"
}
```

### Container Logs

```bash
# View logs
docker-compose logs topdesk-custom-mcp

# Follow logs
docker-compose logs -f topdesk-custom-mcp

# View last 100 lines
docker-compose logs --tail=100 topdesk-custom-mcp
```

### Container Status

```bash
# Check container status
docker ps | grep topdesk-custom-mcp

# Check health status
docker inspect topdesk-custom-mcp | grep -A 5 Health

# Resource usage
docker stats topdesk-custom-mcp --no-stream
```

## Troubleshooting

### Server Won't Start

**Check environment variables:**
```bash
docker exec topdesk-custom-mcp env | grep TOPDESK
```

**Check logs:**
```bash
docker-compose logs topdesk-custom-mcp
```

**Common issues:**
- Missing or invalid environment variables
- Port 3003 already in use
- Invalid TopDesk credentials

### Authentication Failures

**Verify bearer token:**
```bash
# Test without token (should fail)
curl -X POST http://localhost:3003 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# Should return: {"jsonrpc":"2.0","id":1,"error":{"code":-32001,"message":"Unauthorized: Invalid or missing bearer token"}}
```

**Common issues:**
- Bearer token not configured in environment
- Token not included in Authorization header
- Token format incorrect (should be `Bearer <token>`)

### TopDesk API Errors

**Test TopDesk connectivity:**
```bash
# From within container
docker exec topdesk-custom-mcp curl -I https://your-instance.topdesk.net

# Test API directly
curl -u "username:password" https://your-instance.topdesk.net/tas/api/incidents
```

**Common issues:**
- Invalid TopDesk URL (must include `/tas/api`)
- Invalid credentials
- Network connectivity issues
- TopDesk instance not accessible

### Parameter Mapping Issues

The server automatically maps MCP parameters to TopDesk API format:

**MCP Format:**
```json
{
  "caller_id": "uuid",
  "brief_description": "text",
  "category": "name",
  "priority": "name"
}
```

**TopDesk API Format:**
```json
{
  "caller": {"id": "uuid"},
  "briefDescription": "text",
  "category": {"name": "name"},
  "priority": {"name": "name"}
}
```

This mapping is handled automatically by the `TopDeskAPIClient` class.

## Security

### Bearer Token Management

- Store tokens securely in `.env` file
- Use strong, random tokens (32+ characters)
- Rotate tokens periodically
- Never commit tokens to version control

### Container Security

- Runs as non-root user (`topdeskuser`, UID 1001)
- Read-only root filesystem
- No new privileges flag
- Resource limits enforced
- Temporary filesystems for logs

### Network Security

- Internal Docker network only
- NGINX proxy handles external access
- IP allowlist enforced by NGINX
- Bearer token authentication required
- TLS/SSL via NGINX

## Performance

### Resource Limits

```yaml
resources:
  limits:
    memory: 512M
    cpus: "1.0"
  reservations:
    memory: 256M
    cpus: "0.5"
```

### Expected Performance

- Health check: <50ms
- MCP initialize: <100ms
- Tools/list: <100ms
- Simple tool call: <500ms
- Incident creation: <2s (depends on TopDesk)

## Maintenance

### Updating

```bash
# Pull latest changes
git pull

# Rebuild container
docker-compose build topdesk-custom-mcp

# Restart service
docker-compose up -d topdesk-custom-mcp
```

### Backup

No data storage required - all data is in TopDesk.

Environment variables should be backed up as part of your infrastructure backup.

### Scaling

The server is stateless and can be horizontally scaled:

```yaml
topdesk-custom-mcp:
  deploy:
    replicas: 3
    update_config:
      parallelism: 1
      delay: 10s
```

## Support

For issues specific to TopDesk Custom MCP:
1. Check container logs
2. Verify configuration
3. Test with `test_e2e.py` script
4. Review this deployment guide
5. Open issue in repository

For TopDesk API issues:
- Consult TopDesk API documentation
- Verify credentials and permissions
- Test with direct API calls
