# TopDesk Custom MCP Server

A custom Python-based Model Context Protocol (MCP) server for TopDesk integration. This implementation avoids the known bugs in existing topdesk-mcp packages by implementing the MCP protocol directly.

## Overview

This server provides a reliable interface to TopDesk API via the MCP protocol, with proper parameter mapping and bearer token authentication matching the GoogleCalendarMCP security pattern.

## Features

- **Direct MCP Implementation**: No FastMCP dependency - implements JSON-RPC 2.0 protocol directly
- **Proper Parameter Mapping**: Correctly transforms MCP calls to TopDesk API format
- **Bearer Token Authentication**: Secure authentication matching existing MCP pattern
- **Incident Management**: Create, retrieve, and list TopDesk incidents
- **Person Management**: Search and retrieve person information
- **Status Operations**: Get categories and priorities
- **Docker Integration**: Containerized with health checks
- **Comprehensive Testing**: Unit and integration tests with 90%+ coverage target

## Configuration

The server requires the following environment variables:

### TopDesk API Configuration
- `TOPDESK_BASE_URL`: Base URL of your TopDesk instance (e.g., `https://company.topdesk.net/tas/api`)
- `TOPDESK_USERNAME`: TopDesk API username
- `TOPDESK_PASSWORD`: TopDesk API password/token

### MCP Server Configuration
- `MCP_HOST`: Host to bind to (default: `0.0.0.0`)
- `MCP_PORT`: Port to listen on (default: `3002`)
- `MCP_LOG_LEVEL`: Logging level (default: `INFO`)

### Security Configuration
- `BEARER_TOKENS`: Bearer tokens for authentication (JSON array or comma-separated)

See `.env.example` for a complete configuration template.

## Available Tools

### Incident Management

#### `topdesk_create_incident`
Create a new TopDesk incident.

**Parameters:**
- `caller_id` (required): UUID of the caller (person)
- `brief_description` (required): Short description of the incident
- `request` (required): Detailed description of the issue
- `category` (optional): Incident category name
- `priority` (optional): Incident priority name

**Example:**
```json
{
  "caller_id": "d34b277f-e6a2-534c-a96b-23bf383cb4a1",
  "brief_description": "Cannot login to Windows",
  "request": "User cannot login. Error: 'no user with this name'",
  "category": "Core applicaties",
  "priority": "P1 (I&A)"
}
```

#### `topdesk_get_incident`
Get a specific incident by ID.

**Parameters:**
- `incident_id` (required): UUID of the incident

#### `topdesk_list_incidents`
List incidents with optional filters.

**Parameters:**
- `status` (optional): Filter by status name
- `caller_id` (optional): Filter by caller UUID
- `limit` (optional): Maximum number of incidents (default: 10)

### Person Management

#### `topdesk_get_person`
Get a specific person by ID.

**Parameters:**
- `person_id` (required): UUID of the person

#### `topdesk_search_persons`
Search for persons by query.

**Parameters:**
- `query` (required): Search query string
- `limit` (optional): Maximum number of results (default: 10)

### Status Operations

#### `topdesk_get_categories`
Get list of available incident categories.

#### `topdesk_get_priorities`
Get list of available incident priorities.

## Parameter Mapping

This implementation correctly maps MCP call parameters to TopDesk API format:

**MCP Call Format:**
```json
{
  "caller_id": "uuid-here",
  "brief_description": "Short desc",
  "request": "Detailed description",
  "category": "Core applicaties",
  "priority": "P1 (I&A)"
}
```

**TopDesk API Format:**
```json
{
  "briefDescription": "Short desc",
  "request": "Detailed description",
  "caller": {"id": "uuid-here"},
  "category": {"name": "Core applicaties"},
  "priority": {"name": "P1 (I&A)"}
}
```

## Running Locally

### Prerequisites
- Python 3.11+
- pip

### Installation
```bash
cd Servers/TopDeskCustomMCP
pip install -r requirements.txt
```

### Configuration
```bash
cp .env.example .env
# Edit .env with your configuration
```

### Start Server
```bash
python -m src.main
```

The server will start on `http://0.0.0.0:3003` by default.

## Docker Deployment

### Build
```bash
docker build -t topdesk-custom-mcp .
```

### Run
```bash
docker run -d \
  --name topdesk-custom-mcp \
  -p 3003:3003 \
  -e TOPDESK_BASE_URL=https://your-instance.topdesk.net/tas/api \
  -e TOPDESK_USERNAME=your_username \
  -e TOPDESK_PASSWORD=your_password \
  -e BEARER_TOKENS='["your-token"]' \
  topdesk-custom-mcp
```

### Health Check
```bash
curl http://localhost:3003/health
```

## Testing

### Unit Tests
```bash
pytest tests/unit/ -v --cov=src
```

### Integration Tests
```bash
pytest tests/integration/ -v
```

### All Tests with Coverage
```bash
pytest tests/ -v --cov=src --cov-report=html
```

## Security

- **Non-root User**: Runs as `topdeskuser` (UID 1001)
- **Bearer Token Authentication**: All MCP methods (except initialize) require valid bearer token
- **Read-only Filesystem**: Container configured with read-only root filesystem
- **No New Privileges**: Security flag prevents privilege escalation
- **Resource Limits**: Docker container enforces memory and CPU limits

## Architecture

```
TopDeskCustomMCP/
├── src/
│   ├── main.py              # Entry point and tool registration
│   ├── mcp_server.py        # Direct MCP protocol implementation
│   ├── topdesk_client.py    # TopDesk API client with parameter mapping
│   ├── auth/
│   │   └── bearer_validator.py  # Bearer token authentication
│   ├── handlers/
│   │   ├── incidents.py     # Incident operation handlers
│   │   ├── persons.py       # Person operation handlers
│   │   └── status.py        # Status operation handlers
│   └── models/              # Data models (future)
├── tests/
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests
├── Dockerfile              # Container definition
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Integration with Existing Infrastructure

This MCP server integrates seamlessly with the existing multi-MCP setup:

1. **Same Security Model**: Bearer token authentication matching GoogleCalendarMCP
2. **Port 3003**: Custom MCP on port 3003 (old TopDeskMCP uses 3002)
3. **Docker Compose**: Add to main docker-compose.yml
4. **NGINX Routing**: Configure `/topdesk-custom/` route
5. **Health Checks**: Standard health endpoint at `/health`

## Troubleshooting

### Server won't start
- Check environment variables are set correctly
- Verify TopDesk credentials are valid
- Check port 3003 is not in use

### Authentication failures
- Verify bearer token is configured correctly
- Check Authorization header format: `Bearer <token>`
- Ensure token matches one in BEARER_TOKENS configuration

### TopDesk API errors
- Verify TopDesk URL is correct (include `/tas/api`)
- Check username/password credentials
- Verify person/category/priority names match TopDesk instance

## Development

### Code Style
```bash
black src/
flake8 src/
mypy src/
```

### Adding New Tools
1. Create handler method in appropriate handler class
2. Register tool in `src/main.py`
3. Add unit tests
4. Update documentation

## License

See main repository LICENSE file.

## Support

For issues specific to this MCP implementation, please open an issue in the main repository.
