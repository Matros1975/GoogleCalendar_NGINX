# MCP_NGINX - Secure Multi-MCP Server Deployment with NGINX Proxy

A production-ready deployment configuration for running multiple MCP (Model Context Protocol) servers behind a secure NGINX reverse proxy, with SSL termination and bearer token authentication, designed for Oracle Cloud Infrastructure.

## Overview

This repository provides a flexible multi-server architecture for deploying MCP services:

- **Multi-MCP Support**: Deploy multiple MCP servers simultaneously
- **NGINX Reverse Proxy**: SSL termination, security headers, rate limiting
- **Bearer Token Authentication**: API access control for all MCP servers
- **Internal Docker Network**: MCP containers isolated from internet
- **SSL/TLS Encryption**: HTTPS only with modern ciphers
- **Oracle Cloud Optimized**: Specifically configured for Oracle VM deployment

### Included MCP Server

- **Google Calendar MCP**: Full-featured calendar management (included by default)

### Easy to Add More

The architecture supports adding additional MCP servers with minimal configuration. See [Multi-MCP Setup Guide](docs/multi-mcp-setup.md).

## Architecture

```
Internet
   ↓
NGINX Proxy (SSL/TLS + Bearer Token Auth)
   ↓
Internal Docker Network
   ↓
├─→ Google Calendar MCP
├─→ [Your Additional MCP Servers]
└─→ [Future MCP Services]
```

## Project Structure

```
/
├── Servers/
│   ├── GoogleCalendarMCP/    # Google Calendar MCP server
│   │   ├── src/               # Source code
│   │   ├── Dockerfile         # Container build
│   │   └── ...
│   ├── NGINX/                 # NGINX proxy configuration
│   │   ├── conf.d/            # Server configs
│   │   ├── ssl/               # SSL certificates
│   │   └── nginx.conf
│   └── [YourMCPServer]/       # Add more MCP servers here
├── docker-compose.yml         # Main orchestration
├── scripts/                   # Helper scripts
└── docs/                      # Documentation
```

## Key Security Features

- ✅ **SSL Termination**: NGINX handles HTTPS with strong ciphers
- ✅ **Bearer Token Auth**: API access control (NGINX validates tokens)
- ✅ **Internal Networking**: MCP containers not exposed to internet
- ✅ **Rate Limiting**: Protection against abuse and DoS attacks
- ✅ **Security Headers**: XSS, CSRF, clickjacking protection
- ✅ **OAuth Protection**: Separate endpoint handling for OAuth flows
- ✅ **Request Size Limiting**: Prevention of payload attacks
- ✅ **IP Allowlisting**: Restrict access to trusted networks

## Quick Start

### Prerequisites

1. Oracle Cloud VM instance (Ubuntu/Oracle Linux) or any Linux server
2. Docker and Docker Compose installed
3. Domain name pointing to your VM (for production SSL)
4. Google OAuth credentials (JSON file) for Calendar MCP

### Installation

```bash
# Clone the repository
git clone <your-repo-url> mcp-nginx
cd mcp-nginx

# Copy your Google OAuth credentials to the Calendar MCP directory
cp /path/to/your/gcp-oauth.keys.json ./Servers/GoogleCalendarMCP/gcp-oauth.keys.json

# Run the automated setup (recommended)
./setup-oracle-vm.sh

# OR manual setup:
# Generate SSL certificates (self-signed for testing)
mkdir -p Servers/NGINX/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout Servers/NGINX/ssl/key.pem -out Servers/NGINX/ssl/cert.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Deploy the containers
docker compose up -d
```

# Run automated setup
./setup-oracle-vm.sh
```

### Manual Setup

```bash
# 1. Configure environment
cp Servers/GoogleCalendarMCP/.env.production Servers/GoogleCalendarMCP/.env

# 2. Generate bearer tokens
./manage-tokens.sh add

# 3. Update domain in NGINX config
sed -i 's/your-domain.com/your-actual-domain.com/' Servers/NGINX/conf.d/mcp-proxy.conf

# 4. Setup SSL certificates (Let's Encrypt recommended)
sudo certbot certonly --standalone -d your-domain.com
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem /etc/ssl/certs/your-domain.crt
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem /etc/ssl/private/your-domain.key

# 5. Start services
docker compose up -d

# 6. Authenticate with Google
docker compose exec calendar-mcp npm run auth
```

## Adding More MCP Servers

This architecture makes it easy to deploy multiple MCP servers. See the [Multi-MCP Setup Guide](docs/multi-mcp-setup.md) for:

- Step-by-step instructions for adding new MCP servers
- Path-based routing (e.g., `/calendar/`, `/othermcp/`)
- Subdomain routing (e.g., `calendar.domain.com`, `othermcp.domain.com`)
- Security configuration per server
- Examples and templates

## Configuration Files

### Core Configuration
- `docker-compose.yml` - Production container orchestration with NGINX proxy
- `docker-compose.dev.yml` - Development/Claude Desktop integration
- `docker-compose.multi-mcp.yml` - Multi-MCP example configuration
- `Servers/NGINX/conf.d/mcp-proxy.conf` - NGINX reverse proxy with authentication
- `Servers/GoogleCalendarMCP/.env.production` - Production environment variables

### Security & Management
- `setup-oracle-vm.sh` - Automated deployment script
- `manage-tokens.sh` - Bearer token management (supports new structure)
- `Servers/GoogleCalendarMCP/scripts/test-deployment.sh` - Comprehensive deployment testing
- `docs/oracle-cloud-firewall.md` - Firewall configuration guide

### SSL/TLS
- `Servers/NGINX/ssl/` - SSL certificate directory
- `Servers/NGINX/nginx.conf` - Main NGINX configuration

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
