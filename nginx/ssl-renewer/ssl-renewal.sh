#!/bin/bash
# SSL Certificate Renewal Script for Containerized Environment
# This script checks and renews Let's Encrypt certificates
# and restarts NGINX container only when certificates are actually renewed

set -euo pipefail

# Configuration
DOMAIN="${DOMAIN:-matrosmcp.duckdns.org}"
LOGFILE="${LOGFILE:-/var/log/ssl-renewal/renewal.log}"
COMPOSE_PROJECT_PATH="${COMPOSE_PROJECT_PATH:-/compose}"
NGINX_CONTAINER="${NGINX_CONTAINER:-nginx-proxy}"
CERT_FILE="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
CERT_EXPIRY_DAYS="${CERT_EXPIRY_DAYS:-30}"

# Ensure log directory exists
mkdir -p "$(dirname "$LOGFILE")"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOGFILE"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" | tee -a "$LOGFILE" >&2
}

# Function to check certificate expiry
check_certificate_expiry() {
    if [[ ! -f "$CERT_FILE" ]]; then
        log "Certificate file not found: $CERT_FILE"
        return 1
    fi
    
    local expiry_date
    expiry_date=$(openssl x509 -enddate -noout -in "$CERT_FILE" | cut -d= -f2)
    local expiry_epoch
    expiry_epoch=$(date -d "$expiry_date" +%s)
    local current_epoch
    current_epoch=$(date +%s)
    local days_until_expiry=$(( (expiry_epoch - current_epoch) / 86400 ))
    
    log "Certificate expires in $days_until_expiry days (on $expiry_date)"
    
    if [[ $days_until_expiry -le $CERT_EXPIRY_DAYS ]]; then
        log "Certificate expires within $CERT_EXPIRY_DAYS days - renewal recommended"
        return 0
    else
        log "Certificate still valid for $days_until_expiry days - no renewal needed"
        return 1
    fi
}

# Function to get certificate file modification time
get_cert_mtime() {
    if [[ -f "$CERT_FILE" ]]; then
        stat -c %Y "$CERT_FILE" 2>/dev/null || stat -f %m "$CERT_FILE" 2>/dev/null || echo "0"
    else
        echo "0"
    fi
}

# Function to test HTTPS endpoint
test_https_endpoint() {
    local url="https://$DOMAIN/health"
    log "Testing HTTPS endpoint: $url"
    
    if curl -sSf -k --connect-timeout 10 --max-time 30 "$url" > /dev/null 2>&1; then
        log "✅ HTTPS endpoint is accessible"
        return 0
    else
        log_error "❌ HTTPS endpoint test failed"
        return 1
    fi
}

# Function to restart NGINX container
restart_nginx() {
    log "Attempting to restart NGINX container: $NGINX_CONTAINER"
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker command not available"
        return 1
    fi
    
    # Method 1: Try using docker-compose if available
    if [[ -f "$COMPOSE_PROJECT_PATH/docker-compose.yml" ]]; then
        log "Using docker-compose to restart NGINX..."
        if docker compose -f "$COMPOSE_PROJECT_PATH/docker-compose.yml" restart "$NGINX_CONTAINER" >> "$LOGFILE" 2>&1; then
            log "✅ NGINX restarted successfully via docker-compose"
            return 0
        else
            log "⚠️  docker-compose restart failed, trying docker command..."
        fi
    fi
    
    # Method 2: Try direct docker restart
    if docker restart "$NGINX_CONTAINER" >> "$LOGFILE" 2>&1; then
        log "✅ NGINX restarted successfully via docker"
        return 0
    else
        log_error "❌ Failed to restart NGINX container"
        return 1
    fi
}

# Main renewal process
main() {
    log "=========================================="
    log "Starting SSL certificate renewal check"
    log "Domain: $DOMAIN"
    log "=========================================="
    
    # Check if certificate exists and its expiry
    if ! check_certificate_expiry; then
        log "Certificate does not need renewal at this time"
        log "Renewal check completed"
        log ""
        exit 0
    fi
    
    # Store certificate modification time before renewal
    local cert_mtime_before
    cert_mtime_before=$(get_cert_mtime)
    log "Certificate mtime before renewal: $cert_mtime_before"
    
    # Attempt certificate renewal
    log "Executing certbot renew..."
    if certbot renew --quiet --no-self-upgrade >> "$LOGFILE" 2>&1; then
        log "✅ Certbot renewal command completed successfully"
    else
        log_error "❌ Certbot renewal command failed!"
        log "Renewal check completed with errors"
        log ""
        exit 1
    fi
    
    # Check if certificate was actually renewed (by comparing modification time)
    local cert_mtime_after
    cert_mtime_after=$(get_cert_mtime)
    log "Certificate mtime after renewal: $cert_mtime_after"
    
    if [[ "$cert_mtime_before" != "$cert_mtime_after" ]]; then
        log "🔄 Certificate was renewed (mtime changed)"
        log "Restarting NGINX to load new certificate..."
        
        if restart_nginx; then
            # Wait a moment for NGINX to start
            sleep 5
            
            # Test HTTPS endpoint
            if test_https_endpoint; then
                log "✅ Certificate renewal and NGINX restart completed successfully"
            else
                log "⚠️  Certificate renewed and NGINX restarted, but HTTPS test failed"
            fi
        else
            log_error "❌ Certificate renewed but NGINX restart failed"
            exit 1
        fi
    else
        log "ℹ️  Certificate was not renewed (already up to date)"
    fi
    
    log "Renewal check completed"
    log ""
}

# Execute main function
main "$@"
