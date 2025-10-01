#!/bin/bash
# Comprehensive Deployment Testing Script
# Tests container startup, endpoint reachability, health checks, security, TLS, and YAML configs
# Usage: ./scripts/test-deployment.sh [--pre-refactor|--post-refactor]

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEST_MODE="${1:-pre-refactor}"
TEST_RESULTS_DIR="$PROJECT_ROOT/test-results"
TEST_REPORT="$TEST_RESULTS_DIR/deployment-test-$TEST_MODE-$(date +%Y%m%d-%H%M%S).json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0
TEST_DETAILS=()

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Track test result
record_test() {
    local test_name="$1"
    local result="$2"
    local details="$3"
    
    case "$result" in
        "PASS")
            TESTS_PASSED=$((TESTS_PASSED + 1))
            log_success "$test_name: PASSED"
            ;;
        "FAIL")
            TESTS_FAILED=$((TESTS_FAILED + 1))
            log_error "$test_name: FAILED - $details"
            ;;
        "SKIP")
            TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
            log_warn "$test_name: SKIPPED - $details"
            ;;
    esac
    
    TEST_DETAILS+=("{\"test\":\"$test_name\",\"result\":\"$result\",\"details\":\"$details\"}")
}

# Setup test results directory
setup_test_env() {
    mkdir -p "$TEST_RESULTS_DIR"
    log_info "Test mode: $TEST_MODE"
    log_info "Results will be saved to: $TEST_REPORT"
}

# Test 1: Container Startup Test
test_container_startup() {
    log_section "TEST 1: Container Startup"
    
    log_info "Checking if containers are running..."
    
    # Check calendar-mcp container
    if docker ps --format '{{.Names}}' | grep -q "calendar-mcp"; then
        record_test "Container: calendar-mcp" "PASS" "Container is running"
    else
        record_test "Container: calendar-mcp" "FAIL" "Container is not running"
        return 1
    fi
    
    # Check nginx-proxy container
    if docker ps --format '{{.Names}}' | grep -q "nginx-proxy"; then
        record_test "Container: nginx-proxy" "PASS" "Container is running"
    else
        record_test "Container: nginx-proxy" "FAIL" "Container is not running"
        return 1
    fi
    
    # Check duckdns-updater container
    if docker ps --format '{{.Names}}' | grep -q "duckdns-updater"; then
        record_test "Container: duckdns-updater" "PASS" "Container is running"
    else
        record_test "Container: duckdns-updater" "SKIP" "DuckDNS container not running (optional)"
    fi
    
    # Check container health status
    local mcp_health=$(docker inspect --format='{{.State.Health.Status}}' calendar-mcp 2>/dev/null || echo "none")
    if [[ "$mcp_health" == "healthy" || "$mcp_health" == "none" ]]; then
        record_test "Health Check: calendar-mcp" "PASS" "Health status: $mcp_health"
    else
        record_test "Health Check: calendar-mcp" "FAIL" "Health status: $mcp_health"
    fi
    
    local nginx_health=$(docker inspect --format='{{.State.Health.Status}}' nginx-proxy 2>/dev/null || echo "none")
    if [[ "$nginx_health" == "healthy" || "$nginx_health" == "none" ]]; then
        record_test "Health Check: nginx-proxy" "PASS" "Health status: $nginx_health"
    else
        record_test "Health Check: nginx-proxy" "FAIL" "Health status: $nginx_health"
    fi
}

# Test 2: Endpoint Reachability Test
test_endpoint_reachability() {
    log_section "TEST 2: Endpoint Reachability"
    
    # Test NGINX health endpoint (should be accessible without auth)
    log_info "Testing NGINX health endpoint..."
    if curl -k -f -s "https://localhost/health" > /dev/null 2>&1; then
        record_test "NGINX Health Endpoint" "PASS" "Accessible via HTTPS"
    elif curl -f -s "http://localhost/health" > /dev/null 2>&1; then
        record_test "NGINX Health Endpoint" "PASS" "Accessible via HTTP"
    else
        record_test "NGINX Health Endpoint" "FAIL" "Not accessible"
    fi
    
    # Test direct MCP health endpoint (internal)
    log_info "Testing direct MCP health endpoint (internal)..."
    if docker exec nginx-proxy curl -f -s "http://calendar-mcp:3000/health" > /dev/null 2>&1; then
        record_test "MCP Health Endpoint (Internal)" "PASS" "Accessible from NGINX container"
    else
        record_test "MCP Health Endpoint (Internal)" "FAIL" "Not accessible from NGINX container"
    fi
    
    # Test OAuth endpoints
    log_info "Testing OAuth callback endpoint..."
    local oauth_status=$(curl -k -s -o /dev/null -w "%{http_code}" "https://localhost/oauth/callback" 2>/dev/null || echo "000")
    if [[ "$oauth_status" == "200" || "$oauth_status" == "404" || "$oauth_status" == "400" ]]; then
        record_test "OAuth Callback Endpoint" "PASS" "Endpoint reachable (status: $oauth_status)"
    else
        record_test "OAuth Callback Endpoint" "FAIL" "Endpoint not reachable (status: $oauth_status)"
    fi
}

# Test 3: Health Check Test
test_health_checks() {
    log_section "TEST 3: Health Check Validation"
    
    # Test MCP health endpoint response
    log_info "Validating MCP health check response..."
    local health_response=$(curl -k -s "https://localhost/health" 2>/dev/null || echo "{}")
    
    if echo "$health_response" | grep -q "healthy"; then
        record_test "MCP Health Response Format" "PASS" "Valid health response received"
    else
        record_test "MCP Health Response Format" "FAIL" "Invalid health response: $health_response"
    fi
    
    # Check if health response includes expected fields
    if echo "$health_response" | grep -q "google-calendar-mcp"; then
        record_test "MCP Server Identification" "PASS" "Server identified correctly"
    else
        record_test "MCP Server Identification" "FAIL" "Server identification missing"
    fi
    
    # Test Docker health check configuration
    log_info "Validating Docker health check configuration..."
    local mcp_healthcheck=$(docker inspect calendar-mcp --format='{{.Config.Healthcheck.Test}}' 2>/dev/null || echo "")
    if [[ -n "$mcp_healthcheck" ]]; then
        record_test "Docker Healthcheck Config: calendar-mcp" "PASS" "Healthcheck configured"
    else
        record_test "Docker Healthcheck Config: calendar-mcp" "SKIP" "No healthcheck configured"
    fi
}

# Test 4: Bearer Token Security Test
test_bearer_token_security() {
    log_section "TEST 4: Bearer Token Security"
    
    # Test without bearer token (should be rejected)
    log_info "Testing access without bearer token (should fail)..."
    local no_token_status=$(curl -k -s -o /dev/null -w "%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","method":"tools/list","id":1}' \
        "https://localhost/" 2>/dev/null || echo "000")
    
    if [[ "$no_token_status" == "401" || "$no_token_status" == "403" ]]; then
        record_test "Bearer Token: Reject No Token" "PASS" "Correctly rejected (status: $no_token_status)"
    else
        record_test "Bearer Token: Reject No Token" "FAIL" "Should reject but got status: $no_token_status"
    fi
    
    # Test with invalid bearer token (should be rejected)
    log_info "Testing access with invalid bearer token (should fail)..."
    local invalid_token_status=$(curl -k -s -o /dev/null -w "%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer invalid-token-12345" \
        -d '{"jsonrpc":"2.0","method":"tools/list","id":1}' \
        "https://localhost/" 2>/dev/null || echo "000")
    
    if [[ "$invalid_token_status" == "401" || "$invalid_token_status" == "403" ]]; then
        record_test "Bearer Token: Reject Invalid Token" "PASS" "Correctly rejected (status: $invalid_token_status)"
    else
        record_test "Bearer Token: Reject Invalid Token" "FAIL" "Should reject but got status: $invalid_token_status"
    fi
    
    # Test with valid bearer token (should succeed if token is configured)
    log_info "Testing access with valid bearer token..."
    if [[ -f "$PROJECT_ROOT/.env.production" ]]; then
        local valid_token=$(grep "BEARER_TOKENS=" "$PROJECT_ROOT/.env.production" | cut -d'=' -f2 | cut -d',' -f1)
        if [[ -n "$valid_token" ]]; then
            local valid_token_status=$(curl -k -s -o /dev/null -w "%{http_code}" \
                -X POST \
                -H "Content-Type: application/json" \
                -H "Authorization: Bearer $valid_token" \
                -d '{"jsonrpc":"2.0","method":"tools/list","id":1}' \
                "https://localhost/" 2>/dev/null || echo "000")
            
            if [[ "$valid_token_status" == "200" || "$valid_token_status" == "500" ]]; then
                record_test "Bearer Token: Accept Valid Token" "PASS" "Token accepted (status: $valid_token_status)"
            else
                record_test "Bearer Token: Accept Valid Token" "FAIL" "Valid token rejected (status: $valid_token_status)"
            fi
        else
            record_test "Bearer Token: Accept Valid Token" "SKIP" "No valid token found in .env.production"
        fi
    else
        record_test "Bearer Token: Accept Valid Token" "SKIP" ".env.production file not found"
    fi
    
    # Test health endpoint without token (should work)
    log_info "Testing health endpoint without token (should succeed)..."
    local health_no_token=$(curl -k -s -o /dev/null -w "%{http_code}" "https://localhost/health" 2>/dev/null || echo "000")
    if [[ "$health_no_token" == "200" ]]; then
        record_test "Bearer Token: Health Endpoint No Auth" "PASS" "Health endpoint accessible without token"
    else
        record_test "Bearer Token: Health Endpoint No Auth" "FAIL" "Health endpoint requires token (status: $health_no_token)"
    fi
}

# Test 5: TLS Certificate Test
test_tls_certificates() {
    log_section "TEST 5: TLS Certificate Validation"
    
    # Test HTTPS connection
    log_info "Testing HTTPS connection..."
    if curl -k -s "https://localhost/health" > /dev/null 2>&1; then
        record_test "TLS: HTTPS Connection" "PASS" "HTTPS connection successful"
    else
        record_test "TLS: HTTPS Connection" "FAIL" "Cannot establish HTTPS connection"
        return 1
    fi
    
    # Test certificate validity
    log_info "Checking certificate validity..."
    local cert_info=$(echo | openssl s_client -connect localhost:443 -servername localhost 2>/dev/null | openssl x509 -noout -dates 2>/dev/null || echo "")
    
    if [[ -n "$cert_info" ]]; then
        record_test "TLS: Certificate Info" "PASS" "Certificate information retrieved"
        
        # Check certificate expiration
        local not_after=$(echo "$cert_info" | grep "notAfter" | cut -d'=' -f2)
        if [[ -n "$not_after" ]]; then
            local expiry_epoch=$(date -d "$not_after" +%s 2>/dev/null || echo "0")
            local now_epoch=$(date +%s)
            
            if [[ $expiry_epoch -gt $now_epoch ]]; then
                local days_until_expiry=$(( ($expiry_epoch - $now_epoch) / 86400 ))
                record_test "TLS: Certificate Expiration" "PASS" "Valid for $days_until_expiry more days"
            else
                record_test "TLS: Certificate Expiration" "FAIL" "Certificate has expired"
            fi
        fi
    else
        record_test "TLS: Certificate Info" "FAIL" "Cannot retrieve certificate information"
    fi
    
    # Test SSL protocols
    log_info "Testing SSL protocols..."
    if openssl s_client -connect localhost:443 -tls1_2 </dev/null 2>/dev/null | grep -q "Protocol.*TLSv1.2"; then
        record_test "TLS: TLS 1.2 Support" "PASS" "TLS 1.2 supported"
    else
        record_test "TLS: TLS 1.2 Support" "FAIL" "TLS 1.2 not supported"
    fi
    
    if openssl s_client -connect localhost:443 -tls1_3 </dev/null 2>/dev/null | grep -q "Protocol.*TLSv1.3"; then
        record_test "TLS: TLS 1.3 Support" "PASS" "TLS 1.3 supported"
    else
        record_test "TLS: TLS 1.3 Support" "SKIP" "TLS 1.3 not supported (acceptable)"
    fi
    
    # Check certificate files in NGINX container
    log_info "Checking certificate files in NGINX container..."
    if docker exec nginx-proxy test -f /etc/ssl/certs/matrosmcp.crt; then
        record_test "TLS: Certificate File Exists" "PASS" "Certificate file found in container"
    else
        record_test "TLS: Certificate File Exists" "FAIL" "Certificate file not found in container"
    fi
    
    if docker exec nginx-proxy test -f /etc/ssl/private/matrosmcp.key; then
        record_test "TLS: Private Key File Exists" "PASS" "Private key file found in container"
    else
        record_test "TLS: Private Key File Exists" "FAIL" "Private key file not found in container"
    fi
}

# Test 6: YAML Configuration Test
test_yaml_configuration() {
    log_section "TEST 6: YAML Configuration Validation"
    
    # Test docker-compose.yml syntax
    log_info "Validating docker-compose.yml syntax..."
    cd "$PROJECT_ROOT"
    if docker compose config > /dev/null 2>&1; then
        record_test "YAML: docker-compose.yml Syntax" "PASS" "Valid YAML syntax"
    else
        record_test "YAML: docker-compose.yml Syntax" "FAIL" "Invalid YAML syntax"
        return 1
    fi
    
    # Check required services are defined
    log_info "Checking required services in docker-compose.yml..."
    local compose_services=$(docker compose config --services 2>/dev/null || echo "")
    
    if echo "$compose_services" | grep -q "calendar-mcp"; then
        record_test "YAML: Service calendar-mcp defined" "PASS" "Service defined"
    else
        record_test "YAML: Service calendar-mcp defined" "FAIL" "Service not defined"
    fi
    
    if echo "$compose_services" | grep -q "nginx-proxy"; then
        record_test "YAML: Service nginx-proxy defined" "PASS" "Service defined"
    else
        record_test "YAML: Service nginx-proxy defined" "FAIL" "Service not defined"
    fi
    
    # Check network configuration
    log_info "Validating network configuration..."
    if docker compose config | grep -q "mcp-internal"; then
        record_test "YAML: Network mcp-internal defined" "PASS" "Network defined"
    else
        record_test "YAML: Network mcp-internal defined" "FAIL" "Network not defined"
    fi
    
    # Check volume configuration
    log_info "Validating volume configuration..."
    if docker compose config | grep -q "calendar-tokens"; then
        record_test "YAML: Volume calendar-tokens defined" "PASS" "Volume defined"
    else
        record_test "YAML: Volume calendar-tokens defined" "FAIL" "Volume not defined"
    fi
    
    # Test NGINX configuration syntax
    log_info "Validating NGINX configuration syntax..."
    if docker exec nginx-proxy nginx -t > /dev/null 2>&1; then
        record_test "YAML: NGINX Config Syntax" "PASS" "Valid NGINX configuration"
    else
        record_test "YAML: NGINX Config Syntax" "FAIL" "Invalid NGINX configuration"
    fi
    
    # Check if .env.production exists
    if [[ -f "$PROJECT_ROOT/.env.production" ]]; then
        record_test "Config: .env.production exists" "PASS" "Environment file found"
        
        # Check critical environment variables
        if grep -q "BEARER_TOKENS=" "$PROJECT_ROOT/.env.production"; then
            record_test "Config: BEARER_TOKENS defined" "PASS" "Bearer tokens configured"
        else
            record_test "Config: BEARER_TOKENS defined" "FAIL" "Bearer tokens not configured"
        fi
    else
        record_test "Config: .env.production exists" "SKIP" "Environment file not found"
    fi
}

# Test 7: Network Connectivity Test
test_network_connectivity() {
    log_section "TEST 7: Network Connectivity"
    
    # Test internal network connectivity
    log_info "Testing internal network connectivity..."
    if docker exec nginx-proxy ping -c 1 calendar-mcp > /dev/null 2>&1; then
        record_test "Network: NGINX to MCP" "PASS" "Internal connectivity working"
    else
        record_test "Network: NGINX to MCP" "FAIL" "Cannot reach MCP from NGINX"
    fi
    
    # Test that MCP is not exposed directly to host
    log_info "Testing MCP isolation (should not be directly accessible)..."
    if ! curl -s --max-time 2 "http://localhost:3000/health" > /dev/null 2>&1; then
        record_test "Network: MCP Isolation" "PASS" "MCP not directly accessible (secure)"
    else
        record_test "Network: MCP Isolation" "WARN" "MCP directly accessible from host"
    fi
    
    # Test that NGINX is accessible
    log_info "Testing NGINX accessibility..."
    if curl -k -s --max-time 2 "https://localhost/health" > /dev/null 2>&1; then
        record_test "Network: NGINX Accessibility" "PASS" "NGINX accessible from host"
    else
        record_test "Network: NGINX Accessibility" "FAIL" "NGINX not accessible from host"
    fi
}

# Generate test report
generate_report() {
    log_section "Test Summary"
    
    local total_tests=$((TESTS_PASSED + TESTS_FAILED + TESTS_SKIPPED))
    
    echo "Total Tests: $total_tests"
    echo "  ✅ Passed: $TESTS_PASSED"
    echo "  ❌ Failed: $TESTS_FAILED"
    echo "  ⚠️  Skipped: $TESTS_SKIPPED"
    echo ""
    
    # Generate JSON report
    cat > "$TEST_REPORT" <<EOF
{
  "test_mode": "$TEST_MODE",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "summary": {
    "total": $total_tests,
    "passed": $TESTS_PASSED,
    "failed": $TESTS_FAILED,
    "skipped": $TESTS_SKIPPED
  },
  "tests": [
    $(IFS=','; echo "${TEST_DETAILS[*]}")
  ]
}
EOF
    
    log_info "Detailed report saved to: $TEST_REPORT"
    
    # Return exit code based on failures
    if [[ $TESTS_FAILED -gt 0 ]]; then
        log_error "Some tests failed. Please review the failures above."
        return 1
    else
        log_success "All tests passed!"
        return 0
    fi
}

# Main execution
main() {
    log_section "Starting Deployment Tests"
    log_info "Mode: $TEST_MODE"
    
    setup_test_env
    
    # Run all tests
    test_container_startup || true
    test_endpoint_reachability || true
    test_health_checks || true
    test_bearer_token_security || true
    test_tls_certificates || true
    test_yaml_configuration || true
    test_network_connectivity || true
    
    # Generate report and exit
    generate_report
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "Comprehensive Deployment Testing Script"
        echo ""
        echo "Usage: $0 [--pre-refactor|--post-refactor]"
        echo ""
        echo "Options:"
        echo "  --pre-refactor     Run tests before refactoring (default)"
        echo "  --post-refactor    Run tests after refactoring"
        echo "  --help, -h         Show this help message"
        echo ""
        echo "Tests performed:"
        echo "  1. Container Startup Test"
        echo "  2. Endpoint Reachability Test"
        echo "  3. Health Check Test"
        echo "  4. Bearer Token Security Test"
        echo "  5. TLS Certificate Test"
        echo "  6. YAML Configuration Test"
        echo "  7. Network Connectivity Test"
        echo ""
        echo "Prerequisites:"
        echo "  - Docker and Docker Compose running"
        echo "  - Containers must be started (docker compose up -d)"
        echo "  - SSL certificates configured"
        echo "  - Bearer tokens configured in .env.production"
        exit 0
        ;;
    --pre-refactor)
        TEST_MODE="pre-refactor"
        main
        ;;
    --post-refactor)
        TEST_MODE="post-refactor"
        main
        ;;
    "")
        TEST_MODE="pre-refactor"
        main
        ;;
    *)
        log_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac
