# VoiceClone Pre-Call Service

**Version:** 2.0.0  
**Port:** 3006  
**Status:** Production Ready

## Overview

The VoiceClone Pre-Call Service integrates Twilio with ElevenLabs Voice Agent API to dynamically clone voices before initiating calls. This service implements an innovative asynchronous voice cloning workflow using TwiML-based call control that eliminates awkward silence during voice cloning.

### Key Features

- **Instant TwiML Response**: Returns greeting within 100ms using Twilio TwiML
- **Async Voice Cloning**: Clones voice in background while greeting plays
- **Automatic Transition**: Seamlessly connects to ElevenLabs via WebSocket when ready
- **Zero Perceived Wait**: Professional, uninterrupted conversation experience
- **Voice Clone Caching**: Performance optimization with 24-hour TTL
- **Comprehensive Logging**: Full audit trail for calls and clones
- **Twilio Native**: Uses TwiML and WebSocket streaming for direct integration

## Architecture

```
Twilio Phone → Webhook → VoiceClone Service → ElevenLabs WebSocket
                              ↓
                        PostgreSQL (voice_clones DB)
```

### Workflow

1. **Incoming Call**: Twilio sends webhook notification to `/webhooks/inbound`
2. **Immediate TwiML Response**: Service returns TwiML with greeting (100ms)
3. **Background Clone**: Voice cloning happens asynchronously (5-30s)
4. **Status Polling**: Twilio polls `/webhooks/status-callback` to check completion
5. **WebSocket Connection**: When ready, TwiML connects to ElevenLabs via WebSocket
6. **Call Logging**: Full transcript and metrics stored

## Technology Stack

- **Framework**: FastAPI (async-first)
- **Server**: Uvicorn
- **Database**: PostgreSQL 15+ (voice_clones database)
- **API Client**: httpx (async HTTP)
- **Python**: 3.11
- **ORM**: SQLAlchemy (async)
- **Migrations**: Alembic
- **Telephony**: Twilio (TwiML + WebSocket)
- **Voice AI**: ElevenLabs (WebSocket streaming)

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- ElevenLabs API account
- Twilio account with phone number
- Public webhook URL (use ngrok for local testing)

### Installation

```bash
# Clone repository
cd Servers/VoiceClone_PreCall_Service

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run database migrations
alembic upgrade head

# Start service
python -m src.main
```

### Docker Deployment

```bash
# Build and run with docker-compose
cd /home/runner/work/GoogleCalendar_NGINX/GoogleCalendar_NGINX
docker-compose up -d voiceclone-precall
```

## Configuration

See `.env.example` for all configuration options. Key variables:

```bash
# ElevenLabs
ELEVENLABS_API_KEY=your-api-key
ELEVENLABS_AGENT_ID=your-agent-id

# Twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890
SKIP_WEBHOOK_SIGNATURE_VALIDATION=false  # Set to true for local testing

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/voice_clones

# Greeting (Async Workflow)
GREETING_VOICE_ID=default_greeting_voice
GREETING_MESSAGE="Hello, thanks for calling..."
GREETING_MUSIC_ENABLED=true
GREETING_MUSIC_URL=https://your-domain.com/hold-music.mp3
```

## API Endpoints

### Health Check
```http
GET /health
```

### Twilio Webhooks
```http
POST /webhooks/inbound          # Incoming call from Twilio
POST /webhooks/status-callback  # Status polling (clone completion check)
```

### ElevenLabs POST-Call Webhook
```http
POST /webhook/elevenlabs/postcall
```

### Voice Clone Cache Management
```http
DELETE /api/v1/cache/{caller_id}
GET /api/v1/statistics
```

## Twilio Configuration

### 1. Configure Phone Number Webhook

In Twilio Console → Phone Numbers → Manage → Active numbers:

**Voice & Fax → A CALL COMES IN:**
- Webhook: `https://your-domain.com/webhooks/inbound`
- HTTP Method: `POST`

### 2. Test Locally with ngrok

```bash
# Start ngrok
ngrok http 8000

# Set webhook URL in Twilio to:
# https://your-ngrok-url.ngrok.io/webhooks/inbound

# Or use test script:
SKIP_WEBHOOK_SIGNATURE_VALIDATION=true ./test-twilio-webhook.sh
```

## Database Schema

### Tables

1. **caller_voice_mapping** - Maps caller IDs to voice samples
2. **voice_clone_cache** - Caches cloned voices (24h TTL)
3. **call_log** - Call records and transcripts (updated: uses `call_sid` instead of `threecx_call_id`)
4. **voice_clone_log** - Clone creation audit trail
5. **clone_ready_events** - Clone completion tracking
6. **clone_failed_events** - Clone failure tracking
7. **clone_transfer_events** - Greeting-to-agent handoff tracking

See `docs/DATABASE.md` for complete schema documentation.

## Testing

```bash
# Test Twilio webhooks locally
./test-twilio-webhook.sh

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/ -m integration
```

## Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

### Logs

Logs are written to `/var/log/mcp-services/voiceclone.log` with rotation.

### Metrics

- Cache hit/miss rates
- Average clone creation time
- Call success/failure rates
- API response times

## Security

- HMAC signature validation for webhooks
- API key authentication for admin endpoints
- IP whitelisting support
- Secure credential storage
- Non-root container execution

## Documentation

- [API Documentation](docs/API.md)
- [Database Schema](docs/DATABASE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Architecture Overview](docs/ARCHITECTURE.md)

## Troubleshooting

### Voice Clone Timeout

If voice cloning exceeds `CLONE_MAX_WAIT_SECONDS` (default: 35s), the service will:
1. Log the timeout event
2. Fall back to default voice
3. Continue the call

### Database Connection Issues

```bash
# Test database connectivity
python -c "from src.services.database_service import DatabaseService; import asyncio; asyncio.run(DatabaseService().health_check())"
```

### ElevenLabs API Errors

Check logs for API response codes:
- 401: Invalid API key
- 429: Rate limit exceeded
- 500: ElevenLabs service issue

## License

Proprietary - All rights reserved

## Support

For issues and questions, contact the development team.
