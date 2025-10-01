#!/bin/bash

# SSL Certificate Troubleshooting Script
echo "🔍 SSL Certificate Troubleshooting for matrosmcp.duckdns.org"
echo "============================================================"

# 1. Check DNS resolution
echo "1. DNS Resolution Test:"
echo "   Google DNS (8.8.8.8):"
dig +short matrosmcp.duckdns.org @8.8.8.8
echo "   Cloudflare DNS (1.1.1.1):"
dig +short matrosmcp.duckdns.org @1.1.1.1 2>/dev/null || echo "   FAILED"
echo "   System DNS:"
dig +short matrosmcp.duckdns.org

# 2. Check firewall
echo -e "\n2. Firewall Status:"
sudo ufw status | grep 80

# 3. Test port binding
echo -e "\n3. Port 80 Binding Test:"
sudo python3 -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.bind(('0.0.0.0', 80))
    print('   ✅ Port 80 binding successful')
    s.close()
except Exception as e:
    print(f'   ❌ Port 80 binding failed: {e}')
"

# 4. Create temporary test server and test externally
echo -e "\n4. External Connectivity Test:"
echo "   Starting test server..."
sudo python3 -m http.server 80 --bind 0.0.0.0 > /dev/null 2>&1 &
SERVER_PID=$!
sleep 3

echo "   Testing from localhost..."
curl -I http://localhost 2>/dev/null | head -1 || echo "   ❌ Local test failed"

echo "   Testing external connectivity (this may take a moment)..."
timeout 10 curl -I http://matrosmcp.duckdns.org 2>/dev/null | head -1 || echo "   ❌ External test failed"

# Clean up
echo "   Stopping test server..."
sudo kill $SERVER_PID 2>/dev/null

echo -e "\n5. Attempting Let's Encrypt Certificate:"
echo "   This will take about 30 seconds..."
sudo certbot certonly --standalone -d matrosmcp.duckdns.org --email matros1975@gmail.com --agree-tos --non-interactive 2>&1 | grep -E "(SUCCESS|FAIL|Error|Certificate)"

echo -e "\n🔍 Diagnosis Complete!"
echo "If external connectivity test failed, check Oracle Cloud Security List."
echo "If Let's Encrypt failed, try again in 10-15 minutes for DNS propagation."