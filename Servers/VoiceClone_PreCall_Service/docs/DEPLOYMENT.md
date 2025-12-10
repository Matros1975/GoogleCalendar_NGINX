# Deployment Guide

## Overview

This guide covers deploying the Voice Clone Pre-Call Service using Docker and Docker Compose.

---

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- PostgreSQL 15+ (or use Docker)
- Redis 7+ (or use Docker)
- ElevenLabs API account with:
  - API key
  - Agent ID
  - Registered phone number ID

---

## Quick Start

### 1. Clone Repository

```bash
git clone <repository-url>
cd Servers/VoiceClone_PreCall_Service
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
nano .env
```

**Required Variables**:
```env
ELEVENLABS_API_KEY=sk-your-api-key
ELEVENLABS_AGENT_ID=your-agent-id
ELEVENLABS_PHONE_NUMBER_ID=your-phone-number-id
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/voiceclone_db
REDIS_URL=redis://localhost:6379/0
WEBHOOK_SECRET=your-secure-secret-here
3CX_WEBHOOK_SECRET=your-3cx-secret-here
```

### 3. Build and Run

**Standalone**:
```bash
docker build -t voiceclone-precall .
docker run -p 3006:3006 --env-file .env voiceclone-precall
```

**With Docker Compose** (from repository root):
```bash
docker-compose up -d voiceclone-precall
```

### 4. Verify Deployment

```bash
curl http://localhost:3006/health
```

Expected response:
```json
{
  "status": "ok",
  "database": "ok",
  "redis": "ok",
  "elevenlabs": "ok",
  "timestamp": "2025-12-10T12:00:00.000000Z"
}
```

---

## Production Deployment

### Docker Compose Configuration

The service is configured in the root `docker-compose.yml`:

```yaml
voiceclone-precall:
  build: ./Servers/VoiceClone_PreCall_Service
  container_name: voiceclone-precall
  restart: unless-stopped
  env_file:
    - .env
  networks:
    - mcp-internal
  environment:
    - ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY}
    - DATABASE_URL=${VOICECLONE_DATABASE_URL}
    # ... more environment variables
  volumes:
    - voiceclone-data:/app/data
    - ./logs:/var/log/mcp-services
  ports:
    - "3006:3006"  # Only for development
  healthcheck:
    test: ["CMD-SHELL", "curl -f http://localhost:3006/health || exit 1"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 15s
```

### NGINX Reverse Proxy

The service is exposed through NGINX at:
- `https://matrosmcp.duckdns.org/voiceclone/*`

**NGINX Configuration** (`nginx/conf.d/mcp-proxy.conf`):

```nginx
# Upstream
upstream voiceclone_precall_backend {
    server voiceclone-precall:3006;
    keepalive 32;
}

# Endpoints
location /voiceclone/webhook/3cx {
    proxy_pass http://voiceclone_precall_backend/webhook/3cx;
    # ... proxy settings
}

location /voiceclone/webhook/postcall {
    proxy_pass http://voiceclone_precall_backend/webhook/postcall;
    # ... proxy settings
}

location /voiceclone/health {
    proxy_pass http://voiceclone_precall_backend/health;
}
```

---

## Database Setup

### Using PostgreSQL Docker Container

```bash
docker run -d \
  --name voiceclone-postgres \
  -e POSTGRES_USER=voiceclone \
  -e POSTGRES_PASSWORD=secretpass \
  -e POSTGRES_DB=voiceclone_db \
  -p 5432:5432 \
  -v voiceclone-pgdata:/var/lib/postgresql/data \
  postgres:15-alpine
```

### Run Migrations

```bash
cd Servers/VoiceClone_PreCall_Service
pip install -r requirements.txt
alembic upgrade head
```

### Verify Database

```bash
psql -h localhost -U voiceclone -d voiceclone_db -c "\dt"
```

Should show 7 tables:
- caller_voice_mapping
- voice_clone_cache
- call_log
- voice_clone_log
- clone_ready_events
- clone_failed_events
- clone_transfer_events

---

## Redis Setup

### Using Redis Docker Container

```bash
docker run -d \
  --name voiceclone-redis \
  -p 6379:6379 \
  -v voiceclone-redis-data:/data \
  redis:7-alpine
```

### Verify Redis

```bash
redis-cli ping
# Should return: PONG
```

---

## Voice Sample Storage

### Option 1: Local Storage (Development)

```bash
mkdir -p /data/voices
# Copy voice samples to /data/voices/
```

Configuration:
```env
VOICE_SAMPLE_STORAGE=local
LOCAL_VOICE_SAMPLES_PATH=/data/voices
```

### Option 2: AWS S3 (Production)

1. Create S3 bucket:
```bash
aws s3 mb s3://voice-samples --region eu-west-1
```

2. Upload voice samples:
```bash
aws s3 cp sample.mp3 s3://voice-samples/+31612345678.mp3
```

3. Configure:
```env
VOICE_SAMPLE_STORAGE=s3
S3_BUCKET_NAME=voice-samples
S3_REGION=eu-west-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

### Add Caller Voice Mapping

```sql
INSERT INTO caller_voice_mapping (caller_id, voice_sample_url, voice_name)
VALUES ('+31612345678', 's3://voice-samples/+31612345678.mp3', 'John Doe');
```

---

## 3CX Configuration

### 1. Create Webhook in 3CX

1. Open 3CX Management Console
2. Go to **Settings > Integrations > Webhooks**
3. Click **Add Webhook**
4. Configure:
   - **Name**: Voice Clone Pre-Call
   - **URL**: `https://matrosmcp.duckdns.org/voiceclone/webhook/3cx`
   - **Events**: IncomingCall, CallStateChanged, CallEnded
   - **Method**: POST
   - **Secret**: (your `3CX_WEBHOOK_SECRET`)

### 2. Test Webhook

```bash
# From 3CX, make a test call
# Check logs:
docker logs voiceclone-precall -f
```

---

## ElevenLabs Configuration

### 1. Create Voice Agent

1. Go to ElevenLabs dashboard
2. Create a new Voice Agent
3. Note the **Agent ID**
4. Configure agent settings (persona, knowledge base, etc.)

### 2. Register Phone Number

1. In ElevenLabs dashboard, go to **Phone Numbers**
2. Purchase or register a phone number
3. Note the **Phone Number ID**

### 3. Configure POST-Call Webhook

1. In Voice Agent settings, go to **Webhooks**
2. Add POST-call webhook:
   - **URL**: `https://matrosmcp.duckdns.org/voiceclone/webhook/postcall`
   - **Secret**: (your `WEBHOOK_SECRET`)

---

## Monitoring

### Health Check

```bash
watch -n 5 'curl -s https://matrosmcp.duckdns.org/voiceclone/health | jq'
```

### Logs

```bash
# Container logs
docker logs voiceclone-precall -f

# Application logs
tail -f /var/log/mcp-services/voiceclone.log
```

### Metrics

Check database for metrics:

```sql
-- Clone creation times (last 24 hours)
SELECT 
  AVG(api_response_time_ms) as avg_time,
  MIN(api_response_time_ms) as min_time,
  MAX(api_response_time_ms) as max_time
FROM voice_clone_log
WHERE created_at > NOW() - INTERVAL '24 hours'
  AND status = 'success';

-- Call statistics
SELECT 
  status,
  COUNT(*) as count,
  AVG(duration_seconds) as avg_duration
FROM call_log
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY status;

-- Cache hit rate
SELECT 
  COUNT(*) as total_clones,
  SUM(reuse_count - 1) as cache_hits,
  (SUM(reuse_count - 1) * 100.0 / COUNT(*)) as hit_rate
FROM voice_clone_cache;
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker logs voiceclone-precall

# Common issues:
# 1. Database connection - verify DATABASE_URL
# 2. Redis connection - verify REDIS_URL
# 3. Missing environment variables - check .env
```

### Database Connection Failed

```bash
# Test connection
psql -h localhost -U voiceclone -d voiceclone_db

# If fails, check:
# - PostgreSQL is running
# - Credentials are correct
# - Database exists
```

### Voice Clone Fails

```bash
# Check voice sample exists
aws s3 ls s3://voice-samples/

# Check caller mapping
psql -h localhost -U voiceclone -d voiceclone_db \
  -c "SELECT * FROM caller_voice_mapping WHERE caller_id = '+31612345678';"

# Check ElevenLabs API key
curl -H "xi-api-key: $ELEVENLABS_API_KEY" \
  https://api.elevenlabs.io/v1/voices
```

### Webhook Not Receiving Calls

```bash
# Check NGINX is routing correctly
curl -X POST https://matrosmcp.duckdns.org/voiceclone/health

# Check 3CX webhook configuration
# Verify webhook secret matches
# Check 3CX logs for delivery failures
```

---

## Scaling

### Horizontal Scaling

```yaml
# docker-compose.yml
voiceclone-precall:
  deploy:
    replicas: 3
```

Add load balancer in NGINX:
```nginx
upstream voiceclone_precall_backend {
    server voiceclone-precall-1:3006;
    server voiceclone-precall-2:3006;
    server voiceclone-precall-3:3006;
    keepalive 32;
}
```

### Performance Tuning

1. **Increase cache TTL** for voice clones:
```env
CACHE_TTL=172800  # 48 hours
```

2. **Database connection pooling**:
```python
# In database_service.py, adjust:
pool_size=20
max_overflow=40
```

3. **Redis connection pooling**:
```env
REDIS_MAX_CONNECTIONS=50
```

---

## Security Checklist

- [ ] Webhook secrets configured and secure
- [ ] Database credentials secured
- [ ] AWS credentials (if using S3) secured
- [ ] HTTPS enabled via NGINX
- [ ] Firewall rules configured (only NGINX can access service)
- [ ] Regular security updates applied
- [ ] Logs reviewed regularly for suspicious activity

---

## Backup and Recovery

### Database Backup

```bash
# Automated daily backup
0 2 * * * pg_dump -h localhost -U voiceclone voiceclone_db \
  | gzip > /backups/voiceclone_$(date +\%Y\%m\%d).sql.gz
```

### Voice Samples Backup

```bash
# S3 backup (versioning enabled)
aws s3api put-bucket-versioning \
  --bucket voice-samples \
  --versioning-configuration Status=Enabled

# Local backup
tar -czf voice_samples_backup.tar.gz /data/voices
```

---

## Updates

### Update Service

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up -d --build voiceclone-precall

# Apply migrations
docker exec voiceclone-precall alembic upgrade head
```

---

## Support

For deployment issues:
1. Check logs
2. Review this guide
3. Check GitHub issues
4. Contact repository maintainers
