# Specification: Voice Cloning Pre-Call Service

**Server**: `Servers/VoiceClone_PreCall_Service/`
**Port**: 3006
**Version**: 1.0.0
**Date**: December 10, 2025
**Status**: Ready for Implementation

---

## Overview

Create microservice that integrates 3CX PBX with ElevenLabs Voice Agent. Receives incoming call webhooks from 3CX, retrieves caller-specific voice samples, creates instant voice clones via ElevenLabs API, and triggers voice agent calls with the cloned voice.

**Key Difference from Pre-Call Webhook**: This service is triggered by YOUR 3CX system (not by ElevenLabs). It prepares voice clones BEFORE initiating calls to ElevenLabs.

## Architecture

### Follow Repository WoW
- **Pattern**: Based on `Servers/ElevenLabsWebhook/` structure
- **Guidelines**: Follow `/AGENTS.md` coding standards
- **Python**: 3.11 (matching existing services)
- **Framework**: FastAPI with async/await
- **Deployment**: Docker + NGINX reverse proxy

### Integration Flow

```
3CX PBX (Incoming Call)
    ↓ Webhook
Your Service (Port 3006)
    ↓ Retrieve voice sample
    ↓ Clone voice via ElevenLabs API
    ↓ Update agent configuration
    ↓ Trigger call via ElevenLabs API
ElevenLabs Agent (Makes outbound call with cloned voice)
```

## Project Structure

```
Servers/VoiceClone_PreCall_Service/
├── README.md
├── Dockerfile
├── requirements.txt
├── .env.example
├── .gitignore
├── pytest.ini
├── src/
│   ├── __init__.py
│   ├── main.py                      # FastAPI entry point
│   ├── auth/
│   │   ├── __init__.py
│   │   └── hmac_validator.py        # Reuse from ElevenLabsWebhook
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── threecx_handler.py       # 3CX webhook handling
│   │   └── postcall_handler.py      # ElevenLabs POST-call events
│   ├── services/
│   │   ├── __init__.py
│   │   ├── elevenlabs_client.py     # ElevenLabs API client
│   │   ├── voice_clone_service.py   # Voice cloning orchestration
│   │   ├── cache_service.py         # Redis caching
│   │   ├── database_service.py      # PostgreSQL operations
│   │   └── storage_service.py       # Voice sample retrieval (S3/local)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── webhook_models.py        # Pydantic schemas
│   │   ├── elevenlabs_models.py     # ElevenLabs API models
│   │   └── database_models.py       # SQLAlchemy ORM
│   └── utils/
│       ├── __init__.py
│       ├── logger.py                # Logging (reuse pattern)
│       ├── exceptions.py            # Custom exceptions
│       └── file_handler.py          # Voice sample processing
├── tests/
│   ├── unit/
│   └── integration/
├── docs/
│   ├── API.md
│   ├── DATABASE.md
│   └── DEPLOYMENT.md
└── examples/
    └── test_webhook.py
```

## Environment Configuration

```dotenv
# Service Configuration
VOICECLONE_PRECALL_HOST=0.0.0.0
VOICECLONE_PRECALL_PORT=3006
LOG_LEVEL=INFO
LOG_FORMAT=text
LOG_DIR=/var/log/voiceclone-precall

# ElevenLabs API (required)
ELEVENLABS_API_KEY=your-api-key-here
ELEVENLABS_AGENT_ID=agent_xyz123
ELEVENLABS_PHONE_NUMBER_ID=phone_abc456

# Database (PostgreSQL)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/voiceclone_db

# Cache (Redis)
REDIS_URL=redis://localhost:6379/1
CACHE_TTL=86400                          # 24 hours

# Voice Clone Configuration
VOICE_CLONE_TIMEOUT=30                   # seconds
VOICE_CLONE_MIN_DURATION=3.0             # minimum audio duration
VOICE_CLONE_MAX_SIZE_MB=10.0             # maximum file size

# Voice Sample Storage
VOICE_SAMPLE_STORAGE=local               # "s3" or "local"
LOCAL_VOICE_SAMPLES_PATH=/app/storage/voice_samples
# S3 Configuration (if using S3)
S3_BUCKET_NAME=voice-samples
S3_REGION=eu-west-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

# 3CX Configuration
THREECX_WEBHOOK_SECRET=your-3cx-secret
THREECX_TRUSTED_IPS=127.0.0.1,10.0.0.0/8

# Security
CORS_ORIGINS=["https://your-3cx.com"]
```

## API Endpoints

### 1. Health Check
```
GET /health

Response:
{
  "status": "healthy",
  "database": "ok",
  "redis": "ok",
  "elevenlabs": "ok",
  "timestamp": "2025-12-10T12:00:00Z"
}
```

### 2. 3CX Incoming Call Webhook
```
POST /webhook/3cx-call

Headers:
  - x-3cx-signature: HMAC signature
  - Content-Type: application/json

Request Body:
{
  "event_type": "IncomingCall",
  "call_id": "3cx-call-123",
  "caller_id": "+31612345678",
  "called_number": "+31201234567",
  "timestamp": "2025-12-10T12:00:00Z",
  "direction": "In"
}

Response:
{
  "status": "success",
  "call_id": "elevenlabs-call-xyz",
  "cloned_voice_id": "voice_abc123",
  "cached": true,
  "processing_time_ms": 1250
}
```

### 3. ElevenLabs POST-Call Webhook
```
POST /webhook/postcall

Headers:
  - elevenlabs-signature: HMAC signature

Request Body:
{
  "call_id": "elevenlabs-call-xyz",
  "agent_id": "agent_xyz123",
  "transcript": "...",
  "duration_seconds": 120,
  "status": "completed",
  "timestamp": "2025-12-10T12:05:00Z"
}

Response:
{
  "status": "processed"
}
```

## Core Workflow

### Incoming Call Processing

1. **Receive 3CX Webhook**
   - Validate HMAC signature
   - Extract caller_id and 3cx_call_id

2. **Check Voice Clone Cache** (Redis)
   - Key: `voice_clone:{caller_id}`
   - If cached and valid → use cached voice_id
   - If not cached → proceed to step 3

3. **Retrieve Voice Sample**
   - Query database for caller → voice_sample mapping
   - If no mapping found → error response
   - Download voice sample from S3 or local storage

4. **Create Voice Clone** (ElevenLabs API)
   - POST `/v1/voices/add`
   - Upload voice sample
   - Receive voice_id
   - Store in Redis with TTL
   - Log creation time

5. **Update Agent Configuration** (ElevenLabs API)
   - PATCH `/v1/convai/agents/{agent_id}`
   - Set voice_id for this agent
   - Optional: Set personalized first message

6. **Trigger Voice Agent Call** (ElevenLabs API)
   - POST `/v1/convai/agents/{agent_id}/calls`
   - Provide caller phone number
   - Include custom variables (caller_id, 3cx_call_id)
   - Receive elevenlabs_call_id

7. **Log Call Initiation**
   - Store in database: call_log table
   - Return response to 3CX

## Database Schema

### caller_voice_mapping
```sql
CREATE TABLE caller_voice_mapping (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  caller_id VARCHAR(255) UNIQUE NOT NULL,
  voice_sample_url VARCHAR(2048) NOT NULL,
  voice_name VARCHAR(255) NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_caller_id ON caller_voice_mapping(caller_id);
```

### voice_clone_cache
```sql
CREATE TABLE voice_clone_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  caller_id VARCHAR(255) NOT NULL,
  cloned_voice_id VARCHAR(255) NOT NULL,
  clone_created_at TIMESTAMPTZ DEFAULT NOW(),
  ttl_expires_at TIMESTAMPTZ NOT NULL,
  reuse_count INTEGER DEFAULT 1,
  last_used_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_clone_caller_id ON voice_clone_cache(caller_id);
CREATE INDEX idx_clone_expires ON voice_clone_cache(ttl_expires_at);
```

### call_log
```sql
CREATE TABLE call_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  elevenlabs_call_id VARCHAR(255) UNIQUE NOT NULL,
  threecx_call_id VARCHAR(255) NOT NULL,
  caller_id VARCHAR(255) NOT NULL,
  cloned_voice_id VARCHAR(255) NOT NULL,
  call_started_at TIMESTAMPTZ DEFAULT NOW(),
  call_ended_at TIMESTAMPTZ,
  duration_seconds INTEGER,
  transcript TEXT,
  status VARCHAR(50) DEFAULT 'initiated',
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_call_elevenlabs_id ON call_log(elevenlabs_call_id);
CREATE INDEX idx_call_3cx_id ON call_log(threecx_call_id);
CREATE INDEX idx_call_caller_id ON call_log(caller_id);
```

## Docker Configuration

### Dockerfile
```dockerfile
FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1001 voicecloneuser && \
    useradd -u 1001 -g voicecloneuser -s /bin/bash -m voicecloneuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

COPY src/ /app/src/

RUN mkdir -p /app/logs /app/storage/voice_samples /var/log/mcp-services && \
    chown -R voicecloneuser:voicecloneuser /app /var/log/mcp-services

USER voicecloneuser

EXPOSE 3006

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
    CMD curl -f http://localhost:3006/health || exit 1

CMD ["python", "-m", "src.main"]
```

### Docker Compose Integration
```yaml
# Add to root docker-compose.yml

services:
  voiceclone-precall:
    build:
      context: ./Servers/VoiceClone_PreCall_Service
      dockerfile: Dockerfile
    container_name: voiceclone-precall
    restart: unless-stopped
    ports:
      - "3006:3006"
    env_file:
      - ./Servers/VoiceClone_PreCall_Service/.env
    volumes:
      - ./Servers/VoiceClone_PreCall_Service/logs:/app/logs
      - ./Servers/VoiceClone_PreCall_Service/storage:/app/storage
    depends_on:
      - postgres
      - redis
    networks:
      - mcp-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3006/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## NGINX Configuration

```nginx
# /etc/nginx/conf.d/voiceclone-precall.conf

upstream voiceclone_precall {
    server localhost:3006;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location /voiceclone/webhook {
        proxy_pass http://voiceclone_precall/webhook/3cx-call;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        client_max_body_size 15M;
    }

    location /voiceclone/postcall {
        proxy_pass http://voiceclone_precall/webhook/postcall;
        # Same proxy settings as above
    }

    location /voiceclone/health {
        proxy_pass http://voiceclone_precall/health;
    }
}
```

## Testing Strategy

### Unit Tests (≥85% coverage target)
- Test each service independently with mocks
- Test caching logic (hit/miss scenarios)
- Test database operations
- Test error handling

### Integration Tests
- Test full workflow: 3CX webhook → voice clone → agent call
- Test ElevenLabs API integration
- Test database persistence
- Test cache expiration

### Manual Testing
```bash
# Test 3CX incoming call webhook
curl -X POST http://localhost:3006/webhook/3cx-call \
  -H "Content-Type: application/json" \
  -H "x-3cx-signature: test-signature" \
  -d '{
    "event_type": "IncomingCall",
    "call_id": "test-123",
    "caller_id": "+31612345678",
    "called_number": "+31201234567",
    "timestamp": "2025-12-10T12:00:00Z",
    "direction": "In"
  }'
```

## Implementation Checklist

### Phase 1: Core Infrastructure (2-3 days)
- [ ] Project structure setup
- [ ] Configuration management (`src/config.py`)
- [ ] Database models with Alembic migrations
- [ ] Pydantic schemas
- [ ] Logging infrastructure (reuse pattern)
- [ ] Custom exceptions

### Phase 2: Services (3-4 days)
- [ ] ElevenLabs API client (`elevenlabs_client.py`)
- [ ] Voice clone orchestration service
- [ ] Redis cache service
- [ ] Database service (async SQLAlchemy)
- [ ] Storage service (S3/local)

### Phase 3: Handlers & API (2-3 days)
- [ ] 3CX webhook handler
- [ ] POST-call webhook handler
- [ ] FastAPI endpoints
- [ ] HMAC signature validation
- [ ] Middleware and exception handlers

### Phase 4: Testing & Documentation (2-3 days)
- [ ] Unit tests (≥85% coverage)
- [ ] Integration tests
- [ ] Dockerfile and docker-compose
- [ ] NGINX configuration
- [ ] API documentation
- [ ] README and deployment guide

**Total Estimated Time**: 9-13 days

## Acceptance Criteria

- [ ] All endpoints implemented and tested
- [ ] Voice clone creation working end-to-end
- [ ] 3CX integration tested
- [ ] Cache hit rate >80% after initial run
- [ ] Error handling comprehensive
- [ ] Documentation complete
- [ ] Health check endpoint working
- [ ] Logs properly formatted (matching ElevenLabsWebhook pattern)
- [ ] Docker deployment working
- [ ] NGINX reverse proxy configured
- [ ] Performance: Voice clone <30s, webhook response <500ms
- [ ] Security: HMAC validation, HTTPS only

## Notes

- This service is NOT triggered by ElevenLabs (unlike POST-call webhooks)
- This is triggered by YOUR 3CX PBX system
- Voice samples must be pre-registered in the database
- Caching is critical for performance (avoid re-cloning same voice)
- Clean up expired clones regularly (background task)
