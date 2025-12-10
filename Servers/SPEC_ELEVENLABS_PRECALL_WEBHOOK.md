# Specification: ElevenLabs Pre-Call Webhook Service

## Overview
Create a new microservice `ElevenLabs_PreCall_Webhook` that handles ElevenLabs pre-call webhook events. This webhook is triggered **before** a voice call starts and performs real-time voice cloning and agent customization based on uploaded voice samples.

## Project Objective
Implement a webhook service that:
1. Receives pre-call webhook from ElevenLabs voice agent
2. Processes voice sample files
3. Creates custom voices via ElevenLabs API (instant voice cloning)
4. Activates the new voice to the calling agent
5. Returns caller metadata to the voice agent in JSON format

## Architecture & Principles

### Follow Existing Patterns
- **Based on**: `Servers/ElevenLabsWebhook/` (post-call webhook)
- **Follow**: Repository guidelines from `/AGENTS.md`
- **Adhere to**: "Way of Work" (WoW) principles from existing ElevenLabs webhook

### Project Structure
```
Servers/ElevenLabs_PreCall_Webhook/
├── README.md                      # Service documentation
├── Dockerfile                     # Container definition
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment configuration template
├── .gitignore                     # Git ignore patterns
├── pytest.ini                     # Test configuration
├── src/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry point
│   ├── auth/
│   │   ├── __init__.py
│   │   └── hmac_validator.py     # HMAC signature validation
│   ├── handlers/
│   │   ├── __init__.py
│   │   └── precall_handler.py    # Pre-call webhook handler
│   ├── services/
│   │   ├── __init__.py
│   │   ├── elevenlabs_client.py  # ElevenLabs API client
│   │   └── voice_cloning_service.py  # Voice cloning orchestration
│   ├── models/
│   │   ├── __init__.py
│   │   ├── webhook_models.py     # Pydantic models for webhooks
│   │   └── elevenlabs_models.py  # ElevenLabs API response models
│   └── utils/
│       ├── __init__.py
│       ├── logger.py              # Logging configuration
│       └── file_handler.py        # Voice sample file processing
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_precall_handler.py
│   │   ├── test_elevenlabs_client.py
│   │   └── test_voice_cloning_service.py
│   └── integration/
│       ├── __init__.py
│       ├── test_webhook_endpoint.py
│       └── test_elevenlabs_api.py
├── docs/
│   ├── API.md                     # API documentation
│   ├── VOICE_CLONING.md          # Voice cloning flow
│   └── DEPLOYMENT.md              # Deployment guide
└── examples/
    ├── precall_payload.json       # Sample webhook payload
    └── test_precall_webhook.py    # Test script
```

## Functional Requirements

### 1. Webhook Endpoint

#### Endpoint Specification
```
POST /webhook
```

**Headers:**
- `elevenlabs-signature`: HMAC signature (format: `t=timestamp,v0=hash`)
- `Content-Type`: `application/json` or `multipart/form-data` (for voice sample)

**Request Payload:**
```json
{
  "type": "pre_call",
  "event_timestamp": 1702425485,
  "conversation_id": "conv_abc123xyz",
  "agent_id": "agent_def456uvw",
  "caller_metadata": {
    "name": "Ivan",
    "date_of_birth": "11.12.2007",
    "phone_number": "+31612345678"
  },
  "voice_sample": {
    "format": "base64",
    "data": "UklGRiQAAABXQVZFZm10...",
    "duration_seconds": 5.2,
    "sample_rate": 44100
  }
}
```

**Alternative: Multipart Form Data**
```
POST /webhook
Content-Type: multipart/form-data

Fields:
- metadata: {"type": "pre_call", "conversation_id": "...", "agent_id": "...", "caller_metadata": {...}}
- voice_sample: [audio file]
- elevenlabs_signature: t=1234567890,v0=abc123...
```

**Response (Success):**
```json
{
  "status": "success",
  "conversation_id": "conv_abc123xyz",
  "voice_id": "voice_new_cloned_xyz",
  "voice_name": "Ivan_Clone_20251210",
  "agent_updated": true,
  "caller_info": {
    "Name": "Ivan",
    "DateOfBirth": "11.12.2007"
  },
  "processing_time_ms": 2450
}
```

**Response (Error):**
```json
{
  "status": "error",
  "error_code": "VOICE_CLONING_FAILED",
  "error_message": "Voice sample too short (min 3 seconds required)",
  "conversation_id": "conv_abc123xyz"
}
```

**Status Codes:**
- `200 OK`: Successfully processed pre-call webhook
- `400 Bad Request`: Invalid payload or voice sample
- `401 Unauthorized`: Invalid HMAC signature
- `422 Unprocessable Entity`: Voice cloning failed
- `500 Internal Server Error`: Service error

### 2. Voice Cloning Workflow

#### Step 1: Receive and Validate
1. Validate HMAC signature (same as post-call webhook)
2. Parse webhook payload (JSON or multipart)
3. Validate voice sample:
   - Format: WAV, MP3, or OGG
   - Duration: 3-10 seconds minimum
   - Quality: Sample rate ≥ 16kHz
   - Size: ≤ 10MB

#### Step 2: Create Instant Voice Clone
Use ElevenLabs Voice Cloning API:

```python
POST https://api.elevenlabs.io/v1/voices/add
Headers:
  xi-api-key: {ELEVENLABS_API_KEY}
  Content-Type: multipart/form-data

Form Data:
  name: "Ivan_Clone_20251210_123456"
  files: [voice_sample.mp3]
  description: "Instant clone for conversation conv_abc123xyz"
  labels: {"conversation_id": "conv_abc123xyz", "type": "instant_clone"}
```

**Response:**
```json
{
  "voice_id": "voice_new_xyz",
  "name": "Ivan_Clone_20251210_123456",
  "samples": [...],
  "category": "cloned",
  "fine_tuning": {...}
}
```

#### Step 3: Activate Voice to Agent
Update agent configuration to use new voice:

```python
PATCH https://api.elevenlabs.io/v1/convai/agents/{agent_id}
Headers:
  xi-api-key: {ELEVENLABS_API_KEY}
  Content-Type: application/json

Body:
{
  "conversation_config": {
    "agent": {
      "first_message": "Hallo Ivan, fijn dat je belt!",
      "voice": {
        "voice_id": "voice_new_xyz"
      }
    }
  }
}
```

#### Step 4: Return Caller Metadata
Format and return caller information for agent context:

```json
{
  "caller_info": {
    "Name": "Ivan",
    "DateOfBirth": "11.12.2007"
  }
}
```

### 3. ElevenLabs API Integration

#### API Client (`src/services/elevenlabs_client.py`)

```python
class ElevenLabsAPIClient:
    """Client for ElevenLabs API interactions."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.elevenlabs.io/v1"):
        self.api_key = api_key
        self.base_url = base_url
    
    async def create_instant_voice(
        self,
        voice_sample: bytes,
        voice_name: str,
        description: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create instant voice clone from audio sample.
        
        Args:
            voice_sample: Audio file bytes (WAV, MP3, OGG)
            voice_name: Name for the cloned voice
            description: Optional description
            labels: Optional metadata labels
            
        Returns:
            Voice creation response with voice_id
        """
        pass
    
    async def update_agent_voice(
        self,
        agent_id: str,
        voice_id: str,
        first_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update agent configuration to use new voice.
        
        Args:
            agent_id: ElevenLabs agent ID
            voice_id: Voice ID to activate
            first_message: Optional custom greeting
            
        Returns:
            Agent update response
        """
        pass
    
    async def get_voice_info(self, voice_id: str) -> Dict[str, Any]:
        """Get voice details by ID."""
        pass
    
    async def delete_voice(self, voice_id: str) -> bool:
        """Delete a cloned voice (cleanup)."""
        pass
```

#### Voice Cloning Service (`src/services/voice_cloning_service.py`)

```python
class VoiceCloningService:
    """Orchestrates voice cloning workflow."""
    
    def __init__(self, elevenlabs_client: ElevenLabsAPIClient):
        self.client = elevenlabs_client
    
    async def process_precall_webhook(
        self,
        conversation_id: str,
        agent_id: str,
        voice_sample: bytes,
        caller_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Complete pre-call processing workflow.
        
        1. Validate voice sample
        2. Create instant voice clone
        3. Update agent configuration
        4. Return caller metadata
        
        Returns:
            Processing result with voice_id and caller_info
        """
        pass
    
    def validate_voice_sample(
        self,
        audio_data: bytes,
        min_duration: float = 3.0,
        max_size_mb: float = 10.0
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate voice sample quality.
        
        Returns:
            (is_valid, error_message)
        """
        pass
    
    def generate_voice_name(
        self,
        caller_name: str,
        conversation_id: str
    ) -> str:
        """Generate unique voice name."""
        pass
```

## Technical Requirements

### Environment Variables

```dotenv
# ElevenLabs Pre-Call Webhook Configuration

# ElevenLabs API Configuration (required)
ELEVENLABS_API_KEY=your-api-key-here
ELEVENLABS_WEBHOOK_SECRET=your-webhook-secret-here

# Server Configuration
PRECALL_WEBHOOK_HOST=0.0.0.0
PRECALL_WEBHOOK_PORT=3005

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=text
LOG_DIR=/var/log/elevenlabs-precall-webhook

# Voice Cloning Configuration
VOICE_CLONE_MIN_DURATION=3.0        # Minimum audio duration (seconds)
VOICE_CLONE_MAX_SIZE_MB=10.0        # Maximum file size
VOICE_CLONE_SAMPLE_RATE=44100       # Target sample rate
VOICE_CLONE_AUTO_DELETE=true        # Delete voice after call ends

# Agent Configuration
DEFAULT_FIRST_MESSAGE="Hallo {name}, fijn dat je belt!"

# Optional: Voice Sample Storage
VOICE_SAMPLE_STORAGE_PATH=/app/storage/voice_samples
ENABLE_VOICE_SAMPLE_STORAGE=false
```

### Dependencies (`requirements.txt`)

```txt
# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0

# HTTP Client
httpx==0.25.2
aiofiles==23.2.1

# Audio Processing
pydub==0.25.1          # Audio file manipulation
soundfile==0.12.1      # Audio metadata extraction
librosa==0.10.1        # Audio analysis (optional)

# Security
cryptography==41.0.7

# Logging
python-json-logger==2.0.7

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-mock==3.12.0
responses==0.24.1
```

### Docker Configuration

**Dockerfile:**
```dockerfile
# ElevenLabs Pre-Call Webhook Service
FROM python:3.11-slim

# Install system dependencies for audio processing
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -g 1001 precalluser && \
    useradd -u 1001 -g precalluser -s /bin/bash -m precalluser

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

# Copy application code
COPY src/ /app/src/

# Create directories
RUN mkdir -p /app/logs /app/storage/voice_samples /var/log/mcp-services && \
    chown -R precalluser:precalluser /app /var/log/mcp-services

USER precalluser

EXPOSE 3005

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
    CMD curl -f http://localhost:3005/health || exit 1

CMD ["python", "-m", "src.main"]
```

## Implementation Guidelines

### Coding Standards
Follow existing ElevenLabs webhook patterns:

1. **Python Style:**
   - Python 3.11+
   - Type hints for all functions
   - 4-space indentation
   - PEP 8 compliant
   - Docstrings (Google style)

2. **File Naming:**
   - snake_case for all Python files
   - PascalCase for classes
   - Descriptive names (e.g., `voice_cloning_service.py`)

3. **Error Handling:**
   - Try-except blocks for all external API calls
   - Structured logging (with conversation_id context)
   - Return structured error responses

4. **Security:**
   - HMAC signature validation (same as post-call webhook)
   - Input validation (Pydantic models)
   - API key stored in environment variables
   - No sensitive data in logs

### Testing Requirements

1. **Unit Tests (≥85% coverage):**
   - `test_precall_handler.py`: Webhook handler logic
   - `test_elevenlabs_client.py`: API client methods
   - `test_voice_cloning_service.py`: Voice cloning workflow
   - Mock all external API calls

2. **Integration Tests:**
   - `test_webhook_endpoint.py`: Full webhook flow
   - `test_elevenlabs_api.py`: Real API calls (with test API key)
   - Use sample voice files from `tests/fixtures/`

3. **Test Data:**
   ```
   tests/fixtures/
   ├── voice_samples/
   │   ├── valid_sample_5s.wav
   │   ├── short_sample_2s.wav (invalid)
   │   └── large_sample_15mb.wav (invalid)
   └── payloads/
       ├── valid_precall.json
       └── invalid_precall.json
   ```

### Logging Strategy

Use structured logging with conversation context:

```python
logger.info(
    "Voice cloning initiated",
    extra={
        "conversation_id": conv_id,
        "agent_id": agent_id,
        "caller_name": caller_name,
        "voice_sample_duration": duration,
        "event_type": "voice_clone_start"
    }
)
```

**Log Events:**
- `webhook_received`: Pre-call webhook received
- `signature_validated`: HMAC validation result
- `voice_clone_start`: Voice cloning initiated
- `voice_clone_success`: Voice created successfully
- `voice_clone_failed`: Voice cloning error
- `agent_update_start`: Agent configuration update
- `agent_update_success`: Agent updated
- `webhook_complete`: Full workflow completed

## API Documentation

### ElevenLabs API Endpoints Used

#### 1. Create Voice (Instant Clone)
```
POST /v1/voices/add
```
**Documentation:** https://elevenlabs.io/docs/api-reference/add-voice

#### 2. Update Agent Configuration
```
PATCH /v1/convai/agents/{agent_id}
```
**Documentation:** https://elevenlabs.io/docs/api-reference/update-agent

#### 3. Get Voice Details
```
GET /v1/voices/{voice_id}
```

#### 4. Delete Voice
```
DELETE /v1/voices/{voice_id}
```

## Deployment

### NGINX Configuration
Add reverse proxy configuration (similar to post-call webhook):

```nginx
# /etc/nginx/conf.d/elevenlabs-precall.conf

upstream elevenlabs_precall_webhook {
    server localhost:3005;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location /elevenlabs/precall/webhook {
        proxy_pass http://elevenlabs_precall_webhook/webhook;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase timeouts for voice processing
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Increase body size for voice samples
        client_max_body_size 15M;
    }

    location /elevenlabs/precall/health {
        proxy_pass http://elevenlabs_precall_webhook/health;
    }
}
```

### Docker Compose
```yaml
# Add to docker-compose.yml

services:
  elevenlabs-precall-webhook:
    build:
      context: ./Servers/ElevenLabs_PreCall_Webhook
      dockerfile: Dockerfile
    container_name: elevenlabs-precall-webhook
    restart: unless-stopped
    ports:
      - "3005:3005"
    env_file:
      - ./Servers/ElevenLabs_PreCall_Webhook/.env
    volumes:
      - ./Servers/ElevenLabs_PreCall_Webhook/logs:/app/logs
      - ./Servers/ElevenLabs_PreCall_Webhook/storage:/app/storage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3005/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    networks:
      - mcp-network

networks:
  mcp-network:
    external: true
```

## Validation & Acceptance Criteria

### Functional Acceptance
- [ ] Webhook receives and validates HMAC signature
- [ ] Voice sample is extracted from payload (JSON or multipart)
- [ ] Voice sample validation (duration, size, format)
- [ ] Instant voice clone created via ElevenLabs API
- [ ] Agent configuration updated with new voice ID
- [ ] Caller metadata returned in correct JSON format
- [ ] Error handling for all failure scenarios
- [ ] Health check endpoint responds correctly

### Technical Acceptance
- [ ] Unit tests pass with ≥85% coverage
- [ ] Integration tests pass against ElevenLabs API
- [ ] Code follows existing ElevenLabs webhook patterns
- [ ] Dockerfile builds successfully
- [ ] Docker container runs and passes health check
- [ ] NGINX reverse proxy configuration works
- [ ] Structured logging implemented
- [ ] API documentation complete
- [ ] README.md with setup instructions

### Security Acceptance
- [ ] HMAC signature validation enforced
- [ ] API keys stored in environment variables only
- [ ] No sensitive data logged
- [ ] Input validation on all fields
- [ ] File size limits enforced
- [ ] Non-root user in Docker container

## Timeline & Milestones

### Phase 1: Core Implementation (2-3 days)
- [ ] Project structure setup
- [ ] HMAC authentication (reuse from post-call)
- [ ] Webhook endpoint with payload parsing
- [ ] Voice sample validation

### Phase 2: ElevenLabs Integration (2-3 days)
- [ ] ElevenLabs API client
- [ ] Voice cloning service
- [ ] Agent update functionality
- [ ] Error handling

### Phase 3: Testing & Documentation (1-2 days)
- [ ] Unit tests
- [ ] Integration tests
- [ ] API documentation
- [ ] README and deployment guide

### Phase 4: Deployment & Validation (1 day)
- [ ] Docker configuration
- [ ] NGINX setup
- [ ] End-to-end testing
- [ ] Production deployment

**Total Estimated Time:** 6-9 days

## References

### Existing Codebase
- Post-call webhook: `Servers/ElevenLabsWebhook/`
- HMAC validation: `Servers/ElevenLabsWebhook/src/auth/hmac_validator.py`
- Logging setup: `Servers/ElevenLabsWebhook/src/utils/logger.py`

### ElevenLabs API Documentation
- Voice Cloning: https://elevenlabs.io/docs/api-reference/add-voice
- Conversational AI: https://elevenlabs.io/docs/api-reference/conversational-ai
- Authentication: https://elevenlabs.io/docs/api-reference/authentication

### Repository Guidelines
- `/AGENTS.md`: Repository WoW and standards
- `Servers/README.md`: Server organization

## Notes for Implementation

1. **Voice Sample Handling:**
   - Accept both base64-encoded and raw file upload
   - Support WAV, MP3, OGG formats
   - Convert to optimal format if needed (e.g., MP3 at 44.1kHz)

2. **Performance:**
   - Voice cloning typically takes 2-5 seconds
   - Set webhook timeout to 60 seconds
   - Implement async processing for better performance

3. **Cleanup:**
   - Consider implementing voice cleanup (delete after call)
   - Optional: Keep voice for X hours for debugging
   - Track created voices in logs

4. **Monitoring:**
   - Log all API calls with timing
   - Track success/failure rates
   - Alert on repeated failures

5. **Future Enhancements:**
   - Voice caching (reuse for repeat callers)
   - Multiple voice sample support
   - Voice quality validation
   - A/B testing of different voice settings
