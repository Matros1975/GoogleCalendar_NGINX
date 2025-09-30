# Configuration Migration Summary

This document summarizes the changes made to make the production configuration primary.

## Changes Made

### File Restructuring
- `docker-compose.production.yml` → `docker-compose.yml` (now primary)
- `docker-compose.yml` → `docker-compose.dev.yml` (development/Claude Desktop)
- Created `.env` file for development mode

### Container Names Simplified
- `calendar-mcp-prod` → `calendar-mcp`
- `nginx-mcp-proxy` → `nginx-proxy`

### Updated References
- All documentation now uses `docker compose` (no -f flag needed for production)
- NGINX configuration updated to point to `calendar-mcp:3000`
- All management scripts updated

## Usage

### Production Deployment (Primary)
```bash
# Quick start (production)
docker compose up -d
docker compose exec calendar-mcp npm run auth
```

### Development/Claude Desktop
```bash
# Development mode
docker compose -f docker-compose.dev.yml up -d
docker compose -f docker-compose.dev.yml exec calendar-mcp npm run auth
```

### Benefits
1. **Simplified commands**: No need for `-f` flags in production
2. **Clear separation**: Production vs development configs
3. **Consistent naming**: Container names match service purpose
4. **Better defaults**: Production-ready by default

## Files Updated
- `docker-compose.yml` (new primary, renamed from production)
- `docker-compose.dev.yml` (renamed from docker-compose.yml)
- `nginx/conf.d/mcp-proxy.conf`
- `README.md`
- `DEPLOYMENT.md`
- `setup-oracle-vm.sh`
- `docs/docker.md`
- `.env` (created for development)