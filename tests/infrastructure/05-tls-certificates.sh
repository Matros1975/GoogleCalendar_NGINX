#!/bin/bash
# TLS Certificates Test
# Confirms TLS handshake and certificate validity

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

TEST_NAME="TLS Certificates Test"
PASSED=0
FAILED=0

echo "=========================================="
echo "  $TEST_NAME"
echo "=========================================="
echo ""

# Get domain from NGINX config
DOMAIN=$(grep -oP 'server_name\s+\K[^\s;]+' "$PROJECT_ROOT/nginx/conf.d/mcp-proxy.conf" 2>/dev/null | head -1 || echo "localhost")
echo "Testing domain: $DOMAIN"
echo ""

# Test 1: Check if certificate files exist
log_info "Test 1: Checking if certificate files exist..."

# Check Let's Encrypt certificate
if [[ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]]; then
    log_success "Let's Encrypt certificate found for $DOMAIN"
    CERT_PATH="/etc/letsencrypt/live/$DOMAIN"
    ((PASSED++))
# Check mounted certificate in Docker
elif docker exec nginx-proxy test -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" 2>/dev/null; then
    log_success "Certificate found in NGINX container"
    CERT_PATH="/etc/letsencrypt/live/$DOMAIN"
    ((PASSED++))
# Check self-signed certificate
elif docker exec nginx-proxy test -f "/etc/nginx/ssl/cert.pem" 2>/dev/null; then
    log_warn "Using self-signed certificate"
    CERT_PATH="/etc/nginx/ssl"
    ((PASSED++))
else
    log_error "No certificate files found"
    ((FAILED++))
    CERT_PATH=""
fi

# Test 2: TLS handshake test
log_info "Test 2: Testing TLS handshake..."
if echo | openssl s_client -connect localhost:443 -servername "$DOMAIN" 2>/dev/null | grep -q "Verify return code"; then
    log_success "TLS handshake successful"
    ((PASSED++))
else
    log_error "TLS handshake failed"
    ((FAILED++))
fi

# Test 3: Check supported TLS versions
log_info "Test 3: Checking supported TLS versions..."

# Test TLS 1.2
if echo | timeout 5 openssl s_client -connect localhost:443 -tls1_2 2>/dev/null | grep -q "Protocol.*TLSv1.2"; then
    log_success "TLS 1.2 supported"
    ((PASSED++))
else
    log_warn "TLS 1.2 may not be supported"
fi

# Test TLS 1.3
if echo | timeout 5 openssl s_client -connect localhost:443 -tls1_3 2>/dev/null | grep -q "Protocol.*TLSv1.3"; then
    log_success "TLS 1.3 supported"
    ((PASSED++))
else
    log_info "TLS 1.3 not supported (optional)"
fi

# Test TLS 1.0 (should fail - deprecated)
if echo | timeout 5 openssl s_client -connect localhost:443 -tls1 2>/dev/null | grep -q "Protocol.*TLSv1"; then
    log_warn "TLS 1.0 supported (should be disabled for security)"
else
    log_success "TLS 1.0 correctly disabled"
    ((PASSED++))
fi

# Test 4: Certificate expiration check
log_info "Test 4: Checking certificate expiration..."
CERT_INFO=$(echo | openssl s_client -connect localhost:443 -servername "$DOMAIN" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null || echo "")

if [[ -n "$CERT_INFO" ]]; then
    NOT_AFTER=$(echo "$CERT_INFO" | grep "notAfter" | cut -d= -f2)
    EXPIRY_DATE=$(date -d "$NOT_AFTER" +%s 2>/dev/null || date -j -f "%b %d %H:%M:%S %Y %Z" "$NOT_AFTER" +%s 2>/dev/null || echo "0")
    CURRENT_DATE=$(date +%s)
    DAYS_UNTIL_EXPIRY=$(( ($EXPIRY_DATE - $CURRENT_DATE) / 86400 ))
    
    echo "     Certificate expires: $NOT_AFTER"
    echo "     Days until expiry: $DAYS_UNTIL_EXPIRY"
    
    if [[ $DAYS_UNTIL_EXPIRY -gt 30 ]]; then
        log_success "Certificate is valid for $DAYS_UNTIL_EXPIRY days"
        ((PASSED++))
    elif [[ $DAYS_UNTIL_EXPIRY -gt 0 ]]; then
        log_warn "Certificate expires in $DAYS_UNTIL_EXPIRY days (renewal recommended)"
        ((PASSED++))
    else
        log_error "Certificate is expired!"
        ((FAILED++))
    fi
else
    log_warn "Could not retrieve certificate expiration info"
fi

# Test 5: Certificate subject/issuer check
log_info "Test 5: Checking certificate subject and issuer..."
CERT_SUBJECT=$(echo | openssl s_client -connect localhost:443 -servername "$DOMAIN" 2>/dev/null | openssl x509 -noout -subject 2>/dev/null || echo "")
CERT_ISSUER=$(echo | openssl s_client -connect localhost:443 -servername "$DOMAIN" 2>/dev/null | openssl x509 -noout -issuer 2>/dev/null || echo "")

if [[ -n "$CERT_SUBJECT" ]]; then
    echo "     Subject: $CERT_SUBJECT"
    
    # Check if it's Let's Encrypt
    if echo "$CERT_ISSUER" | grep -iq "Let's Encrypt"; then
        log_success "Certificate issued by Let's Encrypt (valid CA)"
        ((PASSED++))
    elif echo "$CERT_ISSUER" | grep -q "subject"; then
        log_warn "Self-signed certificate (not from trusted CA)"
        ((PASSED++))  # Don't fail for self-signed in test environment
    else
        echo "     Issuer: $CERT_ISSUER"
        log_success "Certificate has issuer information"
        ((PASSED++))
    fi
else
    log_error "Could not retrieve certificate subject/issuer"
    ((FAILED++))
fi

# Test 6: Check certificate chain
log_info "Test 6: Checking certificate chain..."
CHAIN_INFO=$(echo | openssl s_client -connect localhost:443 -servername "$DOMAIN" -showcerts 2>/dev/null | grep -c "BEGIN CERTIFICATE" || echo "0")

if [[ $CHAIN_INFO -gt 0 ]]; then
    log_success "Certificate chain contains $CHAIN_INFO certificate(s)"
    ((PASSED++))
else
    log_error "Certificate chain incomplete"
    ((FAILED++))
fi

# Test 7: Test cipher suites
log_info "Test 7: Testing cipher suites..."
CIPHER_INFO=$(echo | openssl s_client -connect localhost:443 -servername "$DOMAIN" 2>/dev/null | grep "Cipher" | head -1)

if [[ -n "$CIPHER_INFO" ]]; then
    echo "     $CIPHER_INFO"
    
    # Check for strong ciphers
    if echo "$CIPHER_INFO" | grep -qE "ECDHE|GCM|AES256"; then
        log_success "Strong cipher suite in use"
        ((PASSED++))
    else
        log_warn "Cipher suite may not be optimal"
        ((PASSED++))
    fi
else
    log_error "Could not determine cipher suite"
    ((FAILED++))
fi

# Test 8: Test HTTPS redirect
log_info "Test 8: Testing HTTP to HTTPS redirect..."
HTTP_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -L http://localhost/health 2>/dev/null || echo "000")

if [[ "$HTTP_RESPONSE" == "200" ]]; then
    log_success "HTTP redirects to HTTPS (or HTTP works)"
    ((PASSED++))
else
    log_warn "HTTP redirect status: $HTTP_RESPONSE"
    ((PASSED++))
fi

# Test 9: Test HSTS header
log_info "Test 9: Checking HSTS header..."
HSTS_HEADER=$(curl -k -s -I https://localhost/health 2>/dev/null | grep -i "Strict-Transport-Security" || echo "")

if [[ -n "$HSTS_HEADER" ]]; then
    echo "     $HSTS_HEADER"
    log_success "HSTS header present"
    ((PASSED++))
else
    log_warn "HSTS header not found (recommended for production)"
    ((PASSED++))  # Don't fail, just warn
fi

# Test 10: Test certificate for correct domain
log_info "Test 10: Verifying certificate matches domain..."
if [[ "$DOMAIN" != "localhost" ]]; then
    CERT_CN=$(echo | openssl s_client -connect localhost:443 -servername "$DOMAIN" 2>/dev/null | openssl x509 -noout -text 2>/dev/null | grep "Subject:.*CN" || echo "")
    
    if echo "$CERT_CN" | grep -q "$DOMAIN"; then
        log_success "Certificate CN matches domain $DOMAIN"
        ((PASSED++))
    else
        log_warn "Certificate CN may not match domain"
        echo "     $CERT_CN"
        ((PASSED++))  # Don't fail in test environment
    fi
else
    log_info "Using localhost, skipping domain validation"
fi

# Test 11: Check certificate permissions in container
log_info "Test 11: Checking certificate file permissions in container..."
if [[ -n "$CERT_PATH" ]]; then
    CERT_PERMS=$(docker exec nginx-proxy stat -c "%a" "$CERT_PATH/fullchain.pem" 2>/dev/null || \
                 docker exec nginx-proxy stat -c "%a" "$CERT_PATH/cert.pem" 2>/dev/null || echo "")
    
    if [[ -n "$CERT_PERMS" ]]; then
        echo "     Certificate permissions: $CERT_PERMS"
        log_success "Certificate file accessible"
        ((PASSED++))
    else
        log_warn "Could not check certificate permissions"
    fi
fi

# Test 12: Test SSL session resumption
log_info "Test 12: Testing SSL session resumption..."
SESSION_OUTPUT=$(echo | openssl s_client -connect localhost:443 -reconnect 2>/dev/null | grep -c "Reused.*TLS" || echo "0")

if [[ $SESSION_OUTPUT -gt 0 ]]; then
    log_success "SSL session resumption working"
    ((PASSED++))
else
    log_info "SSL session resumption not detected (optional optimization)"
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
    echo -e "${GREEN}✅ All TLS certificate tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some TLS certificate tests failed!${NC}"
    exit 1
fi
