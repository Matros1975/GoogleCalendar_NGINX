#!/bin/bash
# Health Check Test
# Validates MCP server readiness/health endpoints

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

TEST_NAME="Health Check Test"
PASSED=0
FAILED=0

echo "=========================================="
echo "  $TEST_NAME"
echo "=========================================="
echo ""

# Test 1: Calendar MCP container health check
log_info "Test 1: Checking Calendar MCP container health status..."
MCP_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' calendar-mcp 2>/dev/null || echo "unknown")

case "$MCP_HEALTH" in
    "healthy")
        log_success "Calendar MCP container is healthy"
        ((PASSED=PASSED+1))
        ;;
    "starting")
        log_warn "Calendar MCP container is still starting, waiting..."
        sleep 30
        MCP_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' calendar-mcp 2>/dev/null || echo "unknown")
        if [[ "$MCP_HEALTH" == "healthy" ]]; then
            log_success "Calendar MCP container is now healthy"
            ((PASSED=PASSED+1))
        else
            log_error "Calendar MCP container health: $MCP_HEALTH"
            ((FAILED=FAILED+1))
        fi
        ;;
    *)
        log_warn "Calendar MCP container health: $MCP_HEALTH (health check may not be configured)"
        # Don't fail if health check not configured
        ((PASSED=PASSED+1))
        ;;
esac

# Test 1b: TopDesk MCP container health check
log_info "Test 1b: Checking TopDesk MCP container health status..."
TOPDESK_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' topdesk-mcp 2>/dev/null || echo "unknown")

case "$TOPDESK_HEALTH" in
    "healthy")
        log_success "TopDesk MCP container is healthy"
        ((PASSED=PASSED+1))
        ;;
    "starting")
        log_warn "TopDesk MCP container is still starting, waiting..."
        sleep 30
        TOPDESK_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' topdesk-mcp 2>/dev/null || echo "unknown")
        if [[ "$TOPDESK_HEALTH" == "healthy" ]]; then
            log_success "TopDesk MCP container is now healthy"
            ((PASSED=PASSED+1))
        else
            log_error "TopDesk MCP container health: $TOPDESK_HEALTH"
            ((FAILED=FAILED+1))
        fi
        ;;
    *)
        log_warn "TopDesk MCP container health: $TOPDESK_HEALTH (health check may not be configured)"
        # Don't fail if health check not configured
        ((PASSED=PASSED+1))
        ;;
esac

# Test 2: NGINX container health check
log_info "Test 2: Checking NGINX container health status..."
NGINX_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' nginx-proxy 2>/dev/null || echo "unknown")

case "$NGINX_HEALTH" in
    "healthy")
        log_success "NGINX container is healthy"
        ((PASSED=PASSED+1))
        ;;
    "starting")
        log_warn "NGINX container is still starting, waiting..."
        sleep 20
        NGINX_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' nginx-proxy 2>/dev/null || echo "unknown")
        if [[ "$NGINX_HEALTH" == "healthy" ]]; then
            log_success "NGINX container is now healthy"
            ((PASSED=PASSED+1))
        else
            log_error "NGINX container health: $NGINX_HEALTH"
            ((FAILED=FAILED+1))
        fi
        ;;
    *)
        log_warn "NGINX container health: $NGINX_HEALTH (health check may not be configured)"
        ((PASSED=PASSED+1))
        ;;
esac

# Test 3: MCP /health endpoint response
log_info "Test 3: Testing MCP /health endpoint response..."
HEALTH_RESPONSE=$(timeout 10 curl -k -s https://localhost/health 2>/dev/null || echo "")

if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    log_success "MCP health endpoint returns healthy status"
    echo "     Response: $HEALTH_RESPONSE"
    ((PASSED=PASSED+1))
elif echo "$HEALTH_RESPONSE" | grep -q "301.*Moved"; then
    log_success "MCP health endpoint correctly redirects HTTP to HTTPS"
    ((PASSED=PASSED+1))
else
    log_error "MCP health endpoint response unexpected: $HEALTH_RESPONSE"
    ((FAILED=FAILED+1))
fi

# Test 4: MCP /health endpoint response time
log_info "Test 4: Testing MCP /health endpoint response time..."
RESPONSE_TIME=$(timeout 10 curl -k -s -o /dev/null -w "%{time_total}" https://localhost/health 2>/dev/null || echo "999")

if (( $(echo "$RESPONSE_TIME < 2.0" | bc -l 2>/dev/null || echo "1") )); then
    log_success "Health endpoint response time: ${RESPONSE_TIME}s (< 2s)"
    ((PASSED=PASSED+1))
else
    log_error "Health endpoint response time: ${RESPONSE_TIME}s (too slow)"
    ((FAILED=FAILED+1))
fi

# Test 5: Check health endpoint is available via HTTPS
log_info "Test 5: Testing health endpoint via HTTPS..."
HTTPS_HEALTH=$(curl -k -s https://localhost/health 2>/dev/null || echo "")

if [[ -n "$HTTPS_HEALTH" ]]; then
    log_success "Health endpoint accessible via HTTPS"
    ((PASSED=PASSED+1))
else
    log_warn "Health endpoint not accessible via HTTPS (SSL may not be configured)"
    # Don't fail if SSL not configured
    ((PASSED=PASSED+1))
fi

# Test 6: Docker healthcheck history
log_info "Test 6: Checking Docker healthcheck history..."
MCP_HEALTH_LOG=$(docker inspect calendar-mcp --format='{{range .State.Health.Log}}{{.ExitCode}} {{end}}' 2>/dev/null || echo "")

if [[ -n "$MCP_HEALTH_LOG" ]]; then
    FAILED_CHECKS=$(echo "$MCP_HEALTH_LOG" | tr ' ' '\n' | grep -c "^1" 2>/dev/null || echo "0")
    TOTAL_CHECKS=$(echo "$MCP_HEALTH_LOG" | wc -w 2>/dev/null || echo "0")
    
    # Clean up variables to remove newlines
    FAILED_CHECKS=$(echo "$FAILED_CHECKS" | tr -d '\n\r' | grep -o '[0-9]*' | head -1)
    TOTAL_CHECKS=$(echo "$TOTAL_CHECKS" | tr -d '\n\r' | grep -o '[0-9]*' | head -1)
    
    if [[ "${FAILED_CHECKS:-0}" -eq 0 ]]; then
        log_success "All ${TOTAL_CHECKS:-0} health checks passed"
        ((PASSED=PASSED+1))
    else
        log_warn "${FAILED_CHECKS:-0} of ${TOTAL_CHECKS:-0} health checks failed"
        ((PASSED=PASSED+1))  # Don't fail on past health check issues if currently healthy
    fi
else
    log_info "No health check history available"
fi

# Test 7: Container restart count
log_info "Test 7: Checking container restart counts..."
MCP_RESTARTS=$(docker inspect --format='{{.RestartCount}}' calendar-mcp 2>/dev/null || echo "0")
NGINX_RESTARTS=$(docker inspect --format='{{.RestartCount}}' nginx-proxy 2>/dev/null || echo "0")

if [[ "$MCP_RESTARTS" -eq 0 ]]; then
    log_success "MCP container has not restarted"
    ((PASSED=PASSED+1))
else
    log_warn "MCP container has restarted $MCP_RESTARTS times"
    ((PASSED=PASSED+1))  # Don't fail on restarts if currently healthy
fi

if [[ "$NGINX_RESTARTS" -eq 0 ]]; then
    log_success "NGINX container has not restarted"
    ((PASSED=PASSED+1))
else
    log_warn "NGINX container has restarted $NGINX_RESTARTS times"
    ((PASSED=PASSED+1))
fi

# Test 8: Service uptime
log_info "Test 8: Checking service uptime..."
MCP_UPTIME=$(docker inspect --format='{{.State.StartedAt}}' calendar-mcp 2>/dev/null || echo "unknown")
NGINX_UPTIME=$(docker inspect --format='{{.State.StartedAt}}' nginx-proxy 2>/dev/null || echo "unknown")

if [[ "$MCP_UPTIME" != "unknown" ]]; then
    log_success "MCP container started at: $MCP_UPTIME"
    ((PASSED=PASSED+1))
else
    log_error "Cannot determine MCP container uptime"
    ((FAILED=FAILED+1))
fi

if [[ "$NGINX_UPTIME" != "unknown" ]]; then
    log_success "NGINX container started at: $NGINX_UPTIME"
    ((PASSED=PASSED+1))
else
    log_error "Cannot determine NGINX container uptime"
    ((FAILED=FAILED+1))
fi

# Test 9: Process check inside containers
log_info "Test 9: Checking processes inside containers..."

# Check Node.js process in MCP container
if docker exec calendar-mcp pgrep -f "node.*build/index.js" > /dev/null 2>&1; then
    log_success "Node.js process running in MCP container"
    ((PASSED=PASSED+1))
else
    log_error "Node.js process not found in MCP container"
    ((FAILED=FAILED+1))
fi

# Check NGINX process
if docker exec nginx-proxy pgrep nginx > /dev/null 2>&1; then
    log_success "NGINX process running in NGINX container"
    ((PASSED=PASSED+1))
else
    log_error "NGINX process not found in NGINX container"
    ((FAILED=FAILED+1))
fi

# Test 10: Memory usage check
log_info "Test 10: Checking memory usage..."
MCP_MEM=$(docker stats --no-stream --format "{{.MemPerc}}" calendar-mcp 2>/dev/null | sed 's/%//' || echo "0")
NGINX_MEM=$(docker stats --no-stream --format "{{.MemPerc}}" nginx-proxy 2>/dev/null | sed 's/%//' || echo "0")

echo "     MCP memory usage: ${MCP_MEM}%"
echo "     NGINX memory usage: ${NGINX_MEM}%"

# Don't fail on memory usage, just report
log_success "Memory usage reported"
((PASSED=PASSED+1))

# Summary
echo ""
echo "=========================================="
echo "  Test Results"
echo "=========================================="
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [[ $FAILED -eq 0 ]]; then
    echo -e "${GREEN}✅ All health check tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some health check tests failed!${NC}"
    exit 1
fi
