#!/bin/bash
# YAML Configuration Validation Test
# Parse YAML configs to ensure correctness and application of settings

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

TEST_NAME="YAML Configuration Validation Test"
PASSED=0
FAILED=0

echo "=========================================="
echo "  $TEST_NAME"
echo "=========================================="
echo ""

# Test 1: docker-compose.yml exists and is valid YAML
log_info "Test 1: Validating docker-compose.yml syntax..."
if docker compose -f "$PROJECT_ROOT/docker-compose.yml" config > /dev/null 2>&1; then
    log_success "docker-compose.yml syntax is valid"
    ((PASSED=PASSED+1))
else
    log_error "docker-compose.yml has syntax errors"
    docker compose -f "$PROJECT_ROOT/docker-compose.yml" config 2>&1 | head -10
    ((FAILED=FAILED+1))
fi

# Test 2: Check all required services are defined
log_info "Test 2: Checking required services are defined..."
REQUIRED_SERVICES=("calendar-mcp" "nginx-proxy")
CONFIG_OUTPUT=$(docker compose -f "$PROJECT_ROOT/docker-compose.yml" config 2>/dev/null)

for service in "${REQUIRED_SERVICES[@]}"; do
    if echo "$CONFIG_OUTPUT" | grep -q "  $service:"; then
        log_success "Service '$service' is defined"
        ((PASSED=PASSED+1))
    else
        log_error "Service '$service' is not defined"
        ((FAILED=FAILED+1))
    fi
done

# Test 3: Check network configuration
log_info "Test 3: Validating network configuration..."
if echo "$CONFIG_OUTPUT" | grep -q "networks:"; then
    NETWORK_NAME=$(echo "$CONFIG_OUTPUT" | grep -A 2 "^networks:" | grep -v "^networks:" | head -1 | awk '{print $1}' | tr -d ':')
    if [[ -n "$NETWORK_NAME" ]]; then
        log_success "Network '$NETWORK_NAME' is defined"
        ((PASSED=PASSED+1))
    else
        log_error "No network name found"
        ((FAILED=FAILED+1))
    fi
else
    log_error "No networks defined"
    ((FAILED=FAILED+1))
fi

# Test 4: Check volume configuration
log_info "Test 4: Validating volume configuration..."
if echo "$CONFIG_OUTPUT" | grep -q "volumes:"; then
    VOLUME_COUNT=$(echo "$CONFIG_OUTPUT" | grep -A 20 "^volumes:" | grep "driver: local" | wc -l)
    log_success "Found $VOLUME_COUNT volume(s) defined"
    ((PASSED=PASSED+1))
else
    log_warn "No volumes defined (may be expected)"
    ((PASSED=PASSED+1))
fi

# Test 5: Check calendar-mcp service configuration
log_info "Test 5: Validating calendar-mcp service configuration..."

# Check image/build
if echo "$CONFIG_OUTPUT" | grep -A 20 "  calendar-mcp:" | grep -q "build:"; then
    log_success "calendar-mcp has build configuration"
    ((PASSED=PASSED+1))
else
    log_warn "calendar-mcp may not have build configuration"
fi

# Check environment variables
if echo "$CONFIG_OUTPUT" | grep -A 30 "  calendar-mcp:" | grep -q "TRANSPORT"; then
    TRANSPORT_MODE=$(echo "$CONFIG_OUTPUT" | grep -A 30 "  calendar-mcp:" | grep "TRANSPORT" | head -1 | cut -d: -f2 | tr -d ' ')
    log_success "calendar-mcp TRANSPORT mode: $TRANSPORT_MODE"
    ((PASSED=PASSED+1))
else
    log_error "calendar-mcp missing TRANSPORT environment variable"
    ((FAILED=FAILED+1))
fi

# Check ports
if echo "$CONFIG_OUTPUT" | grep -A 30 "  calendar-mcp:" | grep -q "ports:"; then
    log_success "calendar-mcp has port mappings"
    ((PASSED=PASSED+1))
else
    log_warn "calendar-mcp has no port mappings (may use internal network)"
    ((PASSED=PASSED+1))
fi

# Test 6: Check nginx-proxy service configuration
log_info "Test 6: Validating nginx-proxy service configuration..."

# Check image
if echo "$CONFIG_OUTPUT" | grep -A 20 "  nginx-proxy:" | grep -q "image:.*nginx"; then
    log_success "nginx-proxy uses nginx image"
    ((PASSED=PASSED+1))
else
    log_error "nginx-proxy missing or not using nginx image"
    ((FAILED=FAILED+1))
fi

# Check ports 80 and 443
if echo "$CONFIG_OUTPUT" | grep -A 30 "  nginx-proxy:" | grep -E "ports:" -A 10 | grep -q "443"; then
    log_success "nginx-proxy exposes HTTPS port 443"
    ((PASSED=PASSED+1))
else
    log_error "nginx-proxy not exposing HTTPS port 443"
    ((FAILED=FAILED+1))
fi

if echo "$CONFIG_OUTPUT" | grep -A 30 "  nginx-proxy:" | grep -E "ports:" -A 10 | grep -q "80"; then
    log_success "nginx-proxy exposes HTTP port 80"
    ((PASSED=PASSED+1))
else
    log_warn "nginx-proxy not exposing HTTP port 80"
    ((PASSED=PASSED+1))
fi

# Check volumes/config mounting
if echo "$CONFIG_OUTPUT" | grep -A 40 "  nginx-proxy:" | grep -q "/etc/nginx/conf.d"; then
    log_success "nginx-proxy mounts configuration directory"
    ((PASSED=PASSED+1))
else
    log_error "nginx-proxy missing configuration volume mount"
    ((FAILED=FAILED+1))
fi

# Test 7: Check depends_on relationships
log_info "Test 7: Checking service dependencies..."
if echo "$CONFIG_OUTPUT" | grep -A 30 "  nginx-proxy:" | grep -q "depends_on:"; then
    log_success "nginx-proxy has service dependencies defined"
    ((PASSED=PASSED+1))
else
    log_warn "nginx-proxy has no explicit service dependencies"
    ((PASSED=PASSED+1))
fi

# Test 8: Check health check configurations
log_info "Test 8: Validating health check configurations..."
if echo "$CONFIG_OUTPUT" | grep -A 50 "  calendar-mcp:" | grep -q "healthcheck:"; then
    log_success "calendar-mcp has health check defined"
    ((PASSED=PASSED+1))
else
    log_warn "calendar-mcp has no health check defined"
fi

if echo "$CONFIG_OUTPUT" | grep -A 50 "  nginx-proxy:" | grep -q "healthcheck:"; then
    log_success "nginx-proxy has health check defined"
    ((PASSED=PASSED+1))
else
    log_warn "nginx-proxy has no health check defined"
fi

# Test 9: Check security settings
log_info "Test 9: Checking security configurations..."

# Check read-only filesystem
if echo "$CONFIG_OUTPUT" | grep -A 50 "  calendar-mcp:" | grep -q "read_only:.*true"; then
    log_success "calendar-mcp uses read-only filesystem"
    ((PASSED=PASSED+1))
else
    log_info "calendar-mcp not using read-only filesystem"
fi

# Check security_opt
if echo "$CONFIG_OUTPUT" | grep -A 50 "  calendar-mcp:" | grep -q "security_opt:"; then
    log_success "calendar-mcp has security options configured"
    ((PASSED=PASSED+1))
else
    log_info "calendar-mcp has no explicit security options"
fi

# Test 10: Check resource limits
log_info "Test 10: Checking resource limits..."
if echo "$CONFIG_OUTPUT" | grep -A 60 "  calendar-mcp:" | grep -q "deploy:"; then
    if echo "$CONFIG_OUTPUT" | grep -A 70 "  calendar-mcp:" | grep -q "limits:"; then
        log_success "calendar-mcp has resource limits configured"
        ((PASSED=PASSED+1))
    else
        log_warn "calendar-mcp deploy section exists but no limits"
    fi
else
    log_info "calendar-mcp has no resource limits (using defaults)"
fi

# Test 11: Validate docker-compose.dev.yml if it exists
log_info "Test 11: Validating docker-compose.dev.yml (if exists)..."
if [[ -f "$PROJECT_ROOT/docker-compose.dev.yml" ]]; then
    if docker compose -f "$PROJECT_ROOT/docker-compose.dev.yml" config > /dev/null 2>&1; then
        log_success "docker-compose.dev.yml syntax is valid"
        ((PASSED=PASSED+1))
    else
        log_error "docker-compose.dev.yml has syntax errors"
        ((FAILED=FAILED+1))
    fi
else
    log_info "docker-compose.dev.yml not found (optional)"
fi

# Test 12: Check for common misconfigurations
log_info "Test 12: Checking for common misconfigurations..."

# Check for host network mode (security risk)
if echo "$CONFIG_OUTPUT" | grep -q "network_mode:.*host"; then
    log_warn "Using host network mode (potential security risk)"
else
    log_success "Not using host network mode"
    ((PASSED=PASSED+1))
fi

# Check for privileged mode (security risk)
if echo "$CONFIG_OUTPUT" | grep -q "privileged:.*true"; then
    log_warn "Using privileged mode (security risk)"
else
    log_success "Not using privileged mode"
    ((PASSED=PASSED+1))
fi

# Test 13: Validate environment variable references
log_info "Test 13: Checking environment variable references..."
ENV_VARS=$(echo "$CONFIG_OUTPUT" | grep -oP '\$\{[A-Z_]+\}' | sort -u || echo "")

if [[ -n "$ENV_VARS" ]]; then
    echo "     Found environment variable references:"
    echo "$ENV_VARS" | while read -r var; do
        echo "       - $var"
    done
    log_success "Environment variables properly referenced"
    ((PASSED=PASSED+1))
else
    log_info "No environment variable references found"
fi

# Test 14: Check restart policies
log_info "Test 14: Validating restart policies..."
if echo "$CONFIG_OUTPUT" | grep -A 30 "  calendar-mcp:" | grep -q "restart:"; then
    RESTART_POLICY=$(echo "$CONFIG_OUTPUT" | grep -A 30 "  calendar-mcp:" | grep "restart:" | head -1 | cut -d: -f2 | tr -d ' ')
    log_success "calendar-mcp restart policy: $RESTART_POLICY"
    ((PASSED=PASSED+1))
else
    log_warn "calendar-mcp has no restart policy defined"
fi

if echo "$CONFIG_OUTPUT" | grep -A 30 "  nginx-proxy:" | grep -q "restart:"; then
    RESTART_POLICY=$(echo "$CONFIG_OUTPUT" | grep -A 30 "  nginx-proxy:" | grep "restart:" | head -1 | cut -d: -f2 | tr -d ' ')
    log_success "nginx-proxy restart policy: $RESTART_POLICY"
    ((PASSED=PASSED+1))
else
    log_warn "nginx-proxy has no restart policy defined"
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
    echo -e "${GREEN}✅ All YAML validation tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some YAML validation tests failed!${NC}"
    exit 1
fi
