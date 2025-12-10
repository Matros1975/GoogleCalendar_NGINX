# Database Schema Documentation

## Overview

The Voice Clone Pre-Call Service uses PostgreSQL 15+ with asyncpg driver for all database operations. The schema includes 7 tables for managing voice clones, call logs, and event tracking.

---

## Tables

### 1. caller_voice_mapping

Maps caller phone numbers to their voice sample files.

**Purpose**: Store the relationship between callers and their pre-recorded voice samples.

**Columns**:

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | UUID | No | uuid_generate_v4() | Primary key |
| caller_id | VARCHAR(255) | No | - | Caller phone number (E.164 format) |
| voice_sample_url | VARCHAR(2048) | No | - | S3 URL or local path to voice sample |
| voice_name | VARCHAR(255) | No | - | Display name for the voice clone |
| description | TEXT | Yes | NULL | Optional description |
| account_id | VARCHAR(255) | Yes | NULL | Account ID for multi-tenancy |
| created_at | TIMESTAMP | No | NOW() | Record creation timestamp |
| updated_at | TIMESTAMP | No | NOW() | Record update timestamp |
| deleted_at | TIMESTAMP | Yes | NULL | Soft delete timestamp |

**Indexes**:
- `idx_caller_voice_mapping_caller_id` on `caller_id` (UNIQUE)
- `idx_caller_voice_mapping_account_id` on `account_id`
- `idx_caller_voice_mapping_created_at` on `created_at`

**Example**:
```sql
INSERT INTO caller_voice_mapping (caller_id, voice_sample_url, voice_name)
VALUES ('+31612345678', 's3://voice-samples/john_doe.mp3', 'John Doe Voice');
```

---

### 2. voice_clone_cache

Caches created voice clones with TTL for performance optimization.

**Purpose**: Avoid recreating voice clones by caching them with expiration times.

**Columns**:

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | UUID | No | uuid_generate_v4() | Primary key |
| caller_id | VARCHAR(255) | No | - | Caller phone number |
| cloned_voice_id | VARCHAR(255) | No | - | ElevenLabs voice ID |
| clone_created_at | TIMESTAMP | No | NOW() | When clone was created |
| ttl_expires_at | TIMESTAMP | No | - | Cache expiration time |
| reuse_count | INTEGER | No | 1 | Number of times clone was reused |
| last_used_at | TIMESTAMP | No | NOW() | Last time clone was used |
| created_at | TIMESTAMP | No | NOW() | Record creation timestamp |
| deleted_at | TIMESTAMP | Yes | NULL | Soft delete timestamp |

**Indexes**:
- `idx_voice_clone_cache_caller_id` on `caller_id`
- `idx_voice_clone_cache_cloned_voice_id` on `cloned_voice_id`
- `idx_voice_clone_cache_ttl_expires_at` on `ttl_expires_at`

**Example**:
```sql
SELECT cloned_voice_id FROM voice_clone_cache
WHERE caller_id = '+31612345678'
  AND ttl_expires_at > NOW()
  AND deleted_at IS NULL
ORDER BY created_at DESC
LIMIT 1;
```

---

### 3. call_log

Logs all voice agent calls with transcripts and metadata.

**Purpose**: Track all calls for analytics, auditing, and debugging.

**Columns**:

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | UUID | No | uuid_generate_v4() | Primary key |
| call_id | VARCHAR(255) | No | - | ElevenLabs call ID (UNIQUE) |
| threecx_call_id | VARCHAR(255) | No | - | 3CX call ID |
| caller_id | VARCHAR(255) | No | - | Caller phone number |
| cloned_voice_id | VARCHAR(255) | No | - | Voice ID used for call |
| call_started_at | TIMESTAMP | No | NOW() | Call start time |
| call_ended_at | TIMESTAMP | Yes | NULL | Call end time |
| duration_seconds | INTEGER | Yes | NULL | Call duration |
| transcript | TEXT | Yes | NULL | Full conversation transcript |
| status | VARCHAR(50) | No | - | Call status: initiated, completed, failed |
| metadata | JSONB | Yes | NULL | Additional metadata |
| created_at | TIMESTAMP | No | NOW() | Record creation timestamp |
| updated_at | TIMESTAMP | No | NOW() | Record update timestamp |

**Indexes**:
- `idx_call_log_call_id` on `call_id` (UNIQUE)
- `idx_call_log_caller_id` on `caller_id`
- `idx_call_log_threecx_call_id` on `threecx_call_id`
- `idx_call_log_status` on `status`
- `idx_call_log_created_at` on `created_at`

**Example**:
```sql
UPDATE call_log
SET call_ended_at = NOW(),
    duration_seconds = 185,
    transcript = 'Agent: Hello...',
    status = 'completed'
WHERE call_id = 'elevenlabs_call_123';
```

---

### 4. voice_clone_log

Logs voice clone creation events with performance metrics.

**Purpose**: Track clone creation success/failure and performance for monitoring.

**Columns**:

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | UUID | No | uuid_generate_v4() | Primary key |
| caller_id | VARCHAR(255) | No | - | Caller phone number |
| cloned_voice_id | VARCHAR(255) | No | - | Created voice ID |
| clone_created_at | TIMESTAMP | No | NOW() | Clone creation time |
| api_response_time_ms | INTEGER | No | - | API latency in milliseconds |
| sample_file_size_bytes | INTEGER | No | - | Voice sample file size |
| status | VARCHAR(50) | No | - | success or failed |
| error_message | TEXT | Yes | NULL | Error details if failed |
| created_at | TIMESTAMP | No | NOW() | Record creation timestamp |

**Indexes**:
- `idx_voice_clone_log_caller_id` on `caller_id`
- `idx_voice_clone_log_cloned_voice_id` on `cloned_voice_id`
- `idx_voice_clone_log_status` on `status`

**Analytics Queries**:
```sql
-- Average clone creation time
SELECT AVG(api_response_time_ms) FROM voice_clone_log
WHERE status = 'success' AND created_at > NOW() - INTERVAL '7 days';

-- Clone success rate
SELECT 
  status,
  COUNT(*) as count,
  COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
FROM voice_clone_log
GROUP BY status;
```

---

### 5. clone_ready_events

Tracks when voice clones are ready during async workflow.

**Purpose**: Monitor clone completion timing for async greeting workflow.

**Columns**:

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | UUID | No | uuid_generate_v4() | Primary key |
| caller_id | VARCHAR(255) | No | - | Caller phone number |
| greeting_call_id | VARCHAR(255) | No | - | Greeting call ID |
| cloned_voice_id | VARCHAR(255) | No | - | Created voice ID |
| clone_duration_ms | INTEGER | No | - | Time to create clone (ms) |
| ready_at | TIMESTAMP | No | NOW() | When clone became ready |
| created_at | TIMESTAMP | No | NOW() | Record creation timestamp |

**Indexes**:
- `idx_clone_ready_events_caller_id` on `caller_id`
- `idx_clone_ready_events_greeting_call_id` on `greeting_call_id`
- `idx_clone_ready_events_ready_at` on `ready_at`

---

### 6. clone_failed_events

Tracks failed voice clone attempts during async workflow.

**Purpose**: Monitor and debug clone failures.

**Columns**:

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | UUID | No | uuid_generate_v4() | Primary key |
| caller_id | VARCHAR(255) | No | - | Caller phone number |
| greeting_call_id | VARCHAR(255) | No | - | Greeting call ID |
| error_message | TEXT | No | - | Error details |
| failed_at | TIMESTAMP | No | NOW() | When clone failed |
| created_at | TIMESTAMP | No | NOW() | Record creation timestamp |

**Indexes**:
- `idx_clone_failed_events_caller_id` on `caller_id`
- `idx_clone_failed_events_greeting_call_id` on `greeting_call_id`
- `idx_clone_failed_events_failed_at` on `failed_at`

---

### 7. clone_transfer_events

Tracks automatic transfers from greeting to cloned voice agent.

**Purpose**: Monitor call transitions for debugging and analytics.

**Columns**:

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | UUID | No | uuid_generate_v4() | Primary key |
| greeting_call_id | VARCHAR(255) | No | - | Greeting call ID |
| agent_call_id | VARCHAR(255) | No | - | Agent call ID |
| cloned_voice_id | VARCHAR(255) | No | - | Voice ID used |
| transferred_at | TIMESTAMP | No | NOW() | Transfer timestamp |
| created_at | TIMESTAMP | No | NOW() | Record creation timestamp |

**Indexes**:
- `idx_clone_transfer_events_greeting_call_id` on `greeting_call_id`
- `idx_clone_transfer_events_agent_call_id` on `agent_call_id`
- `idx_clone_transfer_events_transferred_at` on `transferred_at`

---

## Database Migrations

Migrations are managed with Alembic.

### Generate Migration

```bash
cd Servers/VoiceClone_PreCall_Service
alembic revision --autogenerate -m "Description of changes"
```

### Apply Migrations

```bash
alembic upgrade head
```

### Rollback Migration

```bash
alembic downgrade -1
```

---

## Performance Considerations

1. **Indexes**: All foreign key and frequently queried columns are indexed
2. **TTL Cleanup**: Expired cache entries should be cleaned periodically
3. **Soft Deletes**: Use `deleted_at IS NULL` in all queries to exclude deleted records
4. **Connection Pooling**: Configured in `DatabaseService` (pool_size=10, max_overflow=20)
5. **Async Operations**: All database operations use async/await for non-blocking I/O

---

## Backup and Maintenance

### Backup

```bash
pg_dump -h localhost -U voiceclone -d voiceclone_db > backup.sql
```

### Restore

```bash
psql -h localhost -U voiceclone -d voiceclone_db < backup.sql
```

### Cleanup Old Records

```sql
-- Cleanup old call logs (older than 90 days)
DELETE FROM call_log WHERE created_at < NOW() - INTERVAL '90 days';

-- Cleanup expired cache entries
DELETE FROM voice_clone_cache WHERE ttl_expires_at < NOW();
```

---

## Connection String Format

```
postgresql+asyncpg://username:password@host:port/database
```

**Example**:
```
DATABASE_URL=postgresql+asyncpg://voiceclone:secretpass@localhost:5432/voiceclone_db
```
