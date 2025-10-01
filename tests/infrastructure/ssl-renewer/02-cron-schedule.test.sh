#!/bin/bash
# SSL Renewer Cron Schedule Test
# Validates cron job configuration and schedule

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

TEST_NAME="SSL Renewer Cron Schedule Test"
PASSED=0
FAILED=0

echo "=========================================="
echo "  $TEST_NAME"
echo "=========================================="
echo ""

CRONTAB_FILE="$PROJECT_ROOT/Servers/NGINX/ssl-renewer/ssl-crontab"

# Test 1: Verify crontab file exists
log_info "Test 1: Checking if ssl-crontab file exists..."
if [[ -f "$CRONTAB_FILE" ]]; then
    log_success "ssl-crontab file exists"
    ((PASSED=PASSED+1))
else
    log_error "ssl-crontab file not found at $CRONTAB_FILE"
    ((FAILED=FAILED+1))
    exit 1
fi

# Test 2: Verify crontab has correct format
log_info "Test 2: Validating crontab file format..."
if grep -E "^[0-9]+ [0-9]+ \* \* \* .*ssl-renewal.sh" "$CRONTAB_FILE" > /dev/null; then
    log_success "Crontab file has valid format"
    ((PASSED=PASSED+1))
else
    log_error "Crontab file format is invalid"
    ((FAILED=FAILED+1))
fi

# Test 3: Verify 3:30 AM schedule
log_info "Test 3: Checking for 3:30 AM schedule..."
if grep -q "30 3 \* \* \* /scripts/ssl-renewal.sh" "$CRONTAB_FILE"; then
    log_success "3:30 AM schedule is configured"
    ((PASSED=PASSED+1))
else
    log_error "3:30 AM schedule not found"
    ((FAILED=FAILED+1))
fi

# Test 4: Verify 3:30 PM schedule
log_info "Test 4: Checking for 3:30 PM schedule..."
if grep -q "30 15 \* \* \* /scripts/ssl-renewal.sh" "$CRONTAB_FILE"; then
    log_success "3:30 PM schedule is configured"
    ((PASSED=PASSED+1))
else
    log_error "3:30 PM schedule not found"
    ((FAILED=FAILED+1))
fi

# Test 5: Verify exactly two cron jobs are configured
log_info "Test 5: Checking number of cron jobs..."
JOB_COUNT=$(grep -c "ssl-renewal.sh" "$CRONTAB_FILE" || echo "0")
if [[ $JOB_COUNT -eq 2 ]]; then
    log_success "Exactly 2 cron jobs configured (as expected)"
    ((PASSED=PASSED+1))
else
    log_error "Expected 2 cron jobs, found $JOB_COUNT"
    ((FAILED=FAILED+1))
fi

# Test 6: Verify cron jobs run daily
log_info "Test 6: Verifying cron jobs run daily..."
DAILY_JOBS=$(grep -c "\* \* \* .*ssl-renewal.sh" "$CRONTAB_FILE" || echo "0")
if [[ $DAILY_JOBS -eq 2 ]]; then
    log_success "Both cron jobs are configured to run daily"
    ((PASSED=PASSED+1))
else
    log_error "Cron jobs may not be configured to run daily"
    ((FAILED=FAILED+1))
fi

# Test 7: Verify script path is correct
log_info "Test 7: Verifying script path in crontab..."
if grep -q "/scripts/ssl-renewal.sh" "$CRONTAB_FILE"; then
    log_success "Script path is correct (/scripts/ssl-renewal.sh)"
    ((PASSED=PASSED+1))
else
    log_error "Script path in crontab is incorrect"
    ((FAILED=FAILED+1))
fi

# Test 8: Verify no duplicate schedules
log_info "Test 8: Checking for duplicate cron schedules..."
SCHEDULE_30_3=$(grep -c "30 3 \* \* \*" "$CRONTAB_FILE" || echo "0")
SCHEDULE_30_15=$(grep -c "30 15 \* \* \*" "$CRONTAB_FILE" || echo "0")
if [[ $SCHEDULE_30_3 -eq 1 ]] && [[ $SCHEDULE_30_15 -eq 1 ]]; then
    log_success "No duplicate schedules found"
    ((PASSED=PASSED+1))
else
    log_error "Duplicate schedules detected (3:30 AM: $SCHEDULE_30_3, 3:30 PM: $SCHEDULE_30_15)"
    ((FAILED=FAILED+1))
fi

# Test 9: Verify crontab file is not empty
log_info "Test 9: Checking if crontab file has content..."
if [[ -s "$CRONTAB_FILE" ]]; then
    log_success "Crontab file has content"
    ((PASSED=PASSED+1))
else
    log_error "Crontab file is empty"
    ((FAILED=FAILED+1))
fi

# Test 10: Verify no conflicting schedules
log_info "Test 10: Checking for conflicting schedules..."
# Check if there are any other schedules that might conflict
OTHER_SCHEDULES=$(grep -v "^#" "$CRONTAB_FILE" | grep -v "30 3 \* \* \*" | grep -v "30 15 \* \* \*" | grep "ssl-renewal.sh" | wc -l || echo "0")
if [[ $OTHER_SCHEDULES -eq 0 ]]; then
    log_success "No conflicting schedules found"
    ((PASSED=PASSED+1))
else
    log_warn "Found $OTHER_SCHEDULES additional schedule(s)"
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
    echo -e "${GREEN}✅ All cron schedule tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some cron schedule tests failed!${NC}"
    exit 1
fi
