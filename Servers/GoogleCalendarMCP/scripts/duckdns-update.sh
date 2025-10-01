#!/bin/bash
# DuckDNS Update Script
# Updates your domain IP address automatically

DOMAIN="${DUCKDNS_DOMAIN:-matrosmcp}"
TOKEN="${DUCKDNS_TOKEN:-6fb5210e-71c6-4327-bbf9-af8283a08b37}"
LOGFILE="/var/log/duckdns.log"

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOGFILE"
}

# Function to get current public IP
get_public_ip() {
    # Try multiple services to get public IP
    for service in "ifconfig.me" "ipinfo.io/ip" "icanhazip.com" "checkip.amazonaws.com"; do
        ip=$(curl -s --connect-timeout 10 "$service" | tr -d '\n\r' | grep -oE '^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$')
        if [[ $ip =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
            echo "$ip"
            return 0
        fi
    done
    return 1
}

# Function to get DuckDNS current IP
get_duckdns_ip() {
    dig +short "${DOMAIN}.duckdns.org" @8.8.8.8 | tail -n1
}

# Function to update DuckDNS
update_duckdns() {
    local new_ip="$1"
    local response
    
    response=$(curl -s "https://www.duckdns.org/update?domains=${DOMAIN}&token=${TOKEN}&ip=${new_ip}")
    
    if [[ "$response" == "OK" ]]; then
        log "✅ Successfully updated ${DOMAIN}.duckdns.org to ${new_ip}"
        return 0
    else
        log "❌ Failed to update DuckDNS: $response"
        return 1
    fi
}

# Main execution
main() {
    log "🔄 Starting DuckDNS update check for ${DOMAIN}.duckdns.org"
    
    # Get current public IP
    current_ip=$(get_public_ip)
    if [[ -z "$current_ip" ]]; then
        log "❌ Failed to determine public IP address"
        exit 1
    fi
    
    # Get DuckDNS current IP
    duckdns_ip=$(get_duckdns_ip)
    if [[ -z "$duckdns_ip" ]]; then
        log "⚠️  Could not resolve current DuckDNS IP, forcing update"
        duckdns_ip="0.0.0.0"
    fi
    
    log "📍 Current public IP: $current_ip"
    log "🌐 DuckDNS current IP: $duckdns_ip"
    
    # Compare IPs and update if different
    if [[ "$current_ip" != "$duckdns_ip" ]]; then
        log "🔄 IP addresses differ, updating DuckDNS..."
        if update_duckdns "$current_ip"; then
            log "✅ DuckDNS update completed successfully"
        else
            log "❌ DuckDNS update failed"
            exit 1
        fi
    else
        log "✅ IP addresses match, no update needed"
    fi
    
    log "🏁 DuckDNS check completed"
}

# Run main function
main "$@"