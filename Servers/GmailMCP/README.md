# Gmail MCP Server

MCP (Model Context Protocol) server for Gmail, providing AI assistants with email management capabilities.

## Features

- **Send Emails**: Send emails with plain text or HTML content
- **List Emails**: List and filter emails from your inbox
- **Get Email Details**: Retrieve full email content and metadata
- **Label Management**: List and manage Gmail labels

## Quick Start

### Prerequisites

1. Node.js 18 or later
2. Google Cloud Project with Gmail API enabled
3. OAuth 2.0 credentials (Desktop app type)

### Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Build the project:**
   ```bash
   npm run build
   ```

3. **Authenticate with Google:**
   ```bash
   npm run auth
   ```
   This will open a browser window for OAuth authentication. The tokens will be saved to `~/.config/gmail-mcp/tokens.json`.

4. **Run the server:**
   ```bash
   npm start
   ```

## OAuth Setup

See [docs/authentication.md](docs/authentication.md) for detailed OAuth setup instructions.

Quick steps:
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project and enable Gmail API
3. Create OAuth 2.0 credentials (Desktop app)
4. Download credentials as `gcp-oauth.keys.json`
5. Place in project root or set `GMAIL_OAUTH_CREDENTIALS` environment variable

Required scopes:
- `https://www.googleapis.com/auth/gmail.modify`
- `https://www.googleapis.com/auth/gmail.settings.basic`

## Usage

### With Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "gmail": {
      "command": "node",
      "args": ["/path/to/GmailMCP/build/index.js"],
      "env": {
        "GMAIL_OAUTH_CREDENTIALS": "/path/to/gcp-oauth.keys.json"
      }
    }
  }
}
```

### Standalone HTTP Server

Run as an HTTP server for use with other MCP clients:

```bash
npm run start:http
# or with custom port
npm run start:http -- --port 3001
```

## Available Tools

### send_email
Send an email via Gmail with support for:
- Multiple recipients (to, cc, bcc)
- Plain text and HTML content
- Reply-to threading

### list_emails
List emails from your inbox with:
- Maximum results limit
- Gmail search queries
- Label filtering

### get_email
Retrieve full email details including:
- Headers (From, To, Subject, Date)
- Full body content
- Message and thread IDs

### list_labels
List all Gmail labels (system and user-created)

## Development

### Run Tests
```bash
npm test              # Unit tests
npm run test:watch    # Watch mode
npm run test:coverage # Coverage report
```

### Lint
```bash
npm run lint
```

### Build for Production
```bash
npm run build
```

## Docker

Build and run with Docker:

```bash
docker build -t gmail-mcp .
docker run -p 3001:3001 \
  -v ./gcp-oauth.keys.json:/app/gcp-oauth.keys.json:ro \
  -v gmail-tokens:/home/nodejs/.config/gmail-mcp \
  -e TRANSPORT=http \
  -e PORT=3001 \
  -e HOST=0.0.0.0 \
  gmail-mcp
```

## Environment Variables

- `GMAIL_OAUTH_CREDENTIALS` - Path to OAuth credentials file
- `GOOGLE_OAUTH_CREDENTIALS` - Alternative path (shared with Calendar MCP)
- `GOOGLE_ACCOUNT_MODE` - Account mode: `normal` or `test` (default: `normal`)
- `TRANSPORT` - Transport type: `stdio` or `http` (default: `stdio`)
- `PORT` - Port for HTTP transport (default: `3001`)
- `HOST` - Host for HTTP transport (default: `127.0.0.1`)
- `DEBUG` - Enable debug logging: `true` or `false`

## Project Structure

```
GmailMCP/
├── src/
│   ├── auth/           # OAuth authentication
│   ├── config/         # Configuration
│   ├── services/       # Business logic (label manager, etc.)
│   ├── tests/          # Unit and integration tests
│   ├── transports/     # stdio and HTTP transports
│   ├── utils/          # Email utilities
│   ├── auth-server.ts  # Standalone auth server
│   └── index.ts        # Main entry point
├── scripts/
│   └── build.js        # Build script
├── Dockerfile          # Container build
└── package.json        # Dependencies
```

## License

MIT

## Contributing

Contributions are welcome! Please ensure tests pass and code is linted before submitting PRs.
