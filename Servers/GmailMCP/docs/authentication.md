# Gmail MCP Authentication Setup

## Overview

The Gmail MCP server requires OAuth 2.0 credentials to access your Gmail account. This guide will walk you through setting up authentication.

## Quick Start

1. Obtain OAuth 2.0 credentials from Google Cloud Console
2. Save credentials as `gcp-oauth.keys.json`
3. Run `npm run auth` to authenticate
4. Start the server with `npm start`

## Detailed Setup

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select an existing one
3. Give it a descriptive name (e.g., "Gmail MCP")

### 2. Enable the Gmail API

1. In the Cloud Console, navigate to "APIs & Services" → "Library"
2. Search for "Gmail API"
3. Click on "Gmail API" and click "Enable"

### 3. Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure the OAuth consent screen first:
   - Choose "External" user type (unless you have a Google Workspace)
   - Fill in the required fields:
     - App name: "Gmail MCP" (or your choice)
     - User support email: Your email
     - Developer contact: Your email
   - Add scopes:
     - Click "Add or Remove Scopes"
     - Add: `https://www.googleapis.com/auth/gmail.modify`
     - Add: `https://www.googleapis.com/auth/gmail.settings.basic`
   - Add test users:
     - Add your Gmail address
     - **Important**: Wait 2-3 minutes for test users to propagate

4. Create the OAuth client:
   - Application type: **Desktop app** (Important!)
   - Name: "Gmail MCP Client"
   - Click "Create"

5. Download the credentials:
   - Click the download button (⬇️) next to your new client
   - Save as `gcp-oauth.keys.json`

### 4. Place Credentials File

You have three options for placing the credentials file:

#### Option 1: Project Directory (Recommended for Development)
```bash
# Place in the Gmail MCP project root
cp /path/to/downloaded/credentials.json ./gcp-oauth.keys.json
```

#### Option 2: Shared Location (Recommended for Multiple MCP Servers)
```bash
# Use same credentials for both Calendar and Gmail MCP
export GOOGLE_OAUTH_CREDENTIALS="/path/to/gcp-oauth.keys.json"
```

#### Option 3: Gmail-Specific Location
```bash
# Gmail MCP specific
export GMAIL_OAUTH_CREDENTIALS="/path/to/gcp-oauth.keys.json"
```

### 5. Authenticate

Run the authentication flow:

```bash
npm run auth
```

This will:
1. Start a local authentication server
2. Open your browser to Google's OAuth page
3. After you authorize, save tokens to `~/.config/gmail-mcp/tokens.json`

## Required OAuth Scopes

The Gmail MCP server requires these scopes:

- `https://www.googleapis.com/auth/gmail.modify` - Read, compose, send, and permanently delete mail
- `https://www.googleapis.com/auth/gmail.settings.basic` - Manage basic mail settings

## Credential File Format

Your credentials file should look like this:

```json
{
  "installed": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "client_secret": "YOUR_CLIENT_SECRET",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "redirect_uris": ["http://localhost"]
  }
}
```

## Token Storage

Tokens are stored in `~/.config/gmail-mcp/tokens.json` and include:
- Access token (short-lived, ~1 hour)
- Refresh token (long-lived, used to get new access tokens)
- Expiry information

The server automatically refreshes access tokens as needed.

## Multi-Account Support

The Gmail MCP supports multiple accounts using the `GOOGLE_ACCOUNT_MODE` environment variable:

```bash
# Normal account (default)
export GOOGLE_ACCOUNT_MODE=normal
npm run auth

# Test account
export GOOGLE_ACCOUNT_MODE=test
npm run auth
```

Each account mode stores tokens separately in the same tokens.json file.

## Troubleshooting

### "Access blocked: This app's request is invalid"

**Cause**: OAuth consent screen not properly configured

**Solution**:
1. Go to OAuth consent screen settings
2. Add your email to test users
3. Wait 2-3 minutes for propagation
4. Try authentication again

### "Error: invalid_client"

**Cause**: Wrong client type or incorrect credentials

**Solution**:
1. Ensure OAuth client type is "Desktop app" (not Web application)
2. Re-download credentials file
3. Verify credentials file format matches example above

### "The port 3500 is already in use"

**Cause**: Another authentication server is running

**Solution**:
1. Kill any running auth servers
2. Or use a different port by modifying the auth server code
3. The server tries ports 3500-3505 automatically

### "ENOENT: no such file or directory"

**Cause**: Credentials file not found

**Solution**:
1. Verify `gcp-oauth.keys.json` exists
2. Check `GMAIL_OAUTH_CREDENTIALS` or `GOOGLE_OAUTH_CREDENTIALS` environment variable
3. Ensure file path is absolute

### Tokens Expired or Invalid

**Cause**: Refresh token revoked or expired

**Solution**:
```bash
# Clear tokens and re-authenticate
rm ~/.config/gmail-mcp/tokens.json
npm run auth
```

## Security Best Practices

1. **Never commit credentials to git**
   - Add `gcp-oauth.keys.json` to `.gitignore`
   - Keep tokens.json private

2. **Use test accounts for development**
   - Set `GOOGLE_ACCOUNT_MODE=test`
   - Use a dedicated test Gmail account

3. **Limit OAuth scope**
   - Only request scopes you need
   - Review scope permissions regularly

4. **Rotate credentials periodically**
   - Generate new OAuth credentials every 6-12 months
   - Remove old credentials from Cloud Console

5. **Monitor OAuth usage**
   - Check Google Cloud Console for unusual activity
   - Review authorized applications in Gmail settings

## Using with Docker

When running in Docker, mount the credentials file:

```bash
docker run -p 3001:3001 \
  -v ./gcp-oauth.keys.json:/app/gcp-oauth.keys.json:ro \
  -v gmail-tokens:/home/nodejs/.config/gmail-mcp \
  -e GMAIL_OAUTH_CREDENTIALS=/app/gcp-oauth.keys.json \
  gmail-mcp
```

For docker-compose, it's already configured:

```yaml
volumes:
  - ./gcp-oauth.keys.json:/app/gcp-oauth.keys.json:ro
  - gmail-tokens:/home/nodejs/.config/gmail-mcp
```

## Shared Credentials with Calendar MCP

You can use the same OAuth credentials for both Gmail and Calendar MCP servers. Just set the `GOOGLE_OAUTH_CREDENTIALS` environment variable, and both will use it:

```bash
export GOOGLE_OAUTH_CREDENTIALS="/path/to/shared/gcp-oauth.keys.json"
```

## Next Steps

After authentication is complete:
1. Start the server: `npm start`
2. Test with a client (Claude Desktop, curl, etc.)
3. See [README.md](../README.md) for available tools and usage

## Support

For issues:
- Check [Troubleshooting](#troubleshooting) section
- Review [Google's OAuth documentation](https://developers.google.com/identity/protocols/oauth2)
- Open an issue on GitHub
