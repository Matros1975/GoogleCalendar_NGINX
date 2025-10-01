# Let's Encrypt Quick Reference

## 🚀 Quick Recreation Commands

### One-liner Certificate Creation
```bash
cd /home/ubuntu/GoogleCalendar_NGINX && ./scripts/create-letsencrypt.sh
```

### Manual Step-by-Step (if script fails)
```bash
# 1. Ensure containers running
docker compose up -d

# 2. Create certificate
sudo certbot certonly --webroot --webroot-path=/var/www/certbot -d matrosmcp.duckdns.org --email matros1975@gmail.com --agree-tos --non-interactive

# 3. Update NGINX config
sudo sed -i 's|ssl_certificate.*|ssl_certificate /etc/letsencrypt/live/matrosmcp.duckdns.org/fullchain.pem;|g' nginx/conf.d/mcp-proxy.conf
sudo sed -i 's|ssl_certificate_key.*|ssl_certificate_key /etc/letsencrypt/live/matrosmcp.duckdns.org/privkey.pem;|g' nginx/conf.d/mcp-proxy.conf

# 4. Restart NGINX
docker compose restart nginx-proxy
```

## 🔧 Essential Commands

### Check Certificate Status
```bash
sudo certbot certificates
curl https://matrosmcp.duckdns.org/health
```

### Test Renewal
```bash
sudo certbot renew --dry-run
```

### Emergency Self-Signed Fallback
```bash
./scripts/ssl-manager.sh selfsigned
```

### View Logs
```bash
sudo tail -f /var/log/letsencrypt/letsencrypt.log
docker compose logs nginx-proxy
```

## 🚨 Prerequisites Checklist

- [ ] Oracle Cloud port 80 open
- [ ] UFW allows port 80: `sudo ufw allow 80/tcp`
- [ ] DuckDNS domain resolves: `dig matrosmcp.duckdns.org`
- [ ] Webroot exists: `sudo mkdir -p /var/www/certbot`
- [ ] NGINX config has webroot location block
- [ ] Docker compose includes letsencrypt volumes

## 📁 Key Files
```
Certificate: /etc/letsencrypt/live/matrosmcp.duckdns.org/fullchain.pem
Private Key: /etc/letsencrypt/live/matrosmcp.duckdns.org/privkey.pem
NGINX Config: nginx/conf.d/mcp-proxy.conf
Docker Compose: docker-compose.yml
Auto-Renewal: scripts/renew-certificate.sh
```