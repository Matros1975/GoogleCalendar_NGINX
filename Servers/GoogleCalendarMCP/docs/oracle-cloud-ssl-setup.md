## 🔧 Oracle Cloud Security List Configuration for Let's Encrypt

### Required Ingress Rule for Port 80:

**Navigate to Oracle Cloud Console:**
1. ☰ Menu → Networking → Virtual Cloud Networks
2. Click your VCN → Security Lists → Default Security List
3. Click "Add Ingress Rules"

**Required Configuration:**
```
Source Type: CIDR
Source CIDR: 0.0.0.0/0
IP Protocol: TCP
Source Port Range: (leave blank/All)
Destination Port Range: 80
Description: HTTP for Let's Encrypt SSL
```

**⚠️ Common Issues:**
- **Wrong Source CIDR**: Must be `0.0.0.0/0` not just your IP
- **Protocol**: Must be TCP, not ALL
- **Port Range**: Must be exactly `80`, not `80-80` or range
- **Applied to**: Default Security List for your subnet

### 🔍 Verification Steps:

1. **Check rule exists**:
   ```bash
   sudo ufw status | grep 80
   ```

2. **Test local binding**:
   ```bash
   sudo python3 -m http.server 80 --bind 0.0.0.0
   ```

3. **Test external access** (from another machine):
   ```bash
   curl -I http://matrosmcp.duckdns.org
   ```

### 🕒 DNS Propagation Issue

We detected DNS inconsistency:
- ✅ Google DNS (8.8.8.8): Works
- ❌ Cloudflare DNS (1.1.1.1): SERVFAIL

**Solution**: Wait 10-15 minutes for DNS to propagate globally, then retry.

### 🚀 Alternative: Self-Signed Certificate

If Let's Encrypt continues to fail, we can create a self-signed certificate for testing:

```bash
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/matrosmcp.key \
  -out /etc/ssl/certs/matrosmcp.crt \
  -subj "/CN=matrosmcp.duckdns.org"
```