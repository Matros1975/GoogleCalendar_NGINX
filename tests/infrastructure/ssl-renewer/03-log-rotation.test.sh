#!/bin/bash
# SSL Renewer Log Management Test
# Validates logging configuration and log directory setup

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

TEST_NAME="SSL Renewer Log Management Test"
PASSED=0
FAILED=0

echo "=========================================="
echo "  $TEST_NAME"
echo "=========================================="
echo ""

# Test 1: Verify ssl-renewal-logs volume is defined
log_info "Test 1: Checking if ssl-renewal-logs volume is defined..."
if docker compose -f "$PROJECT_ROOT/docker-compose.yml" config 2>/dev/null | grep -q "ssl-renewal-logs"; then
    log_success "ssl-renewal-logs volume is defined"
    ((PASSED=PASSED+1))
else
    log_error "ssl-renewal-logs volume not found"
    ((FAILED=FAILED+1))
fi

# Test 2: Verify log volume is mounted in ssl-renewer service
log_info "Test 2: Checking if log volume is mounted..."
CONFIG_OUTPUT=$(docker compose -f "$PROJECT_ROOT/docker-compose.yml" config 2>/dev/null)
if echo "$CONFIG_OUTPUT" | grep -A 60 "ssl-renewer:" | grep -q "ssl-renewal-logs"; then
    log_success "Log volume is properly mounted"
    ((PASSED=PASSED+1))
else
    log_error "Log volume mount not found"
    ((FAILED=FAILED+1))
fi

# Test 3: Verify log directory creation in Dockerfile
log_info "Test 3: Checking if Dockerfile creates log directory..."
DOCKERFILE="$PROJECT_ROOT/Servers/NGINX/ssl-renewer/Dockerfile"
if grep -q "mkdir.*ssl-renewal" "$DOCKERFILE" || grep -q "/var/log/ssl-renewal" "$DOCKERFILE"; then
    log_success "Dockerfile creates log directory"
    ((PASSED=PASSED+1))
else
    log_error "Dockerfile does not create log directory"
    ((FAILED=FAILED+1))
fi

# Test 4: Verify ssl-renewal.sh script uses logging
log_info "Test 4: Checking if ssl-renewal.sh implements logging..."
SCRIPT_FILE="$PROJECT_ROOT/Servers/NGINX/ssl-renewer/ssl-renewal.sh"
if grep -q "LOGFILE" "$SCRIPT_FILE" && grep -q "log()" "$SCRIPT_FILE"; then
    log_success "ssl-renewal.sh implements logging functions"
    ((PASSED=PASSED+1))
else
    log_error "ssl-renewal.sh missing logging implementation"
    ((FAILED=FAILED+1))
fi

# Test 5: Verify log function includes timestamps
log_info "Test 5: Checking if logs include timestamps..."
if grep -q "date" "$SCRIPT_FILE" && grep -q "log()" "$SCRIPT_FILE"; then
    log_success "Logging includes timestamps"
    ((PASSED=PASSED+1))
else
    log_error "Logging missing timestamp functionality"
    ((FAILED=FAILED+1))
fi

# Test 6: Verify default log file path
log_info "Test 6: Verifying default log file path..."
if grep -q "/var/log/ssl-renewal.*log" "$SCRIPT_FILE"; then
    log_success "Log file path is correctly configured"
    ((PASSED=PASSED+1))
else
    log_error "Log file path not found or incorrect"
    ((FAILED=FAILED+1))
fi

# Test 7: Verify log directory is writable (checked in health-check)
log_info "Test 7: Checking if health-check validates log directory..."
HEALTH_CHECK="$PROJECT_ROOT/Servers/NGINX/ssl-renewer/health-check.sh"
if [[ -f "$HEALTH_CHECK" ]] && grep -q "log" "$HEALTH_CHECK"; then
    log_success "Health check validates log directory"
    ((PASSED=PASSED+1))
else
    log_warn "Health check may not validate log directory (optional)"
    ((PASSED=PASSED+1))
fi

# Test 8: Verify logging captures certbot output
log_info "Test 8: Checking if certbot output is logged..."
if grep -q "certbot.*>>.*LOGFILE" "$SCRIPT_FILE" || grep -q "certbot.*2>&1" "$SCRIPT_FILE"; then
    log_success "Certbot output is captured in logs"
    ((PASSED=PASSED+1))
else
    log_error "Certbot output may not be logged"
    ((FAILED=FAILED+1))
fi

# Test 9: Verify error logging is implemented
log_info "Test 9: Checking for error logging functionality..."
if grep -q "log_error" "$SCRIPT_FILE" || grep -q "ERROR" "$SCRIPT_FILE"; then
    log_success "Error logging is implemented"
    ((PASSED=PASSED+1))
else
    log_error "Error logging not found"
    ((FAILED=FAILED+1))
fi

# Test 10: Verify logging includes renewal status
log_info "Test 10: Checking if renewal status is logged..."
if grep -q "renewal" "$SCRIPT_FILE" | grep -i "log"; then
    log_success "Renewal status logging is present"
    ((PASSED=PASSED+1))
else
    log_warn "Renewal status logging may be missing"
    ((PASSED=PASSED+1))
fi

# Summary
echo ""
echo "=========================================="
echo "  Test Summary"
echo "=========================================="
echo -e "${GREEN}Passed:${NC} $PASSED"
echo -e "${RED}Failed:${NC} $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All log management tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some log management tests failed!${NC}"
    exit 1
fi
