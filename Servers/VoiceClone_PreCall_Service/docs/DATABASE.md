# VoiceClone Pre-Call Service - Database Schema

## Overview

The service uses PostgreSQL 15+ with async SQLAlchemy. All tables are created in the `voice_clones` database on the shared PostgreSQL container.

## Tables

### 1. caller_voice_mapping

Maps caller phone numbers to voice sample files.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| caller_id | VARCHAR(255) | Caller phone number (E.164), unique, indexed |
| voice_sample_url | VARCHAR(2048) | S3 URL or local path to voice sample |
| voice_name | VARCHAR(255) | Display name for cloned voice |
| description | TEXT | Optional description |
| account_id | VARCHAR(255) | Account ID for multi-tenant support, indexed |
| created_at | TIMESTAMP | Creation timestamp, indexed |
| updated_at | TIMESTAMP | Last update timestamp |
| deleted_at | TIMESTAMP | Soft delete timestamp |

**Indexes**: `caller_id` (unique), `account_id`, `created_at`

---

### 2. voice_clone_cache

Caches cloned voices with TTL for performance optimization.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| caller_id | VARCHAR(255) | Caller phone number, indexed |
| cloned_voice_id | VARCHAR(255) | ElevenLabs voice ID, indexed |
| clone_created_at | TIMESTAMP | When clone was created |
| ttl_expires_at | TIMESTAMP | Cache expiration time, indexed |
| reuse_count | INTEGER | Number of times clone was reused (default: 1) |
| last_used_at | TIMESTAMP | Last usage timestamp |
| created_at | TIMESTAMP | Creation timestamp |
| deleted_at | TIMESTAMP | Soft delete timestamp |

**Indexes**: `caller_id`, `cloned_voice_id`, `ttl_expires_at`

**Cache Strategy**: 
- Default TTL: 24 hours (configurable via `CACHE_TTL`)
- Cleanup via background task

---

### 3. call_log

Logs all calls made through the voice agent.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| call_id | VARCHAR(255) | ElevenLabs call ID, unique, indexed |
| threecx_call_id | VARCHAR(255) | 3CX call ID, indexed |
| caller_id | VARCHAR(255) | Caller phone number, indexed |
| cloned_voice_id | VARCHAR(255) | Voice ID used for call |
| call_started_at | TIMESTAMP | Call start time |
| call_ended_at | TIMESTAMP | Call end time (nullable) |
| duration_seconds | INTEGER | Call duration (nullable) |
| transcript | TEXT | Full call transcript (nullable) |
| status | VARCHAR(50) | Call status (initiated, completed, failed), indexed |
| metadata | JSON | Extra call metadata |
| created_at | TIMESTAMP | Creation timestamp, indexed |
| updated_at | TIMESTAMP | Last update timestamp |

**Indexes**: `call_id` (unique), `threecx_call_id`, `caller_id`, `status`, `created_at`

**Status Values**: `initiated`, `completed`, `failed`

---

### 4. voice_clone_log

Audit log for all voice clone operations.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| caller_id | VARCHAR(255) | Caller phone number, indexed |
| cloned_voice_id | VARCHAR(255) | ElevenLabs voice ID, indexed |
| clone_created_at | TIMESTAMP | Clone creation time |
| api_response_time_ms | INTEGER | API latency in milliseconds |
| sample_file_size_bytes | INTEGER | Voice sample file size |
| status | VARCHAR(50) | Status (success, failed), indexed |
| error_message | TEXT | Error message if failed (nullable) |
| created_at | TIMESTAMP | Creation timestamp |

**Indexes**: `caller_id`, `cloned_voice_id`, `status`

**Status Values**: `success`, `failed`

---

### 5. clone_ready_events

Tracks when voice clones are ready (async workflow analytics).

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| caller_id | VARCHAR(255) | Caller phone number, indexed |
| greeting_call_id | VARCHAR(255) | Greeting call ID, indexed |
| cloned_voice_id | VARCHAR(255) | ElevenLabs voice ID |
| clone_duration_ms | INTEGER | Clone creation time in ms |
| ready_at | TIMESTAMP | Ready timestamp, indexed |
| created_at | TIMESTAMP | Creation timestamp |

**Indexes**: `caller_id`, `greeting_call_id`, `ready_at`

---

### 6. clone_failed_events

Tracks voice clone failures.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| caller_id | VARCHAR(255) | Caller phone number, indexed |
| greeting_call_id | VARCHAR(255) | Greeting call ID, indexed |
| error_message | TEXT | Error description |
| failed_at | TIMESTAMP | Failure timestamp, indexed |
| created_at | TIMESTAMP | Creation timestamp |

**Indexes**: `caller_id`, `greeting_call_id`, `failed_at`

---

### 7. clone_transfer_events

Tracks handoff from greeting to voice agent.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| greeting_call_id | VARCHAR(255) | Original greeting call ID, indexed |
| agent_call_id | VARCHAR(255) | New agent call ID, indexed |
| cloned_voice_id | VARCHAR(255) | Voice ID used |
| transferred_at | TIMESTAMP | Transfer timestamp, indexed |
| created_at | TIMESTAMP | Creation timestamp |

**Indexes**: `greeting_call_id`, `agent_call_id`, `transferred_at`

---

## Migrations

Migrations are managed by Alembic.

### Create Migration
```bash
cd Servers/VoiceClone_PreCall_Service
alembic revision --autogenerate -m "Description"
```

### Apply Migrations
```bash
alembic upgrade head
```

### Rollback
```bash
alembic downgrade -1
```

## Connection

- **URL**: `postgresql+asyncpg://voiceagent:password@postgres:5432/voice_clones`
- **Pool Size**: 5
- **Max Overflow**: 10
- **Pre-ping**: Enabled
