# Oracle Cloud Infrastructure Firewall Configuration

## Security Rules Configuration

### 1. Oracle Cloud Security Lists (VCN Level)

Add these rules to your VCN's Security List:

#### Ingress Rules
```
Source: 0.0.0.0/0
Protocol: TCP
Port: 80
Description: HTTP (for Let's Encrypt challenges)
```

```
Source: 0.0.0.0/0  
Protocol: TCP
Port: 443
Description: HTTPS (secure MCP API access)
```

```
Source: YOUR_IP/32
Protocol: TCP  
Port: 22
Description: SSH access (replace YOUR_IP with your management IP)
```

#### Egress Rules
```
Destination: 0.0.0.0/0
Protocol: All
Description: Allow all outbound traffic
```

### 2. Oracle Linux Firewall Configuration

Run these commands on your Oracle VM:

```bash
# Check firewall status
sudo firewall-cmd --state

# Add HTTP and HTTPS services
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https

# Or add specific ports
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp

# Reload firewall
sudo firewall-cmd --reload

# Verify rules
sudo firewall-cmd --list-all
```

### 3. iptables Alternative (if not using firewalld)

```bash
# Allow HTTP
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT

# Allow HTTPS  
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Save rules (Oracle Linux)
sudo service iptables save
```

### 4. Security Recommendations

1. **Restrict SSH Access**: Only allow SSH from your management IPs
2. **Disable Root Login**: Use sudo with regular user accounts
3. **Keep System Updated**: Regular security updates
4. **Monitor Logs**: Set up log monitoring for security events
5. **Use Strong Bearer Tokens**: 32+ character random tokens
6. **Regular Token Rotation**: Rotate API tokens periodically

### 5. Monitoring and Logging

Enable logging for security analysis:

```bash
# Enable audit logging
sudo systemctl enable auditd
sudo systemctl start auditd

# Monitor failed authentication attempts
sudo tail -f /var/log/secure

# Monitor NGINX access logs
docker-compose -f docker-compose.production.yml logs -f nginx-proxy
```

### 6. SSL/TLS Security

For production deployments:

1. Use Let's Encrypt certificates (auto-renewal)
2. Implement HSTS headers (already configured in NGINX)
3. Use strong TLS ciphers (configured in NGINX)
4. Regular certificate monitoring

### 7. Network Security Groups (if using OCI)

Alternative to Security Lists, configure Network Security Groups:

1. Create NSG for web tier
2. Add rules for ports 80, 443
3. Attach NSG to VM instance
4. Monitor traffic patterns