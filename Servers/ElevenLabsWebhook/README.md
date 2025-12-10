# ElevenLabs Webhook Microservice

A Python-based microservice to handle ElevenLabs post-call webhooks. This service follows existing infrastructure patterns and is designed to run as a containerized service behind NGINX proxy.

## Deployment

**Azure Container Apps**: Deployed to West Europe  
**Service URL**: https://elevenlabswebhook.kindriver-c1a923f6.westeurope.azurecontainerapps.io  
**Auto-deployment**: Enabled via GitHub Actions on push to `azure-main` branch

## Overview

This service receives and processes webhook events from ElevenLabs voice agents, including:

- **post_call_transcription**: Full conversation data with transcripts, analysis, and metadata
- **post_call_audio**: Base64-encoded MP3 audio recordings
- **call_initiation_failure**: Failed call metadata and error details

## Features

- **HMAC Authentication**: Secure signature validation following ElevenLabs specification
- **Multiple Webhook Types**: Handles all three ElevenLabs webhook event types
- **Optional Storage**: Configurable storage for transcripts and audio files
- **Structured Logging**: JSON or text format logging with configurable levels
- **Docker Integration**: Containerized with health checks and security best practices
- **NGINX Compatible**: Ready for deployment behind NGINX reverse proxy
- **Comprehensive Testing**: Unit and integration tests with 80%+ coverage

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ELEVENLABS_WEBHOOK_SECRET` | Yes | - | HMAC secret from ElevenLabs webhook configuration |
| `ELEVENLABS_WEBHOOK_HOST` | No | `0.0.0.0` | Host to bind to |
| `ELEVENLABS_WEBHOOK_PORT` | No | `3004` | Port to listen on |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT` | No | `text` | Log format (`text` or `json`) |
| `AUDIO_STORAGE_PATH` | No | - | Path for audio file storage |
| `TRANSCRIPT_STORAGE_PATH` | No | - | Path for transcript storage |
| `ENABLE_AUDIO_STORAGE` | No | `false` | Enable audio file storage |
| `ENABLE_TRANSCRIPT_STORAGE` | No | `true` | Enable transcript storage |

### Example Configuration

```bash
cp .env.example .env
# Edit .env with your configuration
```

## API Endpoints

### Health Check

```
GET /health
```

Returns service health status. Used by Docker and NGINX for monitoring.

**Response:**
```json
{
  "status": "healthy",
  "service": "elevenlabs-webhook"
}
```

### Webhook Endpoint

```
POST /webhook
```

Receives ElevenLabs post-call webhooks.

**Headers:**
- `elevenlabs-signature`: HMAC signature in format `t=timestamp,v0=hash`
- `content-type`: `application/json`

**Response:**
```json
{
  "status": "received"
}
```

**Error Responses:**
- `400 Bad Request`: Invalid JSON, expired timestamp, or unknown webhook type
- `401 Unauthorized`: Invalid or missing HMAC signature
- `500 Internal Server Error`: Processing failure

## HMAC Authentication

The service validates webhook signatures following the ElevenLabs specification:

1. **Header Format**: `elevenlabs-signature: t=timestamp,v0=hash`
2. **Hash Computation**: `sha256(timestamp.request_body)` with your webhook secret
3. **Timestamp Tolerance**: 30 minutes (1800 seconds)

### Getting Your Webhook Secret

1. Go to your ElevenLabs dashboard
2. Navigate to your agent's configuration
3. Enable post-call webhooks
4. Copy the webhook secret

## Running Locally

### Prerequisites

- Python 3.11+
- pip

### Installation

```bash
cd Servers/ElevenLabsWebhook
pip install -r requirements.txt
```

### Start Server

```bash
export ELEVENLABS_WEBHOOK_SECRET=your-secret-here
python -m src.main
```

The server will start on `http://0.0.0.0:3004` by default.

## Docker Deployment

### Build

```bash
docker build -t elevenlabs-webhook .
```

### Run

```bash
docker run -d \
  --name elevenlabs-webhook \
  -p 3004:3004 \
  -e ELEVENLABS_WEBHOOK_SECRET=your-secret-here \
  elevenlabs-webhook
```

### Health Check

```bash
curl http://localhost:3004/health
```

## Testing

### Run Unit Tests

```bash
pytest tests/unit/ -v
```

### Run Integration Tests

```bash
pytest tests/integration/ -v
```

### Run All Tests with Coverage

```bash
pytest tests/ -v --cov=src --cov-report=html
```

### Test Utility

Use the test utility to simulate webhook calls:

```bash
# Test health endpoint
python examples/test_webhook.py --health

# Test invalid signature rejection
python examples/test_webhook.py --invalid

# Send test transcription payload
python examples/test_webhook.py examples/test_payload_transcription.json your-secret

# Send test audio payload
python examples/test_webhook.py examples/test_payload_audio.json your-secret

# Custom endpoint
python examples/test_webhook.py payload.json secret http://your-server:3004/webhook
```

## Integration with Existing Infrastructure

### Docker Compose

The service is configured in the main `docker-compose.yml`:

```yaml
elevenlabs-webhook:
  build: ./Servers/ElevenLabsWebhook
  container_name: elevenlabs-webhook
  restart: unless-stopped
  env_file:
    - .env
  networks:
    - mcp-internal
  # ... see docker-compose.yml for full configuration
```

### NGINX Configuration

The service is accessible via NGINX at `/elevenlabs/webhook`:

- IP whitelisting for ElevenLabs static IPs
- No bearer token authentication (HMAC authentication handled by service)
- Large payload support (100MB max)
- Extended timeouts for audio webhooks

See `nginx/conf.d/mcp-proxy.conf` for full configuration.

## Security

### Authentication

1. **HMAC Signature Validation**: All requests must include a valid `elevenlabs-signature` header
2. **Timestamp Validation**: Requests older than 30 minutes are rejected
3. **IP Whitelisting**: NGINX restricts access to ElevenLabs static IPs

### ElevenLabs Static IPs

The following IPs are whitelisted in NGINX:

| Region | IPs |
|--------|-----|
| US Default | 34.67.146.145, 34.59.11.47 |
| EU | 35.204.38.71, 34.147.113.54 |
| Asia | 35.185.187.110, 35.247.157.189 |
| EU Residency | 34.77.234.246, 34.140.184.144 |
| India Residency | 34.93.26.174, 34.93.252.69 |

### Container Security

- Non-root user (`elevenlabsuser`, UID 1001)
- Read-only root filesystem
- No new privileges
- Resource limits (512M memory, 1.0 CPU)
- tmpfs for `/tmp` and `/app/logs`

## Architecture

```
ElevenLabsWebhook/
├── src/
│   ├── main.py                    # Application entry point
│   ├── auth/
│   │   └── hmac_validator.py      # HMAC signature validation
│   ├── handlers/
│   │   ├── transcription_handler.py
│   │   ├── audio_handler.py
│   │   └── call_failure_handler.py
│   ├── models/
│   │   └── webhook_models.py      # Data models
│   └── utils/
│       ├── logger.py              # Logging configuration
│       └── storage.py             # File storage utilities
├── tests/
│   ├── unit/                      # Unit tests
│   └── integration/               # Integration tests
├── examples/
│   ├── test_webhook.py            # Test utility
│   └── test_payload_*.json        # Example payloads
├── Dockerfile
├── requirements.txt
├── README.md
└── .env.example
```

## Troubleshooting

### Server won't start

- Verify `ELEVENLABS_WEBHOOK_SECRET` is set
- Check port 3004 is not in use
- Review logs for error messages

### HMAC validation failures

- Verify webhook secret matches ElevenLabs configuration
- Check server clock is synchronized (NTP)
- Ensure request is not being modified by proxy

### Webhook not receiving events

- Verify NGINX is routing correctly
- Check IP whitelisting includes all ElevenLabs IPs
- Confirm webhook URL in ElevenLabs dashboard

### Large audio files failing

- Check `client_max_body_size` in NGINX (should be 100M)
- Verify proxy timeouts are sufficient
- Check available disk space for storage

## Development

### Code Style

```bash
black src/
flake8 src/
mypy src/
```

### Adding New Webhook Types

1. Create new handler in `src/handlers/`
2. Add model in `src/models/webhook_models.py`
3. Register handler in `src/main.py`
4. Add unit tests
5. Update documentation

## License

See main repository LICENSE file.

## Support

For issues specific to this service, please open an issue in the main repository.


