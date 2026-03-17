# VoiceClone Pre-Call Service - Deployment Guide

## Prerequisites

- Docker & Docker Compose
- PostgreSQL 15+ (shared container)
- ElevenLabs API account with Voice Agent
- 3CX PBX system
- (Optional) AWS S3 for voice sample storage

## Quick Start

### 1. Configuration

Copy environment template:
```bash
cd Servers/VoiceClone_PreCall_Service
cp .env.example .env
```

Edit `.env` with your credentials:
```bash
# Required
ELEVENLABS_API_KEY=your-api-key
ELEVENLABS_AGENT_ID=your-agent-id
ELEVENLABS_PHONE_NUMBER_ID=your-phone-id
DATABASE_URL=postgresql+asyncpg://voiceagent:password@postgres:5432/voice_clones
THREECX_WEBHOOK_SECRET=your-3cx-secret
WEBHOOK_SECRET=your-elevenlabs-secret

# Optional (defaults provided)
GREETING_VOICE_ID=default_greeting_voice
VOICE_SAMPLE_STORAGE=local
CACHE_TTL=86400
```

### 2. Build & Deploy

From repository root:
```bash
docker-compose up -d voiceclone-precall
```

Check logs:
```bash
docker logs -f voiceclone-precall
```

### 3. Verify Deployment

Test health endpoint:
```bash
curl https://matrosmcp.duckdns.org/voiceclone/health
```

Expected response:
```json
{
  "status": "ok",
  "database": "ok",
  "elevenlabs": "ok",
  "timestamp": "2025-12-10T12:00:00Z"
}
```

## Database Setup

The service automatically creates tables on first run. To manually run migrations:

```bash
docker exec -it voiceclone-precall bash
alembic upgrade head
```

## NGINX Configuration

The service is reverse-proxied through NGINX at:
- **3CX Webhook**: `https://matrosmcp.duckdns.org/voiceclone/webhook/3cx`
- **ElevenLabs Webhook**: `https://matrosmcp.duckdns.org/voiceclone/webhook/elevenlabs/postcall`
- **API**: `https://matrosmcp.duckdns.org/voiceclone/api/`
- **Health**: `https://matrosmcp.duckdns.org/voiceclone/health`

## 3CX Integration

### Configure Webhook

1. Go to 3CX Management Console
2. Navigate to Settings → Webhooks
3. Add new webhook:
   - **URL**: `https://matrosmcp.duckdns.org/voiceclone/webhook/3cx`
   - **Events**: Incoming Call, Call Ended
   - **Secret**: Value from `THREECX_WEBHOOK_SECRET`

### Test Integration

Use example script:
```bash
python examples/test_webhook.py
```

## ElevenLabs Integration

### Configure POST-Call Webhook

1. Go to ElevenLabs Dashboard → Agent Settings
2. Add POST-call webhook:
   - **URL**: `https://matrosmcp.duckdns.org/voiceclone/webhook/elevenlabs/postcall`
   - **Secret**: Value from `WEBHOOK_SECRET`

### Voice Samples

#### Local Storage (Default)

Place voice samples in `/app/data/voices/`:
```bash
docker cp sample.mp3 voiceclone-precall:/app/data/voices/+31612345678.mp3
```

Add mapping to database:
```sql
INSERT INTO caller_voice_mapping (id, caller_id, voice_sample_url, voice_name)
VALUES (gen_random_uuid(), '+31612345678', '/app/data/voices/+31612345678.mp3', 'Customer Voice');
```

#### S3 Storage

Configure S3:
```bash
VOICE_SAMPLE_STORAGE=s3
S3_BUCKET_NAME=voice-samples
S3_REGION=eu-west-1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
```

Upload to S3 and add mapping:
```sql
INSERT INTO caller_voice_mapping (id, caller_id, voice_sample_url, voice_name)
VALUES (gen_random_uuid(), '+31612345678', 's3://voice-samples/+31612345678.mp3', 'Customer Voice');
```

## Monitoring

### Logs

View service logs:
```bash
docker logs -f voiceclone-precall

# Or from mounted volume
tail -f logs/voiceclone.log
```

### Metrics

Get statistics:
```bash
curl -H "Authorization: Bearer your-token" \
  https://matrosmcp.duckdns.org/voiceclone/api/v1/statistics
```

### Health Checks

Docker automatically runs health checks every 30 seconds:
```bash
docker ps --filter "name=voiceclone-precall"
```

## Troubleshooting

### Service Won't Start

Check logs:
```bash
docker logs voiceclone-precall
```

Common issues:
- Missing environment variables
- Database connection failed
- Invalid API credentials

### Database Connection Failed

Verify PostgreSQL is running:
```bash
docker ps --filter "name=postgres"
```

Test connection:
```bash
docker exec -it voiceclone-precall python -c "from src.services.database_service import DatabaseService; import asyncio; asyncio.run(DatabaseService().health_check())"
```

### ElevenLabs API Errors

Test API connectivity:
```bash
docker exec -it voiceclone-precall python -c "from src.services.elevenlabs_client import ElevenLabsService; import asyncio; print(asyncio.run(ElevenLabsService().health_check()))"
```

Check API key:
- Valid format
- Correct permissions
- Not expired

### Voice Clone Timeout

If clones consistently timeout (35s default):

1. Increase timeout:
```bash
CLONE_MAX_WAIT_SECONDS=60
```

2. Check voice sample quality:
   - Minimum 1KB
   - Supported formats: mp3, wav, m4a, flac, ogg
   - Clear audio, minimal background noise

3. Check network latency to ElevenLabs

## Performance Tuning

### Cache Hit Rate

Monitor cache effectiveness:
```bash
curl -H "Authorization: Bearer token" \
  https://matrosmcp.duckdns.org/voiceclone/api/v1/statistics | jq '.hit_rate'
```

Target: > 0.80 (80% hit rate)

If low:
- Increase `CACHE_TTL` (default: 24h)
- Verify voice samples are mapped correctly

### Resource Limits

Adjust in `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      memory: 1G  # Increase if needed
      cpus: "2.0"
```

## Security

### Webhook Signatures

Always enable HMAC validation:
- 3CX: Set `THREECX_WEBHOOK_SECRET`
- ElevenLabs: Set `WEBHOOK_SECRET`

### API Authentication

Protect admin endpoints with bearer tokens in NGINX.

### Network Security

- Service on internal network only
- NGINX handles TLS termination
- No direct external access

## Backup & Recovery

### Database Backup

```bash
docker exec postgres pg_dump -U voiceagent voice_clones > backup.sql
```

### Restore

```bash
docker exec -i postgres psql -U voiceagent voice_clones < backup.sql
```

### Voice Samples Backup

```bash
docker run --rm -v voiceclone-voices:/data -v $(pwd):/backup alpine \
  tar czf /backup/voices-backup.tar.gz /data
```

## Scaling

For high-volume deployments:

1. Run multiple service instances behind load balancer
2. Use external PostgreSQL cluster
3. Enable S3 storage for voice samples
4. Increase cache TTL
5. Monitor and adjust resource limits

## Updates

### Pull Latest Changes

```bash
git pull origin main
```

### Rebuild Container

```bash
docker-compose up -d --build voiceclone-precall
```

### Run Migrations

```bash
docker exec -it voiceclone-precall alembic upgrade head
```

## Support

For issues:
1. Check logs: `docker logs voiceclone-precall`
2. Verify health: `/voiceclone/health`
3. Review configuration
4. Contact development team
