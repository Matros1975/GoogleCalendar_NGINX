# Multi-MCP Server Setup Guide

This guide explains how to deploy multiple MCP servers behind the NGINX proxy in this project.

## Architecture Overview

```
Internet
   ↓
NGINX Proxy (SSL/TLS + Bearer Token Auth)
   ↓
Internal Docker Network (mcp-internal)
   ↓
├─→ Google Calendar MCP (calendar-mcp:3000)
├─→ Another MCP Server (another-mcp:3000)
└─→ Additional MCP Servers...
```

## Quick Start: Adding a New MCP Server

### Step 1: Create Server Directory

```bash
# Create directory for new MCP server
mkdir -p Servers/MyNewMCP

# Copy template files if starting from scratch
# Or copy your existing MCP server files here
```

### Step 2: Add to Docker Compose

Edit `docker-compose.yml` and add your new service:

```yaml
services:
  # ... existing services ...
  
  my-new-mcp:
    build: ./Servers/MyNewMCP
    container_name: my-new-mcp
    restart: unless-stopped
    
    networks:
      - mcp-internal
    
    environment:
      - TRANSPORT=http
      - HOST=0.0.0.0
      - PORT=3000
      - NODE_ENV=production
    
    volumes:
      - ./Servers/MyNewMCP/config:/app/config:ro
      - my-new-mcp-data:/app/data
    
    healthcheck:
      test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://0.0.0.0:3000/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  # ... existing volumes ...
  my-new-mcp-data:
    driver: local
```

### Step 3: Configure NGINX Routing

Choose one of two routing strategies:

#### Option A: Path-Based Routing

Add a location block to `Servers/NGINX/conf.d/mcp-proxy.conf`:

```nginx
# Upstream for new MCP service
upstream my_new_mcp_backend {
    server my-new-mcp:3000;
    keepalive 32;
}

# Add inside the main server block
location /mynewmcp/ {
    # IP allowlist check
    if ($allowed_client = 0) {
        return 403 '{"error":"Access denied","message":"IP address not authorized"}';
    }
    
    # Authentication subrequest
    auth_request /auth;
    
    # Forward to MCP service
    proxy_pass http://my_new_mcp_backend/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Authorization $http_authorization;
    
    # Timeouts
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
    
    # Buffer settings
    proxy_buffering off;
    proxy_cache off;
}
```

**Access URLs:**
- Calendar MCP: `https://yourdomain.com/` (or `/calendar/`)
- New MCP: `https://yourdomain.com/mynewmcp/`

#### Option B: Subdomain Routing

Create a new file `Servers/NGINX/conf.d/mynewmcp-proxy.conf`:

```nginx
# Upstream for new MCP service
upstream my_new_mcp_backend {
    server my-new-mcp:3000;
    keepalive 32;
}

# Subdomain server block
server {
    listen 443 ssl http2;
    server_name mynewmcp.yourdomain.com;
    
    # SSL Configuration
    ssl_certificate /etc/ssl/certs/yourdomain.crt;
    ssl_certificate_key /etc/ssl/private/yourdomain.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    
    # Rate limiting
    limit_req zone=api burst=20 nodelay;
    
    # Health check endpoint (no auth required)
    location /health {
        proxy_pass http://my_new_mcp_backend/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # MCP endpoints - require authentication
    location / {
        if ($allowed_client = 0) {
            return 403 '{"error":"Access denied","message":"IP address not authorized"}';
        }
        
        auth_request /auth;
        
        proxy_pass http://my_new_mcp_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Authorization $http_authorization;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        proxy_buffering off;
        proxy_cache off;
    }
}
```

**Access URLs:**
- Calendar MCP: `https://calendar.yourdomain.com/`
- New MCP: `https://mynewmcp.yourdomain.com/`

**Note:** For subdomain routing, ensure your SSL certificate covers all subdomains (use a wildcard certificate or add SANs).

### Step 4: Deploy

```bash
# Build and start all services
docker compose up -d --build

# Check that all containers are running
docker compose ps

# Test new MCP health endpoint
curl -k https://yourdomain.com/mynewmcp/health
# or for subdomain routing:
curl -k https://mynewmcp.yourdomain.com/health

# Test with authentication
curl -k -H "Authorization: Bearer YOUR_TOKEN" \
     https://yourdomain.com/mynewmcp/
```

### Step 5: Validate

```bash
# Run deployment tests
./scripts/test-deployment.sh --post-refactor

# Check container logs
docker compose logs my-new-mcp

# Check NGINX logs
docker compose logs nginx-proxy

# Test internal connectivity
docker exec nginx-proxy ping my-new-mcp
```

## Security Considerations

### Bearer Token Management

You can configure bearer tokens in multiple ways:

#### Shared Tokens (Default)
All MCP servers use the same bearer tokens defined in `.env.production`:

```bash
BEARER_TOKENS=token1,token2,token3
```

#### Per-Server Tokens
If you need different tokens for different MCP servers, you can:

1. **Use NGINX location-specific auth:**
   Modify NGINX config to use different auth endpoints per MCP

2. **Implement token validation in each MCP:**
   Each MCP server validates its own set of tokens

### IP Allowlisting

The `geo $allowed_client` block in NGINX configuration controls which IPs can access your MCP servers. Update `Servers/NGINX/conf.d/mcp-proxy.conf`:

```nginx
geo $allowed_client {
    default 0;
    127.0.0.1/32 1;
    YOUR_IP_ADDRESS/32 1;
    YOUR_NETWORK/24 1;
}
```

### Network Isolation

All MCP servers run on the internal `mcp-internal` Docker network. They are NOT directly accessible from the internet - only through NGINX.

## Resource Management

### Adjusting Resource Limits

For each MCP service in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      memory: 512M      # Maximum memory
      cpus: "1.0"       # Maximum CPU cores
    reservations:
      memory: 256M      # Guaranteed memory
      cpus: "0.5"       # Guaranteed CPU
```

Adjust based on your server's capacity and the MCP's requirements.

### Monitoring Resources

```bash
# View resource usage of all containers
docker stats

# View specific container
docker stats my-new-mcp
```

## Advanced Configuration

### Custom Health Checks

Customize health checks per MCP:

```yaml
healthcheck:
  test: ["CMD-SHELL", "your-custom-health-check-command"]
  interval: 30s      # How often to check
  timeout: 10s       # Max time for check to complete
  retries: 3         # Failed attempts before unhealthy
  start_period: 40s  # Grace period on startup
```

### Environment Variables

Pass configuration to your MCP:

```yaml
environment:
  - TRANSPORT=http
  - PORT=3000
  - LOG_LEVEL=info
  - CUSTOM_CONFIG=/app/config/settings.json
  # Add your MCP-specific variables
```

### Persistent Data

Store MCP data in named volumes:

```yaml
volumes:
  - ./Servers/MyNewMCP/config:/app/config:ro  # Read-only config
  - my-new-mcp-data:/app/data                 # Persistent data
```

### OAuth Ports

If your MCP needs OAuth authentication:

```yaml
ports:
  - "3510:3510"  # OAuth callback port
  - "3511:3511"  # Additional auth port
```

## Troubleshooting

### Container Won't Start

```bash
# Check container logs
docker compose logs my-new-mcp

# Check if port conflicts exist
docker ps -a

# Verify build succeeded
docker compose build my-new-mcp
```

### NGINX Can't Reach MCP

```bash
# Test internal network connectivity
docker exec nginx-proxy ping my-new-mcp

# Check if MCP is on correct network
docker network inspect mcp-internal

# Verify service name matches in NGINX upstream
```

### Health Check Failing

```bash
# Test health endpoint directly
docker exec my-new-mcp wget -O- http://localhost:3000/health

# Check health check configuration
docker inspect my-new-mcp | grep -A 10 Healthcheck
```

### Authentication Issues

```bash
# Test without authentication
curl -k https://yourdomain.com/mynewmcp/health

# Test with bearer token
curl -k -H "Authorization: Bearer YOUR_TOKEN" \
     https://yourdomain.com/mynewmcp/

# Check NGINX auth logs
docker compose logs nginx-proxy | grep auth
```

## Examples

### Example 1: Adding a Simple REST API MCP

```yaml
# docker-compose.yml
services:
  api-mcp:
    image: myregistry/api-mcp:latest
    container_name: api-mcp
    restart: unless-stopped
    networks:
      - mcp-internal
    environment:
      - API_KEY=secret
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
```

```nginx
# Servers/NGINX/conf.d/mcp-proxy.conf
upstream api_mcp_backend {
    server api-mcp:3000;
}

location /api/ {
    auth_request /auth;
    proxy_pass http://api_mcp_backend/;
    # ... proxy settings ...
}
```

### Example 2: Adding a Database-Backed MCP

```yaml
# docker-compose.yml
services:
  db-mcp:
    build: ./Servers/DatabaseMCP
    container_name: db-mcp
    networks:
      - mcp-internal
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/mydb
    depends_on:
      - postgres
  
  postgres:
    image: postgres:15-alpine
    container_name: mcp-postgres
    networks:
      - mcp-internal
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=mydb
    volumes:
      - postgres-data:/var/lib/postgresql/data

volumes:
  postgres-data:
```

## Best Practices

1. **Isolation**: Each MCP in its own directory under `Servers/`
2. **Security**: Always use bearer token authentication
3. **Monitoring**: Implement health checks for all services
4. **Resources**: Set appropriate limits based on load
5. **Logging**: Use structured logging in your MCPs
6. **Backups**: Regular backups of persistent volumes
7. **Updates**: Keep containers and dependencies updated
8. **Testing**: Test new MCPs in development before production

## Migration from Single MCP

If you're migrating from a single MCP setup:

1. Your existing Google Calendar MCP is now at `Servers/GoogleCalendarMCP/`
2. Add new MCPs following this guide
3. Update NGINX config for routing
4. Test thoroughly before deploying

## Support

For issues:
- Check logs: `docker compose logs [service-name]`
- Review NGINX config: `docker exec nginx-proxy nginx -t`
- Test connectivity: `docker exec nginx-proxy ping [service-name]`
- Consult `REFACTORING_GUIDE.md` for troubleshooting

## See Also

- `REFACTORING_GUIDE.md` - Details of the refactoring process
- `docker-compose.multi-mcp.yml` - Multi-MCP example configuration
- `Servers/NGINX/conf.d/multi-mcp-routing.conf.example` - NGINX routing examples
- `DEPLOYMENT.md` - General deployment guide
