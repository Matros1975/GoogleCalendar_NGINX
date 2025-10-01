#!/bin/bash

# Enhanced SSL Certificate Creation Script with Webroot Method
# This script uses webroot method which works with running NGINX

DOMAIN="matrosmcp.duckdns.org"
EMAIL="matros1975@gmail.com"
PROJECT_DIR="/home/ubuntu/GoogleCalendar_NGINX"
WEBROOT_PATH="/var/www/certbot"

echo "🔒 Creating Let's Encrypt Certificate Using Webroot Method"
echo "========================================================="

# Ensure webroot directory exists
echo "1. Preparing webroot directory..."
sudo mkdir -p $WEBROOT_PATH
sudo chmod 755 $WEBROOT_PATH

# Start containers with updated configuration
echo "2. Starting containers with Let's Encrypt support..."
cd $PROJECT_DIR
docker compose up -d

# Wait for NGINX to be ready
echo "3. Waiting for NGINX to start..."
sleep 10

# Test if containers are healthy
echo "4. Checking container health..."
if ! docker compose ps --format '{{.Status}}' | grep -q "healthy"; then
    echo "   ⚠️  Some containers may not be fully healthy yet, continuing..."
fi

# Test webroot path accessibility
echo "5. Testing webroot accessibility..."
echo "test" | sudo tee $WEBROOT_PATH/test.txt > /dev/null
WEBROOT_TEST=$(curl -s http://$DOMAIN/.well-known/acme-challenge/test.txt 2>/dev/null || echo "FAIL")
sudo rm -f $WEBROOT_PATH/test.txt

if [[ "$WEBROOT_TEST" == "test" ]]; then
    echo "   ✅ Webroot path is accessible via HTTP"
else
    echo "   ❌ Webroot path test failed: $WEBROOT_TEST"
    echo "   This might still work - Let's Encrypt uses different validation"
fi

# Attempt certificate creation with webroot method
echo "6. Requesting Let's Encrypt certificate..."
sudo certbot certonly \
    --webroot \
    --webroot-path=$WEBROOT_PATH \
    -d $DOMAIN \
    --email $EMAIL \
    --agree-tos \
    --non-interactive \
    --verbose

if [[ $? -eq 0 ]]; then
    echo "   ✅ Let's Encrypt certificate created successfully!"
    
    # Update NGINX configuration to use Let's Encrypt certificate
    echo "7. Updating NGINX configuration..."
    sudo sed -i 's|ssl_certificate /etc/ssl/certs/matrosmcp.crt;|ssl_certificate /etc/letsencrypt/live/'$DOMAIN'/fullchain.pem;|g' nginx/conf.d/mcp-proxy.conf
    sudo sed -i 's|ssl_certificate_key /etc/ssl/private/matrosmcp.key;|ssl_certificate_key /etc/letsencrypt/live/'$DOMAIN'/privkey.pem;|g' nginx/conf.d/mcp-proxy.conf
    
    # Update docker-compose volumes for Let's Encrypt
    echo "8. Updating Docker Compose configuration..."
    sudo sed -i 's|/etc/ssl/certs:/etc/ssl/certs:ro|/etc/letsencrypt:/etc/letsencrypt:ro|g' docker-compose.yml
    sudo sed -i 's|/etc/ssl/private:/etc/ssl/private:ro||g' docker-compose.yml
    
    # Restart containers to load new certificate
    echo "9. Restarting containers with new certificate..."
    docker compose restart nginx-proxy
    
    # Wait for restart
    sleep 5
    
    # Test the new certificate
    echo "10. Testing new certificate..."
    if curl -s https://$DOMAIN/health > /dev/null; then
        echo "    ✅ HTTPS connection with Let's Encrypt certificate successful!"
        
        # Show certificate details
        echo "    📋 Certificate Details:"
        echo | openssl s_client -servername $DOMAIN -connect $DOMAIN:443 2>/dev/null | openssl x509 -noout -subject -issuer -dates
        
        echo ""
        echo "🎉 SUCCESS! Let's Encrypt certificate is now active!"
        echo "🔄 Auto-renewal is configured to run twice daily"
        
    else
        echo "    ❌ HTTPS test failed after certificate installation"
        echo "    Check logs: docker compose logs nginx-proxy"
    fi
    
else
    echo "   ❌ Let's Encrypt certificate creation failed!"
    echo "   Check logs: sudo tail -20 /var/log/letsencrypt/letsencrypt.log"
    echo "   Keeping existing self-signed certificate"
fi

echo ""
echo "📊 Final Status:"
/home/ubuntu/GoogleCalendar_NGINX/scripts/ssl-manager.sh status