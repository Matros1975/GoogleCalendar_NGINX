# Voice Clone Pre-Call Service

A microservice that integrates 3CX PBX with ElevenLabs Voice Agent API to dynamically clone voices before initiating calls.

## Overview

This service receives incoming call notifications from 3CX, retrieves caller-specific voice samples, creates instant voice clones via ElevenLabs API, and triggers voice agent calls with the cloned voice.

### Key Innovation: Async Greeting Workflow

To eliminate awkward silence during voice cloning (5-30 seconds), this service implements an asynchronous greeting pattern:

- **Immediate Response**: Triggers prerecorded greeting + music within 100ms
- **Background Processing**: Clones voice asynchronously while message/music plays
- **Automatic Transition**: Voice Agent takes over when clone is ready (no user action required)
- **Zero Perceived Wait**: Callers experience professional, uninterrupted conversation with pleasant background music

## Features

- **3CX Integration**: Receives incoming call webhooks from 3CX PBX
- **Voice Cloning**: Creates instant voice clones via ElevenLabs API
- **Voice Agent**: Triggers ElevenLabs Voice Agent calls with cloned voices
- **Caching**: Redis-based voice clone caching for performance optimization
- **Database**: PostgreSQL for persistent storage of caller mappings and call logs
- **Async Processing**: Asynchronous greeting workflow for seamless user experience
- **Analytics**: Comprehensive logging and tracking of clone creation and call events

## Architecture

### Technology Stack

- **Framework**: FastAPI (async-first)
- **Server**: Uvicorn
- **Database**: PostgreSQL 15+ with asyncpg
- **Cache**: Redis 7+
- **API Client**: httpx (async HTTP)
- **Deployment**: Docker + Docker Compose
- **Python Version**: 3.11

### Integration Points

1. **3CX PBX**: Sends webhooks for incoming calls
2. **ElevenLabs API**: Voice cloning + Voice Agent triggering
3. **PostgreSQL**: Persistent storage (caller mappings, call logs)
4. **Redis**: Voice clone caching
5. **NGINX**: Reverse proxy

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker and Docker Compose (for containerized deployment)

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Servers/VoiceClone_PreCall_Service
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run database migrations**:
   ```bash
   alembic upgrade head
   ```

6. **Start the service**:
   ```bash
   python -m src.main
   ```

### Docker Deployment

1. **Build the image**:
   ```bash
   docker build -t voiceclone-precall:latest .
   ```

2. **Run with Docker Compose** (from repository root):
   ```bash
   docker-compose up -d voiceclone-precall
   ```

## Configuration

### Environment Variables

See `.env.example` for all available configuration options. Key variables:

- `ELEVENLABS_API_KEY`: Your ElevenLabs API key
- `ELEVENLABS_AGENT_ID`: Voice Agent ID
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `VOICE_SAMPLE_STORAGE`: Storage type (`s3` or `local`)
- `WEBHOOK_SECRET`: Secret for webhook signature validation

### Greeting Configuration

Configure the async greeting workflow:

- `GREETING_VOICE_ID`: ElevenLabs voice ID for prerecorded greeting
- `GREETING_MESSAGE`: Greeting message text
- `GREETING_MUSIC_ENABLED`: Enable background music during wait
- `GREETING_MUSIC_URL`: URL to hold music file
- `CLONE_MAX_WAIT_SECONDS`: Max wait time before timeout
- `AUTO_TRANSITION_ENABLED`: Auto-switch to cloned voice when ready

## API Endpoints

### Health Check

```
GET /health
```

Returns service health status.

### 3CX Webhook

```
POST /webhook/3cx
```

Receives incoming call notifications from 3CX PBX.

### POST-Call Webhook

```
POST /webhook/postcall
```

Receives post-call events from ElevenLabs.

## Database Schema

The service uses 7 database tables:

1. **caller_voice_mapping**: Maps caller IDs to voice samples
2. **voice_clone_cache**: Caches created voice clones
3. **call_log**: Logs all call events
4. **voice_clone_log**: Logs voice clone creation events
5. **clone_ready_events**: Tracks when clones are ready
6. **clone_failed_events**: Tracks failed clone attempts
7. **clone_transfer_events**: Tracks automatic call transfers

See `docs/DATABASE.md` for detailed schema documentation.

## Testing

### Run Unit Tests

```bash
pytest tests/unit -v
```

### Run Integration Tests

```bash
pytest tests/integration -v
```

### Run All Tests with Coverage

```bash
pytest --cov=src --cov-report=term-missing --cov-report=html
```

## Development

### Code Quality

- **Formatter**: Black
- **Linter**: Flake8
- **Type Checker**: MyPy

```bash
# Format code
black src tests

# Lint code
flake8 src tests

# Type check
mypy src
```

### Project Structure

```
VoiceClone_PreCall_Service/
├── src/
│   ├── auth/                  # Authentication (HMAC validation)
│   ├── handlers/              # Webhook handlers
│   ├── services/              # Business logic services
│   ├── models/                # Data models (Pydantic & SQLAlchemy)
│   ├── utils/                 # Utilities (logging, exceptions)
│   └── main.py                # FastAPI application
├── tests/
│   ├── unit/                  # Unit tests
│   └── integration/           # Integration tests
├── migrations/                # Alembic database migrations
├── docs/                      # Documentation
└── examples/                  # Example scripts and payloads
```

## Documentation

- [API Documentation](docs/API.md)
- [Database Schema](docs/DATABASE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Architecture Overview](docs/ARCHITECTURE.md)

## License

See repository LICENSE file.

## Support

For issues, questions, or contributions, please refer to the main repository.
