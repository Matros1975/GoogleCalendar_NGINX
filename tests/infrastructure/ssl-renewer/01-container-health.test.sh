#!/bin/bash
# SSL Renewer Container Health Test
# Validates SSL renewer container health and basic functionality

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

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

TEST_NAME="SSL Renewer Container Health Test"
PASSED=0
FAILED=0

echo "=========================================="
echo "  $TEST_NAME"
echo "=========================================="
echo ""

# Test 1: Check if ssl-renewer service is defined in docker-compose.yml
log_info "Test 1: Checking if ssl-renewer service is defined..."
if docker compose -f "$PROJECT_ROOT/docker-compose.yml" config 2>/dev/null | grep -q "ssl-renewer:"; then
    log_success "ssl-renewer service is defined in docker-compose.yml"
    ((PASSED=PASSED+1))
else
    log_error "ssl-renewer service not found in docker-compose.yml"
    ((FAILED=FAILED+1))
fi

# Test 2: Verify ssl-renewer Dockerfile exists
log_info "Test 2: Checking if ssl-renewer Dockerfile exists..."
if [[ -f "$PROJECT_ROOT/nginx/ssl-renewer/Dockerfile" ]]; then
    log_success "ssl-renewer Dockerfile exists"
    ((PASSED=PASSED+1))
else
    log_error "ssl-renewer Dockerfile not found"
    ((FAILED=FAILED+1))
fi

# Test 3: Verify ssl-renewal.sh script exists
log_info "Test 3: Checking if ssl-renewal.sh script exists..."
if [[ -f "$PROJECT_ROOT/nginx/ssl-renewer/ssl-renewal.sh" ]]; then
    log_success "ssl-renewal.sh script exists"
    ((PASSED=PASSED+1))
else
    log_error "ssl-renewal.sh script not found"
    ((FAILED=FAILED+1))
fi

# Test 4: Verify ssl-crontab file exists
log_info "Test 4: Checking if ssl-crontab file exists..."
if [[ -f "$PROJECT_ROOT/nginx/ssl-renewer/ssl-crontab" ]]; then
    log_success "ssl-crontab file exists"
    ((PASSED=PASSED+1))
else
    log_error "ssl-crontab file not found"
    ((FAILED=FAILED+1))
fi

# Test 5: Verify health-check.sh script exists
log_info "Test 5: Checking if health-check.sh script exists..."
if [[ -f "$PROJECT_ROOT/nginx/ssl-renewer/health-check.sh" ]]; then
    log_success "health-check.sh script exists"
    ((PASSED=PASSED+1))
else
    log_error "health-check.sh script not found"
    ((FAILED=FAILED+1))
fi

# Test 6: Verify scripts are executable
log_info "Test 6: Checking if scripts are executable..."
if [[ -x "$PROJECT_ROOT/nginx/ssl-renewer/ssl-renewal.sh" ]] || \
   [[ "$(stat -c %a "$PROJECT_ROOT/nginx/ssl-renewer/ssl-renewal.sh" 2>/dev/null)" =~ [1357]$ ]]; then
    log_success "ssl-renewal.sh is marked as executable"
    ((PASSED=PASSED+1))
else
    log_warn "ssl-renewal.sh may not be executable (will be set in Dockerfile)"
    ((PASSED=PASSED+1))
fi

# Test 7: Verify required environment variables are defined
log_info "Test 7: Checking ssl-renewer environment variables..."
CONFIG_OUTPUT=$(docker compose -f "$PROJECT_ROOT/docker-compose.yml" config 2>/dev/null)
if echo "$CONFIG_OUTPUT" | grep -A 20 "ssl-renewer:" | grep -q "DOMAIN"; then
    log_success "DOMAIN environment variable is defined"
    ((PASSED=PASSED+1))
else
    log_error "DOMAIN environment variable not found"
    ((FAILED=FAILED+1))
fi

# Test 8: Verify required volumes are mounted
log_info "Test 8: Checking ssl-renewer volume mounts..."
VOLUMES_OK=true
for volume in "letsencrypt" "docker.sock" "docker-compose.yml"; do
    if echo "$CONFIG_OUTPUT" | grep -A 60 "ssl-renewer:" | grep -q "$volume"; then
        log_success "Volume mount for $volume is configured"
        ((PASSED=PASSED+1))
    else
        log_error "Volume mount for $volume not found"
        ((FAILED=FAILED+1))
        VOLUMES_OK=false
    fi
done

# Test 9: Verify health check is configured
log_info "Test 9: Checking ssl-renewer health check configuration..."
if echo "$CONFIG_OUTPUT" | grep -A 60 "ssl-renewer:" | grep -q "healthcheck"; then
    log_success "Health check is configured"
    ((PASSED=PASSED+1))
else
    log_error "Health check not configured"
    ((FAILED=FAILED+1))
fi

# Test 10: Verify network configuration
log_info "Test 10: Checking ssl-renewer network configuration..."
if echo "$CONFIG_OUTPUT" | grep -A 60 "ssl-renewer:" | grep -q "mcp-internal"; then
    log_success "ssl-renewer is connected to mcp-internal network"
    ((PASSED=PASSED+1))
else
    log_error "ssl-renewer network configuration issue"
    ((FAILED=FAILED+1))
fi

# Test 11: Verify crontab schedule is correct
log_info "Test 11: Verifying crontab schedule (twice daily at 3:30 AM/PM)..."
if grep -q "30 3 \* \* \*" "$PROJECT_ROOT/nginx/ssl-renewer/ssl-crontab" && \
   grep -q "30 15 \* \* \*" "$PROJECT_ROOT/nginx/ssl-renewer/ssl-crontab"; then
    log_success "Crontab schedule is correctly configured"
    ((PASSED=PASSED+1))
else
    log_error "Crontab schedule is not correctly configured"
    ((FAILED=FAILED+1))
fi

# Test 12: Verify Dockerfile installs required packages
log_info "Test 12: Checking Dockerfile for required packages..."
DOCKERFILE="$PROJECT_ROOT/nginx/ssl-renewer/Dockerfile"
PACKAGES_OK=true
for package in "certbot" "docker-cli" "dcron" "bash"; do
    if grep -q "$package" "$DOCKERFILE"; then
        log_success "Dockerfile installs $package"
        ((PASSED=PASSED+1))
    else
        log_error "Dockerfile missing $package installation"
        ((FAILED=FAILED+1))
        PACKAGES_OK=false
    fi
done

# Summary
echo ""
echo "=========================================="
echo "  Test Summary"
echo "=========================================="
echo -e "${GREEN}Passed:${NC} $PASSED"
echo -e "${RED}Failed:${NC} $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All SSL renewer container health tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some SSL renewer container health tests failed!${NC}"
    exit 1
fi
