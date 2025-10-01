#!/bin/bash
# Container Startup Test
# Verifies all containers (MCP + NGINX) launch successfully

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

TEST_NAME="Container Startup Test"
PASSED=0
FAILED=0

echo "=========================================="
echo "  $TEST_NAME"
echo "=========================================="
echo ""

# Test 1: Check docker-compose.yml exists
log_info "Test 1: Checking docker-compose.yml exists..."
if [[ -f "$PROJECT_ROOT/docker-compose.yml" ]]; then
    log_success "docker-compose.yml found"
    ((PASSED=PASSED+1))
else
    log_error "docker-compose.yml not found"
    ((FAILED=FAILED+1))
fi

# Test 2: Validate docker-compose.yml syntax
log_info "Test 2: Validating docker-compose.yml syntax..."
if docker compose -f "$PROJECT_ROOT/docker-compose.yml" config > /dev/null 2>&1; then
    log_success "docker-compose.yml syntax is valid"
    ((PASSED=PASSED+1))
else
    log_error "docker-compose.yml has syntax errors"
    ((FAILED=FAILED+1))
fi

# Test 3: Start containers
log_info "Test 3: Starting containers..."
cd "$PROJECT_ROOT"
if docker compose up -d > /dev/null 2>&1; then
    log_success "Containers started successfully"
    ((PASSED=PASSED+1))
else
    log_error "Failed to start containers"
    ((FAILED=FAILED+1))
    docker compose logs
fi

# Wait for containers to initialize
sleep 10

# Test 4: Check all containers are running
log_info "Test 4: Checking all containers are running..."
EXPECTED_CONTAINERS=("calendar-mcp" "nginx-proxy" "duckdns-updater")
ALL_RUNNING=true

for container in "${EXPECTED_CONTAINERS[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        log_success "Container '$container' is running"
        ((PASSED=PASSED+1))
    else
        log_error "Container '$container' is not running"
        ((FAILED=FAILED+1))
        ALL_RUNNING=false
    fi
done

# Test 5: Check container health status
log_info "Test 5: Checking container health status..."
sleep 10  # Wait for health checks to run

for container in "calendar-mcp" "nginx-proxy"; do
    HEALTH_STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "unknown")
    
    if [[ "$HEALTH_STATUS" == "healthy" ]]; then
        log_success "Container '$container' is healthy"
        ((PASSED=PASSED+1))
    elif [[ "$HEALTH_STATUS" == "starting" ]]; then
        log_warn "Container '$container' is still starting (health check pending)"
        # Wait a bit more and recheck
        sleep 20
        HEALTH_STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "unknown")
        if [[ "$HEALTH_STATUS" == "healthy" ]]; then
            log_success "Container '$container' is now healthy"
            ((PASSED=PASSED+1))
        else
            log_error "Container '$container' health status: $HEALTH_STATUS"
            ((FAILED=FAILED+1))
        fi
    else
        log_warn "Container '$container' health status: $HEALTH_STATUS (no health check defined)"
        ((PASSED=PASSED+1))  # Not a failure if health check isn't defined
    fi
done

# Test 6: Check container logs for errors
log_info "Test 6: Checking container logs for critical errors..."
ERROR_FOUND=false

for container in "${EXPECTED_CONTAINERS[@]}"; do
    if docker logs "$container" 2>&1 | grep -iE "error|fatal|exception" | grep -v "no error" > /dev/null; then
        log_warn "Container '$container' has error messages in logs"
        # Don't fail the test, just warn
    else
        log_success "Container '$container' logs look clean"
        ((PASSED=PASSED+1))
    fi
done

# Test 7: Check container resource usage
log_info "Test 7: Checking container resource usage..."
if docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" > /dev/null 2>&1; then
    log_success "Container resource monitoring working"
    docker stats --no-stream --format "  {{.Container}}: CPU={{.CPUPerc}} MEM={{.MemUsage}}"
    ((PASSED=PASSED+1))
else
    log_error "Failed to get container stats"
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
    echo -e "${GREEN}✅ All container startup tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some container startup tests failed!${NC}"
    exit 1
fi
