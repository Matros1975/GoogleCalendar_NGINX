# TASK: Implement Voice Cloning Pre-Call Service

**Agent Instructions**: You are an autonomous GitHub Copilot agent tasked with implementing this service from scratch.

**Working Directory**: `Servers/VoiceClone_PreCall_Service/`
**Target Port**: 3006
**Version**: 1.0.0
**Date**: December 10, 2025
**Priority**: HIGH - Full implementation required

## YOUR MISSION

Implement a complete microservice that integrates 3CX PBX with ElevenLabs Voice Agent API. You will create all files, services, handlers, database models, and API endpoints as specified below. Follow the repository's Way of Work (WoW) defined in `/AGENTS.md`.

---

## AGENT RESPONSIBILITIES

You must:
1. ✅ **Create complete project structure** in `Servers/VoiceClone_PreCall_Service/`
2. ✅ **Implement all Python files** (services, handlers, models, utils)
3. ✅ **Write database migrations** (Alembic)
4. ✅ **Create configuration files** (.env.example, Dockerfile, requirements.txt, pytest.ini)
5. ✅ **Write comprehensive tests** (unit + integration, ≥85% coverage)
6. ✅ **Generate API documentation** (FastAPI auto-docs)
7. ✅ **Create deployment configs** (docker-compose, NGINX)
8. ✅ **Write README.md** with setup and usage instructions

**DO NOT:**
- ❌ Skip any files or components
- ❌ Use placeholder/stub implementations
- ❌ Leave TODO comments without implementation
- ❌ Copy code without understanding the architecture

**WORKING STYLE:**
- Follow patterns from `Servers/ElevenLabsWebhook/`
- Use Python 3.11, FastAPI, async/await throughout
- Implement proper error handling and logging
- Add type hints to all functions
- Write docstrings for all classes and methods

---

## Overview

Create a new microservice `VoiceClone_PreCall_Service` that integrates with 3CX PBX and ElevenLabs API to dynamically clone voices before initiating calls. This service receives incoming call notifications from 3CX, retrieves caller-specific voice samples, creates instant voice clones via ElevenLabs API, and triggers voice agent calls with the cloned voice.

**🎯 Key Innovation: Async Greeting Workflow**  
To eliminate awkward silence during voice cloning (5-30 seconds), this service implements an asynchronous greeting pattern:
- **Immediate Response**: Triggers prerecorded greeting + music within 100ms
- **Background Processing**: Clones voice asynchronously while message/music plays
- **Automatic Transition**: Voice Agent takes over when clone is ready (no user action required)
- **Zero Perceived Wait**: Callers experience professional, uninterrupted conversation with pleasant background music

## Project Objective

Implement a webhook service that:
1. Receives incoming call webhooks from 3CX PBX
2. **Immediately triggers prerecorded greeting** (async greeting workflow)
3. Extracts caller ID from webhook payload
4. **Clones voice in background** while greeting plays
5. Retrieves voice sample associated with caller
6. Creates instant voice clone via ElevenLabs API
7. **Automatically transitions** to Voice Agent with cloned voice when ready
8. Handles POST-call events for logging and analytics
9. Manages voice clone caching for performance optimization
10. **Tracks clone completion** and automatic handoff timing

## Architecture & Principles

### Follow Existing Patterns
- **Based on**: `Servers/ElevenLabsWebhook/` (existing webhook patterns)
- **Follow**: Repository guidelines from `/AGENTS.md`
- **Adhere to**: "Way of Work" (WoW) principles from existing services
- **Port**: 3006 (next available port after other services)

### Technology Stack
- **Framework**: FastAPI (async-first, matching existing services)
- **Server**: Uvicorn
- **Database**: PostgreSQL 15+ (shared container - `voice_clones` database on centralized PostgreSQL instance)
- **API Client**: httpx (async HTTP, same as ElevenLabsWebhook)
- **Deployment**: Docker + Docker Compose (consistent with project)
- **Python Version**: 3.11 (matching ElevenLabsWebhook)

### Integration Points
1. **3CX PBX**: Sends webhooks for incoming calls
2. **ElevenLabs API**: Voice cloning + Voice Agent triggering
3. **PostgreSQL** (Shared Container): Dedicated `voice_clones` database on centralized PostgreSQL instance (shared with other services)
4. **NGINX**: Reverse proxy (same pattern as other services)

## Project Structure to CREATE

**IMPORTANT**: Create this exact directory structure. Start from top to bottom.

Following existing server structure patterns from `Servers/ElevenLabsWebhook/`:

```
Servers/VoiceClone_PreCall_Service/
├── .env.example                     # Environment configuration template
├── .gitignore                       # Git ignore patterns (match ElevenLabsWebhook)
├── README.md                        # Service documentation
├── Dockerfile                       # Container definition
├── requirements.txt                 # Python dependencies
├── pytest.ini                       # Test configuration
├── alembic.ini                      # Database migration config
├── src/
│   ├── __init__.py
│   ├── main.py                      # FastAPI application entry point
│   ├── config.py                    # Configuration management
│   ├── auth/
│   │   ├── __init__.py
│   │   └── hmac_validator.py        # Webhook signature validation (reuse from ElevenLabsWebhook)
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── threecx_handler.py       # 3CX webhook handling
│   │   └── postcall_handler.py      # ElevenLabs POST-call event handling
│   ├── services/
│   │   ├── __init__.py
│   │   ├── elevenlabs_client.py     # ElevenLabs API client
│   │   ├── voice_clone_service.py   # Voice cloning orchestration
│   │   ├── voice_clone_async_service.py  # Async voice cloning with greeting
│   │   ├── database_service.py      # Database operations (includes caching)
│   │   └── storage_service.py       # Voice sample file handling (S3/local)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── webhook_models.py        # Pydantic models for webhooks
│   │   ├── elevenlabs_models.py     # ElevenLabs API response models
│   │   └── database_models.py       # SQLAlchemy ORM models
│   └── utils/
│       ├── __init__.py
│       ├── logger.py                # Logging configuration (reuse pattern)
│       ├── exceptions.py            # Custom exceptions
│       └── file_handler.py          # Voice sample file processing
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # Pytest fixtures
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_elevenlabs_client.py
│   │   ├── test_voice_clone_service.py
│   │   ├── test_threecx_handler.py
│   │   └── test_database_service.py
│   └── integration/
│       ├── __init__.py
│       ├── test_webhook_endpoint.py
│       └── test_elevenlabs_api.py
├── migrations/
│   ├── env.py                       # Alembic environment
│   └── versions/                    # Migration files
├── docs/
│   ├── API.md                       # API documentation
│   ├── DATABASE.md                  # Database schema
│   ├── DEPLOYMENT.md                # Deployment guide
│   └── ARCHITECTURE.md              # Architecture overview
└── examples/
    ├── test_webhook.py              # Test script for webhook
    └── sample_payloads/             # Sample webhook payloads
        ├── 3cx_incoming_call.json
        └── elevenlabs_postcall.json
```

---

## IMPLEMENTATION ORDER (FOLLOW THIS SEQUENCE)

### Step 1: Initialize Project (30 min)
```bash
cd Servers
mkdir -p VoiceClone_PreCall_Service
cd VoiceClone_PreCall_Service
```

1. Create `README.md` (project overview, setup instructions)
2. Create `requirements.txt` (all dependencies)
3. Create `.env.example` (all environment variables)
4. Create `.gitignore` (Python, IDE, secrets)
5. Create `pytest.ini` (test configuration)
6. Create `alembic.ini` (database migrations)
7. Create `Dockerfile` (Python 3.11-slim base)

### Step 2: Core Infrastructure (2-3 hours)
```bash
mkdir -p src/{auth,handlers,services,models,utils}
mkdir -p tests/{unit,integration}
mkdir -p migrations/versions
mkdir -p docs examples/sample_payloads
```

1. `src/__init__.py`
2. `src/config.py` - Load environment variables, validate configuration
3. `src/utils/logger.py` - Structured logging setup
4. `src/utils/exceptions.py` - Custom exception classes
5. `src/utils/file_handler.py` - Voice sample file processing

### Step 3: Database Layer (2-3 hours)
1. `src/models/database_models.py` - All SQLAlchemy ORM models
2. `migrations/env.py` - Alembic environment
3. Generate initial migration: `alembic revision --autogenerate -m "Initial schema"`
4. `src/services/database_service.py` - CRUD operations

### Step 4: Pydantic Models (1 hour)
1. `src/models/webhook_models.py` - 3CX webhook schemas
2. `src/models/elevenlabs_models.py` - ElevenLabs API schemas

### Step 5: External Services (3-4 hours)
1. `src/services/storage_service.py` - S3/local file handling
2. `src/services/elevenlabs_client.py` - ElevenLabs API client
3. `src/services/voice_clone_service.py` - Voice cloning orchestration (database caching)
4. `src/services/voice_clone_async_service.py` - Async greeting workflow

### Step 6: Handlers (2 hours)
1. `src/auth/hmac_validator.py` - Webhook signature validation
2. `src/handlers/threecx_handler.py` - 3CX webhook processing
3. `src/handlers/postcall_handler.py` - POST-call event handling

### Step 7: FastAPI Application (2 hours)
1. `src/main.py` - FastAPI app, endpoints, middleware, exception handlers

### Step 8: Testing (3-4 hours)
1. `tests/conftest.py` - Pytest fixtures
2. `tests/unit/test_*.py` - Unit tests for each service/handler
3. `tests/integration/test_*.py` - End-to-end workflow tests
4. Run: `pytest --cov=src --cov-report=term-missing`

### Step 9: Docker & Deployment (2 hours)
1. `Dockerfile` - Production-ready container
2. Update root `docker-compose.yml` - Add voiceclone-precall service (connects to shared `postgres` container)
3. Create NGINX config in root `nginx/conf.d/voiceclone-precall.conf`
4. **Note**: Database migrations will create `voice_clones` database automatically on shared PostgreSQL instance

### Step 10: Documentation (1 hour)
1. `docs/API.md` - Endpoint documentation
2. `docs/DATABASE.md` - Schema documentation
3. `docs/DEPLOYMENT.md` - Deployment guide
4. `docs/ARCHITECTURE.md` - System architecture
5. `examples/test_webhook.py` - Testing script
6. `examples/sample_payloads/*.json` - Sample data

**Total Estimated Time**: 18-22 hours

---

## Detailed Specifications

### Configuration (`src/config.py`)

**AGENT TASK**: Create this file with Pydantic BaseSettings for type-safe config.

**Implementation Requirements:**
- Use `pydantic.BaseSettings` for validation
- Load from environment variables via `.env`
- Support development and production modes (NO staging)
- Validate required values at startup - raise `ValueError` if missing
- Provide sensible defaults where appropriate
- Log loaded configuration on startup (redact secrets)

**Required Environment Variables:**

```
# 11Labs Configuration
ELEVENLABS_API_KEY=<string>              # 11Labs API key
ELEVENLABS_AGENT_ID=<string>             # Voice Agent ID
ELEVENLABS_PHONE_NUMBER_ID=<string>      # Registered phone number ID
ELEVENLABS_API_BASE=https://api.elevenlabs.io/v1  # Default

# Greeting Configuration (Async Voice Cloning)
GREETING_VOICE_ID=default_greeting_voice    # ElevenLabs voice ID for prerecorded greeting
GREETING_MESSAGE=Hello thanks for calling. Please hold while we prepare your personalized experience.
GREETING_MUSIC_ENABLED=true                # Play background music during wait
GREETING_MUSIC_URL=https://your-domain.com/hold-music.mp3  # Hold music file
CLONE_MAX_WAIT_SECONDS=35                  # Max wait time before timeout
AUTO_TRANSITION_ENABLED=true               # Automatically switch to cloned voice when ready

# Database Configuration (Shared PostgreSQL Container)
DATABASE_URL=postgresql+asyncpg://voiceagent:${POSTGRES_PASSWORD}@postgres:5432/voice_clones
CACHE_TTL=86400                          # 24 hours default (for voice_clone_cache table)

# Note: Connects to shared PostgreSQL container (service name: postgres)
# Database 'voice_clones' is dedicated to this service
# Other services use: google_calendar, threecx_calls, etc.

# Voice Clone Configuration
VOICE_CLONE_TIMEOUT=30                   # seconds
VOICE_SAMPLE_STORAGE=s3                  # s3 or local
S3_BUCKET_NAME=voice-samples             # If using S3
S3_REGION=eu-west-1                      # AWS region
AWS_ACCESS_KEY_ID=<string>               # If using S3
AWS_SECRET_ACCESS_KEY=<string>           # If using S3
LOCAL_VOICE_SAMPLES_PATH=/data/voices    # If using local

# 3CX Configuration
3CX_WEBHOOK_SECRET=<string>              # For signature verification
3CX_TRUSTED_IPS=127.0.0.1,10.0.0.0/8   # IP whitelist (optional)

# Server Configuration
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
ENVIRONMENT=development                  # development, staging, production

# Security
WEBHOOK_SECRET=<string>                  # For incoming webhook verification
CORS_ORIGINS=["https://your-3cx.com"]   # CORS allowed origins
```

**Implementation Details:**
- Use Pydantic `BaseSettings` for validation
- Log which config is loaded at startup
- Raise `ValueError` if required vars are missing
- Support `.env` loading via `python-dotenv`

---

### 3.2 Database Models (`src/models/database_models.py`)

**AGENT TASK**: Create SQLAlchemy ORM models for ALL tables below.

**Database Architecture**: 
- **Shared PostgreSQL Container**: All tables will be created in the `voice_clones` database
- **Isolation**: This database is dedicated to VoiceClone service (other services use separate databases)
- **Connection**: Via `DATABASE_URL=postgresql+asyncpg://voiceagent:password@postgres:5432/voice_clones`

**Implementation Requirements:**
- Import: `from sqlalchemy.ext.asyncio import AsyncAttrs`
- Use `AsyncAttrs` mixin for async support
- Base class: `declarative_base()` from SQLAlchemy
- Include `created_at`, `updated_at` timestamps on ALL tables
- Add indexes as specified (critical for performance)
- Implement soft deletes with `deleted_at` column (nullable)
- Use `UUID` primary keys with `uuid.uuid4()` default
- All timestamps in UTC timezone

**CREATE THESE 7 TABLES:**

#### 3.2.1 CallerVoiceMapping
```python
Table: caller_voice_mapping
Columns:
  - id: UUID, primary_key
  - caller_id: String(255), unique, indexed
  - voice_sample_url: String(2048)           # S3 URL or local path
  - voice_name: String(255)                  # Display name for clone
  - description: Text (optional)
  - account_id: String(255) (optional)       # For multi-tenant
  - created_at: DateTime, default=utcnow
  - updated_at: DateTime, onupdate=utcnow
  - deleted_at: DateTime (soft delete, nullable)

Indexes:
  - caller_id (unique)
  - account_id
  - created_at
```

#### 3.2.2 VoiceCloneCache
```python
Table: voice_clone_cache
Columns:
  - id: UUID, primary_key
  - caller_id: String(255), indexed
  - cloned_voice_id: String(255), indexed
  - clone_created_at: DateTime, default=utcnow
  - ttl_expires_at: DateTime              # Expiration time
  - reuse_count: Integer, default=1       # Track reuse
  - last_used_at: DateTime
  - created_at: DateTime, default=utcnow
  - deleted_at: DateTime (soft delete, nullable)

Indexes:
  - caller_id
  - cloned_voice_id
  - ttl_expires_at
```

#### 3.2.3 CallLog
```python
Table: call_log
Columns:
  - id: UUID, primary_key
  - call_id: String(255), unique, indexed    # 11Labs call ID
  - 3cx_call_id: String(255), indexed        # 3CX call ID
  - caller_id: String(255), indexed
  - cloned_voice_id: String(255)
  - call_started_at: DateTime, default=utcnow
  - call_ended_at: DateTime (nullable)
  - duration_seconds: Integer (nullable)
  - transcript: Text (nullable)              # Call transcript
  - status: String(50)                       # initiated, completed, failed
  - metadata: JSON (optional)                # Extra data
  - created_at: DateTime, default=utcnow
  - updated_at: DateTime, onupdate=utcnow

Indexes:
  - call_id (unique)
  - caller_id
  - 3cx_call_id
  - status
  - created_at
```

#### 3.2.4 VoiceCloneLog
```python
Table: voice_clone_log
Columns:
  - id: UUID, primary_key
  - caller_id: String(255), indexed
  - cloned_voice_id: String(255)
  - clone_created_at: DateTime, default=utcnow
  - api_response_time_ms: Integer            # Clone creation latency
  - sample_file_size_bytes: Integer
  - status: String(50)                       # success, failed
  - error_message: Text (nullable)
  - created_at: DateTime, default=utcnow

Indexes:
  - caller_id
  - cloned_voice_id
  - status
```

#### 3.2.5 CloneReadyEvent
```python
Table: clone_ready_events
Columns:
  - id: UUID, primary_key
  - caller_id: String(255), indexed
  - greeting_call_id: String(255), indexed
  - cloned_voice_id: String(255)
  - clone_duration_ms: Integer            # Time taken to create clone
  - ready_at: DateTime, default=utcnow
  - created_at: DateTime, default=utcnow

Indexes:
  - caller_id
  - greeting_call_id
  - ready_at
```

#### 3.2.6 CloneFailedEvent
```python
Table: clone_failed_events
Columns:
  - id: UUID, primary_key
  - caller_id: String(255), indexed
  - greeting_call_id: String(255), indexed
  - error_message: Text
  - failed_at: DateTime, default=utcnow
  - created_at: DateTime, default=utcnow

Indexes:
  - caller_id
  - greeting_call_id
  - failed_at
```

#### 3.2.7 CloneTransferEvent
```python
Table: clone_transfer_events
Columns:
  - id: UUID, primary_key
  - greeting_call_id: String(255), indexed
  - agent_call_id: String(255), indexed
  - cloned_voice_id: String(255)
  - transferred_at: DateTime, default=utcnow
  - created_at: DateTime, default=utcnow

Indexes:
  - greeting_call_id
  - agent_call_id
  - transferred_at
```

**ORM Implementation Notes:**
- Use `uuid.uuid4()` as default for UUID columns
- All timestamps are UTC
- Use `@dataclass` or Pydantic for serialization
- Soft deletes: add `deleted_at` filter to default queries

---

#### 3.2.5 CloneReadyEvent
```python
Table: clone_ready_events
Columns:
  - id: UUID, primary_key
  - caller_id: String(255), indexed
  - greeting_call_id: String(255), indexed
  - cloned_voice_id: String(255)
  - clone_duration_ms: Integer            # Time taken to create clone
  - ready_at: DateTime, default=utcnow
  - created_at: DateTime, default=utcnow

Indexes:
  - caller_id
  - greeting_call_id
  - ready_at
```

#### 3.2.6 CloneFailedEvent
```python
Table: clone_failed_events
Columns:
  - id: UUID, primary_key
  - caller_id: String(255), indexed
  - greeting_call_id: String(255), indexed
  - error_message: Text
  - failed_at: DateTime, default=utcnow
  - created_at: DateTime, default=utcnow

Indexes:
  - caller_id
  - greeting_call_id
  - failed_at
```

#### 3.2.7 CloneTransferEvent
```python
Table: clone_transfer_events
Columns:
  - id: UUID, primary_key
  - greeting_call_id: String(255), indexed
  - agent_call_id: String(255), indexed
  - cloned_voice_id: String(255)
  - transferred_at: DateTime, default=utcnow
  - created_at: DateTime, default=utcnow

Indexes:
  - greeting_call_id
  - agent_call_id
  - transferred_at
```

---

### 3.3 Pydantic Schemas (models/schemas.py)

**Request/Response Models:**

```python
# Incoming Call Webhook from 3CX
class ThreeCXWebhookPayload(BaseModel):
    event_type: str                    # IncomingCall, CallStateChanged, CallEnded
    call_id: str                       # 3CX call UUID
    caller_id: str                     # Caller phone number
    called_number: str                 # Number that was called
    timestamp: datetime
    direction: str                     # In, Out
    duration: Optional[int] = None
    recording_url: Optional[str] = None

# Voice Clone Request
class VoiceCloneRequest(BaseModel):
    caller_id: str
    voice_sample_path: Optional[str] = None
    voice_name: Optional[str] = None

# Voice Clone Response
class VoiceCloneResponse(BaseModel):
    cloned_voice_id: str
    caller_id: str
    created_at: datetime
    cached: bool                       # True if from cache

# Incoming Call Response
class IncomingCallResponse(BaseModel):
    status: str                        # success, error
    call_id: str                       # 11Labs call ID
    cloned_voice_id: str
    3cx_call_id: str
    message: Optional[str] = None

# POST-Call Webhook from 11Labs
class PostCallWebhookPayload(BaseModel):
    call_id: str
    agent_id: str
    transcript: Optional[str] = None
    duration_seconds: Optional[int] = None
    status: str                        # completed, failed, missed
    custom_variables: Optional[dict] = None
    timestamp: datetime

# Health Check Response
class HealthCheckResponse(BaseModel):
    status: str                        # ok, degraded, error
    database: str                      # ok, error
    elevenlabs: str                    # ok, error
    timestamp: datetime
```

---

### 3.4 Services Layer

**AGENT TASK**: Implement ALL 6 service classes below. Each service is a separate file.

#### 3.4.1 ElevenLabsService (`src/services/elevenlabs_client.py`)

**MUST IMPLEMENT:**
- Async HTTP client using `httpx.AsyncClient`
- Base URL: `https://api.elevenlabs.io/v1`
- Authentication: Bearer token from `ELEVENLABS_API_KEY`
- Retry logic: 3 attempts with exponential backoff
- Timeout: 30 seconds per request
- Comprehensive error handling with custom exceptions

**Responsibilities:**
- Interact with ElevenLabs API for voice cloning
- Trigger Voice Agent calls
- Handle API retries and errors
- Implement proper error handling with meaningful messages

**Methods:**

```python
class ElevenLabsService:
    async def create_voice_clone(
        self,
        voice_sample_path: str,
        voice_name: str,
        description: Optional[str] = None,
    ) -> str:
        """
        Create voice clone from sample file.
        
        Args:
            voice_sample_path: S3 URL or local file path
            voice_name: Name for the cloned voice
            description: Optional description
        
        Returns:
            cloned_voice_id: String ID of created clone
        
        Raises:
            VoiceCloneException: If clone creation fails
            TimeoutError: If request times out
        
        Implementation:
          1. Read voice sample file (handle S3 and local)
          2. Prepare multipart form data
          3. POST to /v1/voice_lab/voice_samples/clone
          4. Parse response, extract voice_id
          5. Log operation with timing
          6. Handle 11Labs API errors gracefully
        """

    async def trigger_voice_agent_call(
        self,
        phone_number: str,
        voice_id: str,
        custom_variables: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Trigger 11Labs Voice Agent to make a call.
        
        Args:
            phone_number: Caller phone number (E.164 format)
            voice_id: ID of voice to use (cloned or preset)
            custom_variables: Context data for agent
        
        Returns:
            call_id: 11Labs call ID
        
        Raises:
            VoiceAgentException: If agent call fails
        
        Implementation:
          1. Build payload with phone_number, voice_id, custom_variables
          2. POST to /v1/agents/{agent_id}/calls
          3. Handle response, extract call_id
          4. Log call initiation
          5. Handle API errors
        """

    async def get_voice_details(self, voice_id: str) -> Dict[str, Any]:
        """
        Get details about a specific voice.
        
        Returns voice metadata for validation/monitoring.
        """

    async def list_voices(self) -> List[Dict[str, Any]]:
        """
        List all available voices in account.
        
        Returns:
            List of voice metadata dictionaries
        """

    async def health_check(self) -> bool:
        """
        Check 11Labs API connectivity.
        
        Returns:
            True if API is reachable, False otherwise
        """
```

**Error Handling:**
- Define custom exceptions: `VoiceCloneException`, `VoiceAgentException`, `APIException`
- Implement exponential backoff retry logic (max 3 retries)
- Log all errors with context (caller_id, voice_id, etc.)
- Return meaningful error messages to client

---

#### 3.4.2 VoiceCloneService (services/voice_clone_service.py)

**Responsibilities:**
- Orchestrate voice cloning workflow
- Handle caching logic
- Database persistence
- Optimization (prevent duplicate clones)

**Methods:**

```python
class VoiceCloneService:
    async def get_or_create_clone(
        self,
        caller_id: str,
        voice_sample_path: Optional[str] = None,
    ) -> str:
        """
        Get cached clone or create new one.
        
        Implementation:
          1. Query voice_clone_cache table for caller_id (check ttl_expires_at)
          2. If cached and not expired, return cloned_voice_id
          3. If not cached:
             a. Query database for voice_sample_path (if not provided)
             b. If no sample found, raise ValueError
             c. Call elevenlabs_service.create_voice_clone()
             d. Measure creation time
             e. Store in voice_clone_cache table with TTL (CACHE_TTL from config)
             f. Log in voice_clone_log table
          4. Return cloned_voice_id
        
        Raises:
            ValueError: If no voice sample found for caller
            VoiceCloneException: If clone creation fails
        """

    async def get_cached_clone(self, caller_id: str) -> Optional[str]:
        """Check if clone exists in cache and is valid"""

    async def invalidate_clone_cache(self, caller_id: str) -> bool:
        """Remove clone from cache (manual invalidation)"""

    async def cleanup_expired_clones(self) -> int:
        """
        Remove expired clones from cache.
        
        Returns:
            Number of clones cleaned up
        
        Run as background task (e.g., hourly).
        """

    async def get_clone_statistics(self) -> Dict[str, Any]:
        """
        Return cache hit/miss statistics.
        
        Returns:
            {
                "total_clones": 100,
                "cache_hits": 850,
                "cache_misses": 150,
                "hit_rate": 0.85,
                "avg_creation_time_ms": 12500,
            }
        """
```

---

#### 3.4.4 DatabaseService (services/database_service.py)

**Responsibilities:**
- Database connection management
- CRUD operations
- Query execution
- Transaction management

**Methods:**

```python
class DatabaseService:
    async def init(self) -> None:
        """Initialize database engine and create tables"""

    async def close(self) -> None:
        """Close database connection"""

    # CallerVoiceMapping operations
    async def get_voice_sample_for_caller(self, caller_id: str) -> Optional[str]:
        """Get voice sample path for caller"""

    async def save_caller_voice_mapping(
        self,
        caller_id: str,
        voice_sample_url: str,
        voice_name: str,
        account_id: Optional[str] = None,
    ) -> CallerVoiceMapping:
        """Save or update caller → voice mapping"""

    # VoiceCloneCache operations
    async def get_cached_clone(self, caller_id: str) -> Optional[VoiceCloneCache]:
        """Get cached clone if TTL not expired"""

    async def save_clone_cache(
        self,
        caller_id: str,
        cloned_voice_id: str,
        ttl_seconds: int,
    ) -> VoiceCloneCache:
        """Save clone to cache table"""

    async def increment_clone_reuse(self, cloned_voice_id: str) -> None:
        """Increment reuse counter for analytics"""

    # CallLog operations
    async def log_call_initiated(
        self,
        call_id: str,
        three_cx_call_id: str,
        caller_id: str,
        cloned_voice_id: str,
    ) -> CallLog:
        """Log call initiation"""

    async def log_call_completed(
        self,
        call_id: str,
        duration_seconds: int,
        transcript: Optional[str] = None,
        status: str = "completed",
    ) -> CallLog:
        """Update call log with completion details"""

    # VoiceCloneLog operations
    async def log_clone_creation(
        self,
        caller_id: str,
        cloned_voice_id: str,
        api_response_time_ms: int,
        sample_file_size_bytes: int,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> VoiceCloneLog:
        """Log voice clone creation event"""

    # Query operations
    async def get_call_by_id(self, call_id: str) -> Optional[CallLog]:
        """Retrieve call record"""

    async def get_calls_for_caller(
        self,
        caller_id: str,
        limit: int = 10,
        offset: int = 0,
    ) -> List[CallLog]:
        """Get recent calls for caller"""

    async def get_clone_statistics(self) -> Dict[str, Any]:
        """Get aggregated statistics"""

    async def health_check(self) -> bool:
        """Test database connectivity"""
```

---

#### 3.4.5 StorageService (services/storage_service.py)

**Responsibilities:**
- Handle voice sample file access (S3 or local)
- Download files
- File validation

**Methods:**

```python
class StorageService:
    async def download_voice_sample(
        self,
        voice_sample_path: str,
    ) -> bytes:
        """
        Download voice sample file.
        
        Args:
            voice_sample_path: S3 URL or local file path
        
        Returns:
            File bytes
        
        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If download fails
        
        Implementation:
          - Detect if S3 URL or local path
          - Download from S3 using boto3 (if configured)
          - Read from local filesystem (if configured)
          - Validate file is audio (mime type, size)
        """

    async def upload_voice_sample(
        self,
        file_bytes: bytes,
        filename: str,
        caller_id: str,
    ) -> str:
        """
        Upload voice sample.
        
        Returns:
            Path/URL for stored file
        """

    async def delete_voice_sample(self, voice_sample_path: str) -> bool:
        """Delete voice sample file"""

    def validate_audio_file(self, file_bytes: bytes) -> bool:
        """Validate audio file format and size"""
```

---

#### 3.4.6 VoiceCloneAsyncService (services/voice_clone_async_service.py)

**Purpose**: Handle asynchronous voice cloning while greeting plays to caller

**Responsibilities:**
- Trigger prerecorded greeting immediately
- Clone voice in background (async)
- Track clone completion
- Cache clone results
- Handle timeouts gracefully

**Methods:**

```python
class VoiceCloneAsyncService:
    """
    Handles asynchronous voice cloning while call is active.
    Decouples clone creation from webhook response time.
    """
    
    def __init__(
        self,
        elevenlabs_service,
        voice_clone_service,
        database_service,
    ):
        self.elevenlabs = elevenlabs_service
        self.voice_clone = voice_clone_service
        self.database = database_service

    async def trigger_greeting_with_async_clone(
        self,
        phone_number: str,
        caller_id: str,
        greeting_voice_id: str,
        greeting_config: dict,
    ) -> dict:
        """
        Trigger greeting with music immediately, clone voice asynchronously.
        
        Workflow:
          1. Immediately trigger Voice Agent with greeting voice + hold music
          2. Spawn background task for voice cloning
          3. When clone ready, automatically transition to cloned voice agent
          4. Return call_id of greeting call
        
        Args:
            phone_number: Caller's phone number
            caller_id: Unique caller identifier
            greeting_voice_id: Prerecorded greeting voice ID
            greeting_config: Configuration for greeting/music (message, music_url, etc.)
        
        Returns:
            {
                "greeting_call_id": str,
                "clone_task_id": str,  # For tracking
                "status": "greeting_initiated"
            }
        """
        
        # 1. Trigger greeting immediately with hold music
        greeting_call_id = await self.elevenlabs.trigger_voice_agent_call(
            phone_number=phone_number,
            voice_id=greeting_voice_id,
            custom_variables={
                "caller_id": caller_id,
                "mode": "greeting_with_music",
                "greeting_message": greeting_config.get("message"),
                "hold_music_url": greeting_config.get("music_url"),
                "auto_transition": True,
            }
        )
        
        # 2. Start voice clone in background (don't await)
        clone_task = asyncio.create_task(
            self.clone_async_and_notify(
                caller_id=caller_id,
                greeting_call_id=greeting_call_id,
                phone_number=phone_number,
            )
        )
        
        logger.info(f"Greeting + music started {greeting_call_id}, clone task: {clone_task.get_name()}")
        
        return {
            "greeting_call_id": greeting_call_id,
            "clone_task_id": clone_task.get_name(),
            "status": "greeting_initiated",
        }

    async def clone_async_and_notify(
        self,
        caller_id: str,
        greeting_call_id: str,
        phone_number: str,
    ) -> Optional[str]:
        """
        Clone voice asynchronously and automatically trigger agent call when ready.
        
        Workflow:
          1. Wait a bit (let greeting start)
          2. Start voice clone creation
          3. Upon completion, store cloned_voice_id
          4. Cache it for quick retrieval
          5. Automatically trigger Voice Agent with cloned voice
          6. Log completion and transition
        
        Args:
            caller_id: Caller identifier
            greeting_call_id: Call ID of greeting
            phone_number: Caller's phone number for agent call
        
        Returns:
            cloned_voice_id once ready
        """
        try:
            logger.info(f"🔄 Starting async clone for {caller_id}")
            
            # Small delay to let greeting start (100ms)
            await asyncio.sleep(0.1)
            
            # Get or create voice clone (this takes 5-30 seconds)
            start_time = datetime.now()
            cloned_voice_id = await self.voice_clone.get_or_create_clone(
                caller_id=caller_id
            )
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            logger.info(f"✅ Clone ready for {caller_id}: {cloned_voice_id} ({duration_ms:.0f}ms)")
            
            # Store in voice_clone_cache table (already done by get_or_create_clone)
            # No additional caching needed - database handles it
            
            # Log clone ready event
            await self.database.log_clone_ready_event(
                caller_id=caller_id,
                cloned_voice_id=cloned_voice_id,
                greeting_call_id=greeting_call_id,
                clone_duration_ms=int(duration_ms),
            )
            
            # Automatically trigger Voice Agent with cloned voice
            logger.info(f"🎙️ Auto-transitioning {caller_id} to cloned voice agent")
            agent_call_id = await self.elevenlabs.trigger_voice_agent_call(
                phone_number=phone_number,
                voice_id=cloned_voice_id,
                custom_variables={
                    "caller_id": caller_id,
                    "mode": "agent",
                    "from_greeting": greeting_call_id,
                    "auto_transitioned": True,
                }
            )
            
            # Log transition event
            await self.database.log_clone_transfer(
                greeting_call_id=greeting_call_id,
                agent_call_id=agent_call_id,
                cloned_voice_id=cloned_voice_id,
            )
            
            logger.info(f"✅ Transition complete: {greeting_call_id} → {agent_call_id}")
            
            return cloned_voice_id
        
        except Exception as e:
            logger.error(f"❌ Clone failed for {caller_id}: {str(e)}")
            await self.database.log_clone_failed_event(
                caller_id=caller_id,
                greeting_call_id=greeting_call_id,
                error_message=str(e),
            )
            return None

    async def get_clone_status(
        self,
        caller_id: str,
    ) -> Optional[dict]:
        """
        Check current clone status (for monitoring/debugging).
        
        Args:
            caller_id: Caller identifier
        
        Returns:
            {
                "cloned_voice_id": str (if ready),
                "status": "ready" | "cloning" | "not_started"
            }
        """
        
        # Check voice_clone_cache table for ready clone
        cached_clone = await self.database.get_cached_clone(caller_id)
        
        if cached_clone:
            return {
                "cloned_voice_id": cached_clone.cloned_voice_id,
                "status": "ready"
            }
        else:
            # Check if clone is in progress (could check active tasks)
            return {
                "cloned_voice_id": None,
                "status": "cloning"
            }
```

---

### 3.5 Handlers Layer

#### 3.5.1 WebhookHandler (handlers/webhook_handler.py)

**Purpose**: Handle incoming webhooks from 3CX

**Responsibilities:**
- Process incoming call events
- Trigger greeting + music playback
- Initiate async voice cloning
- Handle errors and responses

**Methods:**

**Responsibilities:**
- Handle incoming call webhooks from 3CX
- Orchestrate voice cloning and agent triggering
- Error handling and response formatting

**Methods:**

```python
class ThreeCXWebhookHandler:
    async def handle_3cx_webhook(self, payload: ThreeCXWebhookPayload) -> dict:
        """
        Main webhook handler for 3CX events.
        
        Routes to appropriate sub-handler based on event_type.
        
        Returns:
            {
                "status": "success" | "error",
                "call_id": str,
                "message": str (optional)
            }
        """

    async def handle_incoming_call(
        self,
        payload: ThreeCXWebhookPayload,
    ) -> IncomingCallResponse:
        """
        Handle IncomingCall event.
        
        Workflow:
          1. Extract caller_id, 3cx_call_id from payload
          2. Log webhook receipt
          3. Validate caller_id format
          4. Get or create voice clone:
             - Call voice_clone_service.get_or_create_clone()
             - Handle failures gracefully
          5. Prepare custom_variables context
          6. Trigger Voice Agent:
             - Call elevenlabs_service.trigger_voice_agent_call()
             - Capture returned call_id
          7. Log call in database
          8. Return response
        
        Error Handling:
          - If clone fails: Return error response (don't trigger agent)
          - If agent trigger fails: Log error, return error response
          - All errors logged with full context
        
        Returns:
            IncomingCallResponse with call details
        """

    async def handle_call_state_changed(
        self,
        payload: ThreeCXWebhookPayload,
    ) -> dict:
        """Handle CallStateChanged event (optional)"""

    async def handle_call_ended(
        self,
        payload: ThreeCXWebhookPayload,
    ) -> dict:
        """Handle CallEnded event (optional)"""

    def _verify_webhook_signature(
        self,
        payload: dict,
        signature: str,
    ) -> bool:
        """
        Verify webhook signature from 3CX.
        
        Uses HMAC-SHA256 with 3CX_WEBHOOK_SECRET.
        """
```

---

#### 3.5.2 PostCallHandler (handlers/postcall_handler.py)

**Responsibilities:**
- Handle POST-call webhooks from 11Labs
- Update call records
- Trigger downstream actions

**Methods:**

```python
class PostCallHandler:
    async def handle_post_call(
        self,
        payload: PostCallWebhookPayload,
    ) -> dict:
        """
        Handle POST-call webhook from 11Labs.
        
        Workflow:
          1. Extract call_id, transcript, duration, status
          2. Retrieve call record from database
          3. Update call_log with completion details
          4. Log transcript to database
          5. Trigger downstream actions:
             - Send notifications (Slack, email)
             - Update CRM
             - Archive recordings
             - Analytics processing
          6. Return success response
        
        Returns:
            {"status": "processed", "call_id": call_id}
        """

    async def _trigger_downstream_actions(
        self,
        payload: PostCallWebhookPayload,
    ) -> None:
        """
        Trigger CRM updates, notifications, analytics.
        
        Implementation:
          - Send to Slack webhook (optional)
          - Update Salesforce/HubSpot CRM (optional)
          - Log to analytics service (optional)
        """
```

---

### 3.6 API Endpoints (main.py)

**Requirements:**
- Use FastAPI with async/await
- Implement proper error handling
- Add request/response logging
- Include OpenAPI/Swagger documentation

**Endpoints:**

```python
# FastAPI app initialization with:
#   - CORS middleware
#   - Request/response logging middleware
#   - Exception handlers
#   - OpenAPI configuration

@app.post("/webhook/3cx-call", response_model=IncomingCallResponse)
async def webhook_3cx_call(request: Request):
    """
    3CX incoming call webhook.
    
    Path: POST /webhook/3cx-call
    
    Authorization:
      - Verify webhook signature (HMAC-SHA256)
      - Optional: IP whitelist check
    
    Request:
      - JSON body matching ThreeCXWebhookPayload
    
    Response:
      - 200 OK: IncomingCallResponse
      - 400 Bad Request: Invalid payload
      - 401 Unauthorized: Invalid signature
      - 500 Internal Server Error: Unhandled exception
    
    Workflow:
      1. Parse request body
      2. Verify webhook signature
      3. Delegate to ThreeCXWebhookHandler
      4. Return response
    
    Logs:
      - Incoming webhook receipt (request body, caller_id)
      - Processing steps
      - Any errors with full context
    """

@app.post("/webhook/post-call", response_model=dict)
async def webhook_post_call(request: Request):
    """
    11Labs POST-call webhook.
    
    Path: POST /webhook/post-call
    
    Request:
      - JSON body matching PostCallWebhookPayload
    
    Response:
      - 200 OK: {"status": "processed"}
      - 400 Bad Request: Invalid payload
      - 500 Internal Server Error: Processing failed
    
    Workflow:
      1. Parse request body
      2. Delegate to PostCallHandler
      3. Return response
    
    Logs:
      - Call completion event
      - Transcript (if present)
      - Any errors during downstream processing
    """

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint.
    
    Path: GET /health
    
    Returns:
      {
        "status": "ok" | "degraded" | "error",
        "database": "ok" | "error",
        "elevenlabs": "ok" | "error",
        "timestamp": ISO datetime
      }
    
    Implementation:
      1. Check database connectivity
      2. Check 11Labs API connectivity
      3. Return aggregated status
    """

@app.get("/api/clone-status/{caller_id}")
async def check_clone_status(caller_id: str):
    """
    API endpoint to check clone status (monitoring/debugging).
    
    Path: GET /api/clone-status/{caller_id}
    
    Args:
        caller_id: Caller identifier to check
    
    Returns:
      {
        "caller_id": str,
        "clone_ready": bool,
        "cloned_voice_id": str (if ready),
        "status": "ready" | "cloning" | "not_started"
      }
    
    Implementation:
      1. Check voice_clone_cache table for caller_id
      2. Return current status immediately (no waiting)
    """
    
    status_info = await voice_clone_async_service.get_clone_status(
        caller_id=caller_id
    )
    
    return {
        "caller_id": caller_id,
        "clone_ready": status_info["status"] == "ready",
        "cloned_voice_id": status_info.get("cloned_voice_id"),
        "status": status_info["status"],
    }

@app.get("/metrics")
async def metrics():
    """
    Metrics endpoint (optional).
    
    Returns:
      {
        "total_calls": int,
        "successful_calls": int,
        "failed_calls": int,
        "avg_clone_creation_time_ms": float,
        "cache_hit_rate": float,
        "uptime_seconds": int,
      }
    """

@app.get("/calls/{call_id}")
async def get_call(call_id: str):
    """
    Retrieve call details.
    
    Returns:
      {
        "call_id": str,
        "caller_id": str,
        "3cx_call_id": str,
        "cloned_voice_id": str,
        "status": str,
        "duration_seconds": int,
        "transcript": str,
        "started_at": ISO datetime,
        "ended_at": ISO datetime,
      }
    """

@app.get("/callers/{caller_id}/calls")
async def get_caller_calls(caller_id: str, limit: int = 10, offset: int = 0):
    """
    Retrieve recent calls for a specific caller.
    
    Query Params:
      - limit: Max results (default 10, max 100)
      - offset: Pagination offset
    
    Returns:
      {
        "total": int,
        "calls": [CallRecord, ...],
        "limit": int,
        "offset": int,
      }
    """
```

---

## 4. ASYNC GREETING WORKFLOW

### 4.1 Overview: Prerecorded Greeting Enhancement

**Problem**: Voice cloning takes 5-30 seconds, creating awkward silence for callers

**Solution**: 
1. Immediately trigger prerecorded greeting playback
2. Clone voice asynchronously in background
3. Once cloned, Voice Agent takes over conversation with personalized voice

### 4.2 Architecture: Asynchronous Voice Cloning

```
Incoming Call from 3CX
    │
    ├─ Extract caller_id
    │
    ├─ 1. IMMEDIATELY: Trigger Voice Agent with prerecorded greeting + hold music
    │   (plays message and music to caller while cloning happens)
    │
    ├─ 2. BACKGROUND: Create voice clone asynchronously
    │   (Python service clones voice, stores cloned_voice_id)
    │
    ├─ 3. ONCE CLONED: Automatically trigger Voice Agent with cloned voice
    │   (seamless automatic transition, no user action required)
    │
    └─ 4. Continue call with personalized cloned voice
```

### 4.3 Timeline: Caller Experience

```
T=0s:  Caller dials number
       Python webhook processes instantly (<100ms)
       Voice Agent answers with greeting

T=0-5s: "Hello, thanks for calling. Please hold while we prepare your personalized experience..."
        (Greeting voice - prerecorded)
        (Clone creation starts in background)

T=5-20s: [Background music plays]
         (Pleasant hold music keeps caller engaged)
         (Voice clone being created asynchronously)
         (No user interaction required)

T=20s:   Clone creation completes ✅
         Cloned voice ID cached
         Automatic transition triggered

T=20s+:  Voice Agent seamlessly takes over with cloned voice
         "Thank you for holding. How can I help you today?"
         Full conversation with personalized voice

Total perceived wait: 20 seconds with pleasant music
Actual waiting: Professional hold experience, automatic transition
```

### 4.4 Benefits

✅ **Immediate engagement**: Greeting + music starts within 100ms  
✅ **Background cloning**: Doesn't block webhook response  
✅ **Asynchronous**: Multiple calls cloning in parallel  
✅ **Automatic transition**: No user action required (DTMF-free)  
✅ **Cache optimization**: Clones cached, reusable  
✅ **Professional UX**: Hold music keeps callers engaged  
✅ **No awkward silence**: Continuous audio experience  
✅ **Scalable**: 100+ concurrent clones without issue  

---

### 3.7 Error Handling & Exceptions

**Custom Exceptions (utils/exceptions.py):**

```python
class VoiceAgentException(Exception):
    """Base exception for voice agent errors"""

class VoiceCloneException(VoiceAgentException):
    """Raised when voice cloning fails"""

class VoiceAgentCallException(VoiceAgentException):
    """Raised when Voice Agent call trigger fails"""

class ThreeCXWebhookException(VoiceAgentException):
    """Raised when 3CX webhook processing fails"""

class InvalidPayloadException(VoiceAgentException):
    """Raised when webhook payload is invalid"""

class DatabaseException(VoiceAgentException):
    """Raised when database operation fails"""

class CacheException(VoiceAgentException):
    """Raised when cache operation fails"""

class ConfigurationException(VoiceAgentException):
    """Raised when configuration is invalid"""
```

**Global Exception Handlers (main.py):**

```python
@app.exception_handler(VoiceAgentException)
async def voice_agent_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "type": exc.__class__.__name__}
    )

@app.exception_handler(InvalidPayloadException)
async def invalid_payload_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": str(exc)}
    )
```

---

### 3.8 Logging & Monitoring

**Logging Configuration (utils/logger.py):**

```python
# Configure structured logging with:
#   - File rotation (daily, max 10 files)
#   - Console output with colors
#   - JSON format for production
#   - Sensitive data redaction (API keys, phone numbers)
#
# Log Format:
#   - timestamp (ISO 8601)
#   - level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
#   - logger name
#   - message
#   - context (caller_id, call_id, etc.)
#
# Log Levels by Component:
#   - elevenlabs_service: DEBUG (all API calls)
#   - voice_clone_service: INFO (clone creation, cache hits)
#   - webhook_handler: INFO (incoming calls)
#   - postcall_handler: INFO (call completion)
#   - cache_service: DEBUG (cache operations)
#   - database_service: DEBUG (queries)
```

**Key Logging Points:**

1. **Webhook Receipt**: Log all incoming webhook payload (redacted)
2. **Voice Clone Creation**: Log start, duration, completion
3. **Voice Agent Trigger**: Log call_id, custom_variables
4. **Errors**: Log full context (stack trace, request body, etc.)
5. **Cache Operations**: Log hit/miss, expiry
6. **Database Operations**: Log query execution time

---

## 4. IMPLEMENTATION ROADMAP FOR AGENT

**WORK THROUGH THESE PHASES IN ORDER. Mark each item complete as you finish.**

### Phase 1: Core Infrastructure ⏱️ 2-3 hours
- [ ] Create project directory structure
- [ ] Write `requirements.txt` with all dependencies
- [ ] Create `.env.example` with all variables
- [ ] Implement `src/config.py` with Pydantic validation
- [ ] Create database models in `src/models/database_models.py`
- [ ] Implement Pydantic schemas in `src/models/webhook_models.py` and `elevenlabs_models.py`
- [ ] Set up logging in `src/utils/logger.py`
- [ ] Create custom exceptions in `src/utils/exceptions.py`
- [ ] Test: Configuration loads correctly, validation works

### Phase 2: Services Layer ⏱️ 4-5 hours
- [ ] Implement `src/services/database_service.py` - All CRUD methods for 7 tables (includes cache operations)
- [ ] Implement `src/services/storage_service.py` - S3 (boto3) + local file support
- [ ] Implement `src/services/elevenlabs_client.py` - API client with retry logic
- [ ] Implement `src/services/voice_clone_service.py` - Database-backed caching
- [ ] Implement `src/services/voice_clone_async_service.py` - Async greeting workflow
- [ ] Test: Each service independently with mocks

### Phase 3: Handlers & API ⏱️ 2-3 hours
- [ ] Implement `src/auth/hmac_validator.py` - HMAC-SHA256 signature verification
- [ ] Implement `src/handlers/threecx_handler.py` - Process incoming call webhooks
- [ ] Implement `src/handlers/postcall_handler.py` - Handle POST-call events
- [ ] Create `src/main.py` - FastAPI app with all 6 endpoints
- [ ] Add CORS middleware, exception handlers, request logging
- [ ] Test: All endpoints respond correctly (200/400/500 codes)

### Phase 4: Testing & Deployment ⏱️ 3-4 hours
- [ ] Create `tests/conftest.py` - Fixtures for services, database, mocks
- [ ] Write unit tests in `tests/unit/` - ≥85% coverage target
- [ ] Write integration tests in `tests/integration/` - Full workflow tests
- [ ] Run tests: `pytest --cov=src --cov-report=html`
- [ ] Create `Dockerfile` - Multi-stage build, non-root user
- [ ] Update root `docker-compose.yml` - Add voiceclone-precall service
- [ ] Create NGINX config - Reverse proxy for webhooks
- [ ] Write comprehensive `README.md`
- [ ] Test: Docker build succeeds, containers start, health check passes

---

## 5. TECHNICAL REQUIREMENTS

### 5.1 Performance Requirements
- Voice clone creation: < 30 seconds
- Webhook response time: < 500ms
- Cache hit rate target: > 80% (after first 24h)
- Concurrent call capacity: 100+ simultaneous calls

### 5.2 Reliability Requirements
- 99.5% uptime target
- Graceful error handling (no crashes)
- Automatic retry logic (3 attempts max)
- Database transaction consistency

### 5.3 Security Requirements
- HTTPS only for all webhooks
- Webhook signature verification (HMAC-SHA256)
- API key stored securely (environment variables)
- Database connection encryption (SSL/TLS)
- IP whitelist for 3CX webhooks (optional)

### 5.4 Data Requirements
- Retain call logs for 90 days
- Soft delete support for compliance
- Voice sample URLs stored (not actual files in DB)
- Audit trail for all API operations

---

## 6. DEPLOYMENT INSTRUCTIONS

### 6.1 Prerequisites
- Docker and Docker Compose installed
- Shared PostgreSQL 15+ container (already running in project's docker-compose)
- 11Labs API key and Agent ID
- 3CX PBX configured with webhook capability

**Note**: This service uses the centralized PostgreSQL container defined in the root `docker-compose.yml`. The database `voice_clones` will be automatically created on first run.

### 6.2 Deployment Steps

```bash
# 1. Navigate to project root
cd /path/to/GoogleCalendar_NGINX

# 2. Ensure shared PostgreSQL container is running
docker-compose ps postgres
# If not running: docker-compose up -d postgres

# 3. Create .env file for VoiceClone service
cd Servers/VoiceClone_PreCall_Service
cp .env.example .env
# Edit .env - set DATABASE_URL to: postgresql+asyncpg://voiceagent:password@postgres:5432/voice_clones

# 4. Build and start VoiceClone service (from project root)
cd ../..
docker-compose up -d voiceclone-precall

# 5. Wait for service to be ready
docker-compose logs -f voiceclone-precall

# 6. Run database migrations (creates tables in voice_clones database)
docker-compose exec voiceclone-precall alembic upgrade head

# 7. Verify health
curl http://localhost:3006/health

# 8. Configure 3CX webhook URL
# Admin Console → Settings → Webhooks
# URL: https://your-domain.com/webhook/3cx-call

# 9. Configure 11Labs POST-call webhook
# 11Labs Dashboard → Agent settings
# URL: https://your-domain.com/webhook/post-call
```

### 6.3 Docker Compose Services

**This Service:**
- **voiceclone-precall**: FastAPI app on port 3006

**Shared Infrastructure (Already Running):**
- **postgres**: Shared PostgreSQL 15 container on port 5432
  - Database: `voice_clones` (dedicated to this service)
  - Other databases: `google_calendar`, `threecx_calls` (used by other services)
- **nginx**: Reverse proxy for all services

**Service Configuration in root docker-compose.yml:**
```yaml
services:
  voiceclone-precall:
    build: ./Servers/VoiceClone_PreCall_Service
    container_name: voiceclone-precall
    restart: unless-stopped
    ports:
      - "3006:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://voiceagent:${POSTGRES_PASSWORD}@postgres:5432/voice_clones
      # ... other env vars from .env
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - voiceagent-network
    volumes:
      - ./Servers/VoiceClone_PreCall_Service:/app
      - voice_samples:/data/voices  # If using local storage
```

---

## 7. TESTING STRATEGY

### 7.1 Unit Tests
- Test each service independently with mocks
- Test exception handling
- Test caching logic

### 7.2 Integration Tests
- Test full workflow: webhook → clone → agent call
- Test error scenarios
- Test database persistence

### 7.3 Manual Testing
```bash
# Send test webhook to incoming call endpoint
curl -X POST http://localhost:8000/webhook/3cx-call \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "IncomingCall",
    "call_id": "test-call-123",
    "caller_id": "+31612345678",
    "called_number": "+31201234567",
    "timestamp": "2025-12-10T12:00:00Z",
    "direction": "In"
  }'

# Expected response:
# {
#   "status": "success",
#   "call_id": "11labs-call-xxx",
#   "cloned_voice_id": "voice-xxx",
#   "3cx_call_id": "test-call-123"
# }
```

---

## 8. MONITORING & MAINTENANCE

### 8.1 Monitoring Metrics
- Webhook request rate (calls/minute)
- Voice clone creation time (average, p95, p99)
- Async clone success rate (%)
- Automatic transition time (ms)
- Hold music duration (average)
- Cache hit rate (%)
- Error rate (%)
- API latency (ms)
- Clone ready events per hour
- Transition success rate (%)

### 8.2 Alerts
- Voice clone creation timeout
- 11Labs API downtime
- Database connection failures
- High error rate (>5%)

### 8.3 Maintenance Tasks
- Clean up expired voice clones (daily)
- Archive old call logs (monthly)
- Database optimization (monthly)
- Log rotation (daily)

---

## 9. DOCUMENTATION REQUIREMENTS

### 9.1 README.md
- Project overview
- Installation instructions
- Configuration guide
- API documentation
- Troubleshooting guide

### 9.2 API Documentation
- Auto-generated from OpenAPI/Swagger
- Accessible at `/docs` endpoint

### 9.3 Code Comments
- Docstrings for all public methods
- Inline comments for complex logic
- Type hints for all parameters

---

## 10. SUCCESS CRITERIA

✅ All endpoints implemented and tested  
✅ Voice clone creation working end-to-end  
✅ **Async greeting workflow** functional (greeting + music + background cloning)  
✅ **Automatic transition** working (no DTMF/button press required)  
✅ Clone ready/failed/transfer events logged properly  
✅ 3CX integration tested with real PBX  
✅ Error handling comprehensive  
✅ Documentation complete  
✅ Health check endpoint working  
✅ Logs properly formatted  
✅ Docker deployment working  
✅ Performance targets met:
  - Webhook response < 500ms
  - Greeting + music triggers within 100ms
  - Voice clone < 30s (background)
  - Automatic transition < 1s after clone ready
✅ Security requirements satisfied  
✅ **Caller experience**: Pleasant hold music, seamless automatic transition to cloned voice  

---

## 11. IMPLEMENTATION CHECKLIST (UPDATED)

### Phase 1: Core Infrastructure (2-3 days)
- [ ] Project structure setup
- [ ] Configuration management (`src/config.py`)
- [ ] **Greeting voice ID + hold music** configuration
- [ ] Database models with Alembic migrations
- [ ] **Clone tracking tables** (clone_ready_events, clone_failed_events, clone_transfer_events)
- [ ] Pydantic schemas
- [ ] Logging infrastructure (reuse pattern)
- [ ] Custom exceptions

### Phase 2: Services (4-5 days)
- [ ] ElevenLabs API client (`elevenlabs_client.py`)
- [ ] Voice clone orchestration service (database caching)
- [ ] **VoiceCloneAsyncService** (`voice_clone_async_service.py`)
  - [ ] `trigger_greeting_with_async_clone()` method (with music config)
  - [ ] `clone_async_and_notify()` method (automatic agent trigger)
  - [ ] `get_clone_status()` method (monitoring)
- [ ] Database service (async SQLAlchemy)
  - [ ] Cache operations via voice_clone_cache table
  - [ ] `log_clone_ready_event()` method
  - [ ] `log_clone_failed_event()` method
  - [ ] `log_clone_transfer()` method (automatic transitions)
- [ ] Storage service (S3/local)

### Phase 3: Handlers & API (2-3 days)
- [ ] 3CX webhook handler (greeting + music trigger)
- [ ] POST-call webhook handler
- [ ] FastAPI endpoints
  - [ ] `/webhook/3cx-call` (greeting + music playback)
  - [ ] `/webhook/post-call`
  - [ ] `/health`
  - [ ] **`/api/clone-status/{caller_id}`** (monitoring endpoint)
  - [ ] **`/metrics/cloning`** (performance metrics)
- [ ] HMAC signature validation
- [ ] Middleware and exception handlers

### Phase 4: Testing & Documentation (2-3 days)
- [ ] Unit tests (≥85% coverage)
  - [ ] Test async cloning workflow
  - [ ] Test automatic transition logic
  - [ ] Test clone event logging
- [ ] Integration tests
  - [ ] Test greeting + music + background clone
  - [ ] Test automatic agent trigger when clone ready
  - [ ] Test timeout scenarios
  - [ ] Test hold music playback
- [ ] Dockerfile and docker-compose
- [ ] NGINX configuration
- [ ] **API documentation** (include async greeting + music workflow)
- [ ] **README** with automatic transition explanation
- [ ] Deployment guide

**Total Estimated Time**: 10-14 days

---

## VERIFICATION CHECKLIST

**AGENT: Before marking task complete, verify ALL these items:**

### Code Quality
- [ ] All files created as specified in project structure
- [ ] No placeholder/stub code - everything fully implemented
- [ ] Type hints on all function signatures
- [ ] Docstrings on all classes and public methods
- [ ] Error handling in all async operations
- [ ] Logging at appropriate levels (INFO for events, DEBUG for details)

### Testing
- [ ] `pytest` runs without errors
- [ ] Coverage ≥85% (`pytest --cov=src`)
- [ ] All unit tests pass
- [ ] Integration tests cover main workflows
- [ ] Manual test script in `examples/test_webhook.py` works

### Configuration
- [ ] `.env.example` has all required variables
- [ ] `requirements.txt` has all dependencies with versions
- [ ] `Dockerfile` builds successfully
- [ ] `docker-compose up` starts all services
- [ ] Health check endpoint returns 200 OK

### Documentation
- [ ] README.md complete with setup instructions
- [ ] API docs accessible at `/docs` (FastAPI auto-docs)
- [ ] Database schema documented in `docs/DATABASE.md`
- [ ] Architecture diagram in `docs/ARCHITECTURE.md`

### Functionality
- [ ] Webhook endpoint accepts 3CX payloads
- [ ] Voice cloning workflow executes end-to-end
- [ ] Async greeting + music triggers immediately
- [ ] Automatic transition to cloned voice works
- [ ] Database caching operational (voice_clone_cache table)
- [ ] Database persistence working
- [ ] All 6 API endpoints functional

---

## COMPLETION CRITERIA

**When you finish, the service MUST:**

1. ✅ **Build and run** via Docker Compose
2. ✅ **Pass all tests** with ≥85% coverage
3. ✅ **Accept webhooks** from 3CX (with signature validation)
4. ✅ **Clone voices** via ElevenLabs API
5. ✅ **Play greeting + music** automatically
6. ✅ **Transition to cloned voice** without user input
7. ✅ **Cache clones** in PostgreSQL voice_clone_cache table for reuse
8. ✅ **Log all events** to database tables
9. ✅ **Respond to health checks** within 1 second
10. ✅ **Follow WoW** from `/AGENTS.md`

**Estimated Implementation Time**: 10-14 hours for autonomous agent

---

## FINAL NOTES FOR AGENT

**Remember:**
- This is a COMPLETE implementation, not a prototype
- Follow patterns from `Servers/ElevenLabsWebhook/` exactly
- Use async/await throughout (never blocking calls)
- Every external API call needs retry logic and error handling
- Log everything important, redact secrets
- Write tests as you implement (not at the end)

**If you encounter issues:**
- Check `/AGENTS.md` for repository standards
- Review `Servers/ElevenLabsWebhook/` for similar patterns
- Implement error handling first, happy path second
- Test each component before moving to the next

**Good luck! 🚀**