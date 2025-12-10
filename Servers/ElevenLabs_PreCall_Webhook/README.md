# ElevenLabs Pre-Call Webhook Service

A Python-based microservice to handle ElevenLabs pre-call webhooks with instant voice cloning capabilities. This service receives pre-call webhook events, processes voice samples, creates custom voices via ElevenLabs API, and activates them to calling agents in real-time.

## Overview

This service receives and processes pre-call webhook events from ElevenLabs voice agents, performing:

- **Pre-Call Voice Cloning**: Instant voice cloning from uploaded voice samples
- **Agent Customization**: Real-time agent voice and greeting configuration
- **Caller Metadata Processing**: Format and return caller information to voice agents
- **HMAC Authentication**: Secure signature validation following ElevenLabs specification
- **Multipart Support**: Handles both JSON and multipart/form-data payloads

## Features

- **Instant Voice Cloning**: Creates custom voices from 3-10 second audio samples
- **Real-time Agent Updates**: Activates cloned voices to agents before calls start
- **Dual Payload Support**: Accepts JSON with base64 audio or multipart file uploads
- **HMAC Authentication**: Secure signature validation with timestamp checking
- **Structured Logging**: JSON or text format logging with conversation tracking
- **Docker Integration**: Containerized with health checks and security best practices
- **Audio Processing**: Supports WAV, MP3, and OGG formats with validation
- **Comprehensive Testing**: Unit and integration tests with 85%+ coverage target

## Architecture

```
ElevenLabs_PreCall_Webhook/
├── src/
│   ├── main.py                    # FastAPI application entry point
│   ├── auth/
│   │   └── hmac_validator.py      # HMAC signature validation
│   ├── handlers/
│   │   └── precall_handler.py     # Pre-call webhook handler
│   ├── services/
│   │   ├── elevenlabs_client.py   # ElevenLabs API client
│   │   └── voice_cloning_service.py # Voice cloning orchestration
│   ├── models/
│   │   ├── webhook_models.py      # Pydantic models for webhooks
│   │   └── elevenlabs_models.py   # ElevenLabs API response models
│   └── utils/
│       ├── logger.py               # Logging configuration
│       └── file_handler.py         # Voice sample file processing
├── tests/
│   ├── unit/                       # Unit tests
│   └── integration/                # Integration tests
├── docs/                           # Documentation
├── examples/                       # Example payloads and scripts
├── Dockerfile
├── requirements.txt
└── README.md
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ELEVENLABS_API_KEY` | Yes | - | ElevenLabs API key for voice operations |
| `ELEVENLABS_WEBHOOK_SECRET` | Yes | - | HMAC secret from ElevenLabs webhook configuration |
| `PRECALL_WEBHOOK_HOST` | No | `0.0.0.0` | Host to bind to |
| `PRECALL_WEBHOOK_PORT` | No | `3005` | Port to listen on |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT` | No | `text` | Log format (`text` or `json`) |
| `LOG_DIR` | No | `/var/log/elevenlabs-precall-webhook` | Directory for log files |
| `VOICE_CLONE_MIN_DURATION` | No | `3.0` | Minimum audio duration in seconds |
| `VOICE_CLONE_MAX_SIZE_MB` | No | `10.0` | Maximum file size in MB |
| `DEFAULT_FIRST_MESSAGE` | No | `Hallo {name}, fijn dat je belt!` | Template for agent greeting |
| `VOICE_SAMPLE_STORAGE_PATH` | No | `/app/storage/voice_samples` | Path for optional sample storage |
| `ENABLE_VOICE_SAMPLE_STORAGE` | No | `false` | Enable voice sample persistence |

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
  "service": "elevenlabs-precall-webhook"
}
```

### Webhook Endpoint

```
POST /webhook
```

Receives ElevenLabs pre-call webhooks.

**Headers:**
- `elevenlabs-signature`: HMAC signature in format `t=timestamp,v0=hash`
- `content-type`: `application/json` or `multipart/form-data`

**JSON Payload Format:**
```json
{
  "type": "pre_call",
  "event_timestamp": 1702425485,
  "conversation_id": "conv_abc123xyz",
  "agent_id": "agent_def456uvw",
  "caller_metadata": {
    "name": "Ivan",
    "date_of_birth": "11.12.2007",
    "phone_number": "+31612345678"
  },
  "voice_sample": {
    "format": "base64",
    "data": "UklGRiQAAABXQVZFZm10...",
    "duration_seconds": 5.2,
    "sample_rate": 44100
  }
}
```

**Multipart Form Data Format:**
```
POST /webhook
Content-Type: multipart/form-data

Fields:
- metadata: {"type": "pre_call", "conversation_id": "...", "agent_id": "...", "caller_metadata": {...}}
- voice_sample: [audio file]
```

**Success Response (200 OK):**
```json
{
  "status": "success",
  "conversation_id": "conv_abc123xyz",
  "voice_id": "voice_new_cloned_xyz",
  "voice_name": "Ivan_Clone_20251210_123456",
  "agent_updated": true,
  "caller_info": {
    "Name": "Ivan",
    "DateOfBirth": "11.12.2007"
  },
  "processing_time_ms": 2450
}
```

**Error Response:**
```json
{
  "status": "error",
  "error_code": "VOICE_CLONING_FAILED",
  "error_message": "Voice sample too short (min 3 seconds required)",
  "conversation_id": "conv_abc123xyz"
}
```

**Status Codes:**
- `200 OK`: Successfully processed pre-call webhook
- `400 Bad Request`: Invalid payload or voice sample
- `401 Unauthorized`: Invalid HMAC signature
- `422 Unprocessable Entity`: Voice cloning failed
- `500 Internal Server Error`: Service error

## Voice Cloning Workflow

1. **Receive and Validate**: HMAC signature and voice sample validation
2. **Create Voice Clone**: Instant voice cloning via ElevenLabs API (2-5 seconds)
3. **Update Agent**: Configure agent with new voice and personalized greeting
4. **Return Metadata**: Send caller information back to agent for context

## Running Locally

### Prerequisites

- Python 3.11+
- pip
- ffmpeg (for audio processing)

### Installation

```bash
cd Servers/ElevenLabs_PreCall_Webhook
pip install -r requirements.txt
```

### Start Server

```bash
export ELEVENLABS_API_KEY=your-api-key-here
export ELEVENLABS_WEBHOOK_SECRET=your-secret-here
python -m src.main
```

The server will start on `http://0.0.0.0:3005` by default.

## Docker Deployment

### Build

```bash
docker build -t elevenlabs-precall-webhook .
```

### Run

```bash
docker run -d \
  --name elevenlabs-precall-webhook \
  -p 3005:3005 \
  -e ELEVENLABS_API_KEY=your-api-key-here \
  -e ELEVENLABS_WEBHOOK_SECRET=your-secret-here \
  elevenlabs-precall-webhook
```

### Health Check

```bash
curl http://localhost:3005/health
```

## Testing

### Run Unit Tests

```bash
pytest tests/unit/ -v
```

### Run Integration Tests

```bash
# Requires valid API credentials
export ELEVENLABS_API_KEY=your-api-key-here
pytest tests/integration/ -v
```

### Run All Tests with Coverage

```bash
pytest tests/ -v --cov=src --cov-report=html
```

## Security

### Authentication

1. **HMAC Signature Validation**: All requests must include a valid `elevenlabs-signature` header
2. **Timestamp Validation**: Requests older than 30 minutes are rejected
3. **IP Whitelisting**: NGINX restricts access to ElevenLabs static IPs (recommended)

### Container Security

- Non-root user (`precalluser`, UID 1001)
- Audio processing libraries (ffmpeg, libsndfile1)
- Health check endpoint
- Minimal image size

## Integration with Infrastructure

### NGINX Configuration

Add to your NGINX configuration:

```nginx
upstream elevenlabs_precall_webhook {
    server localhost:3005;
}

location /elevenlabs/precall/webhook {
    proxy_pass http://elevenlabs_precall_webhook/webhook;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    
    # Increase timeouts for voice processing
    proxy_connect_timeout 60s;
    proxy_read_timeout 60s;
    
    # Increase body size for voice samples
    client_max_body_size 15M;
}
```

### Docker Compose

```yaml
elevenlabs-precall-webhook:
  build: ./Servers/ElevenLabs_PreCall_Webhook
  container_name: elevenlabs-precall-webhook
  restart: unless-stopped
  ports:
    - "3005:3005"
  env_file:
    - ./Servers/ElevenLabs_PreCall_Webhook/.env
  volumes:
    - ./Servers/ElevenLabs_PreCall_Webhook/logs:/app/logs
  networks:
    - mcp-network
```

## Troubleshooting

### Server won't start
- Verify `ELEVENLABS_API_KEY` and `ELEVENLABS_WEBHOOK_SECRET` are set
- Check port 3005 is not in use
- Review logs for error messages

### HMAC validation failures
- Verify webhook secret matches ElevenLabs configuration
- Check server clock is synchronized (NTP)
- Ensure request is not being modified by proxy

### Voice cloning failures
- Ensure voice sample is 3-10 seconds minimum
- Check audio format (WAV, MP3, or OGG required)
- Verify API key has voice cloning permissions
- Review ElevenLabs API quota and limits

### Large audio files failing
- Check `client_max_body_size` in NGINX (should be 15M)
- Verify file size is under 10MB limit
- Ensure audio quality is not excessive

## Development

### Code Style

Follow existing patterns from `Servers/ElevenLabsWebhook/`:
- Python 3.11+
- Type hints for all functions
- PEP 8 compliant
- Docstrings (Google style)
- 4-space indentation

### Testing

- Unit tests for all core functionality
- Integration tests with real ElevenLabs API
- Mock external API calls in unit tests
- Use pytest fixtures for test data

## License

See main repository LICENSE file.

## Support

For issues specific to this service, please open an issue in the main repository.

## Related Services

- **ElevenLabsWebhook**: Post-call webhook handler (transcription, audio, failures)
- **GoogleCalendarMCP**: Google Calendar integration
- **TopDeskMCP**: TOPdesk ticket management
