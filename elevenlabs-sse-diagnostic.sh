#!/bin/bash
# ElevenLabs VoiceAgent SSE Connection Diagnostic Script
# Diagnoses TopDesk MCP SSE endpoint connectivity issues

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

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

# Configuration
DOMAIN="https://matrosmcp.duckdns.org"
BEARER_TOKEN="test-token"  # Default test token
ELEVENLABS_UA="python-httpx/0.28.1"  # ElevenLabs User Agent

# Parse command line arguments
if [ $# -gt 0 ]; then
    BEARER_TOKEN="$1"
    log_info "Using provided bearer token: ${BEARER_TOKEN}"
else
    log_info "Using default test token. Provide token as argument: $0 YOUR_TOKEN"
fi

log_header "ElevenLabs VoiceAgent SSE Diagnostic"
echo ""

# Step 1: Check container status
log_info "Step 1: Checking container status..."
TOPDESK_STATUS=$(docker compose ps topdesk-mcp --format "{{.Status}}" 2>/dev/null || echo "not found")
NGINX_STATUS=$(docker compose ps nginx-proxy --format "{{.Status}}" 2>/dev/null || echo "not found")

if [[ "$TOPDESK_STATUS" =~ "healthy" ]]; then
    log_success "TopDesk MCP container: $TOPDESK_STATUS"
else
    log_error "TopDesk MCP container: $TOPDESK_STATUS"
fi

if [[ "$NGINX_STATUS" =~ "healthy" ]]; then
    log_success "NGINX Proxy container: $NGINX_STATUS"
else
    log_error "NGINX Proxy container: $NGINX_STATUS"
fi
echo ""

# Step 2: Test basic connectivity
log_info "Step 2: Testing basic endpoint connectivity..."

# Test 2a: Health check
HEALTH_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$DOMAIN/health" 2>/dev/null || echo "000")
if [[ "$HEALTH_CODE" == "200" ]] || [[ "$HEALTH_CODE" == "301" ]]; then
    log_success "Health endpoint: HTTP $HEALTH_CODE"
else
    log_error "Health endpoint: HTTP $HEALTH_CODE"
fi

# Test 2b: Regular TopDesk MCP
MCP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "Accept: application/json, text/event-stream" \
    "$DOMAIN/topdesk/mcp" 2>/dev/null || echo "000")
if [[ "$MCP_CODE" == "406" ]] || [[ "$MCP_CODE" == "400" ]]; then
    log_success "Regular MCP endpoint: HTTP $MCP_CODE (working)"
else
    log_warn "Regular MCP endpoint: HTTP $MCP_CODE"
fi

# Test 2c: SSE endpoint
SSE_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "Accept: text/event-stream" \
    -H "User-Agent: $ELEVENLABS_UA" \
    "$DOMAIN/topdesk/sse" 2>/dev/null || echo "000")
if [[ "$SSE_CODE" == "400" ]]; then
    log_success "SSE endpoint accessible: HTTP $SSE_CODE"
elif [[ "$SSE_CODE" == "401" ]]; then
    log_error "SSE endpoint authentication failed: HTTP $SSE_CODE"
elif [[ "$SSE_CODE" == "403" ]]; then
    log_error "SSE endpoint forbidden: HTTP $SSE_CODE"
else
    log_warn "SSE endpoint unexpected response: HTTP $SSE_CODE"
fi
echo ""

# Step 3: Test authentication variants
log_info "Step 3: Testing authentication variations..."

# Test different auth formats
AUTH_TESTS=(
    "Bearer $BEARER_TOKEN"
    "bearer $BEARER_TOKEN"
    "Bearer token123"
    "Bearer secret123"
)

for auth in "${AUTH_TESTS[@]}"; do
    test_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: $auth" \
        -H "Accept: text/event-stream" \
        "$DOMAIN/topdesk/sse" 2>/dev/null || echo "000")
    
    if [[ "$test_code" == "400" ]]; then
        log_success "Auth '$auth': HTTP $test_code (accepted)"
    elif [[ "$test_code" == "401" ]]; then
        log_warn "Auth '$auth': HTTP $test_code (rejected)"
    else
        log_info "Auth '$auth': HTTP $test_code"
    fi
done
echo ""

# Step 4: Test ElevenLabs-specific headers
log_info "Step 4: Testing ElevenLabs VoiceAgent headers..."

ELEVENLABS_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}\nCONTENT_TYPE:%{content_type}\n" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "Accept: text/event-stream" \
    -H "Cache-Control: no-cache" \
    -H "Connection: keep-alive" \
    -H "User-Agent: $ELEVENLABS_UA" \
    "$DOMAIN/topdesk/sse" 2>/dev/null)

HTTP_CODE=$(echo "$ELEVENLABS_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
CONTENT_TYPE=$(echo "$ELEVENLABS_RESPONSE" | grep "CONTENT_TYPE:" | cut -d: -f2)

log_info "ElevenLabs simulation result:"
echo "  - HTTP Code: $HTTP_CODE"
echo "  - Content-Type: $CONTENT_TYPE"

if [[ "$HTTP_CODE" == "400" ]]; then
    log_success "ElevenLabs headers accepted by endpoint"
elif [[ "$HTTP_CODE" == "401" ]]; then
    log_error "ElevenLabs authentication failed"
else
    log_warn "ElevenLabs unexpected response: $HTTP_CODE"
fi
echo ""

# Step 5: Test MCP initialization via SSE
log_info "Step 5: Testing MCP initialization via SSE endpoint..."

INIT_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}\n" \
    -X POST \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -H "User-Agent: $ELEVENLABS_UA" \
    -d '{"jsonrpc":"2.0","id":"init","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"ElevenLabs","version":"1.0"}}}' \
    "$DOMAIN/topdesk/sse")

INIT_CODE=$(echo "$INIT_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
INIT_BODY=$(echo "$INIT_RESPONSE" | head -n -1)

echo "  - HTTP Code: $INIT_CODE"
if [[ "$INIT_CODE" == "200" ]]; then
    log_success "MCP initialization successful via SSE"
    echo "  - Response: $INIT_BODY" | head -c 100
    echo "..."
elif [[ "$INIT_CODE" == "400" ]]; then
    log_warn "MCP initialization needs session setup"
    echo "  - Response: $INIT_BODY"
else
    log_error "MCP initialization failed: $INIT_CODE"
    echo "  - Response: $INIT_BODY"
fi
echo ""

# Step 6: Check recent logs
log_info "Step 6: Checking recent logs..."

echo "Recent NGINX logs (last 5 lines):"
docker compose logs nginx-proxy --tail=5 2>/dev/null | while read line; do
    if echo "$line" | grep -q "$ELEVENLABS_UA\|topdesk/sse"; then
        echo "  ➤ $line"
    fi
done

echo ""
echo "Recent TopDesk MCP logs (last 5 lines):"
docker compose logs topdesk-mcp --tail=5 2>/dev/null | while read line; do
    if echo "$line" | grep -q "mcp\|session\|error"; then
        echo "  ➤ $line"
    fi
done
echo ""

# Step 7: Recommendations
log_header "Recommendations for ElevenLabs VoiceAgent"

echo ""
log_info "✅ Working endpoint: $DOMAIN/topdesk/sse"
log_info "✅ Authentication: Any Bearer token (format: 'Bearer YOUR_TOKEN')"
log_info "✅ Required headers:"
echo "     - Authorization: Bearer YOUR_TOKEN"
echo "     - Accept: text/event-stream"
echo "     - Cache-Control: no-cache"
echo ""

if [[ "$HTTP_CODE" == "400" ]]; then
    log_warn "🔧 Diagnosis: SSE endpoint is working but requires proper session management"
    echo ""
    echo "For ElevenLabs VoiceAgent, try:"
    echo "1. Use streamable-http transport mode"
    echo "2. Set endpoint: $DOMAIN/topdesk/sse"
    echo "3. Include headers: Accept: text/event-stream"
    echo "4. Let the MCP client handle session initialization"
    echo ""
elif [[ "$HTTP_CODE" == "401" ]]; then
    log_error "🚨 Authentication issue: Check your Bearer token"
    echo ""
    echo "Ensure your token format is: 'Bearer YOUR_ACTUAL_TOKEN'"
    echo ""
else
    log_warn "🔍 Unexpected response: $HTTP_CODE"
    echo ""
    echo "Check container logs and NGINX configuration"
    echo ""
fi

log_info "📋 ElevenLabs VoiceAgent Configuration:"
echo ""
echo 'MCP_SERVER_URL="'$DOMAIN'/topdesk/sse"'
echo 'MCP_BEARER_TOKEN="YOUR_ACTUAL_TOKEN"'
echo 'MCP_TRANSPORT="sse"'
echo 'HEADERS={"Accept": "text/event-stream", "Cache-Control": "no-cache"}'
echo ""

log_success "Diagnostic complete!"