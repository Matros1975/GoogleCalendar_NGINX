# Docker Deployment Guide

Production-ready Docker setup for MCP Servers (including Google Calendar MCP) with NGINX proxy, SSL termination, and bearer token authentication.

## Project Structure

```
/
├── Servers/
│   ├── GoogleCalendarMCP/    # Google Calendar MCP server
│   ├── NGINX/                 # NGINX proxy configuration
│   └── [YourMCPServer]/       # Add more MCP servers here
├── docker-compose.yml         # Production deployment
├── docker-compose.dev.yml     # Development/Claude Desktop
└── docker-compose.multi-mcp.yml  # Multi-server template
```

## Quick Start (Production Deployment)

```bash
# 1. Place OAuth credentials in the Calendar MCP directory
cp /path/to/your/gcp-oauth.keys.json ./Servers/GoogleCalendarMCP/gcp-oauth.keys.json

# 2. Generate SSL certificates (self-signed for testing)
mkdir -p Servers/NGINX/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout Servers/NGINX/ssl/key.pem -out Servers/NGINX/ssl/cert.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# 3. Build and start the secure deployment
docker compose up -d

# 4. Authenticate (one-time setup)
docker compose exec calendar-mcp npm run auth

# 5. Test the deployment
curl -k https://localhost/health
```

## Development Mode (Claude Desktop Integration)

For Claude Desktop integration using stdio mode, use the development compose file:

### stdio Mode (For Claude Desktop)
**Direct process integration for Claude Desktop:**

#### Step 1: Initial Setup
```bash
# Clone and setup
git clone https://github.com/Matros1975/GoogleCalendar_NGINX.git
cd GoogleCalendar_NGINX

# Place your OAuth credentials in the Calendar MCP directory
cp /path/to/your/gcp-oauth.keys.json ./Servers/GoogleCalendarMCP/gcp-oauth.keys.json

# Create development environment file
cp Servers/GoogleCalendarMCP/.env.example Servers/GoogleCalendarMCP/.env

# Build and start the container in development mode
docker compose -f docker-compose.dev.yml up -d

# Authenticate (one-time setup)
docker compose -f docker-compose.dev.yml exec calendar-mcp npm run auth
```

#### Step 2: Claude Desktop Configuration
Add to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "google-calendar": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "--mount", "type=bind,src=/absolute/path/to/your/gcp-oauth.keys.json,dst=/app/gcp-oauth.keys.json",
        "--mount", "type=volume,src=google-calendar-mcp_calendar-tokens,dst=/home/nodejs/.config/google-calendar-mcp",
        "google-calendar-mcp-calendar-mcp"
      ]
    }
  }
}
```

**⚠️ Important**: Replace `/absolute/path/to/your/gcp-oauth.keys.json` with the actual absolute path to your credentials file.

#### Step 3: Restart Claude Desktop
Restart Claude Desktop to load the new configuration. The server should now work without authentication prompts.

### HTTP Mode
**For testing, debugging, and web integration (Claude Desktop uses stdio):**

#### Step 1: Configure Environment
```bash
# Clone and setup
git clone https://github.com/nspady/google-calendar-mcp.git
cd google-calendar-mcp

# Place your OAuth credentials in the project root
cp /path/to/your/gcp-oauth.keys.json ./gcp-oauth.keys.json

# Configure for HTTP mode
cp .env.example .env
# Edit .env to set:
echo "TRANSPORT=http" >> .env
echo "HOST=0.0.0.0" >> .env
echo "PORT=3000" >> .env
echo "GOOGLE_OAUTH_CREDENTIALS=./gcp-oauth.keys.json" >> .env
```

#### Step 2: Start and Authenticate
```bash
# Build and start the server in HTTP mode
docker compose up -d

# Authenticate (one-time setup)
docker compose exec calendar-mcp npm run auth
# This will show authentication URLs (visit the displayed URL)
# This step only needs to be done once unless the app is in testing mode
# in which case the tokens expire after 7 days 

# Verify server is running
curl http://localhost:3000/health
# Should return: {"status":"healthy","server":"google-calendar-mcp","version":"1.3.0"}
```

#### Step 3: Test with cURL Example
```bash
# Run comprehensive HTTP tests
bash examples/http-with-curl.sh

# Or test specific endpoint
bash examples/http-with-curl.sh http://localhost:3000
```

#### Step 4: Claude Desktop HTTP Configuration
Add to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "google-calendar": {
      "command": "mcp-client",
      "args": ["http://localhost:3000"]
    }
  }
}
```

**Note**: HTTP mode requires the container to be running (`docker compose up -d`)