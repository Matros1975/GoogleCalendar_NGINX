# Architecture Overview

## System Architecture

The Voice Clone Pre-Call Service is a microservice that integrates 3CX PBX with ElevenLabs Voice Agent API to provide dynamic voice cloning for incoming calls.

```
┌─────────────┐                ┌──────────────────────────────────┐
│   3CX PBX   │───Webhook────▶ │  Voice Clone Pre-Call Service    │
└─────────────┘                │                                  │
                               │  ┌────────────────────────────┐  │
                               │  │   FastAPI Application      │  │
                               │  │  - 3CX Webhook Handler     │  │
                               │  │  - POST-call Handler       │  │
┌─────────────┐                │  │  - HMAC Validation         │  │
│  ElevenLabs │◀──API Calls──┬─│  │  - Health Check            │  │
│  Voice API  │              │ │  └────────────────────────────┘  │
└─────────────┘              │ │                                  │
      │                      │ │  ┌────────────────────────────┐  │
      │                      │ │  │   Services Layer           │  │
      │                      └─┼──│  - Voice Clone Service     │  │
      │                        │  │  - Async Voice Service     │  │
      │                        │  │  - ElevenLabs Client       │  │
      │                        │  │  - Cache Service           │  │
      │                        │  │  - Storage Service         │  │
      │                        │  │  - Database Service        │  │
      └──POST-call Webhook────▶  └────────────────────────────┘  │
                               │                                  │
┌──────────────┐               │  ┌────────────────────────────┐  │
│  PostgreSQL  │◀─────────────┼──│   Data Layer               │  │
└──────────────┘               │  │  - 7 Database Tables       │  │
                               │  │  - Alembic Migrations      │  │
┌──────────────┐               │  └────────────────────────────┘  │
│    Redis     │◀─────────────┼──                                │
└──────────────┘               │  ┌────────────────────────────┐  │
                               │  │   Storage                  │  │
┌──────────────┐               │  │  - S3 or Local Files       │  │
│  S3 / Local  │◀─────────────┼──│  - Voice Samples           │  │
└──────────────┘               │  └────────────────────────────┘  │
                               └──────────────────────────────────┘
                                        │
                                   ┌────┴────┐
                                   │  NGINX  │
                                   │ Reverse │
                                   │  Proxy  │
                                   └─────────┘
```

---

## Component Overview

### 1. FastAPI Application

**Location**: `src/main.py`

**Responsibilities**:
- HTTP server on port 3006
- Request routing and validation
- HMAC signature validation
- CORS middleware
- Health check endpoint
- Error handling and logging

**Endpoints**:
- `GET /health` - Service health check
- `POST /webhook/3cx` - 3CX incoming call webhook
- `POST /webhook/postcall` - ElevenLabs POST-call webhook

### 2. Handlers Layer

**Location**: `src/handlers/`

**Components**:

#### ThreeCXHandler
- Processes incoming call webhooks from 3CX
- Validates webhook payloads
- Initiates async voice cloning workflow
- Handles call state changes and call end events

#### PostCallHandler
- Processes POST-call events from ElevenLabs
- Updates call logs with transcripts and duration
- Handles call completion and failure events

### 3. Services Layer

**Location**: `src/services/`

**Components**:

#### Voice Clone Service
- **Core orchestration** for voice cloning
- Checks cache for existing clones
- Retrieves voice samples from storage
- Creates clones via ElevenLabs API
- Stores clones in cache with TTL
- Logs all operations

**Key Method**: `get_or_create_clone(caller_id)`

#### Async Voice Service
- **Implements async greeting workflow**
- Immediately triggers greeting call
- Clones voice in background while greeting plays
- Automatically transitions to voice agent when ready
- Tracks active clone operations
- Handles timeout and error scenarios

**Key Method**: `process_incoming_call(caller_id, threecx_call_id)`

#### ElevenLabs Client
- **HTTP client** for ElevenLabs API
- Voice clone creation
- Voice agent call initiation
- Retry logic with exponential backoff (3 retries)
- Timeout handling (30 seconds default)
- Error handling and logging

**Key Methods**:
- `create_voice_clone(voice_sample_content, voice_name)`
- `trigger_voice_agent_call(phone_number, voice_id, custom_variables)`

#### Cache Service
- **Redis operations** for voice clone caching
- Key-value storage with TTL
- Cache hit/miss tracking
- Connection pooling
- Health check

**Key Methods**:
- `get(key)`, `set(key, value, ttl)`, `delete(key)`

#### Storage Service
- **File operations** for voice samples
- S3 or local filesystem support
- Read/write voice sample files
- Health check

**Key Methods**:
- `get_voice_sample(file_path)`
- `save_voice_sample(file_path, content)`

#### Database Service
- **PostgreSQL operations** via async SQLAlchemy
- CRUD operations for all 7 tables
- Connection pooling (10 connections, max 20 overflow)
- Transaction management
- Health check

**Key Methods**:
- `get_voice_sample_for_caller(caller_id)`
- `save_clone_cache(caller_id, cloned_voice_id, ttl_seconds)`
- `log_call_initiated(...)`
- `log_call_completed(...)`

### 4. Data Layer

**Database Tables** (7 total):

1. **caller_voice_mapping**: Maps callers to voice samples
2. **voice_clone_cache**: Caches created voice clones
3. **call_log**: Logs all voice agent calls
4. **voice_clone_log**: Logs clone creation events
5. **clone_ready_events**: Tracks async clone completion
6. **clone_failed_events**: Tracks clone failures
7. **clone_transfer_events**: Tracks call transitions

**Migrations**: Managed by Alembic

### 5. Authentication

**HMAC Signature Validation**:
- Header format: `X-Signature: t=timestamp,v0=hash`
- Algorithm: HMAC-SHA256
- Tolerance: 30 minutes (1800 seconds)
- Constant-time comparison to prevent timing attacks

---

## Async Greeting Workflow

The service's core innovation is the **zero perceived wait time** async greeting workflow:

### Workflow Sequence

```
1. 3CX Call Arrives
   ↓
2. Service Receives Webhook (< 50ms)
   ↓
3. Immediately Trigger Greeting Call (< 100ms)
   │
   ├─→ Greeting plays with background music
   │   (Caller hears: "Hello, please hold...")
   │
   └─→ START BACKGROUND TASK (async)
       │
       ├─→ Retrieve voice sample from storage
       ├─→ Create voice clone via ElevenLabs API (5-30s)
       ├─→ Cache clone in Redis + Database
       ├─→ Log clone ready event
       └─→ Trigger voice agent call with cloned voice
           │
           └─→ AUTOMATIC TRANSITION (seamless)
               Greeting ends, cloned voice takes over
```

### Timing

- **Step 1-3**: < 100ms (user gets immediate response)
- **Background cloning**: 5-30 seconds (parallel to greeting)
- **Total perceived wait**: 0 seconds (music plays throughout)

### Error Handling

1. **Clone Timeout**: If clone takes > 35 seconds:
   - Log failure event
   - Greeting continues until natural end
   - Option: Fallback to default voice

2. **Clone Failure**: If API error:
   - Log failure event with error details
   - Greeting completes normally
   - Option: Retry with exponential backoff

3. **Missing Voice Sample**:
   - Log error
   - Return error response to 3CX
   - Option: Use default voice

---

## Data Flow

### Incoming Call Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. 3CX sends IncomingCall webhook                              │
│    POST /webhook/3cx                                            │
│    {                                                            │
│      "event_type": "IncomingCall",                             │
│      "caller_id": "+31612345678",                              │
│      "call_id": "3cx_call_123"                                 │
│    }                                                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. HMAC validation                                              │
│    - Verify X-Signature header                                  │
│    - Check timestamp tolerance                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. ThreeCXHandler processes webhook                             │
│    - Parse payload                                              │
│    - Call async_voice_service.process_incoming_call()           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. Trigger greeting call (IMMEDIATE)                            │
│    - ElevenLabs API: trigger_voice_agent_call()                 │
│    - Voice: default_greeting_voice                              │
│    - Message: "Hello, please hold..."                           │
│    - Background music enabled                                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. Return success response (< 100ms)                            │
│    {                                                            │
│      "status": "success",                                       │
│      "call_id": "greeting_123",                                │
│      "3cx_call_id": "3cx_call_123"                             │
│    }                                                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. BACKGROUND: Clone voice (ASYNC)                              │
│    a. Check cache: voice_clone:{caller_id}                      │
│    b. If not cached:                                            │
│       - Get voice sample URL from database                      │
│       - Download voice sample (S3 or local)                     │
│       - Call ElevenLabs: create_voice_clone()                   │
│       - Store in cache (TTL: 24 hours)                          │
│       - Log clone creation                                      │
│    c. Log clone ready event                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 7. BACKGROUND: Trigger voice agent call                         │
│    - ElevenLabs API: trigger_voice_agent_call()                 │
│    - Voice: cloned_voice_id                                     │
│    - Custom variables: caller_id, threecx_call_id               │
│    - Log call initiation                                        │
│    - Log clone transfer event                                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 8. AUTOMATIC TRANSITION                                         │
│    Greeting ends → Voice agent takes over seamlessly            │
└─────────────────────────────────────────────────────────────────┘
```

### POST-Call Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. ElevenLabs sends POST-call webhook                           │
│    POST /webhook/postcall                                       │
│    {                                                            │
│      "call_id": "elevenlabs_call_123",                         │
│      "transcript": "Agent: Hello...",                           │
│      "duration_seconds": 185,                                   │
│      "status": "completed"                                      │
│    }                                                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. HMAC validation                                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. PostCallHandler processes webhook                            │
│    - Update call_log table                                      │
│    - Store transcript                                           │
│    - Update duration and status                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. Return success response                                      │
│    {                                                            │
│      "status": "success",                                       │
│      "message": "POST-call event processed"                     │
│    }                                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Caching Strategy

### Voice Clone Cache

**Purpose**: Avoid recreating voice clones unnecessarily

**Storage**: Redis (primary) + PostgreSQL (backup)

**Key Format**: `voice_clone:{caller_id}`

**Value**:
```json
{
  "voice_id": "voice_123abc",
  "created_at": "2025-12-10T12:00:00Z",
  "caller_id": "+31612345678"
}
```

**TTL**: 24 hours (configurable via `CACHE_TTL`)

**Eviction**: Automatic (Redis TTL) + Manual cleanup task

### Cache Hit Rate Optimization

1. **Long TTL**: 24 hours default (frequent callers benefit)
2. **Database backup**: Persistent storage in `voice_clone_cache` table
3. **Reuse tracking**: `reuse_count` column tracks cache efficiency
4. **Metrics**: Track hit rate for optimization

---

## Security Architecture

### 1. HMAC Signature Validation

- **Algorithm**: HMAC-SHA256
- **Secret**: Unique per webhook endpoint
- **Timestamp**: Prevents replay attacks
- **Constant-time**: Prevents timing attacks

### 2. Network Security

- **Internal network**: Service not exposed directly to internet
- **NGINX proxy**: Only entry point
- **IP whitelisting**: Optional for 3CX webhook
- **TLS/HTTPS**: All external communication encrypted

### 3. Container Security

- **Read-only filesystem**: Container runs with read-only root
- **No new privileges**: Security option enabled
- **Capability dropping**: All capabilities dropped
- **tmpfs**: Temporary files in memory
- **Non-root user**: Runs as `voicecloneuser` (UID 1001)

### 4. Secret Management

- **Environment variables**: Secrets loaded from `.env`
- **No secrets in code**: All sensitive data externalized
- **Redacted logging**: Secrets not logged

---

## Scalability

### Horizontal Scaling

**Stateless design** allows multiple instances:

```yaml
deploy:
  replicas: 3
```

**Load balancing** via NGINX:

```nginx
upstream voiceclone_precall_backend {
    server voiceclone-precall-1:3006;
    server voiceclone-precall-2:3006;
    server voiceclone-precall-3:3006;
    least_conn;
}
```

### Performance Optimizations

1. **Async/await**: Non-blocking I/O throughout
2. **Connection pooling**: Database (10-20), Redis (configurable)
3. **Caching**: Voice clones cached for 24 hours
4. **Background tasks**: Voice cloning doesn't block webhook response

### Resource Limits

**Default (Docker Compose)**:
- **Memory**: 256MB-512MB
- **CPU**: 0.5-1.0 cores

**For high traffic**:
- Scale horizontally (add replicas)
- Increase cache TTL
- Use S3 for voice samples (better than local)

---

## Monitoring and Observability

### Health Checks

- **Docker**: `curl -f http://localhost:3006/health`
- **NGINX**: Proxied to `/voiceclone/health`
- **Interval**: 30 seconds
- **Timeout**: 10 seconds

### Logging

**Structured logging** with context:

```
2025-12-10 12:00:00 - [3cx_call_123] - INFO - Processing incoming call...
2025-12-10 12:00:01 - [3cx_call_123] - INFO - Voice clone created: voice_123abc
```

**Log levels**:
- `DEBUG`: Detailed debugging info
- `INFO`: Normal operations
- `WARNING`: Recoverable issues
- `ERROR`: Errors requiring attention
- `CRITICAL`: Service-impacting failures

### Metrics

**Database-based metrics**:

1. **Clone creation time**: `voice_clone_log.api_response_time_ms`
2. **Call duration**: `call_log.duration_seconds`
3. **Success rates**: `status` columns across tables
4. **Cache hit rate**: `voice_clone_cache.reuse_count`

**Custom dashboards**: Query database for real-time metrics

---

## Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Framework | FastAPI | 0.104+ | HTTP server |
| Server | Uvicorn | 0.24+ | ASGI server |
| Language | Python | 3.11 | Core language |
| Database | PostgreSQL | 15+ | Persistent storage |
| ORM | SQLAlchemy | 2.0+ | Database ORM |
| Migrations | Alembic | 1.13+ | Schema migrations |
| Cache | Redis | 7+ | Voice clone caching |
| HTTP Client | httpx | 0.25+ | Async HTTP |
| Validation | Pydantic | 2.5+ | Data validation |
| Container | Docker | 20.10+ | Containerization |
| Proxy | NGINX | Latest | Reverse proxy |
| Storage | S3 / Local | - | Voice samples |

---

## Future Enhancements

1. **Multi-language support**: Clone detection and routing
2. **Voice quality scoring**: AI-based quality assessment
3. **Real-time analytics dashboard**: Web UI for metrics
4. **A/B testing**: Compare cloned vs. default voices
5. **Webhook retry queue**: Dead letter queue for failed webhooks
6. **Sentiment analysis**: Analyze call transcripts
7. **Auto-tuning**: ML-based cache TTL optimization
8. **GraphQL API**: Alternative to REST endpoints

---

## Contributing

See main repository README for contribution guidelines.

---

## License

See repository LICENSE file.
