#!/bin/bash
# Health check script for SSL renewal container
# Checks if cron daemon is running and certbot is available

# Check if crond is running
if ! pgrep crond > /dev/null; then
    echo "ERROR: cron daemon not running"
    exit 1
fi

# Check if certbot is available
if ! command -v certbot &> /dev/null; then
    echo "ERROR: certbot not found"
    exit 1
fi

# Check if docker is available
if ! command -v docker &> /dev/null; then
    echo "ERROR: docker not found"
    exit 1
fi

# Check if log directory is writable
if [[ ! -w /var/log/ssl-renewal ]]; then
    echo "ERROR: log directory not writable"
    exit 1
fi

# All checks passed
exit 0
