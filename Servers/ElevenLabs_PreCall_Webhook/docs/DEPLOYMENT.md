# Deployment Guide

## ElevenLabs Pre-Call Webhook Service Deployment

This guide covers deploying the Pre-Call Webhook Service in various environments.

---

## Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- NGINX (for production)
- ElevenLabs API key
- ElevenLabs webhook secret

---

## Local Development

### 1. Clone Repository

```bash
cd Servers/ElevenLabs_PreCall_Webhook
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

Required variables:
```env
ELEVENLABS_API_KEY=your-api-key-here
ELEVENLABS_WEBHOOK_SECRET=your-webhook-secret-here
```

### 4. Run Service

```bash
python -m src.main
```

Service runs on: `http://localhost:3005`

### 5. Test

```bash
# Health check
curl http://localhost:3005/health

# Run unit tests
pytest tests/unit/ -v

# Test with example payload
python examples/test_precall_webhook.py --health
```

---

## Docker Deployment

### 1. Build Image

```bash
cd Servers/ElevenLabs_PreCall_Webhook
docker build -t elevenlabs-precall-webhook:latest .
```

### 2. Run Container

```bash
docker run -d \
  --name elevenlabs-precall-webhook \
  -p 3005:3005 \
  -e ELEVENLABS_API_KEY=your-api-key \
  -e ELEVENLABS_WEBHOOK_SECRET=your-webhook-secret \
  --restart unless-stopped \
  elevenlabs-precall-webhook:latest
```

### 3. Verify

```bash
# Check container status
docker ps | grep elevenlabs-precall

# Check logs
docker logs elevenlabs-precall-webhook

# Test health endpoint
curl http://localhost:3005/health
```

### 4. Stop/Remove

```bash
docker stop elevenlabs-precall-webhook
docker rm elevenlabs-precall-webhook
```

---

## Docker Compose

### Add to docker-compose.yml

```yaml
services:
  elevenlabs-precall-webhook:
    build:
      context: ./Servers/ElevenLabs_PreCall_Webhook
      dockerfile: Dockerfile
    container_name: elevenlabs-precall-webhook
    restart: unless-stopped
    ports:
      - "3005:3005"
    environment:
      - ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY}
      - ELEVENLABS_WEBHOOK_SECRET=${ELEVENLABS_WEBHOOK_SECRET}
      - LOG_LEVEL=INFO
      - LOG_FORMAT=text
      - PRECALL_WEBHOOK_PORT=3005
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

### Deploy

```bash
# Start service
docker-compose up -d elevenlabs-precall-webhook

# View logs
docker-compose logs -f elevenlabs-precall-webhook

# Restart
docker-compose restart elevenlabs-precall-webhook

# Stop
docker-compose stop elevenlabs-precall-webhook
```

---

## NGINX Configuration

### Reverse Proxy Setup

Create `/etc/nginx/conf.d/elevenlabs-precall.conf`:

```nginx
# ElevenLabs Pre-Call Webhook upstream
upstream elevenlabs_precall_webhook {
    server localhost:3005;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Pre-Call Webhook Endpoint
    location /elevenlabs/precall/webhook {
        proxy_pass http://elevenlabs_precall_webhook/webhook;
        
        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts (voice processing can take 5-10 seconds)
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Body size (voice samples up to 10MB)
        client_max_body_size 15M;
        client_body_buffer_size 15M;
        
        # Optional: IP Whitelisting for ElevenLabs
        # allow 34.67.146.145;    # US Default
        # allow 34.59.11.47;      # US Default
        # allow 35.204.38.71;     # EU
        # allow 34.147.113.54;    # EU
        # deny all;
    }

    # Health Check Endpoint
    location /elevenlabs/precall/health {
        proxy_pass http://elevenlabs_precall_webhook/health;
        proxy_set_header Host $host;
        
        # Allow internal monitoring
        allow 127.0.0.1;
        allow 10.0.0.0/8;
        deny all;
    }
}
```

### Test Configuration

```bash
# Test NGINX config
sudo nginx -t

# Reload NGINX
sudo systemctl reload nginx
```

### Verify

```bash
# Test health endpoint
curl https://your-domain.com/elevenlabs/precall/health

# Should return 401 without proper signature
curl -X POST https://your-domain.com/elevenlabs/precall/webhook
```

---

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `ELEVENLABS_API_KEY` | ElevenLabs API key | `sk_abc123...` |
| `ELEVENLABS_WEBHOOK_SECRET` | Webhook signing secret | `whsec_xyz789...` |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `PRECALL_WEBHOOK_HOST` | `0.0.0.0` | Host to bind to |
| `PRECALL_WEBHOOK_PORT` | `3005` | Port to listen on |
| `LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT` | `text` | Log format (text, json) |
| `LOG_DIR` | `/var/log/elevenlabs-precall-webhook` | Log directory |
| `VOICE_CLONE_MIN_DURATION` | `3.0` | Min audio duration (seconds) |
| `VOICE_CLONE_MAX_SIZE_MB` | `10.0` | Max file size (MB) |
| `DEFAULT_FIRST_MESSAGE` | `Hallo {name}, fijn dat je belt!` | Agent greeting template |
| `ENABLE_VOICE_SAMPLE_STORAGE` | `false` | Save voice samples to disk |
| `VOICE_SAMPLE_STORAGE_PATH` | `/app/storage/voice_samples` | Storage path |

---

## ElevenLabs Configuration

### 1. Get API Key

1. Go to [ElevenLabs Dashboard](https://elevenlabs.io/app/settings/api-keys)
2. Create or copy your API key
3. Add to environment: `ELEVENLABS_API_KEY=sk_...`

### 2. Configure Webhook

1. Go to agent settings in ElevenLabs
2. Enable "Pre-call webhook"
3. Set URL: `https://your-domain.com/elevenlabs/precall/webhook`
4. Copy webhook secret
5. Add to environment: `ELEVENLABS_WEBHOOK_SECRET=whsec_...`

### 3. Test Configuration

```bash
# In ElevenLabs dashboard, send test webhook
# Check service logs for successful processing
docker logs elevenlabs-precall-webhook
```

---

## Monitoring

### Health Checks

```bash
# Docker health check
docker inspect elevenlabs-precall-webhook | jq '.[0].State.Health'

# Manual check
curl http://localhost:3005/health
```

### Logs

```bash
# Docker logs
docker logs -f elevenlabs-precall-webhook

# File logs (if mounted)
tail -f ./logs/precall_webhook.log

# Search for errors
docker logs elevenlabs-precall-webhook 2>&1 | grep -i error
```

### Metrics

Key metrics to monitor:
- Request rate (requests/minute)
- Success rate (successful voice clones)
- Processing time (should be < 10 seconds)
- Error rate (by error type)
- Voice creation failures
- Agent update failures

---

## Troubleshooting

### Service Won't Start

**Check environment variables:**
```bash
docker exec elevenlabs-precall-webhook env | grep ELEVENLABS
```

**Check logs:**
```bash
docker logs elevenlabs-precall-webhook
```

**Common issues:**
- Missing API key or webhook secret
- Port 3005 already in use
- Insufficient permissions for log directory

### HMAC Validation Failures

**Symptoms:**
- All requests return 401 Unauthorized
- Logs show "HMAC validation failed"

**Solutions:**
1. Verify webhook secret matches ElevenLabs
2. Check server clock is synchronized (NTP)
3. Ensure NGINX is not modifying request body
4. Check signature header is being passed through

**Test:**
```bash
# Use test script with correct secret
python examples/test_precall_webhook.py \
  examples/precall_payload.json \
  your-webhook-secret \
  http://localhost:3005
```

### Voice Cloning Failures

**Symptoms:**
- Requests return 422 Unprocessable Entity
- Logs show "Voice cloning failed"

**Solutions:**
1. Check API key has voice cloning permissions
2. Verify voice sample quality (format, size, duration)
3. Check ElevenLabs API quota and limits
4. Review ElevenLabs account status

**Debug:**
```bash
# Enable debug logging
docker run -e LOG_LEVEL=DEBUG ...

# Check voice sample
file voice_sample.mp3
ffprobe voice_sample.mp3
```

### Agent Update Failures

**Symptoms:**
- Response shows `"agent_updated": false`
- Voice created but not activated

**Solutions:**
1. Verify agent_id is correct
2. Check agent permissions in ElevenLabs
3. Ensure agent exists and is active

### High Processing Times

**Normal:** 2-5 seconds  
**Slow:** > 10 seconds

**Causes:**
- Large voice samples (>5 seconds)
- Poor network to ElevenLabs API
- High API load
- Low quality voice samples (more processing)

**Solutions:**
1. Optimize voice sample quality
2. Keep samples 3-5 seconds
3. Check network latency
4. Monitor ElevenLabs API status

---

## Security Checklist

- [ ] HTTPS enabled with valid SSL certificate
- [ ] HMAC signature validation enforced
- [ ] API keys in environment variables (not code)
- [ ] IP whitelisting configured (optional)
- [ ] Non-root user in Docker container
- [ ] Log files have appropriate permissions
- [ ] Voice samples not persisted by default
- [ ] Caller data sanitized in logs
- [ ] Regular security updates applied

---

## Scaling

### Horizontal Scaling

Run multiple instances behind load balancer:

```yaml
services:
  elevenlabs-precall-webhook-1:
    # ... same config
    ports:
      - "3005:3005"
  
  elevenlabs-precall-webhook-2:
    # ... same config
    ports:
      - "3006:3005"
  
  elevenlabs-precall-webhook-3:
    # ... same config
    ports:
      - "3007:3005"
```

**NGINX load balancing:**
```nginx
upstream elevenlabs_precall_webhook {
    least_conn;
    server localhost:3005;
    server localhost:3006;
    server localhost:3007;
}
```

### Resource Limits

```yaml
services:
  elevenlabs-precall-webhook:
    # ...
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

---

## Backup & Recovery

### Configuration Backup

```bash
# Backup environment file
cp .env .env.backup

# Backup NGINX config
sudo cp /etc/nginx/conf.d/elevenlabs-precall.conf \
       /etc/nginx/conf.d/elevenlabs-precall.conf.backup
```

### Log Rotation

Automatic with Docker, or configure logrotate:

```bash
# /etc/logrotate.d/elevenlabs-precall-webhook
/app/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
}
```

---

## Maintenance

### Updates

```bash
# Pull latest code
git pull origin main

# Rebuild image
docker-compose build elevenlabs-precall-webhook

# Deploy with zero downtime
docker-compose up -d --no-deps elevenlabs-precall-webhook
```

### Database/State

Service is stateless - no database required.

---

## Support

For issues:
1. Check logs for error messages
2. Verify configuration
3. Test with example payloads
4. Open issue in repository
