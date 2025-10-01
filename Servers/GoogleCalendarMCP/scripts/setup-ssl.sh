#!/bin/bash

# SSL Certificate Setup Script
# This script will test connectivity and create Let's Encrypt certificate

echo "🔒 SSL Certificate Setup for matrosmcp.duckdns.org"
echo "================================================="

# Test if port 80 is reachable externally
echo "1. Testing external connectivity on port 80..."
timeout 10 curl -I http://matrosmcp.duckdns.org 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Port 80 is accessible externally"
else
    echo "❌ Port 80 is not accessible externally"
    echo "   Please open port 80 in Oracle Cloud Security List first!"
    exit 1
fi

# Create the certificate
echo "2. Creating SSL certificate..."
sudo certbot certonly \
    --standalone \
    -d matrosmcp.duckdns.org \
    --email matros1975@gmail.com \
    --agree-tos \
    --non-interactive

if [ $? -eq 0 ]; then
    echo "✅ SSL Certificate created successfully!"
    echo "📁 Certificate location: /etc/letsencrypt/live/matrosmcp.duckdns.org/"
    
    # List certificate files
    echo "📋 Certificate files:"
    sudo ls -la /etc/letsencrypt/live/matrosmcp.duckdns.org/
    
    # Close port 80 after certificate creation (optional)
    echo "3. Closing port 80 (no longer needed)..."
    sudo ufw delete allow 80/tcp
    echo "✅ Port 80 closed in UFW"
    
else
    echo "❌ Certificate creation failed!"
    exit 1
fi

echo "🎉 SSL setup complete! Ready to update NGINX configuration."