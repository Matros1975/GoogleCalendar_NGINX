# VoiceClone Pre-Call Service - API Documentation

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://matrosmcp.duckdns.org/voiceclone`

## Endpoints

### Health Check

**GET** `/health`

Check service health status.

**Response**:
```json
{
  "status": "ok",
  "database": "ok",
  "elevenlabs": "ok",
  "timestamp": "2025-12-10T12:00:00.000Z"
}
```

---

### 3CX Incoming Call Webhook

**POST** `/webhook/3cx`

Receives incoming call notifications from 3CX PBX.

**Headers**:
- `X-3CX-Signature`: HMAC signature (optional)
- `Content-Type`: application/json

**Request Body**:
```json
{
  "event_type": "IncomingCall",
  "call_id": "3cx-call-12345",
  "caller_id": "+31612345678",
  "called_number": "+31201234567",
  "timestamp": "2025-12-10T12:00:00Z",
  "direction": "In",
  "duration": null,
  "recording_url": null
}
```

**Response**:
```json
{
  "status": "success",
  "call_id": "elevenlabs-call-67890",
  "cloned_voice_id": "pending",
  "threecx_call_id": "3cx-call-12345",
  "message": "Greeting initiated, voice cloning in progress"
}
```

---

### ElevenLabs POST-Call Webhook

**POST** `/webhook/elevenlabs/postcall`

Receives post-call events from ElevenLabs Voice Agent.

**Headers**:
- `elevenlabs-signature`: HMAC signature (required)
- `Content-Type`: application/json

**Request Body**:
```json
{
  "call_id": "elevenlabs-call-67890",
  "agent_id": "agent-abc123",
  "transcript": "Hello, how can I help you today?",
  "duration_seconds": 120,
  "status": "completed",
  "custom_variables": {
    "threecx_call_id": "3cx-call-12345"
  },
  "timestamp": "2025-12-10T12:02:00Z"
}
```

**Response**:
```json
{
  "status": "processed",
  "call_id": "elevenlabs-call-67890"
}
```

---

### Invalidate Voice Clone Cache

**DELETE** `/api/v1/cache/{caller_id}`

Manually invalidate cached voice clone for a caller.

**Headers**:
- `Authorization`: Bearer {token}

**Response**:
```json
{
  "success": true,
  "message": "Cache invalidated for caller +31612345678"
}
```

---

### Get Statistics

**GET** `/api/v1/statistics`

Get voice clone statistics and metrics.

**Headers**:
- `Authorization`: Bearer {token}

**Response**:
```json
{
  "total_clones": 100,
  "cache_hits": 850,
  "cache_misses": 150,
  "hit_rate": 0.85,
  "avg_creation_time_ms": 12500.0,
  "total_calls": 950
}
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid JSON payload"
}
```

### 401 Unauthorized
```json
{
  "detail": "Invalid signature"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## Webhook Configuration

### 3CX Setup

1. Configure webhook in 3CX settings
2. Set URL: `https://matrosmcp.duckdns.org/voiceclone/webhook/3cx`
3. Add webhook secret to `.env`: `THREECX_WEBHOOK_SECRET=your-secret`

### ElevenLabs Setup

1. Configure POST-call webhook in ElevenLabs agent settings
2. Set URL: `https://matrosmcp.duckdns.org/voiceclone/webhook/elevenlabs/postcall`
3. Use same secret as `WEBHOOK_SECRET` in `.env`
