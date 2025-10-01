#!/bin/bash
# Master Test Runner for Infrastructure Tests
# Runs all infrastructure tests in sequence and reports results

# Note: We don't use 'set -e' here because we want to continue running
# all tests even if some fail, and collect pass/fail statistics

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_header() { echo -e "${CYAN}╔═══════════════════════════════════════════════════════╗${NC}"; echo -e "${CYAN}║  $1${NC}"; echo -e "${CYAN}╚═══════════════════════════════════════════════════════╝${NC}"; }
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[PASS]${NC} $1"; }
log_error() { echo -e "${RED}[FAIL]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# Test results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

# Test suite configuration
declare -A TESTS
TESTS=(
    ["01-container-startup.sh"]="Container Startup"
    ["02-endpoint-reachability.sh"]="Endpoint Reachability"
    ["03-health-check.sh"]="Health Check"
    ["04-bearer-token-security.sh"]="Bearer Token Security"
    ["05-tls-certificates.sh"]="TLS Certificates"
    ["06-yaml-validation.sh"]="YAML Configuration"
)

# Parse command line arguments
RUN_MODE="all"
CLEANUP_AFTER=false
SAVE_RESULTS=false
RESULTS_FILE=""

usage() {
    echo "Infrastructure Test Suite Runner"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --all              Run all tests (default)"
    echo "  --quick            Run only quick tests (YAML validation, no container startup)"
    echo "  --security         Run only security tests (bearer token, TLS)"
    echo "  --cleanup          Clean up containers after tests"
    echo "  --save-results FILE Save test results to file"
    echo "  --help, -h         Show this help message"
    echo ""
    exit 0
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            RUN_MODE="all"
            shift
            ;;
        --quick)
            RUN_MODE="quick"
            shift
            ;;
        --security)
            RUN_MODE="security"
            shift
            ;;
        --cleanup)
            CLEANUP_AFTER=true
            shift
            ;;
        --save-results)
            SAVE_RESULTS=true
            RESULTS_FILE="$2"
            shift 2
            ;;
        --help|-h)
            usage
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Banner
clear
echo ""
log_header "     Google Calendar MCP Infrastructure Tests     "
echo ""
echo -e "Test Mode: ${CYAN}$RUN_MODE${NC}"
echo -e "Project Root: $PROJECT_ROOT"
echo -e "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "════════════════════════════════════════════════════════"
echo ""

# Initialize results file if requested
if [[ "$SAVE_RESULTS" == true ]]; then
    {
        echo "Google Calendar MCP Infrastructure Test Results"
        echo "================================================"
        echo "Run Date: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Test Mode: $RUN_MODE"
        echo ""
    } > "$RESULTS_FILE"
fi

# Function to run a test
run_test() {
    local test_script="$1"
    local test_name="$2"
    local test_path="$SCRIPT_DIR/$test_script"
    
    ((TOTAL_TESTS++))
    
    echo ""
    log_info "Running: $test_name"
    echo "────────────────────────────────────────────────────────"
    
    if [[ ! -f "$test_path" ]]; then
        log_error "Test script not found: $test_script"
        ((FAILED_TESTS++))
        return 1
    fi
    
    # Make sure script is executable
    chmod +x "$test_path"
    
    # Run the test and capture output
    if [[ "$SAVE_RESULTS" == true ]]; then
        if "$test_path" 2>&1 | tee -a "$RESULTS_FILE"; then
            log_success "✓ $test_name passed"
            ((PASSED_TESTS++))
            echo "" >> "$RESULTS_FILE"
        else
            log_error "✗ $test_name failed"
            ((FAILED_TESTS++))
            echo "" >> "$RESULTS_FILE"
        fi
    else
        if "$test_path"; then
            log_success "✓ $test_name passed"
            ((PASSED_TESTS++))
        else
            log_error "✗ $test_name failed"
            ((FAILED_TESTS++))
        fi
    fi
    
    echo "────────────────────────────────────────────────────────"
}

# Determine which tests to run
case "$RUN_MODE" in
    "quick")
        log_info "Running quick tests only (no container startup)..."
        run_test "06-yaml-validation.sh" "YAML Configuration"
        ;;
    
    "security")
        log_info "Running security tests only..."
        run_test "01-container-startup.sh" "Container Startup"
        run_test "04-bearer-token-security.sh" "Bearer Token Security"
        run_test "05-tls-certificates.sh" "TLS Certificates"
        ;;
    
    "all"|*)
        log_info "Running all infrastructure tests..."
        for test_script in "${!TESTS[@]}"; do
            run_test "$test_script" "${TESTS[$test_script]}"
        done
        ;;
esac

# Cleanup if requested
if [[ "$CLEANUP_AFTER" == true ]]; then
    echo ""
    log_info "Cleaning up containers..."
    cd "$PROJECT_ROOT"
    docker compose down -v > /dev/null 2>&1 || true
    log_success "Cleanup completed"
fi

# Final summary
echo ""
echo "════════════════════════════════════════════════════════"
echo ""
log_header "               Test Results Summary                "
echo ""
echo -e "Total Tests:   ${CYAN}$TOTAL_TESTS${NC}"
echo -e "Passed:        ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed:        ${RED}$FAILED_TESTS${NC}"
echo -e "Skipped:       ${YELLOW}$SKIPPED_TESTS${NC}"
echo ""

if [[ $FAILED_TESTS -eq 0 ]]; then
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║          ✅ ALL TESTS PASSED! ✅                       ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    if [[ "$SAVE_RESULTS" == true ]]; then
        echo "✅ ALL TESTS PASSED!" >> "$RESULTS_FILE"
        log_info "Results saved to: $RESULTS_FILE"
    fi
    
    exit 0
else
    echo -e "${RED}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║          ❌ SOME TESTS FAILED! ❌                      ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    if [[ "$SAVE_RESULTS" == true ]]; then
        echo "❌ $FAILED_TESTS TESTS FAILED!" >> "$RESULTS_FILE"
        log_info "Results saved to: $RESULTS_FILE"
    fi
    
    exit 1
fi
