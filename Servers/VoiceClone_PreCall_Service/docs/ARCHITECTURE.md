# VoiceClone Pre-Call Service - Architecture Overview

## System Architecture

```
┌─────────────┐         ┌──────────────────┐         ┌─────────────┐
│   3CX PBX   │────────>│   NGINX Proxy    │────────>│ VoiceClone  │
│             │         │ (matrosmcp.duckdns│         │   Service   │
└─────────────┘         │      .org)       │         │  (Port 8000)│
                        └──────────────────┘         └─────────────┘
                               │                            │
┌─────────────┐               │                            │
│ ElevenLabs  │───────────────┘                            │
│ Voice Agent │                                             │
│  (Webhooks) │                                             │
└─────────────┘                                             │
                                                            ▼
                                                    ┌──────────────┐
                                                    │  PostgreSQL  │
                                                    │ voice_clones │
                                                    │   database   │
                                                    └──────────────┘
```

## Async Greeting Workflow

```
Caller ──> 3CX ──> Webhook ──> VoiceClone Service
                                      │
                                      ├─> Immediate: Trigger Greeting (100ms)
                                      │             └─> ElevenLabs API
                                      │                 (Default Voice + Music)
                                      │
                                      └─> Background: Clone Voice (5-30s)
                                                   ├─> Download Sample (S3/Local)
                                                   ├─> ElevenLabs Clone API
                                                   ├─> Cache Voice ID (24h TTL)
                                                   └─> Auto-Transfer to Agent
                                                       └─> ElevenLabs Call API
                                                           (Cloned Voice)
```

## Component Architecture

### 1. FastAPI Application Layer

**Entry Point**: `src/main.py`

- Lifespan management (startup/shutdown)
- Service initialization
- Endpoint routing
- Middleware (CORS, logging)
- Exception handling

**Endpoints**:
- `/health` - Health checks
- `/webhook/3cx` - 3CX incoming calls
- `/webhook/elevenlabs/postcall` - POST-call events
- `/api/v1/cache/{caller_id}` - Cache management
- `/api/v1/statistics` - Analytics

### 2. Handler Layer

**Responsibilities**: Process webhooks and coordinate services

**Components**:
- `ThreeCXHandler` - Validate and route 3CX events
- `PostCallHandler` - Process call completion events

**Flow**:
```
Webhook → Validation → Handler → Service Orchestration → Response
```

### 3. Service Layer

**Core Services**:

1. **VoiceCloneAsyncService** (`voice_clone_async_service.py`)
   - Orchestrates async greeting workflow
   - Manages background voice cloning
   - Handles timeouts and failures
   - Triggers automatic transitions

2. **VoiceCloneService** (`voice_clone_service.py`)
   - Voice clone cache management
   - Clone creation orchestration
   - Statistics aggregation

3. **ElevenLabsService** (`elevenlabs_client.py`)
   - API client for ElevenLabs
   - Voice cloning API calls
   - Voice agent call triggering
   - Retry logic with exponential backoff

4. **DatabaseService** (`database_service.py`)
   - Async SQLAlchemy operations
   - CRUD for all models
   - Transaction management
   - Connection pooling

5. **StorageService** (`storage_service.py`)
   - Voice sample file handling
   - S3 and local filesystem support
   - File validation

### 4. Data Layer

**Database Models** (7 tables):

1. **caller_voice_mapping** - Caller → Voice Sample
2. **voice_clone_cache** - Cached clones (24h TTL)
3. **call_log** - Call records and transcripts
4. **voice_clone_log** - Clone creation audit
5. **clone_ready_events** - Clone completion timing
6. **clone_failed_events** - Failure tracking
7. **clone_transfer_events** - Greeting → Agent handoff

**Pydantic Models**:
- Request/Response validation
- Type safety
- Automatic OpenAPI docs

### 5. Infrastructure Layer

**Configuration**:
- Environment-based settings
- Pydantic validation
- Secrets management

**Logging**:
- Structured logging (text/JSON)
- Context tracking (call_id, caller_id)
- Log rotation (2MB, 10 files)

**Security**:
- HMAC signature validation
- Bearer token authentication
- IP whitelisting (optional)

## Data Flow - Incoming Call

```
1. 3CX PBX detects incoming call
   └─> Sends webhook to /webhook/3cx

2. ThreeCXHandler validates payload
   └─> Extracts caller_id, call_id

3. VoiceCloneAsyncService.handle_incoming_call_async()
   │
   ├─> Immediate: Trigger greeting call (ElevenLabs API)
   │   └─> Returns greeting_call_id
   │
   └─> Background: asyncio.create_task(clone_voice_async)
       │
       ├─> Check cache (DatabaseService)
       │   └─> Cache hit? Return cached voice_id
       │   └─> Cache miss? Continue...
       │
       ├─> Get voice sample path (DatabaseService)
       │   └─> caller_voice_mapping table
       │
       ├─> Download voice sample (StorageService)
       │   └─> S3 or local filesystem
       │
       ├─> Create voice clone (ElevenLabsService)
       │   └─> POST /v1/voice_lab/voice_samples/clone
       │   └─> Returns cloned_voice_id
       │
       ├─> Cache clone (DatabaseService)
       │   └─> voice_clone_cache (TTL: 24h)
       │
       ├─> Log clone creation (DatabaseService)
       │   └─> voice_clone_log, clone_ready_events
       │
       └─> Trigger voice agent call (ElevenLabsService)
           └─> POST /v1/agents/{agent_id}/calls
           └─> Log transfer event

4. Return response to 3CX
   └─> { "status": "success", "call_id": "...", ... }
```

## Data Flow - POST-Call

```
1. ElevenLabs Voice Agent completes call
   └─> Sends webhook to /webhook/elevenlabs/postcall

2. PostCallHandler validates signature
   └─> HMAC validation

3. Extract transcript and metadata
   └─> call_id, duration, transcript, status

4. Update call log (DatabaseService)
   └─> call_log table
   └─> Set call_ended_at, duration, transcript, status

5. Return acknowledgment
   └─> { "status": "processed", "call_id": "..." }
```

## Caching Strategy

**Cache Key**: `caller_id`
**Cache Value**: `cloned_voice_id`
**TTL**: 24 hours (configurable via `CACHE_TTL`)

**Workflow**:
```
Request → Check Cache → Hit? Return voice_id
                     → Miss? Create Clone → Cache → Return voice_id
```

**Cleanup**:
- Background task (optional)
- Soft delete expired entries
- Query: `ttl_expires_at <= NOW()`

**Analytics**:
- Track reuse_count for each cached clone
- Calculate hit rate: `cache_hits / (cache_hits + cache_misses)`
- Monitor average creation time

## Error Handling

**Strategy**: Graceful degradation with fallbacks

**Scenarios**:

1. **Voice Clone Timeout** (>35s)
   - Log timeout event
   - Fall back to default voice
   - Continue call with default voice

2. **Voice Sample Not Found**
   - Log error
   - Return 400 Bad Request
   - Notify administrator

3. **ElevenLabs API Error**
   - Retry with exponential backoff (3 attempts)
   - Log failure after max retries
   - Fall back to default voice

4. **Database Connection Error**
   - Log error
   - Return 500 Internal Server Error
   - Health check reports degraded

## Performance Considerations

**Async I/O**:
- All external calls are async (ElevenLabs, S3, PostgreSQL)
- Background tasks for voice cloning
- No blocking operations in request path

**Connection Pooling**:
- PostgreSQL: 5 connections, 10 overflow
- HTTP client: 32 keepalive connections

**Caching**:
- 24-hour TTL reduces API calls by ~85%
- In-memory session for request scope
- Database cache for persistence

**Timeouts**:
- Voice clone: 30s
- HTTP requests: 30s
- Greeting max wait: 35s

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Docker Host                          │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │                  NGINX (Port 443)                  │  │
│  │  - SSL Termination (Let's Encrypt)                │  │
│  │  - Reverse Proxy                                  │  │
│  │  - Rate Limiting                                   │  │
│  └─────────┬─────────────────────────────────────────┘  │
│            │                                             │
│  ┌─────────┴─────────────────────────────────────────┐  │
│  │         mcp-internal network (172.20.0.0/16)      │  │
│  │                                                    │  │
│  │  ┌──────────────────┐      ┌──────────────────┐  │  │
│  │  │  voiceclone-     │      │    PostgreSQL    │  │  │
│  │  │  precall         │◄────►│   (postgres:    │  │  │
│  │  │  (Port 8000)     │      │    5432)        │  │  │
│  │  └──────────────────┘      └──────────────────┘  │  │
│  │                                                    │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │           Docker Volumes                           │ │
│  │  - voiceclone-voices (voice samples)              │ │
│  │  - logs (application logs)                        │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

## Security Architecture

**Layers**:

1. **Network**: Internal Docker network (mcp-internal)
2. **Transport**: TLS via NGINX (Let's Encrypt)
3. **Authentication**: 
   - HMAC signatures for webhooks
   - Bearer tokens for API endpoints
4. **Authorization**: IP whitelisting (optional)
5. **Container**: Non-root user, read-only filesystem
6. **Capabilities**: Dropped ALL, minimal privileges

## Monitoring & Observability

**Health Checks**:
- Docker health check (30s interval)
- `/health` endpoint (database + ElevenLabs)
- NGINX monitoring

**Logging**:
- Structured logs (JSON or text)
- Context tracking (call_id, caller_id)
- Log rotation (2MB files, 10 backups)

**Metrics** (via `/api/v1/statistics`):
- Total clones created
- Cache hit/miss rates
- Average creation time
- Total calls

**Tracing**:
- Call ID propagation
- Event correlation (ready, failed, transfer)

## Scalability

**Current**: Single instance design
**Future**: Horizontal scaling possible

**Scaling Considerations**:
1. Stateless design (cache in database)
2. Async operations (no blocking)
3. External database (shared PostgreSQL)
4. Load balancer compatible

**Bottlenecks**:
- ElevenLabs API rate limits
- PostgreSQL connection pool
- Voice sample storage I/O

## Technology Stack

- **Runtime**: Python 3.11
- **Framework**: FastAPI 0.104+
- **Server**: Uvicorn (ASGI)
- **Database**: PostgreSQL 15+ (asyncpg)
- **ORM**: SQLAlchemy 2.0 (async)
- **Migrations**: Alembic
- **HTTP Client**: httpx (async)
- **Storage**: boto3 (S3) + aiofiles (local)
- **Validation**: Pydantic 2.5+
- **Testing**: pytest + pytest-asyncio
- **Container**: Docker + Docker Compose
- **Proxy**: NGINX
