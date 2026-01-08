#!/bin/bash
# Script to clean up Docker container logs and restart containers with new log configuration
# This addresses the issue of unbounded log file growth in /var/lib/docker/containers/

set -e

echo "=== Docker Log Cleanup Script ==="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}ERROR: This script must be run as root (sudo)${NC}"
    echo "Reason: Docker log files are owned by root and located in /var/lib/docker/"
    exit 1
fi

# Get all running container IDs
echo -e "${YELLOW}Finding all Docker containers...${NC}"
CONTAINERS=$(docker ps -aq)

if [ -z "$CONTAINERS" ]; then
    echo "No containers found"
    exit 0
fi

# Calculate total log size
echo -e "${YELLOW}Calculating total log size...${NC}"
TOTAL_SIZE=$(find /var/lib/docker/containers/ -name "*-json.log" -exec du -ch {} + 2>/dev/null | grep total$ | awk '{print $1}')
echo -e "Total Docker log size: ${RED}${TOTAL_SIZE}${NC}"
echo

# Show individual container log sizes
echo -e "${YELLOW}Container log sizes:${NC}"
for container in $CONTAINERS; do
    NAME=$(docker inspect --format='{{.Name}}' "$container" | sed 's/^\///')
    LOG_FILE="/var/lib/docker/containers/${container}/${container}-json.log"
    if [ -f "$LOG_FILE" ]; then
        SIZE=$(du -h "$LOG_FILE" | awk '{print $1}')
        echo "  - $NAME: $SIZE"
    fi
done
echo

# Ask for confirmation
read -p "Do you want to truncate all Docker logs? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted"
    exit 0
fi

# Truncate all container logs
echo -e "${YELLOW}Truncating container logs...${NC}"
for container in $CONTAINERS; do
    NAME=$(docker inspect --format='{{.Name}}' "$container" | sed 's/^\///')
    LOG_FILE="/var/lib/docker/containers/${container}/${container}-json.log"
    
    if [ -f "$LOG_FILE" ]; then
        OLD_SIZE=$(du -h "$LOG_FILE" | awk '{print $1}')
        truncate -s 0 "$LOG_FILE"
        echo -e "  ${GREEN}✓${NC} Truncated $NAME (was $OLD_SIZE)"
    fi
done

echo
echo -e "${GREEN}✓ All logs truncated successfully${NC}"
echo

# Verify new configuration
echo -e "${YELLOW}Verifying docker-compose.yml has logging configuration...${NC}"
if grep -q "logging:" /home/ubuntu/GoogleCalendar_NGINX/docker-compose.yml; then
    echo -e "${GREEN}✓ Logging configuration found in docker-compose.yml${NC}"
else
    echo -e "${RED}⚠ WARNING: No logging configuration found in docker-compose.yml${NC}"
    echo "  You may need to add logging configuration to prevent future log growth"
fi

echo
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Restart your Docker Compose services to apply new log rotation settings:"
echo "   cd /home/ubuntu/GoogleCalendar_NGINX"
echo "   docker-compose down"
echo "   docker-compose up -d"
echo
echo "2. Verify log rotation is working:"
echo "   docker inspect <container_name> | grep -A 10 LogConfig"
echo
echo -e "${GREEN}Done!${NC}"
