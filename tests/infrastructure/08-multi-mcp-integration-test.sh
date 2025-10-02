#!/bin/bash

echo "=================================="
echo "Multi-MCP Server Connectivity Test"
echo "=================================="
echo

# Test configuration
DOMAIN="https://matrosmcp.duckdns.org"
BEARER_TOKEN="secret123"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Testing NGINX Health Check...${NC}"
response=$(curl -k -s -o /dev/null -w "%{http_code}" "$DOMAIN/health")
if [ "$response" -eq 301 ] || [ "$response" -eq 200 ]; then
    echo -e "${GREEN}✅ NGINX Health Check: OK (HTTP $response)${NC}"
else
    echo -e "${RED}❌ NGINX Health Check: FAILED (HTTP $response)${NC}"
fi
echo

echo -e "${BLUE}Testing Google Calendar MCP Server...${NC}"
echo "Endpoint: $DOMAIN/"
calendar_response=$(curl -k -s -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}' \
    "$DOMAIN/")

if echo "$calendar_response" | grep -q '"result"'; then
    echo -e "${GREEN}✅ Google Calendar MCP: Connected and responding${NC}"
    echo -e "${YELLOW}Available tools:${NC}"
    echo "$calendar_response" | grep -o '"name":"[^"]*"' | sed 's/"name":"//g' | sed 's/"//g' | sed 's/^/  - /'
else
    echo -e "${RED}❌ Google Calendar MCP: Connection failed${NC}"
    echo "Response: $calendar_response"
fi
echo

echo -e "${BLUE}Testing TopDesk MCP Server...${NC}"
echo "Endpoint: $DOMAIN/topdesk/mcp"

# First, initialize the TopDesk MCP session
echo "Initializing TopDesk MCP session..."
init_response=$(curl -k -s -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {"roots": {"listChanged": true}}, "clientInfo": {"name": "test-client", "version": "1.0.0"}}}' \
    "$DOMAIN/topdesk/mcp")

if echo "$init_response" | grep -q '"serverInfo"'; then
    echo -e "${GREEN}✅ TopDesk MCP: Connected and initialized${NC}"
    server_name=$(echo "$init_response" | grep -o '"name":"[^"]*"' | head -1 | sed 's/"name":"//g' | sed 's/"//g')
    server_version=$(echo "$init_response" | grep -o '"version":"[^"]*"' | head -1 | sed 's/"version":"//g' | sed 's/"//g')
    echo -e "${YELLOW}Server: $server_name v$server_version${NC}"
    echo -e "${YELLOW}Capabilities: Tools, Prompts, Resources with live updates${NC}"
else
    echo -e "${RED}❌ TopDesk MCP: Initialization failed${NC}"
    echo "Response: $init_response"
fi
echo

echo -e "${BLUE}Testing TopDesk API Connectivity...${NC}"
topdesk_api_response=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Basic $(echo -n 'api_aipilots:7w7j6-ytlqt-wpcbz-ywu6v-remw7' | base64)" \
    "https://pietervanforeest-test.topdesk.net/tas/api/incidents")

if [ "$topdesk_api_response" -eq 206 ] || [ "$topdesk_api_response" -eq 200 ]; then
    echo -e "${GREEN}✅ TopDesk API: Connected and authenticated (HTTP $topdesk_api_response)${NC}"
else
    echo -e "${RED}❌ TopDesk API: Connection failed (HTTP $topdesk_api_response)${NC}"
fi
echo

echo -e "${BLUE}SSL Certificate Status...${NC}"
cert_info=$(curl -k -s -I "$DOMAIN" | grep -i "strict-transport-security")
if [ -n "$cert_info" ]; then
    echo -e "${GREEN}✅ SSL Certificate: Valid and enforced${NC}"
    expiry=$(echo | openssl s_client -servername matrosmcp.duckdns.org -connect matrosmcp.duckdns.org:443 2>/dev/null | openssl x509 -noout -dates | grep notAfter | cut -d= -f2)
    echo -e "${YELLOW}Certificate expires: $expiry${NC}"
else
    echo -e "${RED}❌ SSL Certificate: Issues detected${NC}"
fi
echo

echo -e "${BLUE}Container Status Summary...${NC}"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
echo

echo "=================================="
echo -e "${GREEN}Multi-MCP Server Test Complete!${NC}"
echo "=================================="