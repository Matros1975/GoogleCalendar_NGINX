# Task Specification: ElevenLabs Webhook Microservice

## Project Overview
Create a new Python-based microservice to handle ElevenLabs post-call webhooks. The service must follow existing infrastructure patterns in this repository and be deployed as a containerized service behind NGINX proxy.

## Reference Documentation
- **ElevenLabs Webhook Documentation**: https://elevenlabs.io/docs/agents-platform/workflows/post-call-webhooks
- **Existing Service Examples**: 
  - `/home/ubuntu/GoogleCalendar_NGINX/Servers/TopDeskCustomMCP/` (Python-based MCP server)
  - `/home/ubuntu/GoogleCalendar_NGINX/docker-compose.yml` (service configuration)
  - `/home/ubuntu/GoogleCalendar_NGINX/nginx/conf.d/mcp-proxy.conf` (NGINX routing)

## Service Requirements

### 1. Directory Structure
Follow the existing pattern in `Servers/` directory:
```
Servers/ElevenLabsWebhook/
├── src/
│   ├── main.py                    # Application entry point
│   ├── webhook_handler.py         # Core webhook processing logic
│   ├── auth/
│   │   └── hmac_validator.py      # HMAC signature validation
│   ├── handlers/
│   │   ├── transcription_handler.py    # post_call_transcription handler
│   │   ├── audio_handler.py            # post_call_audio handler
│   │   └── call_failure_handler.py     # call_initiation_failure handler
│   ├── models/
│   │   └── webhook_models.py      # Data models for webhook payloads
│   └── utils/
│       ├── logger.py              # Logging configuration
│       └── storage.py             # Optional: conversation storage
├── tests/
│   ├── unit/
│   │   ├── test_hmac_validator.py
│   │   ├── test_transcription_handler.py
│   │   ├── test_audio_handler.py
│   │   └── test_call_failure_handler.py
│   └── integration/
│       └── test_webhook_endpoint.py
├── examples/
│   ├── test_payload_transcription.json
│   ├── test_payload_audio.json
│   └── test_payload_call_failure.json
├── Dockerfile
├── requirements.txt
├── README.md
└── .env.example
```

### 2. Core Functionality

#### 2.1 Webhook Endpoint
Implement POST endpoint `/webhook` that:
- Accepts all three webhook types:
  - `post_call_transcription` - Full conversation data with transcripts
  - `post_call_audio` - Base64-encoded MP3 audio
  - `call_initiation_failure` - Failed call metadata
- Returns 200 status code for successful processing
- Handles chunked transfer encoding for large audio files
- Implements proper error handling and logging

#### 2.2 HMAC Authentication
Implement HMAC signature validation following ElevenLabs spec:
- Header format: `elevenlabs-signature: t=timestamp,v0=hash`
- Hash validation: `sha256(timestamp.request_body)`
- Timestamp tolerance: 30 minutes (1800 seconds)
- Secret stored in environment variable: `ELEVENLABS_WEBHOOK_SECRET`
- Return 401 Unauthorized for invalid signatures
- Return 400 Bad Request for expired timestamps

#### 2.3 Webhook Handlers
Create specialized handlers for each webhook type:

**TranscriptionHandler:**
- Parse full conversation transcript
- Extract metadata (duration, cost, timestamps)
- Process analysis results (evaluation, summary)
- Handle dynamic variables
- Store/log conversation data
- Support for new fields (has_audio, has_user_audio, has_response_audio) coming August 2025

**AudioHandler:**
- Handle chunked/streaming requests
- Decode base64 audio to MP3
- Optional: Save audio files to storage
- Log conversation_id and agent_id
- Handle large file processing efficiently

**CallFailureHandler:**
- Parse failure metadata (SIP vs Twilio format)
- Log failure reasons (busy, no-answer, unknown)
- Extract provider-specific details
- Support monitoring/alerting integration

#### 2.4 Testing Utilities
Create test function to simulate webhook calls:
```python
async def test_webhook(payload_file: str, secret: str):
    """
    Test webhook endpoint with a payload file.
    
    Args:
        payload_file: Path to JSON payload file
        secret: HMAC secret for signature generation
    
    Returns:
        Response status and data
    """
    # Load payload
    # Generate valid HMAC signature
    # Make POST request to endpoint
    # Return results
```

### 3. Configuration

#### 3.1 Environment Variables (.env.example)
```bash
# ElevenLabs Webhook Configuration
ELEVENLABS_WEBHOOK_SECRET=your-webhook-secret-here
ELEVENLABS_WEBHOOK_HOST=0.0.0.0
ELEVENLABS_WEBHOOK_PORT=3004

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Optional: Storage
AUDIO_STORAGE_PATH=/app/storage/audio
TRANSCRIPT_STORAGE_PATH=/app/storage/transcripts
ENABLE_AUDIO_STORAGE=false
ENABLE_TRANSCRIPT_STORAGE=true

# Optional: Database (for future stateful conversation tracking)
# DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

#### 3.2 Python Dependencies (requirements.txt)
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
python-multipart>=0.0.6
aiofiles>=23.2.1
httpx>=0.25.0
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
```

### 4. Docker Integration

#### 4.1 Dockerfile
Follow the TopDeskCustomMCP pattern:
- Base image: `python:3.11-slim`
- Non-root user: `elevenlabsuser` (UID 1001)
- Working directory: `/app`
- Expose port: `3004`
- Health check endpoint: `/health`
- Security: no-new-privileges, read-only root filesystem (with /tmp tmpfs)

#### 4.2 docker-compose.yml Integration
Add new service following existing pattern:
```yaml
elevenlabs-webhook:
  build: ./Servers/ElevenLabsWebhook
  container_name: elevenlabs-webhook
  restart: unless-stopped
  
  env_file:
    - .env
  
  networks:
    - mcp-internal
  
  environment:
    - HOST=${ELEVENLABS_WEBHOOK_HOST:-0.0.0.0}
    - PORT=${ELEVENLABS_WEBHOOK_PORT:-3004}
    - LOG_LEVEL=${LOG_LEVEL:-INFO}
  
  volumes:
    # Optional: Persistent storage for audio/transcripts
    - elevenlabs-storage:/app/storage
  
  deploy:
    resources:
      limits:
        memory: 512M
        cpus: "1.0"
      reservations:
        memory: 256M
        cpus: "0.5"
  
  security_opt:
    - no-new-privileges:true
    - apparmor:unconfined
  
  read_only: true
  tmpfs:
    - /tmp
    - /app/logs
  
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:3004/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 10s
```

Add volume definition:
```yaml
volumes:
  elevenlabs-storage:
    driver: local
```

#### 4.3 NGINX Configuration
Add to `/nginx/conf.d/mcp-proxy.conf`:

```nginx
# Upstream for ElevenLabs Webhook service
upstream elevenlabs_webhook_backend {
    server elevenlabs-webhook:3004;
    keepalive 32;
}

# In the main server block, add location:
    # ElevenLabs Webhook endpoint
    location /elevenlabs/webhook {
        # IP whitelisting - ElevenLabs static IPs
        # US Default
        allow 34.67.146.145;
        allow 34.59.11.47;
        # EU
        allow 35.204.38.71;
        allow 34.147.113.54;
        # Asia
        allow 35.185.187.110;
        allow 35.247.157.189;
        # EU Residency
        allow 34.77.234.246;
        allow 34.140.184.144;
        # India Residency
        allow 34.93.26.174;
        allow 34.93.252.69;
        deny all;
        
        # Remove authentication requirement (handled by HMAC)
        auth_request off;
        
        # Proxy settings
        proxy_pass http://elevenlabs_webhook_backend/webhook;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Handle large payloads (audio webhooks can be large)
        client_max_body_size 100M;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
        
        # Enable buffering for chunked encoding
        proxy_request_buffering off;
        proxy_buffering off;
    }
    
    # Health check endpoint (no IP restriction)
    location /elevenlabs/health {
        auth_request off;
        proxy_pass http://elevenlabs_webhook_backend/health;
        proxy_http_version 1.1;
        access_log off;
    }
```

### 5. Implementation Details

#### 5.1 Main Application (src/main.py)
```python
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
import logging
import os

from src.auth.hmac_validator import HMACValidator
from src.handlers.transcription_handler import TranscriptionHandler
from src.handlers.audio_handler import AudioHandler
from src.handlers.call_failure_handler import CallFailureHandler
from src.utils.logger import setup_logger

app = FastAPI(title="ElevenLabs Webhook Service", version="1.0.0")
logger = setup_logger()

# Initialize components
hmac_validator = HMACValidator(
    secret=os.getenv('ELEVENLABS_WEBHOOK_SECRET', '')
)
transcription_handler = TranscriptionHandler()
audio_handler = AudioHandler()
call_failure_handler = CallFailureHandler()

@app.get("/health")
async def health_check():
    """Health check endpoint for Docker/NGINX monitoring."""
    return {"status": "healthy", "service": "elevenlabs-webhook"}

@app.post("/webhook")
async def webhook_endpoint(
    request: Request,
    elevenlabs_signature: str = Header(None, alias="elevenlabs-signature")
):
    """
    Main webhook endpoint for ElevenLabs post-call webhooks.
    Handles three types: post_call_transcription, post_call_audio, call_initiation_failure
    """
    try:
        # Read request body
        body = await request.body()
        
        # Validate HMAC signature
        if not hmac_validator.validate(elevenlabs_signature, body):
            logger.warning("Invalid HMAC signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse JSON payload
        import json
        payload = json.loads(body.decode('utf-8'))
        
        # Route to appropriate handler based on type
        webhook_type = payload.get("type")
        
        if webhook_type == "post_call_transcription":
            result = await transcription_handler.handle(payload)
        elif webhook_type == "post_call_audio":
            result = await audio_handler.handle(payload)
        elif webhook_type == "call_initiation_failure":
            result = await call_failure_handler.handle(payload)
        else:
            logger.error(f"Unknown webhook type: {webhook_type}")
            raise HTTPException(status_code=400, detail="Unknown webhook type")
        
        logger.info(f"Successfully processed {webhook_type} webhook")
        return JSONResponse(content={"status": "received"}, status_code=200)
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON payload")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    host = os.getenv('ELEVENLABS_WEBHOOK_HOST', '0.0.0.0')
    port = int(os.getenv('ELEVENLABS_WEBHOOK_PORT', 3004))
    uvicorn.run(app, host=host, port=port)
```

#### 5.2 HMAC Validator (src/auth/hmac_validator.py)
```python
import hmac
import time
from hashlib import sha256
import logging

logger = logging.getLogger(__name__)

class HMACValidator:
    """Validates ElevenLabs webhook HMAC signatures."""
    
    def __init__(self, secret: str, tolerance_seconds: int = 1800):
        """
        Args:
            secret: HMAC secret from ElevenLabs webhook configuration
            tolerance_seconds: Maximum age of timestamp (default 30 minutes)
        """
        self.secret = secret
        self.tolerance_seconds = tolerance_seconds
    
    def validate(self, signature_header: str, payload: bytes) -> bool:
        """
        Validate HMAC signature from elevenlabs-signature header.
        
        Args:
            signature_header: Header value "t=timestamp,v0=hash"
            payload: Raw request body bytes
            
        Returns:
            True if signature is valid, False otherwise
        """
        if not signature_header:
            logger.warning("Missing signature header")
            return False
        
        try:
            # Parse header: "t=timestamp,v0=hash"
            parts = signature_header.split(',')
            timestamp = parts[0].split('=')[1]
            received_hash = parts[1]  # "v0=hash"
            
            # Validate timestamp (not too old)
            current_time = int(time.time())
            timestamp_int = int(timestamp)
            
            if current_time - timestamp_int > self.tolerance_seconds:
                logger.warning(f"Timestamp too old: {timestamp}")
                return False
            
            # Compute expected hash
            payload_str = payload.decode('utf-8')
            full_payload = f"{timestamp}.{payload_str}"
            
            mac = hmac.new(
                key=self.secret.encode('utf-8'),
                msg=full_payload.encode('utf-8'),
                digestmod=sha256
            )
            expected_hash = 'v0=' + mac.hexdigest()
            
            # Compare hashes
            if not hmac.compare_digest(received_hash, expected_hash):
                logger.warning("HMAC signature mismatch")
                return False
            
            return True
            
        except (IndexError, ValueError) as e:
            logger.error(f"Error parsing signature header: {e}")
            return False
```

#### 5.3 Test Utility Function
Add to `examples/test_webhook.py`:
```python
#!/usr/bin/env python3
"""
Test utility to send webhook payloads to the service.
Usage: python test_webhook.py <payload_file> [secret]
"""

import sys
import json
import time
import hmac
from hashlib import sha256
import httpx
import asyncio

async def test_webhook(
    payload_file: str,
    secret: str,
    endpoint: str = "http://localhost:3004/webhook"
):
    """
    Test webhook endpoint with a payload file.
    
    Args:
        payload_file: Path to JSON payload file
        secret: HMAC secret for signature generation
        endpoint: Webhook endpoint URL
    """
    # Load payload
    with open(payload_file, 'r') as f:
        payload = json.load(f)
    
    # Convert to bytes
    payload_bytes = json.dumps(payload).encode('utf-8')
    
    # Generate HMAC signature
    timestamp = str(int(time.time()))
    full_payload = f"{timestamp}.{payload_bytes.decode('utf-8')}"
    
    mac = hmac.new(
        key=secret.encode('utf-8'),
        msg=full_payload.encode('utf-8'),
        digestmod=sha256
    )
    signature = f"t={timestamp},v0={mac.hexdigest()}"
    
    # Send request
    async with httpx.AsyncClient() as client:
        response = await client.post(
            endpoint,
            content=payload_bytes,
            headers={
                'elevenlabs-signature': signature,
                'content-type': 'application/json'
            }
        )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    return response

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_webhook.py <payload_file> [secret]")
        sys.exit(1)
    
    payload_file = sys.argv[1]
    secret = sys.argv[2] if len(sys.argv) > 2 else "test-secret-key"
    
    asyncio.run(test_webhook(payload_file, secret))
```

### 6. Example Test Payloads

Create example JSON files in `examples/` directory with sample payloads from the documentation for each webhook type.

### 7. Documentation Requirements

#### README.md must include:
- Service overview and purpose
- Configuration instructions
- Environment variable reference
- API endpoint documentation
- HMAC authentication setup
- Testing instructions
- Integration with existing infrastructure
- Troubleshooting guide
- Security considerations (IP whitelisting + HMAC)

### 8. Security Requirements
- Non-root user in Docker container
- HMAC signature validation (mandatory)
- IP whitelisting in NGINX (ElevenLabs static IPs)
- Timestamp validation (30-minute tolerance)
- Read-only filesystem with tmpfs for /tmp
- Resource limits (512M memory, 1.0 CPU)
- no-new-privileges security option

### 9. Testing Requirements
- Unit tests for HMAC validator (valid/invalid signatures, expired timestamps)
- Unit tests for each webhook handler
- Integration test for full webhook flow
- Test utility script for manual testing
- Example payloads for all three webhook types
- Pytest with async support
- Code coverage target: 80%+

### 10. Integration Checklist
- [ ] Service directory created in `Servers/ElevenLabsWebhook/`
- [ ] Dockerfile following existing pattern
- [ ] Service added to docker-compose.yml
- [ ] NGINX upstream and location configured
- [ ] Health check endpoint implemented
- [ ] HMAC validation implemented
- [ ] All three webhook types handled
- [ ] Test utility created
- [ ] Example payloads created
- [ ] README.md completed
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Docker build successful
- [ ] Service starts and passes health check
- [ ] Webhook endpoint accessible via NGINX
- [ ] IP whitelisting configured
- [ ] .env.example created

### 11. Implementation Guidelines
1. Follow existing code patterns from TopDeskCustomMCP
2. Use FastAPI for HTTP server (matches existing Python services)
3. Implement proper structured logging
4. Use async/await for I/O operations
5. Type hints throughout the codebase
6. Comprehensive error handling
7. Clear separation of concerns (handlers, auth, models)
8. Follow Python best practices (PEP 8)
9. Keep dependencies minimal
10. Document all public functions/classes

### 12. Success Criteria
- Service builds and starts successfully
- Health check endpoint returns 200
- Webhook endpoint accepts valid ElevenLabs requests
- HMAC validation rejects invalid signatures
- All three webhook types are processed correctly
- Test utility can successfully invoke the webhook
- Service integrates seamlessly with existing NGINX proxy
- No security vulnerabilities (IP whitelisting + HMAC)
- All tests pass
- Documentation is complete and accurate

## Notes
- This is a webhook receiver service, not an MCP server
- Focus on reliability and security (HMAC + IP whitelisting)
- Handle large payloads efficiently (chunked encoding for audio)
- Log all webhook events for monitoring
- Consider future enhancement: stateful conversation tracking with database
- The service should be production-ready and follow all existing security patterns
