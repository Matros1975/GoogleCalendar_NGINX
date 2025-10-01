#!/bin/bash

# Let's Encrypt Certificate Renewal Script
# This script renews certificates and reloads NGINX if renewal occurs

LOGFILE="/var/log/letsencrypt-renewal.log"
DOMAIN="matrosmcp.duckdns.org"

echo "[$(date)] Starting certificate renewal check for $DOMAIN" >> $LOGFILE

# Try to renew certificate
sudo certbot renew --quiet --no-self-upgrade >> $LOGFILE 2>&1

if [ $? -eq 0 ]; then
    echo "[$(date)] Certificate renewal check completed successfully" >> $LOGFILE
    
    # Check if certificates were actually renewed (certbot creates renewal hooks)
    # If renewed, restart docker containers to reload certificates
    if [ -f "/etc/letsencrypt/renewal/$DOMAIN.conf" ]; then
        CERT_FILE="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
        if [ -f "$CERT_FILE" ]; then
            # Check if certificate was modified in last hour (indicating renewal)
            if [ $(find "$CERT_FILE" -mmin -60 | wc -l) -gt 0 ]; then
                echo "[$(date)] Certificate was renewed, restarting containers..." >> $LOGFILE
                cd /home/ubuntu/GoogleCalendar_NGINX
                docker compose restart nginx
                echo "[$(date)] NGINX container restarted" >> $LOGFILE
            fi
        fi
    fi
else
    echo "[$(date)] Certificate renewal failed!" >> $LOGFILE
fi

echo "[$(date)] Renewal check completed" >> $LOGFILE