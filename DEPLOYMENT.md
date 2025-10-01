# Secure Google Calendar MCP Deployment on Oracle VM

This guide provides a complete setup for deploying the Google Calendar MCP server on Oracle Cloud Infrastructure with NGINX proxy, SSL termination, and bearer token authentication.

## Architecture Overview

```
Internet → NGINX Proxy (SSL/TLS) → Internal Docker Network → MCP Container
           ↓
        OAuth + Bearer Token
        Authentication
```

## Security Features

- ✅ **NGINX Reverse Proxy**: SSL termination and security headers
- ✅ **Bearer Token Authentication**: API access control
- ✅ **Internal Docker Network**: MCP container not exposed to internet
- ✅ **SSL/TLS Encryption**: HTTPS only with modern ciphers
- ✅ **Rate Limiting**: Prevent abuse and DoS attacks
- ✅ **Security Headers**: XSS, CSRF, and clickjacking protection
- ✅ **OAuth Flow Protection**: Separate endpoint handling
- ✅ **Request Size Limiting**: Prevent payload attacks

## Prerequisites

1. Oracle Cloud VM instance (Ubuntu/Oracle Linux)
2. Docker and Docker Compose installed
3. Domain name pointing to your VM (for SSL certificates)
4. Google OAuth credentials (JSON file)

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/nspady/google-calendar-mcp.git
cd google-calendar-mcp

# Copy your Google OAuth credentials
cp /path/to/your/gcp-oauth.keys.json ./gcp-oauth.keys.json

# Run the automated setup
./setup-oracle-vm.sh
```

The setup script will:
- Check prerequisites
- Generate secure bearer tokens
- Configure SSL certificates
- Build and start services
- Setup OAuth authentication

### 2. Manual Configuration (Alternative)

If you prefer manual setup:

```bash
# 1. Create production environment
cp .env.production .env

# 2. Generate bearer tokens
./manage-tokens.sh generate
./manage-tokens.sh add <your-token>

# 3. Setup SSL certificates (see SSL section below)

# 4. Update domain in NGINX config
sed -i 's/your-domain.com/actual-domain.com/' Servers/NGINX/conf.d/mcp-proxy.conf

# 5. Start services
docker compose up -d

# 6. Authenticate with Google
docker compose exec calendar-mcp npm run auth
```

## SSL Certificate Setup

### Option 1: Let's Encrypt (Recommended)

```bash
# Install certbot
sudo yum install certbot -y  # Oracle Linux
# or
sudo apt install certbot -y  # Ubuntu

# Get certificates
sudo certbot certonly --standalone -d your-domain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem Servers/NGINX/ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem Servers/NGINX/ssl/key.pem
sudo chown $USER:$USER Servers/NGINX/ssl/*.pem

# Setup auto-renewal
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
```

### Option 2: Self-Signed (Development)

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout Servers/NGINX/ssl/key.pem \
    -out Servers/NGINX/ssl/cert.pem \
    -subj "/C=US/ST=State/L=City/O=MCP/OU=Calendar/CN=your-domain.com"
```

## Bearer Token Management

### Generate New Tokens

```bash
# Generate and add a new token
./manage-tokens.sh add

# Generate without adding
./manage-tokens.sh generate
```

### View Current Tokens

```bash
./manage-tokens.sh show
```

### Test Token

```bash
./manage-tokens.sh test <your-token> https://your-domain.com/health
```

### Rotate All Tokens

```bash
./manage-tokens.sh rotate
```

## API Usage

### Health Check (No Authentication)

```bash
curl https://your-domain.com/health
```

### Authenticated Requests

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

## Security Configuration

### Firewall Setup

See [Oracle Cloud Firewall Configuration](docs/oracle-cloud-firewall.md) for detailed firewall rules.

### Environment Variables

Key security settings in `.env.production`:

```bash
# Bearer tokens (comma-separated)
BEARER_TOKENS=token1,token2,token3

# Allowed origins (optional, for additional security)
ALLOWED_ORIGINS=https://your-domain.com,https://app.your-domain.com

# Disable debug mode
DEBUG=false
NODE_ENV=production
```

## Monitoring and Logs

### View Service Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f nginx-proxy
docker compose logs -f calendar-mcp
```

### NGINX Access Logs

```bash
# Real-time access logs
docker compose exec nginx-proxy tail -f /var/log/nginx/access.log

# Error logs
docker compose exec nginx-proxy tail -f /var/log/nginx/error.log
```

### Health Monitoring

```bash
# Check service health
docker compose ps

# Test endpoints
curl -k https://localhost/health
```

## Maintenance

### Update Services

```bash
# Pull latest images
docker compose pull

# Rebuild and restart
docker compose up -d --build
```

### Backup Configuration

```bash
# Backup important files
tar -czf mcp-backup-$(date +%Y%m%d).tar.gz \
    .env.production \
    Servers/NGINX/ssl/ \
    gcp-oauth.keys.json \
    docker-compose.production.yml
```

### Restart Services

```bash
# Restart all services
docker compose restart

# Restart specific service
docker compose restart nginx-proxy
```

## Troubleshooting

### Common Issues

1. **SSL Certificate Errors**
   ```bash
   # Check certificate validity
   openssl x509 -in Servers/NGINX/ssl/cert.pem -text -noout
   
   # Test SSL
   openssl s_client -connect your-domain.com:443
   ```

2. **Authentication Failures**
   ```bash
   # Check OAuth credentials
   docker compose exec calendar-mcp cat /app/gcp-oauth.keys.json
   
   # Re-authenticate
   docker compose exec calendar-mcp npm run auth
   ```

3. **Network Issues**
   ```bash
   # Check internal connectivity
   docker compose exec nginx-proxy curl http://calendar-mcp:3000/health
   
   # Check external access
   curl -k https://localhost/health
   ```

4. **Token Issues**
   ```bash
   # Test token validity
   ./manage-tokens.sh test <your-token>
   
   # Check token configuration
   grep BEARER_TOKENS .env.production
   ```

### Log Analysis

```bash
# NGINX authentication logs
docker compose logs nginx-proxy | grep "auth_result"

# MCP service errors
docker compose logs calendar-mcp | grep -i error

# System resource usage
docker stats
```

## Production Checklist

- [ ] SSL certificates configured and valid
- [ ] Firewall rules properly configured
- [ ] Bearer tokens generated and stored securely
- [ ] OAuth authentication completed
- [ ] Health checks passing
- [ ] Log monitoring configured
- [ ] Backup procedures in place
- [ ] Domain DNS configured
- [ ] Rate limiting tested
- [ ] Security headers verified

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review logs for error messages
3. Verify network connectivity and firewall rules
4. Test individual components (OAuth, SSL, tokens)
5. Consult the original project documentation