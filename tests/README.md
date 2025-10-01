# Infrastructure Test Suite

This directory contains automated infrastructure tests for the Google Calendar MCP deployment with NGINX proxy.

## Overview

The test suite validates the entire deployment stack including:
- Container orchestration and startup
- Network connectivity and endpoints
- Health checks and monitoring
- Security (bearer tokens, TLS/SSL)
- Configuration validation

## Test Scripts

### Individual Tests

1. **01-container-startup.sh** - Container Startup Test
   - Validates docker-compose.yml syntax
   - Tests container startup and health status
   - Checks resource usage

2. **02-endpoint-reachability.sh** - Endpoint Reachability Test
   - Tests HTTP/HTTPS health endpoints
   - Validates NGINX upstream connectivity
   - Tests OAuth endpoints
   - Checks inter-container networking

3. **03-health-check.sh** - Health Check Test
   - Validates Docker health checks
   - Tests MCP /health endpoint
   - Monitors container restart counts
   - Checks process health

4. **04-bearer-token-security.sh** - Bearer Token Security Test
   - Tests authentication with/without tokens
   - Validates token rejection logic
   - Tests rate limiting
   - Ensures proper access control

5. **05-tls-certificates.sh** - TLS Certificates Test
   - Tests TLS handshake
   - Validates certificate expiration
   - Checks supported TLS versions
   - Tests HSTS headers
   - Validates certificate chain

6. **06-yaml-validation.sh** - YAML Configuration Test
   - Validates docker-compose.yml syntax
   - Checks service definitions
   - Validates network and volume configs
   - Checks security settings

### Master Test Runner

**run-all-tests.sh** - Runs all tests in sequence with comprehensive reporting

Usage:
```bash
# Run all tests
./tests/infrastructure/run-all-tests.sh

# Run only quick tests (no container startup)
./tests/infrastructure/run-all-tests.sh --quick

# Run only security tests
./tests/infrastructure/run-all-tests.sh --security

# Clean up containers after tests
./tests/infrastructure/run-all-tests.sh --cleanup

# Save results to file
./tests/infrastructure/run-all-tests.sh --save-results results.txt

# Show help
./tests/infrastructure/run-all-tests.sh --help
```

## Running Tests

### Prerequisites

- Docker and Docker Compose installed
- Project built and configured
- OAuth credentials in place (for full tests)
- Containers running (for most tests)

### Quick Start

```bash
# Start containers
cd /path/to/project
docker compose up -d

# Run all tests
./tests/infrastructure/run-all-tests.sh

# Or run individual tests
./tests/infrastructure/01-container-startup.sh
```

### Test Modes

#### All Tests (Default)
Runs the complete test suite including container startup, security, and configuration validation.

```bash
./tests/infrastructure/run-all-tests.sh --all
```

#### Quick Mode
Runs only YAML validation without starting containers. Useful for CI/CD pipelines.

```bash
./tests/infrastructure/run-all-tests.sh --quick
```

#### Security Mode
Focuses on security-related tests: container startup, bearer tokens, and TLS certificates.

```bash
./tests/infrastructure/run-all-tests.sh --security
```

## Test Results

Tests output color-coded results:
- 🟢 **GREEN** - Test passed
- 🟡 **YELLOW** - Warning (test passed with notes)
- 🔴 **RED** - Test failed

### Interpreting Results

- **PASS** - All checks passed successfully
- **WARN** - Test passed but has warnings (non-critical)
- **FAIL** - Critical test failure that needs attention

### Baseline Testing

Before any major changes:
1. Run the full test suite
2. Save results for comparison
3. Document any expected failures

```bash
./tests/infrastructure/run-all-tests.sh --save-results baseline-results.txt
```

After changes:
1. Run tests again
2. Compare with baseline
3. Investigate any new failures

```bash
./tests/infrastructure/run-all-tests.sh --save-results post-refactor-results.txt
diff baseline-results.txt post-refactor-results.txt
```

## CI/CD Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Infrastructure Tests
  run: |
    docker compose up -d
    sleep 30
    ./tests/infrastructure/run-all-tests.sh --save-results test-results.txt
    
- name: Upload Test Results
  uses: actions/upload-artifact@v2
  with:
    name: test-results
    path: test-results.txt
```

## Troubleshooting

### Common Issues

**Tests fail due to timing**
- Some tests may fail if containers haven't fully started
- Wait 30-60 seconds after `docker compose up` before testing
- Health checks may need time to complete

**Certificate tests fail**
- Expected if using self-signed certificates in development
- Tests will warn but not fail for self-signed certs
- For production, ensure Let's Encrypt certificates are properly configured

**Bearer token tests fail**
- Ensure tokens are configured in `nginx/auth/tokens`
- Check `.env.production` for token configuration
- May need to run `./manage-tokens.sh` to generate tokens

**Port conflicts**
- Ensure no other services are using ports 80, 443, or OAuth ports (3500-3505)
- Check with `netstat -tuln | grep :80` or similar

### Debug Mode

For detailed output, run individual tests directly:

```bash
bash -x ./tests/infrastructure/01-container-startup.sh
```

## Maintenance

### Adding New Tests

1. Create a new test script in `tests/infrastructure/`
2. Follow the naming convention: `NN-test-name.sh`
3. Use the standard test template (see existing tests)
4. Update `run-all-tests.sh` to include the new test
5. Update this README

### Test Template

```bash
#!/bin/bash
set -e

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

PASSED=0
FAILED=0

# Test implementation here

# Summary
if [[ $FAILED -eq 0 ]]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed!${NC}"
    exit 1
fi
```

## Support

For issues or questions about the test suite:
1. Check container logs: `docker compose logs`
2. Review test output for specific errors
3. Consult project documentation
4. Open an issue with test results attached
