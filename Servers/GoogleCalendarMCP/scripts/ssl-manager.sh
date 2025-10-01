#!/bin/bash

# SSL Certificate Management Script
# Manages both self-signed and Let's Encrypt certificates for matrosmcp.duckdns.org

DOMAIN="matrosmcp.duckdns.org"
EMAIL="matros1975@gmail.com"
PROJECT_DIR="/home/ubuntu/GoogleCalendar_NGINX"

echo "🔒 SSL Certificate Management for $DOMAIN"
echo "=========================================="

function show_status() {
    echo -e "\n📊 Current SSL Status:"
    
    # Check certificate type
    if [[ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]]; then
        echo "   📋 Certificate Type: Let's Encrypt (Trusted)"
        echo "   📁 Certificate Path: /etc/letsencrypt/live/$DOMAIN/"
        echo "   📅 Expires: $(sudo openssl x509 -enddate -noout -in /etc/letsencrypt/live/$DOMAIN/fullchain.pem | cut -d= -f2)"
    elif [[ -f "/etc/ssl/certs/matrosmcp.crt" ]]; then
        echo "   📋 Certificate Type: Self-Signed (Testing Only)"
        echo "   📁 Certificate Path: /etc/ssl/certs/matrosmcp.crt"
        echo "   📅 Expires: $(sudo openssl x509 -enddate -noout -in /etc/ssl/certs/matrosmcp.crt | cut -d= -f2)"
    else
        echo "   ❌ No SSL certificate found!"
        return 1
    fi
    
    # Check NGINX configuration
    echo "   🌐 NGINX Status: $(docker compose ps nginx-proxy --format '{{.Status}}')"
    
    # Test HTTPS connectivity
    echo -e "\n🔍 Connectivity Test:"
    if curl -k -s https://$DOMAIN/health > /dev/null; then
        echo "   ✅ HTTPS connection successful"
    else
        echo "   ❌ HTTPS connection failed"
    fi
}

function create_letsencrypt() {
    echo -e "\n🚀 Creating Let's Encrypt Certificate..."
    
    # Stop containers to free port 80
    echo "   Stopping containers..."
    cd $PROJECT_DIR
    docker compose down
    
    # Attempt certificate creation
    echo "   Requesting certificate from Let's Encrypt..."
    sudo certbot certonly \
        --standalone \
        -d $DOMAIN \
        --email $EMAIL \
        --agree-tos \
        --non-interactive
    
    if [[ $? -eq 0 ]]; then
        echo "   ✅ Let's Encrypt certificate created successfully!"
        
        # Update NGINX configuration
        echo "   Updating NGINX configuration..."
        sudo sed -i 's|ssl_certificate /etc/ssl/certs/matrosmcp.crt;|ssl_certificate /etc/letsencrypt/live/'$DOMAIN'/fullchain.pem;|g' nginx/conf.d/mcp-proxy.conf
        sudo sed -i 's|ssl_certificate_key /etc/ssl/private/matrosmcp.key;|ssl_certificate_key /etc/letsencrypt/live/'$DOMAIN'/privkey.pem;|g' nginx/conf.d/mcp-proxy.conf
        
        # Update docker-compose volumes
        sudo sed -i 's|/etc/ssl/certs:/etc/ssl/certs:ro|/etc/letsencrypt:/etc/letsencrypt:ro|g' docker-compose.yml
        sudo sed -i 's|/etc/ssl/private:/etc/ssl/private:ro||g' docker-compose.yml
        
        echo "   ✅ Configuration updated for Let's Encrypt"
    else
        echo "   ❌ Let's Encrypt certificate creation failed!"
        echo "   Using self-signed certificate instead..."
    fi
    
    # Restart containers
    echo "   Starting containers..."
    docker compose up -d
}

function create_selfsigned() {
    echo -e "\n🔧 Creating Self-Signed Certificate..."
    
    sudo mkdir -p /etc/ssl/certs /etc/ssl/private
    
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/ssl/private/matrosmcp.key \
        -out /etc/ssl/certs/matrosmcp.crt \
        -subj "/C=US/ST=Cloud/L=Oracle/O=MCP/CN=$DOMAIN"
    
    if [[ $? -eq 0 ]]; then
        echo "   ✅ Self-signed certificate created successfully!"
        
        # Update NGINX configuration
        sudo sed -i 's|ssl_certificate /etc/letsencrypt/live.*|ssl_certificate /etc/ssl/certs/matrosmcp.crt;|g' nginx/conf.d/mcp-proxy.conf
        sudo sed -i 's|ssl_certificate_key /etc/letsencrypt/live.*|ssl_certificate_key /etc/ssl/private/matrosmcp.key;|g' nginx/conf.d/mcp-proxy.conf
        
        echo "   ✅ Configuration updated for self-signed certificate"
    else
        echo "   ❌ Self-signed certificate creation failed!"
        return 1
    fi
}

function test_connection() {
    echo -e "\n🧪 Testing SSL Connection..."
    
    echo "   HTTP Health Check:"
    curl -s http://$DOMAIN/health | jq -r '.status // "Failed"' || echo "   ❌ HTTP failed"
    
    echo "   HTTPS Health Check (ignoring certificate warnings):"
    curl -k -s https://$DOMAIN/health | jq -r '.status // "Failed"' || echo "   ❌ HTTPS failed"
    
    echo "   Certificate Details:"
    echo | openssl s_client -servername $DOMAIN -connect $DOMAIN:443 2>/dev/null | openssl x509 -noout -subject -issuer -dates
}

function show_renewal_status() {
    echo -e "\n🔄 Auto-Renewal Status:"
    echo "   Cron Jobs:"
    sudo crontab -l | grep -E "(certbot|renew)" || echo "   No renewal cron jobs found"
    
    echo "   Certbot Timer (systemd):"
    sudo systemctl status certbot.timer --no-pager -l 2>/dev/null || echo "   Certbot timer not available"
}

# Main menu
case "${1:-status}" in
    "status")
        show_status
        show_renewal_status
        ;;
    "letsencrypt")
        create_letsencrypt
        show_status
        ;;
    "selfsigned")
        create_selfsigned
        show_status
        ;;
    "test")
        test_connection
        ;;
    "renewal")
        show_renewal_status
        ;;
    *)
        echo "Usage: $0 [status|letsencrypt|selfsigned|test|renewal]"
        echo ""
        echo "Commands:"
        echo "  status      - Show current SSL certificate status (default)"
        echo "  letsencrypt - Create/update Let's Encrypt certificate"
        echo "  selfsigned  - Create/update self-signed certificate"
        echo "  test        - Test SSL connectivity"
        echo "  renewal     - Show auto-renewal configuration"
        ;;
esac