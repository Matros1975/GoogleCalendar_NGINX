# Task Specification: TopDeskCustomMCP Development

## 🎯 Project Overview

**Objective**: Create a custom Python-based MCP (Model Context Protocol) server for TopDesk integration from scratch, avoiding the known bugs in existing topdesk-mcp packages.

**Context**: Recent investigation revealed that the existing PyPI package `topdesk-mcp` (v0.8.1) has documented parameter validation bugs in FastMCP integration, causing "Invalid request parameters" (-32602) errors. A direct, custom implementation is required.

## 📋 Requirements

### 1. Core Functionality
- **Language**: Python 3.11+
- **Framework**: Direct MCP implementation (NOT FastMCP due to known bugs)
- **Name**: `TopDeskCustomMCP`
- **Location**: `/home/ubuntu/GoogleCalendar_NGINX/Servers/TopDeskCustomMCP/`
- **Integration Base**: Use `/home/ubuntu/GoogleCalendar_NGINX/test.py` as reference for working TopDesk API connection

### 2. Security Requirements
- **Bearer Token Authentication**: Same pattern as GoogleCalendarMCP
- **Token Validation**: Implement robust bearer token validator
- **Environment Variables**: Secure credential management
- **Input Validation**: Strict parameter validation for all API calls

### 3. TopDesk API Integration
- **Base Configuration** (from test.py):
  ```python
  base_url = "https://pietervanforeest-test.topdesk.net/tas/api"
  username = "api_aipilots"
  password = "7w7j6-ytlqt-wpcbz-ywu6v-remw7"
  ```
- **Authentication**: Basic Auth with base64 encoding
- **Core Operations**: Incidents, Persons, Status tracking
- **Error Handling**: Comprehensive error mapping and logging

### 4. MCP Protocol Implementation
- **Protocol Version**: 2024-11-05
- **Transport**: HTTP with SSE (Server-Sent Events)
- **Methods**: initialize, tools/list, tools/call
- **Session Management**: Proper session ID handling
- **Compliance**: Full MCP specification adherence

### 5. Docker Integration
- **Container**: Standalone Docker container
- **Port**: 3002 (next available in sequence)
- **Health Checks**: Comprehensive health monitoring
- **Security**: Non-root user, minimal attack surface
- **Logging**: Structured logging with log rotation

## 🏗️ Architecture Requirements

### Directory Structure
```
Servers/TopDeskCustomMCP/
├── src/
│   ├── main.py                 # Entry point
│   ├── mcp_server.py          # MCP protocol implementation
│   ├── topdesk_client.py      # TopDesk API client
│   ├── auth/
│   │   ├── __init__.py
│   │   └── bearer_validator.py # Bearer token validation
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── incidents.py       # Incident operations
│   │   ├── persons.py         # Person operations
│   │   └── base.py           # Base handler class
│   ├── models/
│   │   ├── __init__.py
│   │   ├── mcp_types.py      # MCP data models
│   │   └── topdesk_types.py  # TopDesk data models
│   └── utils/
│       ├── __init__.py
│       ├── logging.py        # Logging utilities
│       └── validation.py    # Input validation
├── tests/
│   ├── unit/
│   │   ├── test_auth.py
│   │   ├── test_handlers.py
│   │   ├── test_mcp_server.py
│   │   └── test_topdesk_client.py
│   ├── integration/
│   │   ├── test_docker_health.py
│   │   ├── test_mcp_compliance.py
│   │   ├── test_security.py
│   │   └── test_topdesk_integration.py
│   └── conftest.py
├── Dockerfile
├── requirements.txt
├── docker-compose.test.yml
├── .env.example
└── README.md
```

## 🔧 Implementation Details

### Core Tools to Implement

1. **Incident Management**:
   ```python
   - topdesk_create_incident(caller_id, brief_description, request, category, priority)
   - topdesk_get_incident(incident_id)
   - topdesk_list_incidents(status, caller_id, limit)
   - topdesk_update_incident(incident_id, fields)
   - topdesk_add_action(incident_id, action_text)
   ```

2. **Person Management**:
   ```python
   - topdesk_get_person(person_id)
   - topdesk_search_persons(query)
   - topdesk_get_person_by_email(email)
   ```

3. **Status Operations**:
   ```python
   - topdesk_get_categories()
   - topdesk_get_priorities()
   - topdesk_get_incident_statuses()
   ```

### Parameter Mapping (Critical for Success)

Based on investigation, ensure correct parameter transformation:

**From MCP Call**:
```json
{
  "caller_id": "d34b277f-e6a2-534c-a96b-23bf383cb4a1",
  "brief_description": "Cannot login to Windows",
  "request": "User Jacob cannot login...",
  "category": "Core applicaties", 
  "priority": "P1 (I&A)"
}
```

**To TopDesk API**:
```json
{
  "briefDescription": "Cannot login to Windows",
  "request": "User Jacob cannot login...",
  "caller": {"id": "d34b277f-e6a2-534c-a96b-23bf383cb4a1"},
  "category": {"name": "Core applicaties"},
  "priority": {"name": "P1 (I&A)"}
}
```

## 🧪 Testing Requirements

### Unit Tests (90%+ Coverage)
- **Authentication**: Bearer token validation
- **MCP Protocol**: All protocol methods
- **TopDesk Client**: API call construction and response parsing
- **Handlers**: All tool implementations
- **Validation**: Input parameter validation

### Integration Tests
1. **Docker Health Tests**:
   ```python
   def test_container_startup()
   def test_health_endpoint()
   def test_container_security()
   def test_resource_limits()
   ```

2. **MCP Compliance Tests**:
   ```python
   def test_mcp_initialization()
   def test_tools_list_compliance()
   def test_tools_call_compliance()
   def test_session_management()
   def test_error_responses()
   ```

3. **Security Tests**:
   ```python
   def test_bearer_token_required()
   def test_invalid_token_rejection()
   def test_token_extraction()
   def test_unauthorized_access()
   ```

4. **TopDesk Integration Tests**:
   ```python
   def test_incident_creation()
   def test_person_lookup()
   def test_parameter_mapping()
   def test_api_error_handling()
   def test_network_resilience()
   ```

### Test Data Factory
Create comprehensive test data factory similar to existing MCP patterns:
```python
class TopDeskTestDataFactory:
    @staticmethod
    def create_valid_incident_data():
        return {
            "caller_id": "d34b277f-e6a2-534c-a96b-23bf383cb4a1",
            "brief_description": "Test incident",
            "request": "Test request details",
            "category": "Core applicaties",
            "priority": "P2 (Normaal)"
        }
    
    @staticmethod  
    def create_invalid_incident_data():
        # Various invalid scenarios for testing
```

## 🐳 Docker Configuration

### Dockerfile Requirements
```dockerfile
FROM python:3.11-slim

# Security: non-root user
RUN useradd -m -u 1001 -s /bin/bash topdeskuser

# Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application
COPY src/ /app/src/
WORKDIR /app

# Security settings
USER topdeskuser
EXPOSE 3002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:3002/health || exit 1

CMD ["python", "-m", "src.main"]
```

### Environment Variables
```bash
# TopDesk API Configuration
TOPDESK_BASE_URL=https://pietervanforeest-test.topdesk.net/tas/api
TOPDESK_USERNAME=api_aipilots
TOPDESK_PASSWORD=7w7j6-ytlqt-wpcbz-ywu6v-remw7

# MCP Server Configuration  
MCP_HOST=0.0.0.0
MCP_PORT=3002
MCP_LOG_LEVEL=INFO

# Security
BEARER_TOKENS=["your-bearer-token-here"]
```

## 📊 Integration Points

### Docker Compose Integration
Add to main `docker-compose.yml`:
```yaml
  topdesk-custom-mcp:
    build: ./Servers/TopDeskCustomMCP
    container_name: topdesk-custom-mcp
    ports:
      - "3002:3002"
    environment:
      - TOPDESK_BASE_URL=${TOPDESK_BASE_URL}
      - TOPDESK_USERNAME=${TOPDESK_USERNAME}  
      - TOPDESK_PASSWORD=${TOPDESK_PASSWORD}
      - BEARER_TOKENS=${TOPDESK_BEARER_TOKENS}
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:3002/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
```

### NGINX Configuration
Create `/nginx/conf.d/topdesk-custom-proxy.conf`:
```nginx
location /topdesk-custom/ {
    proxy_pass http://topdesk-custom-mcp:3002/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # SSE support
    proxy_buffering off;
    proxy_cache off;
    proxy_set_header Connection '';
    proxy_http_version 1.1;
    chunked_transfer_encoding off;
}
```

## 🔍 Quality Assurance

### MCP Best Practices Validation
1. **Protocol Compliance**: Strict adherence to MCP 2024-11-05 specification
2. **Error Handling**: Proper JSON-RPC error codes and messages
3. **Type Safety**: Comprehensive type hints and validation
4. **Logging**: Structured logging with correlation IDs
5. **Performance**: Response time under 500ms for simple operations

### Code Quality
- **Type Hints**: 100% type coverage
- **Linting**: Black, flake8, mypy compliance
- **Documentation**: Comprehensive docstrings and README
- **Security**: No hardcoded credentials, input sanitization

## 🚀 Delivery Criteria

### Must Have (P0)
- ✅ Working MCP server with bearer token auth
- ✅ Docker container with health checks
- ✅ Core incident management tools
- ✅ Person lookup functionality
- ✅ 90%+ unit test coverage
- ✅ Integration with existing infrastructure

### Should Have (P1) 
- ✅ Comprehensive integration tests
- ✅ MCP compliance validation
- ✅ Security testing suite
- ✅ Performance benchmarks
- ✅ Documentation and examples

### Could Have (P2)
- ✅ Advanced TopDesk features (attachments, time tracking)
- ✅ Metrics and monitoring endpoints
- ✅ Rate limiting and caching
- ✅ Advanced error recovery

## 📚 Reference Materials

### Working Code Reference
- **Base API Connection**: `/home/ubuntu/GoogleCalendar_NGINX/test.py`
- **Security Pattern**: `/home/ubuntu/GoogleCalendar_NGINX/Servers/GoogleCalendarMCP/src/auth/bearerTokenValidator.ts`
- **Project Structure**: `/home/ubuntu/GoogleCalendar_NGINX/Servers/GoogleCalendarMCP/`

### Known Issues to Avoid
1. **FastMCP Parameter Validation**: Don't use FastMCP - implement MCP protocol directly
2. **Parameter Mapping**: Ensure correct transformation between MCP calls and TopDesk API
3. **JSON-RPC Compliance**: Strict adherence to avoid -32602 errors
4. **Transport Layer**: Proper SSE implementation for real-time responses

### TopDesk API Documentation
- **Test Instance**: https://pietervanforeest-test.topdesk.net/tas/api
- **Authentication**: Basic Auth with api_aipilots:7w7j6-ytlqt-wpcbz-ywu6v-remw7
- **Key Endpoints**: /incidents, /persons, /incidents/statuses

## 🎯 Success Metrics

### Functional Success
- All tools work correctly with real TopDesk test instance
- Bearer token authentication prevents unauthorized access
- Docker container starts healthy and passes all health checks
- MCP protocol compliance passes validation

### Technical Success  
- 90%+ unit test coverage
- All integration tests pass
- Performance: <500ms response time for simple operations
- Security: No vulnerabilities in security scan

### Integration Success
- Seamless integration with existing multi-MCP infrastructure
- NGINX proxy configuration works correctly
- ElevenLabs voice agent can successfully call all tools
- No interference with existing GoogleCalendar MCP

## 🔧 Implementation Notes for Autonomous Agent

### Start Here
1. **Create Directory Structure**: Follow the exact structure specified
2. **Copy Security Patterns**: Use GoogleCalendarMCP bearer token implementation as template
3. **Implement MCP Protocol**: Direct implementation, NOT FastMCP
4. **Use test.py as API Reference**: Working TopDesk connection patterns

### Critical Success Factors
1. **Parameter Mapping**: This is where existing packages fail - ensure correct transformation
2. **Bearer Token Auth**: Must match existing pattern exactly
3. **Docker Integration**: Follow existing container patterns
4. **Testing**: Comprehensive test suite is mandatory for reliability

### Avoid These Pitfalls
1. **Don't use FastMCP or existing topdesk-mcp packages** - they have documented bugs
2. **Don't skip parameter mapping validation** - this is the root cause of existing failures
3. **Don't implement without tests** - testing is critical for MCP reliability
4. **Don't hardcode credentials** - use environment variables consistently

This specification provides complete guidance for building a robust, secure, and fully-tested TopDeskCustomMCP that avoids all known issues with existing implementations.