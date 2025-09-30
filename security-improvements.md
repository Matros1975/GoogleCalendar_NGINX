# Security Improvements for MCP Calendar Server

## 1. CRITICAL: Enhanced Client Authentication

### Current Issue
- Bearer tokens provide unlimited access to personal calendar
- No client identification or IP restrictions
- Tokens don't expire

### Recommended Solutions

#### A. IP Allowlisting
```nginx
# Add to nginx config
geo $allowed_client {
    default 0;
    192.168.1.100/32 1;  # Your trusted IP
    10.0.0.0/8 1;        # Internal networks
    # Add specific client IPs
}

server {
    # In main location block
    if ($allowed_client = 0) {
        return 403 '{"error":"IP not allowed"}';
    }
}
```

#### B. Client Certificates (Mutual TLS)
```nginx
# Add client certificate authentication
ssl_client_certificate /etc/nginx/ssl/ca.crt;
ssl_verify_client on;
ssl_verify_depth 2;

# In location block
if ($ssl_client_verify != SUCCESS) {
    return 403 '{"error":"Client certificate required"}';
}
```

#### C. JWT-based Authentication with Expiry
```typescript
// Replace simple bearer tokens with JWT
interface JWTPayload {
  clientId: string;
  allowedIPs: string[];
  permissions: string[];
  exp: number;  // Expiry timestamp
}
```

## 2. Token Management Improvements

### A. Token Rotation
```bash
# Script to rotate bearer tokens
#!/bin/bash
NEW_TOKEN=$(openssl rand -hex 32)
echo "New token: $NEW_TOKEN"
# Update .env.production and restart containers
```

### B. Token Scoping
```typescript
interface TokenPermissions {
  readCalendars: boolean;
  createEvents: boolean;
  deleteEvents: boolean;
  calendars: string[];  // Specific calendar IDs only
}
```

## 3. Enhanced Monitoring & Logging

### A. Failed Authentication Alerts
```nginx
# Log failed auth attempts
log_format security '$remote_addr - $remote_user [$time_local] '
                   '"$request" $status $body_bytes_sent '
                   '"$http_referer" "$http_user_agent" '
                   'auth_result="$auth_result" '
                   'client_cert="$ssl_client_s_dn"';
```

### B. Real-time Monitoring
```bash
# Monitor for suspicious activity
tail -f /var/log/nginx/access.log | grep "auth_result=\"invalid\""
```

## 4. Additional Security Layers

### A. Fail2Ban Integration
```ini
# /etc/fail2ban/jail.local
[nginx-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/access.log
maxretry = 3
bantime = 3600
findtime = 600
filter = nginx-auth
```

### B. Geolocation Blocking
```nginx
# Block unexpected countries
map $geoip_country_code $allowed_country {
    default 0;
    US 1;
    CA 1;
    # Add your expected countries
}
```

## 5. Infrastructure Security

### A. VPN-Only Access
- Deploy behind VPN/VPC
- Only allow access through secured tunnels
- Use Wireguard or similar

### B. Let's Encrypt Automation
```bash
# Replace self-signed certificates
certbot --nginx -d your-domain.com
```

## 6. Container Security Hardening

### A. Security Scanning
```bash
# Scan for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image googlecalendar_nginx-calendar-mcp
```

### B. Minimal Base Images
```dockerfile
# Use distroless or alpine-based images
FROM node:18-alpine
# Or even better:
FROM gcr.io/distroless/nodejs18-debian11
```

## Priority Implementation Order

1. **IMMEDIATE**: IP allowlisting
2. **SHORT-TERM**: JWT tokens with expiry
3. **MEDIUM-TERM**: Client certificates
4. **LONG-TERM**: VPN deployment

## Risk Assessment

| Risk | Current | With Improvements |
|------|---------|------------------|
| Unauthorized Access | HIGH | LOW |
| Token Theft | HIGH | MEDIUM |
| Data Breach | MEDIUM | LOW |
| DoS Attacks | LOW | VERY LOW |