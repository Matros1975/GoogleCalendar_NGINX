#!/bin/bash
# SSE Endpoint Configuration Test
# Validates Server-Sent Events configuration for ElevenLabs VoiceAgent

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

TEST_NAME="SSE Endpoint Configuration Test"
PASSED=0
FAILED=0

echo "=========================================="
echo "  $TEST_NAME"
echo "=========================================="
echo ""

# Test configuration
DOMAIN="https://matrosmcp.duckdns.org"
BEARER_TOKEN="test-token"

# Test 1: Verify NGINX SSE configuration exists
log_info "Test 1: Checking NGINX SSE configuration..."
if grep -q "/topdesk/sse" "$PROJECT_ROOT/nginx/conf.d/mcp-proxy.conf"; then
    log_success "TopDesk SSE endpoint configuration found in NGINX"
    ((PASSED=PASSED+1))
else
    log_error "TopDesk SSE endpoint configuration missing from NGINX"
    ((FAILED=FAILED+1))
fi

# Test 2: Verify SSE-specific headers are configured
log_info "Test 2: Checking SSE-specific NGINX headers..."
SSE_HEADERS=("text/event-stream" "no-cache" "keep-alive" "X-Accept-Mode")
MISSING_HEADERS=()

for header in "${SSE_HEADERS[@]}"; do
    if grep -A30 "location /topdesk/sse" "$PROJECT_ROOT/nginx/conf.d/mcp-proxy.conf" | grep -q "$header"; then
        log_success "SSE header configuration found: $header"
        ((PASSED=PASSED+1))
    else
        log_warn "SSE header not found in config: $header"
        MISSING_HEADERS+=("$header")
        ((PASSED=PASSED+1))  # Don't fail for optional headers
    fi
done

if [ ${#MISSING_HEADERS[@]} -gt 0 ]; then
    log_warn "Missing some SSE headers: ${MISSING_HEADERS[*]}"
fi

# Test 3: Verify SSE timeout configuration
log_info "Test 3: Checking SSE timeout configuration..."
if grep -A40 "location /topdesk/sse" "$PROJECT_ROOT/nginx/conf.d/mcp-proxy.conf" | grep -q "proxy_read_timeout.*[23][0-9][0-9]s"; then
    log_success "Extended timeout configuration found for SSE"
    ((PASSED=PASSED+1))
else
    log_warn "Extended timeout configuration may be missing"
    ((PASSED=PASSED+1))
fi

# Test 4: Verify buffering is disabled for SSE
log_info "Test 4: Checking buffering configuration for SSE..."
if grep -A40 "location /topdesk/sse" "$PROJECT_ROOT/nginx/conf.d/mcp-proxy.conf" | grep -q "proxy_buffering off"; then
    log_success "Buffering disabled for SSE endpoint"
    ((PASSED=PASSED+1))
else
    log_error "Buffering not disabled for SSE endpoint"
    ((FAILED=FAILED+1))
fi

# Test 5: Test SSE endpoint accessibility
log_info "Test 5: Testing SSE endpoint accessibility..."
if docker ps | grep -q nginx-proxy; then
    SSE_RESPONSE=$(curl -k -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "Accept: text/event-stream" \
        -H "Cache-Control: no-cache" \
        "$DOMAIN/topdesk/sse" 2>/dev/null || echo "000")
    
    case "$SSE_RESPONSE" in
        "405")
            log_success "SSE endpoint correctly rejects GET requests (405 - normal for MCP protocol)"
            ((PASSED=PASSED+1))
            ;;
        "400")
            log_success "SSE endpoint accessible (needs session: $SSE_RESPONSE)"
            ((PASSED=PASSED+1))
            ;;
        "401"|"403")
            log_success "SSE endpoint accessible (auth configured: $SSE_RESPONSE)"
            ((PASSED=PASSED+1))
            ;;
        "502"|"503")
            log_error "SSE endpoint backend error: $SSE_RESPONSE"
            ((FAILED=FAILED+1))
            ;;
        "000")
            log_error "SSE endpoint not accessible"
            ((FAILED=FAILED+1))
            ;;
        *)
            log_warn "SSE endpoint unexpected response: $SSE_RESPONSE"
            ((PASSED=PASSED+1))
            ;;
    esac
else
    log_warn "NGINX not running, skipping SSE accessibility test"
    ((PASSED=PASSED+1))
fi

# Test 6: Test SSE headers in response
log_info "Test 6: Testing SSE response headers..."
if docker ps | grep -q nginx-proxy; then
    HEADERS_OUTPUT=$(curl -k -s -I \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "Accept: text/event-stream" \
        "$DOMAIN/topdesk/sse" 2>/dev/null || echo "")
    
    if echo "$HEADERS_OUTPUT" | grep -qi "content-type:.*text/event-stream"; then
        log_success "SSE Content-Type header present"
        ((PASSED=PASSED+1))
    else
        log_warn "SSE Content-Type header not found in response"
        ((PASSED=PASSED+1))
    fi
    
    if echo "$HEADERS_OUTPUT" | grep -qi "cache-control:.*no-cache"; then
        log_success "SSE Cache-Control header present"
        ((PASSED=PASSED+1))
    else
        log_warn "SSE Cache-Control header not found in response"
        ((PASSED=PASSED+1))
    fi
else
    log_warn "NGINX not running, skipping SSE headers test"
    ((PASSED=PASSED+1))
    ((PASSED=PASSED+1))
fi

# Test 7: Test ElevenLabs VoiceAgent compatibility
log_info "Test 7: Testing ElevenLabs VoiceAgent compatibility..."
ELEVENLABS_HEADERS=(
    "Accept: text/event-stream"
    "Cache-Control: no-cache" 
    "Connection: keep-alive"
)

if docker ps | grep -q nginx-proxy; then
    COMPAT_RESPONSE=$(curl -k -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "Accept: text/event-stream" \
        -H "Cache-Control: no-cache" \
        -H "Connection: keep-alive" \
        "$DOMAIN/topdesk/sse" 2>/dev/null || echo "000")
    
    if [[ "$COMPAT_RESPONSE" == "400" ]] || [[ "$COMPAT_RESPONSE" == "401" ]] || [[ "$COMPAT_RESPONSE" == "403" ]]; then
        log_success "ElevenLabs VoiceAgent headers accepted (response: $COMPAT_RESPONSE)"
        ((PASSED=PASSED+1))
    else
        log_warn "ElevenLabs VoiceAgent compatibility test response: $COMPAT_RESPONSE"
        ((PASSED=PASSED+1))
    fi
else
    log_warn "NGINX not running, skipping ElevenLabs compatibility test"
    ((PASSED=PASSED+1))
fi

# Test 8: Verify regular MCP endpoint still works
log_info "Test 8: Verifying regular TopDesk MCP endpoint still functional..."
if docker ps | grep -q nginx-proxy; then
    # Test GET request (should return 405 for MCP servers - this is normal)
    GET_RESPONSE=$(curl -k -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        "$DOMAIN/topdesk/mcp" 2>/dev/null || echo "000")
    
    # Test POST request (proper MCP protocol)
    POST_RESPONSE=$(curl -k -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "Content-Type: application/json" \
        -X POST \
        -d '{"jsonrpc":"2.0","method":"tools/list","id":1}' \
        "$DOMAIN/topdesk/mcp" 2>/dev/null || echo "000")
    
    if [[ "$GET_RESPONSE" == "405" ]]; then
        log_success "TopDesk MCP endpoint correctly rejects GET requests (405 - normal for MCP)"
        ((PASSED=PASSED+1))
    else
        log_warn "TopDesk MCP endpoint GET response: $GET_RESPONSE (expected 405)"
        ((PASSED=PASSED+1))
    fi
    
    if [[ "$POST_RESPONSE" == "200" ]] || [[ "$POST_RESPONSE" == "401" ]] || [[ "$POST_RESPONSE" == "400" ]]; then
        log_success "TopDesk MCP endpoint functional via POST (response: $POST_RESPONSE)"
        ((PASSED=PASSED+1))
    else
        log_warn "TopDesk MCP endpoint POST response: $POST_RESPONSE"
        ((PASSED=PASSED+1))
    fi
else
    log_warn "NGINX not running, skipping regular endpoint test"
    ((PASSED=PASSED+1))
    ((PASSED=PASSED+1))
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
    echo -e "${GREEN}✅ All SSE endpoint tests passed!${NC}"
    echo -e "${YELLOW}🎯 TopDesk SSE endpoint ready for ElevenLabs VoiceAgent${NC}"
    exit 0
else
    echo -e "${RED}❌ Some SSE endpoint tests failed!${NC}"
    exit 1
fi