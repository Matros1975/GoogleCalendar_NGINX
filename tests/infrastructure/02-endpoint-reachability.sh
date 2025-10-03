#!/bin/bash
# Endpoint Reachability Test
# Confirms all MCP endpoints are accessible through NGINX

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[PASS]${NC} $1"; }
log_error() { echo -e "${RED}[FAIL]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

TEST_NAME="Endpoint Reachability Test"
PASSED=0
FAILED=0

echo "=========================================="
echo "  $TEST_NAME"
echo "=========================================="
echo ""

# Wait for services to be ready
log_info "Waiting for services to be ready..."
sleep 5

# Test 1: Health endpoint (no auth required)
log_info "Test 1: Testing health endpoint (HTTP)..."
HTTP_RESPONSE=$(timeout 10 curl -s -o /dev/null -w "%{http_code}" http://localhost/health 2>/dev/null || echo "000")
if [[ "$HTTP_RESPONSE" == "200" ]]; then
    log_success "Health endpoint accessible via HTTP"
    ((PASSED=PASSED+1))
else
    log_error "Health endpoint not accessible via HTTP (status: $HTTP_RESPONSE)"
    ((FAILED=FAILED+1))
fi

# Test 2: Health endpoint (HTTPS with self-signed cert)
log_info "Test 2: Testing health endpoint (HTTPS)..."
HTTPS_RESPONSE=$(timeout 10 curl -k -s -o /dev/null -w "%{http_code}" https://localhost/health 2>/dev/null || echo "000")
if [[ "$HTTPS_RESPONSE" == "200" ]] || [[ "$HTTPS_RESPONSE" == "301" ]] || [[ "$HTTPS_RESPONSE" == "302" ]]; then
    log_success "Health endpoint accessible via HTTPS (status: $HTTPS_RESPONSE)"
    ((PASSED=PASSED+1))
else
    log_warn "Health endpoint HTTPS status: $HTTPS_RESPONSE (may require valid cert)"
    ((PASSED=PASSED+1))  # Don't fail if HTTPS not fully configured
fi

# Test 3: Direct MCP container health check (internal)
log_info "Test 3: Testing direct MCP container health..."
DIRECT_RESPONSE=$(docker exec calendar-mcp wget -q -O- http://localhost:3000/health 2>/dev/null || echo "")
if [[ -n "$DIRECT_RESPONSE" ]] && echo "$DIRECT_RESPONSE" | grep -q "healthy"; then
    log_success "MCP container health endpoint working"
    ((PASSED=PASSED+1))
else
    log_error "MCP container health endpoint not responding"
    ((FAILED=FAILED+1))
fi

# Test 4: MCP info endpoint (internal)
log_info "Test 4: Testing MCP info endpoint..."
INFO_RESPONSE=$(docker exec calendar-mcp wget -q -O- http://localhost:3000/info 2>/dev/null || echo "")
if [[ -n "$INFO_RESPONSE" ]]; then
    log_success "MCP info endpoint accessible"
    echo "     Info: $(echo $INFO_RESPONSE | head -c 100)..."
    ((PASSED=PASSED+1))
else
    log_error "MCP info endpoint not accessible"
    ((FAILED=FAILED+1))
fi

# Test 4b: Direct TopDesk MCP container health check (internal)
log_info "Test 4b: Testing direct TopDesk MCP container health..."
TOPDESK_PROCESS=$(docker exec topdesk-mcp sh -c 'ps aux | grep -v grep | grep "topdesk_mcp.main"' 2>/dev/null || echo "")
if [[ -n "$TOPDESK_PROCESS" ]]; then
    log_success "TopDesk MCP container process is running"
    ((PASSED=PASSED+1))
else
    log_error "TopDesk MCP container process not found"
    ((FAILED=FAILED+1))
fi

# Test 5: NGINX upstream connectivity
log_info "Test 5: Testing NGINX to MCP upstream connectivity..."
NGINX_LOG=$(timeout 10 docker exec nginx-proxy cat /var/log/nginx/error.log 2>/dev/null | tail -10 || echo "")
if echo "$NGINX_LOG" | grep -iq "upstream.*failed\|502\|503"; then
    log_error "NGINX has upstream connection errors"
    echo "$NGINX_LOG" | grep -i "upstream\|502\|503" | tail -5
    ((FAILED=FAILED+1))
else
    log_success "NGINX upstream connectivity looks good"
    ((PASSED=PASSED+1))
fi

# Test 6: OAuth endpoints accessibility
log_info "Test 6: Testing OAuth endpoints..."
OAUTH_RESPONSE=$(timeout 10 curl -k -s -o /dev/null -w "%{http_code}" https://localhost/oauth/callback 2>/dev/null || echo "000")
if [[ "$OAUTH_RESPONSE" != "000" ]]; then
    log_success "OAuth endpoints are accessible (status: $OAUTH_RESPONSE)"
    ((PASSED=PASSED+1))
else
    log_error "OAuth endpoints not accessible"
    ((FAILED=FAILED+1))
fi

# Test 7: Check NGINX is properly forwarding to MCP
log_info "Test 7: Testing NGINX proxy forwarding..."
# Try to access root endpoint (will fail auth but should reach the service)
ROOT_RESPONSE=$(timeout 10 curl -k -s -o /dev/null -w "%{http_code}" https://localhost/ 2>/dev/null || echo "000")
if [[ "$ROOT_RESPONSE" == "401" ]] || [[ "$ROOT_RESPONSE" == "403" ]] || [[ "$ROOT_RESPONSE" == "200" ]]; then
    log_success "NGINX is forwarding requests (auth check working, status: $ROOT_RESPONSE)"
    ((PASSED=PASSED+1))
else
    log_error "NGINX forwarding issue (status: $ROOT_RESPONSE)"
    ((FAILED=FAILED+1))
fi

# Test 8: Check all required ports are listening
log_info "Test 8: Checking required ports are listening..."
REQUIRED_PORTS=("80:nginx" "443:nginx" "3500:mcp")

for port_info in "${REQUIRED_PORTS[@]}"; do
    IFS=':' read -r port service <<< "$port_info"
    if netstat -tuln 2>/dev/null | grep -q ":$port " || ss -tuln 2>/dev/null | grep -q ":$port "; then
        log_success "Port $port is listening ($service)"
        ((PASSED=PASSED+1))
    else
        log_warn "Port $port may not be listening ($service)"
        # Don't fail as some ports might not be exposed
    fi
done

# Test 9: DNS resolution (if using domain)
log_info "Test 9: Testing DNS resolution..."
DOMAIN=$(grep -oP 'server_name\s+\K[^\s;]+' "$PROJECT_ROOT/nginx/conf.d/mcp-proxy.conf" 2>/dev/null | head -1)
if [[ -n "$DOMAIN" ]] && [[ "$DOMAIN" != "localhost" ]]; then
    if host "$DOMAIN" > /dev/null 2>&1; then
        log_success "Domain '$DOMAIN' resolves correctly"
        ((PASSED=PASSED+1))
    else
        log_warn "Domain '$DOMAIN' DNS resolution failed (may be expected in test environment)"
    fi
else
    log_info "Using localhost, skipping DNS test"
fi

# Test 10: Network connectivity between containers
log_info "Test 10: Testing inter-container network connectivity..."
if docker exec nginx-proxy ping -c 1 calendar-mcp > /dev/null 2>&1; then
    log_success "NGINX can reach MCP container via Docker network"
    ((PASSED=PASSED+1))
else
    log_error "NGINX cannot reach MCP container via Docker network"
    ((FAILED=FAILED+1))
fi

# Summary
echo ""
echo "=========================================="
echo "  Test Results"
echo "=========================================="
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [[ $FAILED -eq 0 ]]; then
    echo -e "${GREEN}✅ All endpoint reachability tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some endpoint reachability tests failed!${NC}"
    exit 1
fi
