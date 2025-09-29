# MCP_GINX - Secure Google Calendar MCP with NGINX Proxy

A secure deployment configuration for Google Calendar MCP (Model Context Protocol) server with NGINX reverse proxy, SSL termination, and bearer token authentication designed for Oracle Cloud Infrastructure.

## Overview

This repository contains a production-ready deployment of the Google Calendar MCP server with enterprise-grade security features:

- **NGINX Reverse Proxy**: SSL termination, security headers, rate limiting
- **Bearer Token Authentication**: API access control
- **Internal Docker Network**: MCP container isolated from internet
- **SSL/TLS Encryption**: HTTPS only with modern ciphers
- **Oracle Cloud Optimized**: Specifically configured for Oracle VM deployment

## Architecture

```
Internet → NGINX Proxy (SSL/TLS) → Internal Docker Network → MCP Container
           ↓
        OAuth + Bearer Token
        Authentication
```

## Key Security Features

- ✅ **SSL Termination**: NGINX handles HTTPS with strong ciphers
- ✅ **Bearer Token Auth**: API access control (NGINX validates tokens)
- ✅ **Internal Networking**: MCP container not exposed to internet
- ✅ **Rate Limiting**: Protection against abuse and DoS attacks
- ✅ **Security Headers**: XSS, CSRF, clickjacking protection
- ✅ **OAuth Protection**: Separate endpoint handling for Google OAuth
- ✅ **Request Size Limiting**: Prevention of payload attacks

## Quick Start

### Prerequisites

1. Oracle Cloud VM instance (Ubuntu/Oracle Linux)
2. Docker and Docker Compose installed
3. Domain name pointing to your VM
4. Google OAuth credentials (JSON file)

### Installation

```bash
# Clone the repository
git clone <your-repo-url> mcp-ginx
cd mcp-ginx

# Copy your Google OAuth credentials
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
sed -i 's/your-domain.com/your-actual-domain.com/' nginx/conf.d/mcp-proxy.conf

# 4. Setup SSL certificates (Let's Encrypt recommended)
sudo certbot certonly --standalone -d your-domain.com
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/key.pem

# 5. Start services
docker-compose -f docker-compose.production.yml up -d

# 6. Authenticate with Google
docker-compose -f docker-compose.production.yml exec calendar-mcp-prod npm run auth
```

## Configuration Files

### Core Configuration
- `docker-compose.production.yml` - Production container orchestration
- `nginx/conf.d/mcp-proxy.conf` - NGINX reverse proxy with authentication
- `.env.production` - Environment variables and security settings

### Security & Management
- `setup-oracle-vm.sh` - Automated deployment script
- `manage-tokens.sh` - Bearer token management
- `docs/oracle-cloud-firewall.md` - Firewall configuration guide

### SSL/TLS
- `nginx/ssl/` - SSL certificate directory
- `nginx/nginx.conf` - Main NGINX configuration

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
