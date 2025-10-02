# Migration Guide: Centralized .env Configuration

## Overview

This guide helps you migrate from the legacy `.env.production` configuration to the new centralized `.env` configuration that consolidates all MCP server settings in one place.

## What Changed?

### Before (Legacy)
- Configuration in `.env.production` with limited settings
- Some environment variables hardcoded in `docker-compose.yml`
- Separate configuration files for different services

### After (New)
- Single `.env` file for all configuration
- Comprehensive `.env.template` with documentation
- All environment variables centralized and documented
- Backward compatibility maintained

## Migration Steps

### 1. Backup Your Current Configuration

```bash
# Backup existing configuration
cp .env.production .env.production.backup
```

### 2. Create New Configuration from Template

```bash
# Copy the template
cp .env.template .env
```

### 3. Migrate Your Settings

Transfer your existing settings to the new `.env` file:

#### Bearer Token Migration

**Old format in `.env.production`:**
```bash
BEARER_TOKENS=token1,token2
```

**New format in `.env`:**
```bash
MCP_BEARER_TOKEN=token1
```

Note: The new format uses a single primary token. If you had multiple tokens, choose your primary token or generate a new one:
```bash
# Generate a new secure token
openssl rand -hex 32
```

#### Google Calendar MCP Settings

**Old format (some in `.env.production`, some in `docker-compose.yml`):**
```bash
TRANSPORT=http
HOST=0.0.0.0
PORT=3000
GOOGLE_OAUTH_CREDENTIALS=/app/gcp-oauth.keys.json
```

**New format in `.env` (same variables, but all in one place):**
```bash
MCP_TRANSPORT=http
GOOGLE_MCP_HOST=0.0.0.0
GOOGLE_MCP_PORT=3000
GOOGLE_OAUTH_CREDENTIALS=/app/gcp-oauth.keys.json
GOOGLE_ACCOUNT_MODE=normal
```

#### TopDesk MCP Settings

**Add to `.env`:**
```bash
TOPDESK_URL=https://yourcompany.topdesk.net
TOPDESK_USERNAME=your_username
TOPDESK_PASSWORD=your_api_token
TOPDESK_MCP_TRANSPORT=streamable-http
TOPDESK_MCP_HOST=0.0.0.0
TOPDESK_MCP_PORT=3030
```

#### DuckDNS and SSL Settings

**If you have these in your old configuration, add them:**
```bash
DUCKDNS_DOMAIN=your-domain
DUCKDNS_TOKEN=your-token
DOMAIN=your-domain.duckdns.org
TZ=Europe/Amsterdam
CERT_EXPIRY_DAYS=30
```

### 4. Review and Complete Configuration

Open `.env` and:
1. Verify all your settings are correct
2. Add any missing required values
3. Review optional settings and configure as needed
4. Ensure sensitive values are properly set

### 5. Test Configuration

```bash
# Validate docker-compose configuration
docker compose config --quiet

# If successful, you'll see no output
# If there are errors, they will be displayed
```

### 6. Restart Services

```bash
# Stop current services
docker compose down

# Start with new configuration
docker compose up -d

# Check service status
docker compose ps

# View logs
docker compose logs -f
```

### 7. Verify Services

```bash
# Test health endpoint
curl -k https://localhost/health

# Test MCP with bearer token
curl -k -H "Authorization: Bearer YOUR_TOKEN" https://localhost/health

# Check Google Calendar MCP
docker compose logs calendar-mcp

# Check TopDesk MCP
docker compose logs topdesk-mcp
```

## Backward Compatibility

### Scripts Support Both Formats

All management scripts support both `.env` and `.env.production`:

```bash
# Token management works with both
./manage-tokens.sh show

# Setup script migrates automatically
./setup-oracle-vm.sh
```

### Keeping .env.production (Optional)

You can keep your `.env.production` file as a backup, but it won't be used if `.env` exists. The system prioritizes:
1. `.env` (new format)
2. `.env.production` (legacy format)

## Troubleshooting

### Issue: Services won't start

**Check:**
```bash
# Verify .env file exists
ls -la .env

# Validate configuration
docker compose config --quiet

# Check for syntax errors
cat .env | grep -v "^#" | grep -v "^$"
```

### Issue: Environment variables not loading

**Solution:**
```bash
# Ensure .env is in the project root
pwd
ls .env

# Check docker-compose.yml references .env
grep "env_file" docker-compose.yml
```

### Issue: Token authentication fails

**Solution:**
```bash
# Verify token in .env
grep MCP_BEARER_TOKEN .env

# Test token with manage-tokens.sh
./manage-tokens.sh show

# Generate new token if needed
./manage-tokens.sh generate
```

### Issue: Google OAuth not working

**Check:**
```bash
# Verify OAuth credentials path
grep GOOGLE_OAUTH_CREDENTIALS .env

# Check file exists and is mounted
ls -la gcp-oauth.keys.json

# Re-run OAuth flow if needed
docker compose exec calendar-mcp npm run auth
```

## Configuration Reference

See `.env.template` for complete documentation of all available configuration options.

### Required Settings

Minimum configuration for basic operation:

```bash
# Shared
NODE_ENV=production
MCP_BEARER_TOKEN=your-secure-token

# Google Calendar MCP
GOOGLE_OAUTH_CREDENTIALS=/app/gcp-oauth.keys.json
GOOGLE_MCP_HOST=0.0.0.0
GOOGLE_MCP_PORT=3000

# TopDesk MCP
TOPDESK_URL=https://yourcompany.topdesk.net
TOPDESK_USERNAME=your_username
TOPDESK_PASSWORD=your_api_token
```

## Rolling Back

If you need to roll back to the old configuration:

```bash
# Stop services
docker compose down

# Restore backup
mv .env.production.backup .env.production

# Remove new .env
rm .env

# Checkout previous docker-compose.yml version
git checkout HEAD~1 docker-compose.yml

# Restart services
docker compose up -d
```

## Getting Help

If you encounter issues:
1. Check the logs: `docker compose logs`
2. Validate configuration: `docker compose config`
3. Review `.env.template` for correct format
4. Check AGENTS.md for service-specific requirements
5. Open an issue with error details

## Benefits of New Configuration

✅ **Single source of truth** - All settings in one place  
✅ **Better documentation** - Comprehensive comments in `.env.template`  
✅ **Easier maintenance** - Update one file instead of multiple locations  
✅ **Consistent patterns** - All services follow same configuration style  
✅ **Better defaults** - Sensible fallback values for optional settings  
✅ **Git-safe** - Clear separation between template and actual configuration  

---

**Note:** This migration maintains full backward compatibility. Existing deployments continue to work during transition.
