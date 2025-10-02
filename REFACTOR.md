# Project Refactor: Multi-MCP Deployment Structure

This document describes the structural refactoring performed to support multiple MCP servers behind a shared NGINX proxy.

## Overview

The project has been refactored from a single MCP deployment to a multi-MCP architecture that allows:
- Multiple MCP servers running in isolated containers
- Centralized NGINX proxy for routing and security
- Easy addition of new MCP servers without structural changes
- Consistent security and configuration across all services

## Changes Made

### 1. Directory Structure

**Before:**
```
.
├── src/              # MCP server source
├── nginx/            # NGINX configuration
├── Dockerfile        # MCP server build
├── docker-compose.yml
└── ...
```

**After:**
```
.
├── Servers/
│   ├── GoogleCalendarMCP/  # Google Calendar MCP server
│   │   ├── src/
│   │   ├── Dockerfile
│   │   ├── package.json
│   │   └── ...
│   └── TEMPLATE_MCP_SERVER/ # Template for new servers
├── nginx/                   # NGINX proxy configuration
│   ├── nginx.conf
│   ├── conf.d/
│   ├── ssl/
│   └── auth/
├── tests/                   # Infrastructure tests
├── docker-compose.yml       # Orchestrates all services
└── ...
```

### 2. Docker Compose Configuration

The `docker-compose.yml` has been updated to:
- Reference the new `Servers/` directory structure
- Support multiple MCP services
- Maintain all security configurations
- Use relative paths for build contexts

**Key changes:**
```yaml
# Before
services:
  calendar-mcp:
    build: .

# After  
services:
  calendar-mcp:
    build: ./Servers/GoogleCalendarMCP
```

```yaml
# Before
volumes:
  - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro

# After (now consistent)
volumes:
  - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
```

### 3. Infrastructure Tests

Added comprehensive test suite in `tests/infrastructure/`:
- **01-container-startup.sh** - Validates container orchestration
- **02-endpoint-reachability.sh** - Tests network connectivity
- **03-health-check.sh** - Monitors service health
- **04-bearer-token-security.sh** - Validates authentication
- **05-tls-certificates.sh** - Tests SSL/TLS configuration
- **06-yaml-validation.sh** - Validates configuration files
- **run-all-tests.sh** - Master test runner

These tests can be run before and after changes to ensure system integrity.

### 4. Documentation

New documentation files:
- `Servers/README.md` - Guide for adding new MCP servers
- `Servers/TEMPLATE_MCP_SERVER/README.md` - Quick start template
- `tests/README.md` - Test suite documentation
- `REFACTOR.md` - This file

## Backwards Compatibility

The refactoring maintains full backwards compatibility:

### Environment Variables
All existing environment variables continue to work:
- `TRANSPORT=http`
- `HOST=0.0.0.0`
- `PORT=3000`
- `NODE_ENV=production`
- `GOOGLE_OAUTH_CREDENTIALS`

### Port Mappings
All port mappings remain the same:
- `80:80` - HTTP (NGINX)
- `443:443` - HTTPS (NGINX)
- `3500-3505` - OAuth ports (MCP)

### Volume Mounts
OAuth credentials and token storage unchanged:
- `./gcp-oauth.keys.json:/app/gcp-oauth.keys.json:ro`
- `calendar-tokens:/home/nodejs/.config/google-calendar-mcp`

### Security Configuration
All security features preserved:
- Read-only filesystems
- Non-root users
- Resource limits
- Security options
- Health checks
- Bearer token authentication
- TLS/SSL termination

## Migration Steps

If you have an existing deployment, follow these steps:

### 1. Backup Current Configuration

```bash
# Backup existing configuration
cp docker-compose.yml docker-compose.yml.backup
cp -r nginx nginx.backup

# Export environment
docker compose config > current-config.yml
```

### 2. Pull Updated Code

```bash
git pull origin main
```

### 3. Verify Configuration

```bash
# Validate docker-compose.yml
docker compose config

# Run quick tests
./tests/infrastructure/run-all-tests.sh --quick
```

### 4. Rebuild Containers

```bash
# Stop existing containers
docker compose down

# Rebuild with new structure
docker compose build

# Start services
docker compose up -d
```

### 5. Verify Deployment

```bash
# Check container status
docker compose ps

# Run full test suite
./tests/infrastructure/run-all-tests.sh

# Check logs
docker compose logs -f
```

### 6. Test Functionality

- Access health endpoint: `curl -k https://localhost/health`
- Test OAuth flow: Visit configured OAuth URL
- Test MCP tools: Use existing client applications
- Verify bearer token auth: Test with/without valid tokens

## Adding New MCP Servers

With the new structure, adding MCP servers is straightforward:

### 1. Create Server Directory

```bash
cp -r Servers/TEMPLATE_MCP_SERVER Servers/YourMCPServer
```

### 2. Add Server Code

Place your MCP server implementation in the new directory with:
- Source code
- Dockerfile
- Dependencies (package.json, etc.)
- Configuration files
- README.md

### 3. Update docker-compose.yml

Add service definition:

```yaml
services:
  your-mcp-server:
    build: ./Servers/YourMCPServer
    container_name: your-mcp-server
    restart: unless-stopped
    networks:
      - mcp-internal
    environment:
      - TRANSPORT=http
      - HOST=0.0.0.0
      - PORT=3001  # Different port
    # ... (see Servers/README.md for full template)
```

### 4. Update NGINX Configuration

Add upstream and location in `nginx/conf.d/mcp-proxy.conf`:

```nginx
upstream your_mcp_backend {
    server your-mcp-server:3001;
    keepalive 32;
}

location /your-service/ {
    # Authentication and proxying
    # ... (see Servers/README.md for full template)
}
```

### 5. Deploy

```bash
docker compose up -d your-mcp-server
docker compose exec nginx-proxy nginx -s reload
```

See `Servers/README.md` for detailed instructions and best practices.

## Testing

### Pre-Refactor Baseline

Before refactoring, establish baseline:

```bash
# Run tests and save results
./tests/infrastructure/run-all-tests.sh --save-results baseline-results.txt
```

### Post-Refactor Validation

After refactoring, verify functionality:

```bash
# Run tests again
./tests/infrastructure/run-all-tests.sh --save-results post-refactor-results.txt

# Compare results
diff baseline-results.txt post-refactor-results.txt
```

### Continuous Testing

Integrate tests into CI/CD pipeline:

```yaml
# Example GitHub Actions
- name: Run Infrastructure Tests
  run: |
    docker compose up -d
    sleep 30
    ./tests/infrastructure/run-all-tests.sh
```

## File Mapping

### Moved Files

| Original Location | New Location |
|------------------|--------------|
| `./Dockerfile` | `./Servers/GoogleCalendarMCP/Dockerfile` |
| `./src/` | `./Servers/GoogleCalendarMCP/src/` |
| `./package.json` | `./Servers/GoogleCalendarMCP/package.json` |
| `./scripts/` | `./Servers/GoogleCalendarMCP/scripts/` |
| `./docs/` | `./Servers/GoogleCalendarMCP/docs/` |
| `./nginx/` | `./nginx/` (moved from Servers/) |

### Unchanged Files

These files remain at project root:
- `docker-compose.yml` (modified to reference new paths)
- `docker-compose.dev.yml`
- `gcp-oauth.keys.json` (not in git)
- `.env.production`
- `README.md`
- `DEPLOYMENT.md`
- `LICENSE`
- Management scripts (`manage-tokens.sh`, `setup-oracle-vm.sh`)

### New Files

- `Servers/README.md`
- `Servers/TEMPLATE_MCP_SERVER/README.md`
- `tests/infrastructure/*.sh`
- `tests/README.md`
- `REFACTOR.md`

## Troubleshooting

### Build Fails After Refactor

```bash
# Clean Docker build cache
docker compose build --no-cache

# Verify paths
docker compose config
```

### Cannot Find Source Files

Check that build context is correct:
```yaml
build: ./Servers/GoogleCalendarMCP  # Not ./Servers
```

### NGINX Cannot Connect to MCP

1. Verify service names match in docker-compose.yml and nginx config
2. Check network configuration: `docker network inspect googlecalendar_nginx_mcp-internal`
3. Test connectivity: `docker compose exec nginx-proxy ping calendar-mcp`

### Volume Mount Issues

Ensure volume paths are relative to project root:
```yaml
# Correct
volumes:
  - ./gcp-oauth.keys.json:/app/gcp-oauth.keys.json:ro

# Wrong (from Servers/ directory)
volumes:
  - ../gcp-oauth.keys.json:/app/gcp-oauth.keys.json:ro
```

### Health Checks Fail

1. Wait for services to fully start (40s for MCP)
2. Check health check command in docker-compose.yml
3. Test manually: `docker compose exec calendar-mcp wget -O- http://localhost:3000/health`

## Performance Impact

The refactoring has **no performance impact**:
- Same number of containers
- Same resource allocations
- Same network configuration
- Same build process
- Only difference is directory organization

## Security Considerations

All security features are preserved:
- ✅ Bearer token authentication
- ✅ TLS/SSL termination
- ✅ Rate limiting
- ✅ IP allowlisting
- ✅ Security headers
- ✅ Read-only filesystems
- ✅ Non-root users
- ✅ Resource limits

## Future Enhancements

The new structure enables:

1. **Multiple MCP Servers** - Easily add new MCP servers for different APIs
2. **Load Balancing** - NGINX can load balance across multiple instances
3. **Service Discovery** - Could integrate with Consul or etcd
4. **Dynamic Configuration** - Could generate NGINX config from service registry
5. **Monitoring** - Centralized monitoring of all MCP servers
6. **CI/CD Integration** - Test each MCP server independently

## Support

For issues or questions:
1. Check this document for migration steps
2. Review `Servers/README.md` for service management
3. Run infrastructure tests: `./tests/infrastructure/run-all-tests.sh`
4. Check container logs: `docker compose logs`
5. Consult `DEPLOYMENT.md` for deployment guides

## Related Documentation

- `README.md` - Project overview and quick start
- `DEPLOYMENT.md` - Production deployment guide
- `Servers/README.md` - Service management guide
- `tests/README.md` - Test suite documentation
- `MIGRATION.md` - Previous configuration changes
