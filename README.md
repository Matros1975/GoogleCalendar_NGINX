# MCP_NGINX - Multi-MCP Deployment with NGINX Proxy

A secure, scalable deployment configuration supporting multiple MCP (Model Context Protocol) servers behind a shared NGINX reverse proxy with SSL termination and bearer token authentication.

## Overview

This repository provides a production-ready infrastructure for deploying multiple MCP servers with:

- **Multi-MCP Architecture**: Support for multiple MCP servers in isolated containers
- **NGINX Reverse Proxy**: Centralized SSL termination, security headers, rate limiting
- **Bearer Token Authentication**: API access control for all services
- **Internal Docker Network**: MCP containers isolated from direct internet access
- **SSL/TLS Encryption**: HTTPS-only with modern ciphers and Let's Encrypt support
- **Easy Extensibility**: Add new MCP servers without structural changes

## Architecture

```
Internet → NGINX Proxy (SSL/TLS) → Internal Docker Network → Multiple MCP Containers
           ↓                                                   ├── GoogleCalendarMCP:3000
        OAuth + Bearer Token                                   ├── YourMCP:3001
        Authentication                                         └── AnotherMCP:3002
```

### Directory Structure

```
.
├── Servers/                    # All server components
│   ├── GoogleCalendarMCP/      # Google Calendar MCP server
│   ├── NGINX/                  # NGINX proxy configuration
│   └── TEMPLATE_MCP_SERVER/    # Template for new servers
├── tests/                      # Infrastructure test suite
├── docker-compose.yml          # Orchestrates all services
└── ...
```

## Key Features

### Security
- ✅ **SSL/TLS Termination**: NGINX handles HTTPS with strong ciphers
- ✅ **Bearer Token Auth**: API access control validated by NGINX
- ✅ **IP Allowlisting**: Restrict access to trusted networks
- ✅ **Internal Networking**: MCP containers not exposed to internet
- ✅ **Rate Limiting**: Protection against abuse and DoS attacks
- ✅ **Security Headers**: XSS, CSRF, clickjacking protection
- ✅ **OAuth Protection**: Separate endpoint handling
- ✅ **Request Size Limiting**: Prevention of payload attacks

### Multi-MCP Support
- ✅ **Isolated Containers**: Each MCP server runs independently
- ✅ **Resource Limits**: Per-service CPU and memory limits
- ✅ **Independent Configuration**: Service-specific environment variables
- ✅ **Easy Addition**: Template-based server addition
- ✅ **Centralized Routing**: NGINX handles all external requests
- ✅ **Health Monitoring**: Per-service health checks

### Testing & Validation
- ✅ **Infrastructure Tests**: Automated validation of entire stack
- ✅ **Security Testing**: Bearer token and TLS validation
- ✅ **Configuration Validation**: YAML and Docker Compose checks
- ✅ **Health Checks**: Service readiness monitoring

## Quick Start

### Prerequisites

1. Docker and Docker Compose installed
2. Domain name pointing to your server (for production SSL)
3. Google OAuth credentials (JSON file) for Calendar MCP
4. Linux server (tested on Oracle Cloud, works on any Docker host)

### Installation

```bash
# Clone the repository
git clone <your-repo-url> mcp-nginx
cd mcp-nginx

# Copy your Google OAuth credentials
cp /path/to/your/gcp-oauth.keys.json ./gcp-oauth.keys.json

# Run the automated setup (recommended)
./setup-oracle-vm.sh

# OR manual setup:
# Generate SSL certificates (self-signed for testing)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Deploy the containers
docker compose up -d
```
cp /path/to/your/gcp-oauth.keys.json ./gcp-oauth.keys.json

# Run automated setup
./setup-oracle-vm.sh
```

### Manual Setup

```bash
# 1. Configure environment
cp .env.production .env

# 2. Generate bearer tokens
./manage-tokens.sh add

# 3. Update domain in NGINX config
sed -i 's/your-domain.com/your-actual-domain.com/' Servers/NGINX/conf.d/mcp-proxy.conf

# 4. Setup SSL certificates (Let's Encrypt recommended)
sudo certbot certonly --standalone -d your-domain.com
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem Servers/NGINX/ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem Servers/NGINX/ssl/key.pem

# 5. Start services
docker compose up -d

# 6. Authenticate with Google
docker compose exec calendar-mcp npm run auth
```

## Adding New MCP Servers

The architecture supports multiple MCP servers. To add a new server:

### 1. Create Server Directory

```bash
# Copy template
cp -r Servers/TEMPLATE_MCP_SERVER Servers/YourMCPServer

# Add your server code, Dockerfile, and configuration
```

### 2. Update docker-compose.yml

Add your service definition:

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
      - PORT=3001  # Use different port
    # ... (see Servers/README.md for complete template)
```

### 3. Update NGINX Configuration

Add routing in `Servers/NGINX/conf.d/mcp-proxy.conf`:

```nginx
upstream your_mcp_backend {
    server your-mcp-server:3001;
    keepalive 32;
}

location /your-service/ {
    # Authentication and proxy configuration
    # ... (see Servers/README.md for complete template)
}
```

### 4. Deploy

```bash
docker compose up -d your-mcp-server
docker compose exec nginx-proxy nginx -s reload
```

See `Servers/README.md` for detailed instructions and best practices.

## Configuration Files

### Core Configuration
- `docker-compose.yml` - Multi-MCP orchestration with NGINX proxy
- `docker-compose.dev.yml` - Development/Claude Desktop integration
- `Servers/NGINX/conf.d/mcp-proxy.conf` - NGINX routing and authentication
- `.env.production` - Production environment variables

### Service Directories
- `Servers/GoogleCalendarMCP/` - Google Calendar MCP server
- `Servers/NGINX/` - NGINX proxy configuration
- `Servers/TEMPLATE_MCP_SERVER/` - Template for new servers

### Security & Management
- `setup-oracle-vm.sh` - Automated deployment script
- `manage-tokens.sh` - Bearer token management
- `docs/oracle-cloud-firewall.md` - Firewall configuration

### Testing
- `tests/infrastructure/` - Automated infrastructure tests
- `tests/README.md` - Test suite documentation

## Testing

### Run Infrastructure Tests

```bash
# Run all tests
./tests/infrastructure/run-all-tests.sh

# Run quick tests (no container startup)
./tests/infrastructure/run-all-tests.sh --quick

# Run security tests only
./tests/infrastructure/run-all-tests.sh --security

# Save results for comparison
./tests/infrastructure/run-all-tests.sh --save-results results.txt
```

Tests validate:
- Container startup and health
- Endpoint reachability
- Bearer token security
- TLS/SSL certificates
- YAML configuration
- Network connectivity

## API Usage

### Health Check (No Authentication)
```bash
curl https://your-domain.com/health
```

### Authenticated API Calls
```bash
# Replace YOUR_TOKEN with your bearer token
curl -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","method":"tools/list","id":1}' \
     https://your-domain.com/
```

### Example: List Calendar Events
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "method": "tools/call",
       "params": {
         "name": "list_events",
         "arguments": {
           "timeMin": "2024-01-01T00:00:00Z",
           "timeMax": "2024-12-31T23:59:59Z"
         }
       },
       "id": 1
     }' \
     https://your-domain.com/
```

## Bearer Token Management

```bash
# Generate and add a new token
./manage-tokens.sh add

# View current tokens
./manage-tokens.sh show

# Test a token
./manage-tokens.sh test <token> https://your-domain.com/health

# Rotate all tokens
./manage-tokens.sh rotate
```

## Monitoring

### View Logs
```bash
# All services
docker-compose -f docker-compose.production.yml logs -f

# NGINX access logs
docker-compose -f docker-compose.production.yml exec nginx-proxy tail -f /var/log/nginx/access.log

# MCP service logs
docker-compose -f docker-compose.production.yml logs -f calendar-mcp-prod
```

### Health Checks
```bash
# Service status
docker-compose -f docker-compose.production.yml ps

# Test endpoints
curl -k https://localhost/health
```

## Deployment Guide

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete deployment instructions, troubleshooting, and production checklist.

## Security Considerations

1. **Bearer Tokens**: Use strong, randomly generated tokens (32+ characters)
2. **SSL Certificates**: Use Let's Encrypt or commercial certificates
3. **Firewall**: Configure Oracle Cloud security lists properly
4. **Updates**: Keep system and dependencies updated
5. **Monitoring**: Set up log monitoring and alerting

## Original Project

This deployment is based on the excellent [Google Calendar MCP Server](https://github.com/nspady/google-calendar-mcp) by nspady, enhanced with production security features for Oracle Cloud deployment.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

For deployment-specific issues:
1. Check [DEPLOYMENT.md](DEPLOYMENT.md) troubleshooting section
2. Review logs and verify configuration
3. Test individual components (OAuth, SSL, tokens, networking)

For Google Calendar MCP functionality:
- Refer to the [original project documentation](https://github.com/nspady/google-calendar-mcp)

**To avoid weekly re-authentication**, publish your app to production mode (without verification):
1. Go to Google Cloud Console → "APIs & Services" → "OAuth consent screen"
2. Click "PUBLISH APP" and confirm
3. Your tokens will no longer expire after 7 days but Google will show a more threatning warning when connecting to the app about it being unverified. 

See [Authentication Guide](docs/authentication.md#moving-to-production-mode-recommended) for details.

## Example Usage

Along with the normal capabilities you would expect for a calendar integration you can also do really dynamic, multi-step processes like:

1. **Cross-calendar availability**:
   ```
   Please provide availability looking at both my personal and work calendar for this upcoming week.
   I am looking for a good time to meet with someone in London for 1 hr.
   ```

2. Add events from screenshots, images and other data sources:
   ```
   Add this event to my calendar based on the attached screenshot.
   ```
   Supported image formats: PNG, JPEG, GIF
   Images can contain event details like date, time, location, and description

3. Calendar analysis:
   ```
   What events do I have coming up this week that aren't part of my usual routine?
   ```
4. Check attendance:
   ```
   Which events tomorrow have attendees who have not accepted the invitation?
   ```
5. Auto coordinate events:
   ```
   Here's some available that was provided to me by someone. {available times}
   Take a look at the times provided and let me know which ones are open on my calendar.
   ```

## Available Tools

| Tool | Description |
|------|-------------|
| `list-calendars` | List all available calendars |
| `list-events` | List events with date filtering |
| `search-events` | Search events by text query |
| `create-event` | Create new calendar events |
| `update-event` | Update existing events |
| `delete-event` | Delete events |
| `get-freebusy` | Check availability across calendars, including external calendars |
| `list-colors` | List available event colors |

## Documentation

- [Authentication Setup](docs/authentication.md) - Detailed Google Cloud setup
- [Advanced Usage](docs/advanced-usage.md) - Multi-account, batch operations
- [Deployment Guide](docs/deployment.md) - HTTP transport, remote access
- [Docker Guide](docs/docker.md) - Docker deployment with stdio and HTTP modes
- [OAuth Verification](docs/oauth-verification.md) - Moving from test to production mode
- [Architecture](docs/architecture.md) - Technical architecture overview
- [Development](docs/development.md) - Contributing and testing
- [Testing](docs/testing.md) - Unit and integration testing guide
- **[Let's Encrypt SSL Setup](docs/letsencrypt-setup-guide.md)** - Complete SSL certificate procedure
- **[SSL Quick Reference](docs/letsencrypt-quick-reference.md)** - Emergency SSL commands

## Configuration

**Environment Variables:**
- `GOOGLE_OAUTH_CREDENTIALS` - Path to OAuth credentials file
- `GOOGLE_CALENDAR_MCP_TOKEN_PATH` - Custom token storage location (optional)

**Claude Desktop Config Location:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`


## Security

- OAuth tokens are stored securely in your system's config directory
- Credentials never leave your local machine
- All calendar operations require explicit user consent

### Troubleshooting

1. **OAuth Credentials File Not Found:**
   - For npx users: You **must** specify the credentials file path using `GOOGLE_OAUTH_CREDENTIALS`
   - Verify file paths are absolute and accessible

2. **Authentication Errors:**
   - Ensure your credentials file contains credentials for a **Desktop App** type
   - Verify your user email is added as a **Test User** in the Google Cloud OAuth Consent screen
   - Try deleting saved tokens and re-authenticating
   - Check that no other process is blocking ports 3000-3004

3. **Build Errors:**
   - Run `npm install && npm run build` again
   - Check Node.js version (use LTS)
   - Delete the `build/` directory and run `npm run build`
4. **"Something went wrong" screen during browser authentication**
   - Perform manual authentication per the below steps
   - Use a Chromium-based browser to open the authentication URL. Test app authentication may not be supported on some non-Chromium browsers.

### Manual Authentication
For re-authentication or troubleshooting:
```bash
# For npx installations
export GOOGLE_OAUTH_CREDENTIALS="/path/to/your/credentials.json"
npx @cocal/google-calendar-mcp auth

# For local installations
npm run auth
```

## License

MIT

## Support

- [GitHub Issues](https://github.com/nspady/google-calendar-mcp/issues)
- [Documentation](docs/)
