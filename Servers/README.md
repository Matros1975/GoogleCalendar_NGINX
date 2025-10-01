# Servers Directory

This directory contains all server components for the multi-MCP deployment, organized by service.

## Structure

```
Servers/
├── GoogleCalendarMCP/    # Google Calendar MCP server
│   ├── src/              # Source code
│   ├── Dockerfile        # Container build config
│   ├── package.json      # Dependencies
│   └── ...
├── NGINX/                # NGINX reverse proxy configuration
│   ├── nginx.conf        # Main NGINX config
│   ├── conf.d/           # Virtual host configs
│   └── ssl/              # SSL certificates (not in git)
└── README.md             # This file
```

## Adding a New MCP Server

To add a new MCP server to the deployment:

### 1. Create Server Directory

```bash
mkdir -p Servers/YourMCPServer
```

### 2. Add Server Files

Place your MCP server code, Dockerfile, and configuration in the new directory:

```
Servers/YourMCPServer/
├── src/              # Your source code
├── Dockerfile        # Container build config
├── package.json      # Dependencies (if applicable)
└── README.md         # Server documentation
```

### 3. Update docker-compose.yml

Add your new service to the root `docker-compose.yml`:

```yaml
services:
  # ... existing services ...

  your-mcp-server:
    build: ./Servers/YourMCPServer
    container_name: your-mcp-server
    restart: unless-stopped
    
    networks:
      - mcp-internal
    
    ports:
      - "PORT:PORT"  # If needed for OAuth or external access
    
    environment:
      - TRANSPORT=http
      - HOST=0.0.0.0
      - PORT=3001  # Use different port from other MCP servers
      - NODE_ENV=production
    
    volumes:
      - ./your-config.json:/app/config.json:ro
      - your-mcp-data:/app/data
    
    # Resource limits
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "1.0"
        reservations:
          memory: 256M
          cpus: "0.5"
    
    # Security options
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=100m
    
    # Health check
    healthcheck:
      test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://0.0.0.0:3001/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  your-mcp-data:
    driver: local
```

### 4. Update NGINX Configuration

Add a new upstream and location block in `Servers/NGINX/conf.d/mcp-proxy.conf`:

```nginx
# Upstream for your new MCP service
upstream your_mcp_backend {
    server your-mcp-server:3001;
    keepalive 32;
}

# In the main server block, add a location for your service
location /your-service/ {
    # Same auth and security as other services
    if ($allowed_client = 0) {
        return 403 '{"error":"Access denied","message":"IP address not authorized"}';
    }
    
    auth_request /auth;
    
    proxy_pass http://your_mcp_backend/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Timeouts
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
    
    # Buffer settings
    proxy_buffering off;
    proxy_cache off;
}
```

### 5. Test Configuration

```bash
# Validate docker-compose.yml
docker compose config

# Start your new service
docker compose up -d your-mcp-server

# Check logs
docker compose logs -f your-mcp-server

# Test NGINX config
docker compose exec nginx-proxy nginx -t

# Reload NGINX if config is valid
docker compose exec nginx-proxy nginx -s reload
```

### 6. Add to Tests

Update `tests/infrastructure/` scripts to include your new service in validation.

## Service Isolation

Each MCP server:
- Has its own build context and dependencies
- Runs in its own container with resource limits
- Has isolated environment variables and configuration
- Communicates via the shared Docker network (`mcp-internal`)
- Is accessible only through NGINX (except OAuth ports if needed)

## Security

All services:
- Use non-root users
- Have read-only filesystems (with tmpfs for temporary files)
- Enforce resource limits
- Require bearer token authentication through NGINX
- Use TLS/SSL for external access

## Common Patterns

### Environment Variables
Define service-specific variables in docker-compose.yml or use `.env` files:

```yaml
environment:
  - SERVICE_NAME=your-service
  - API_KEY=${YOUR_API_KEY}  # From .env file
```

### Volume Mounts
For configuration, credentials, and persistent data:

```yaml
volumes:
  - ./config.json:/app/config.json:ro          # Config (read-only)
  - ./credentials.json:/app/creds.json:ro      # Credentials (read-only)
  - service-data:/app/data                      # Persistent data
```

### Health Checks
Always define health checks for monitoring:

```yaml
healthcheck:
  test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:PORT/health || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Networking
Use the shared internal network for service-to-service communication:

```yaml
networks:
  - mcp-internal
```

Only expose ports that need external access (OAuth, debugging, etc.).

## Maintenance

### Updating a Service

```bash
# Pull changes
git pull

# Rebuild specific service
docker compose build your-mcp-server

# Restart with new build
docker compose up -d your-mcp-server
```

### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f your-mcp-server

# Last N lines
docker compose logs --tail=100 your-mcp-server
```

### Scaling Services

If a service needs multiple instances, use Docker Compose scale:

```bash
docker compose up -d --scale your-mcp-server=3
```

Update NGINX config for load balancing:

```nginx
upstream your_mcp_backend {
    server your-mcp-server:3001;
    # Additional instances added automatically by Docker DNS
    keepalive 32;
}
```

## Troubleshooting

### Service Won't Start
1. Check logs: `docker compose logs your-mcp-server`
2. Verify build: `docker compose build your-mcp-server`
3. Check config: `docker compose config`
4. Validate NGINX: `docker compose exec nginx-proxy nginx -t`

### Can't Access Through NGINX
1. Verify service is running: `docker compose ps`
2. Check NGINX logs: `docker compose logs nginx-proxy`
3. Test direct access: `docker exec your-mcp-server curl http://localhost:PORT/health`
4. Verify network connectivity: `docker exec nginx-proxy ping your-mcp-server`

### High Resource Usage
1. Check stats: `docker stats`
2. Review resource limits in docker-compose.yml
3. Check for memory leaks in application logs
4. Consider horizontal scaling

## Support

For issues specific to:
- **GoogleCalendarMCP**: See `Servers/GoogleCalendarMCP/README.md`
- **NGINX Configuration**: See `docs/nginx-configuration.md`
- **Infrastructure Tests**: See `tests/README.md`
- **General Deployment**: See `DEPLOYMENT.md`
