# Multi-MCP Server Refactoring Guide

This document describes the refactoring process to support multiple MCP servers deployed behind NGINX.

## Overview

This refactoring transforms the project from a single Google Calendar MCP deployment to a flexible multi-server architecture where multiple MCP services can be deployed simultaneously, all routed through a central NGINX proxy.

## Pre-Refactor Testing

Before making any structural changes, run the automated test suite to establish a baseline:

```bash
# Ensure containers are running
docker compose up -d

# Run pre-refactor tests
./scripts/test-deployment.sh --pre-refactor

# Review test results
ls -la test-results/
```

Test results are saved in JSON format with timestamp for comparison with post-refactor tests.

## New Project Structure

The refactored structure organizes all server components under a `Servers/` directory:

```
/
├── Servers/
│   ├── GoogleCalendarMCP/        # Google Calendar MCP server
│   │   ├── src/                  # Source code
│   │   ├── Dockerfile            # Container build file
│   │   ├── package.json          # Dependencies
│   │   ├── gcp-oauth.keys.json   # OAuth credentials
│   │   └── .env                  # Environment variables
│   │
│   ├── NGINX/                    # NGINX reverse proxy
│   │   ├── conf.d/               # Server configurations
│   │   │   ├── mcp-proxy.conf    # Main proxy config
│   │   │   └── [server].conf     # Per-server configs
│   │   ├── nginx.conf            # Main NGINX config
│   │   ├── ssl/                  # SSL certificates
│   │   └── auth/                 # Auth tokens
│   │
│   └── [FutureMCPServer]/        # Template for additional servers
│
├── docker-compose.yml            # Orchestration file
├── scripts/                      # Helper scripts
└── docs/                         # Documentation
```

## Migration Steps

### Step 1: Create New Directory Structure

```bash
# Create main Servers directory
mkdir -p Servers/GoogleCalendarMCP
mkdir -p Servers/NGINX

# Verify structure
tree -L 2 Servers/
```

### Step 2: Move Google Calendar MCP

Move the MCP application files to the new location:

```bash
# Move source code and configs
mv src Servers/GoogleCalendarMCP/
mv package*.json Servers/GoogleCalendarMCP/
mv tsconfig*.json Servers/GoogleCalendarMCP/
mv vitest.config.ts Servers/GoogleCalendarMCP/
mv Dockerfile Servers/GoogleCalendarMCP/
mv scripts Servers/GoogleCalendarMCP/

# Move OAuth credentials (if present)
mv gcp-oauth.keys.json Servers/GoogleCalendarMCP/ 2>/dev/null || true

# Copy environment file templates
cp .env.example Servers/GoogleCalendarMCP/
cp .env.production Servers/GoogleCalendarMCP/
```

### Step 3: Move NGINX Configuration

Move NGINX files to the new location:

```bash
# Move NGINX configs
mv nginx/conf.d Servers/NGINX/
mv nginx/nginx.conf Servers/NGINX/
mv nginx/ssl Servers/NGINX/
mv nginx/auth Servers/NGINX/ 2>/dev/null || true

# Remove old nginx directory
rmdir nginx 2>/dev/null || rm -rf nginx
```

### Step 4: Update Docker Compose Configuration

The `docker-compose.yml` needs to be updated to reference the new paths:

**Before:**
```yaml
services:
  calendar-mcp:
    build: .
    volumes:
      - ./gcp-oauth.keys.json:/app/gcp-oauth.keys.json:ro
```

**After:**
```yaml
services:
  calendar-mcp:
    build: ./Servers/GoogleCalendarMCP
    volumes:
      - ./Servers/GoogleCalendarMCP/gcp-oauth.keys.json:/app/gcp-oauth.keys.json:ro
```

### Step 5: Update Path References

Update all scripts and configuration files:

```bash
# Update setup script
sed -i 's|^\./|./Servers/GoogleCalendarMCP/|g' setup-oracle-vm.sh

# Update NGINX config paths
sed -i 's|/etc/nginx/conf.d/|/etc/nginx/conf.d/|g' docker-compose.yml
```

### Step 6: Test After Migration

After moving files, rebuild and test:

```bash
# Rebuild containers with new structure
docker compose down
docker compose build --no-cache
docker compose up -d

# Wait for services to start
sleep 10

# Run post-refactor tests
./scripts/test-deployment.sh --post-refactor
```

### Step 7: Compare Test Results

```bash
# Compare pre and post refactor test results
diff test-results/deployment-test-pre-refactor-*.json \
     test-results/deployment-test-post-refactor-*.json
```

All tests should pass with identical results.

## Adding Additional MCP Servers

Once the refactoring is complete, adding new MCP servers is straightforward:

### 1. Create New Server Directory

```bash
# Create directory for new server
mkdir -p Servers/NewMCPServer
cd Servers/NewMCPServer

# Copy template files
cp -r ../GoogleCalendarMCP/Dockerfile .
cp ../GoogleCalendarMCP/package.json .
```

### 2. Update Docker Compose

Add new service to `docker-compose.yml`:

```yaml
services:
  # ... existing services ...
  
  new-mcp:
    build: ./Servers/NewMCPServer
    container_name: new-mcp
    restart: unless-stopped
    networks:
      - mcp-internal
    environment:
      - TRANSPORT=http
      - HOST=0.0.0.0
      - PORT=3000
    volumes:
      - ./Servers/NewMCPServer/config:/app/config
      - new-mcp-data:/app/data
    healthcheck:
      test: ["CMD-SHELL", "wget --spider http://0.0.0.0:3000/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  # ... existing volumes ...
  new-mcp-data:
    driver: local
```

### 3. Configure NGINX Routing

Create new NGINX configuration file:

```bash
# Create server-specific config
cat > Servers/NGINX/conf.d/new-mcp-proxy.conf <<'EOF'
# Upstream for New MCP service
upstream new_mcp_backend {
    server new-mcp:3000;
    keepalive 32;
}

# Add location block in main server
# Or create subdomain configuration
EOF
```

### 4. Configure Path-Based or Subdomain Routing

**Option A: Path-Based Routing** (e.g., `/calendar/*` and `/newmcp/*`)

```nginx
location /newmcp/ {
    auth_request /auth;
    proxy_pass http://new_mcp_backend/;
    proxy_http_version 1.1;
    # ... proxy settings ...
}
```

**Option B: Subdomain Routing** (e.g., `calendar.domain.com` and `newmcp.domain.com`)

```nginx
server {
    listen 443 ssl http2;
    server_name newmcp.domain.com;
    
    location / {
        auth_request /auth;
        proxy_pass http://new_mcp_backend;
        # ... proxy settings ...
    }
}
```

### 5. Deploy and Test

```bash
# Rebuild and restart services
docker compose up -d --build

# Test new service
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://your-domain.com/newmcp/health
```

## Security Considerations

### Bearer Token Management

Each MCP server can have:
- **Shared tokens**: Single token validates access to all MCP servers
- **Per-server tokens**: Different tokens for different MCP servers

Update `Servers/NGINX/auth/` with appropriate token configuration.

### Network Isolation

All MCP servers communicate only through the internal Docker network (`mcp-internal`). Only NGINX is exposed to the internet.

### SSL/TLS Configuration

SSL certificates in `Servers/NGINX/ssl/` are shared across all MCP servers. For subdomain routing, ensure certificates cover all subdomains (use wildcard certificates).

## Rollback Procedure

If issues occur during refactoring:

```bash
# Stop containers
docker compose down

# Restore from git
git checkout HEAD -- .

# Restart with original structure
docker compose up -d
```

Or restore from backup:

```bash
# Restore backup (if created before refactoring)
tar -xzf mcp-backup-YYYYMMDD.tar.gz -C /path/to/restore
```

## Troubleshooting

### Issue: Containers fail to start after refactoring

**Solution:**
1. Check Docker Compose syntax: `docker compose config`
2. Verify all paths are correct in `docker-compose.yml`
3. Check volume mounts point to correct locations
4. Review container logs: `docker compose logs`

### Issue: NGINX cannot reach MCP containers

**Solution:**
1. Verify containers are on same network: `docker network inspect mcp-internal`
2. Check service names match in NGINX upstream configs
3. Test internal connectivity: `docker exec nginx-proxy ping calendar-mcp`

### Issue: Tests fail after refactoring

**Solution:**
1. Compare test results to identify specific failures
2. Check if all endpoints are accessible
3. Verify environment variables are correctly set
4. Ensure SSL certificates are in correct location

## Validation Checklist

After completing the refactoring, verify:

- [ ] All containers start successfully
- [ ] NGINX routes to Google Calendar MCP correctly
- [ ] Health endpoints are accessible
- [ ] Bearer token authentication works
- [ ] TLS certificates are valid
- [ ] All pre-refactor tests pass with post-refactor structure
- [ ] Documentation is updated
- [ ] Scripts reference correct paths
- [ ] OAuth authentication still works
- [ ] Logs are accessible

## Documentation Updates Required

After refactoring, update:

- [ ] `README.md` - Installation and setup instructions
- [ ] `DEPLOYMENT.md` - Deployment procedures
- [ ] `docs/docker.md` - Docker documentation
- [ ] `docs/architecture.md` - Architecture diagrams
- [ ] `setup-oracle-vm.sh` - Path references
- [ ] `manage-tokens.sh` - Configuration file locations

## Benefits of New Structure

1. **Scalability**: Easy to add new MCP servers
2. **Isolation**: Each server has its own directory and configuration
3. **Maintainability**: Clear separation of concerns
4. **Flexibility**: Can run different versions or types of MCP servers
5. **Organization**: Logical grouping of related files
6. **Testing**: Easier to test individual servers in isolation

## Next Steps

After successful refactoring:

1. Document any additional MCP servers added
2. Consider creating templates for common server types
3. Automate new server provisioning with scripts
4. Setup monitoring for all MCP servers
5. Create backup procedures for multi-server setup
6. Update CI/CD pipelines if applicable

## Support

For issues or questions:
- Check logs: `docker compose logs [service-name]`
- Review test results in `test-results/`
- Consult original documentation in `docs/`
- Check NGINX error logs: `docker compose exec nginx-proxy cat /var/log/nginx/error.log`
