# Let's Encrypt SSL Certificate Setup Guide

## 📋 Complete Procedure to Create Let's Encrypt Certificate for matrosmcp.duckdns.org

### Prerequisites

1. **Domain Setup**: DuckDNS domain `matrosmcp.duckdns.org` pointing to server IP
2. **Oracle Cloud**: Port 80 and 443 open in Security Lists
3. **Ubuntu Server**: With Docker and Docker Compose installed
4. **Project**: GoogleCalendar_NGINX repository deployed

### 🚀 Step-by-Step Procedure

#### Step 1: Install Certbot
```bash
sudo apt update
sudo apt install -y certbot cron
```

#### Step 2: Configure Oracle Cloud Firewall
**In Oracle Cloud Console:**
1. Navigate to: ☰ → Networking → Virtual Cloud Networks
2. Select your VCN → Security Lists → Default Security List
3. Add Ingress Rule:
   ```
   Source Type: CIDR
   Source CIDR: 0.0.0.0/0
   IP Protocol: TCP
   Destination Port Range: 80
   Description: HTTP for Let's Encrypt SSL
   ```

#### Step 3: Configure UFW Firewall
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw status
```

#### Step 4: Prepare NGINX Configuration
Edit `/home/ubuntu/GoogleCalendar_NGINX/nginx/conf.d/mcp-proxy.conf`:

**Add Let's Encrypt webroot support:**
```nginx
# Let's Encrypt challenge path (allow HTTP)
location ^~ /.well-known/acme-challenge/ {
    default_type "text/plain";
    root /var/www/certbot;
    allow all;
}

# Redirect HTTP to HTTPS (except Let's Encrypt challenges)  
if ($scheme != "https") {
    return 301 https://$server_name$request_uri;
}
```

#### Step 5: Create Webroot Directory
```bash
sudo mkdir -p /var/www/certbot
sudo chmod 755 /var/www/certbot
```

#### Step 6: Update Docker Compose Configuration
Edit `/home/ubuntu/GoogleCalendar_NGINX/docker-compose.yml`:

**Add webroot volume to nginx-proxy service:**
```yaml
volumes:
  - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
  - ./nginx/conf.d:/etc/nginx/conf.d:ro
  - /etc/letsencrypt:/etc/letsencrypt:ro  # Let's Encrypt certificates
  - /var/www/certbot:/var/www/certbot:ro  # Let's Encrypt webroot
  - ./nginx/auth:/etc/nginx/auth:ro
  - nginx-logs:/var/log/nginx
```

#### Step 7: Start Containers for Certificate Creation
```bash
cd /home/ubuntu/GoogleCalendar_NGINX
docker compose up -d
sleep 10  # Wait for NGINX to start
```

#### Step 8: Create Let's Encrypt Certificate
```bash
sudo certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    -d matrosmcp.duckdns.org \
    --email matros1975@gmail.com \
    --agree-tos \
    --non-interactive \
    --verbose
```

**Expected Output:**
```
Successfully received certificate.
Certificate is saved at: /etc/letsencrypt/live/matrosmcp.duckdns.org/fullchain.pem
Key is saved at:         /etc/letsencrypt/live/matrosmcp.duckdns.org/privkey.pem
This certificate expires on [DATE].
```

#### Step 9: Update NGINX to Use Let's Encrypt Certificate
Edit `/home/ubuntu/GoogleCalendar_NGINX/nginx/conf.d/mcp-proxy.conf`:
```nginx
# SSL Configuration - Using Let's Encrypt certificate
ssl_certificate /etc/letsencrypt/live/matrosmcp.duckdns.org/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/matrosmcp.duckdns.org/privkey.pem;
```

#### Step 10: Restart Containers
```bash
docker compose restart nginx-proxy
sleep 10
```

#### Step 11: Verify Certificate Installation
```bash
# Test HTTPS without -k flag (should work with trusted certificate)
curl https://matrosmcp.duckdns.org/health

# Check certificate details
echo | openssl s_client -servername matrosmcp.duckdns.org -connect matrosmcp.duckdns.org:443 2>/dev/null | openssl x509 -noout -subject -issuer -dates

# List all certificates
sudo certbot certificates
```

### 🔄 Auto-Renewal Setup

#### Step 12: Create Renewal Script
Create `/home/ubuntu/GoogleCalendar_NGINX/scripts/renew-certificate.sh`:
```bash
#!/bin/bash
LOGFILE="/var/log/letsencrypt-renewal.log"
DOMAIN="matrosmcp.duckdns.org"

echo "[$(date)] Starting certificate renewal check for $DOMAIN" >> $LOGFILE

sudo certbot renew --quiet --no-self-upgrade >> $LOGFILE 2>&1

if [ $? -eq 0 ]; then
    echo "[$(date)] Certificate renewal check completed successfully" >> $LOGFILE
    
    CERT_FILE="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
    if [ -f "$CERT_FILE" ]; then
        if [ $(find "$CERT_FILE" -mmin -60 | wc -l) -gt 0 ]; then
            echo "[$(date)] Certificate was renewed, restarting containers..." >> $LOGFILE
            cd /home/ubuntu/GoogleCalendar_NGINX
            docker compose restart nginx-proxy
            echo "[$(date)] NGINX container restarted" >> $LOGFILE
        fi
    fi
else
    echo "[$(date)] Certificate renewal failed!" >> $LOGFILE
fi
```

#### Step 13: Setup Cron Jobs
```bash
chmod +x /home/ubuntu/GoogleCalendar_NGINX/scripts/renew-certificate.sh

# Create crontab file
cat > /tmp/ssl-crontab << EOF
# Let's Encrypt Certificate Auto-Renewal
# Runs twice daily at 3:30 AM and 3:30 PM
30 3,15 * * * /home/ubuntu/GoogleCalendar_NGINX/scripts/renew-certificate.sh

# Weekly certificate check and log cleanup (Sundays at 4:00 AM)
0 4 * * 0 find /var/log/letsencrypt-renewal.log -mtime +30 -delete 2>/dev/null || true

EOF

# Install crontab
sudo crontab /tmp/ssl-crontab
```

### 🧪 Testing and Verification

#### Test Certificate
```bash
# Health check with trusted certificate
curl https://matrosmcp.duckdns.org/health

# Test with API (replace YOUR_TOKEN)
curl -H "Authorization: Bearer YOUR_TOKEN" https://matrosmcp.duckdns.org/mcp/v1/tools/list

# Verify certificate chain
openssl s_client -servername matrosmcp.duckdns.org -connect matrosmcp.duckdns.org:443 -verify_return_error
```

#### Test Auto-Renewal
```bash
# Dry run renewal
sudo certbot renew --dry-run

# Check renewal logs
sudo tail -f /var/log/letsencrypt-renewal.log

# Check cron jobs
sudo crontab -l
```

### 🚨 Troubleshooting

#### Common Issues and Solutions

**1. "connection refused" or "no route to host"**
- Check Oracle Cloud Security List has port 80 open
- Verify UFW firewall: `sudo ufw status`
- Test: `curl -I http://matrosmcp.duckdns.org`

**2. "DNS problem: SERVFAIL"**
- Wait 10-15 minutes for DNS propagation
- Test DNS: `dig matrosmcp.duckdns.org @8.8.8.8`

**3. "too many failed authorizations"**
- Wait 1 hour before retrying (Let's Encrypt rate limit)
- Check: `sudo tail /var/log/letsencrypt/letsencrypt.log`

**4. NGINX fails to start after certificate**
- Check certificate paths exist:
  ```bash
  sudo ls -la /etc/letsencrypt/live/matrosmcp.duckdns.org/
  ```
- Check container logs: `docker compose logs nginx-proxy`

**5. Docker Compose validation errors**
- Verify YAML syntax with proper indentation
- Check volume mounts don't have empty entries

### 📁 Important File Locations

```
Certificates:
├── /etc/letsencrypt/live/matrosmcp.duckdns.org/
│   ├── fullchain.pem (certificate + chain)
│   ├── privkey.pem (private key)
│   ├── cert.pem (certificate only)
│   └── chain.pem (chain only)
│
Scripts:
├── /home/ubuntu/GoogleCalendar_NGINX/scripts/
│   ├── renew-certificate.sh (auto-renewal)
│   ├── ssl-manager.sh (management tool)
│   └── create-letsencrypt.sh (creation helper)
│
Logs:
├── /var/log/letsencrypt/letsencrypt.log
├── /var/log/letsencrypt-renewal.log
└── docker compose logs nginx-proxy
```

### 🔄 Certificate Renewal Information

- **Certificate Validity**: 90 days
- **Auto-Renewal**: 30 days before expiration
- **Renewal Schedule**: Twice daily (3:30 AM/PM)
- **Renewal Method**: Webroot authentication
- **Post-Renewal**: Automatic NGINX restart

### 📞 Emergency Recovery

If certificate expires or becomes invalid:

1. **Quick fix with self-signed:**
   ```bash
   ./scripts/ssl-manager.sh selfsigned
   ```

2. **Recreate Let's Encrypt:**
   ```bash
   sudo rm -rf /etc/letsencrypt/live/matrosmcp.duckdns.org/
   sudo rm -rf /etc/letsencrypt/archive/matrosmcp.duckdns.org/
   # Then follow steps 7-11 above
   ```

3. **Debug mode:**
   ```bash
   sudo certbot certonly --webroot --webroot-path=/var/www/certbot -d matrosmcp.duckdns.org --dry-run --verbose
   ```

---

## 📝 Creation History

**Created**: October 1, 2025  
**Domain**: matrosmcp.duckdns.org  
**Method**: Webroot authentication via NGINX  
**Auto-Renewal**: Configured and tested  
**Status**: Production ready with trusted certificate  

This procedure was successfully tested and is known to work with Oracle Cloud Infrastructure and DuckDNS.