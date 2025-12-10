# API Documentation

## ElevenLabs Pre-Call Webhook Service API

Base URL: `http://localhost:3005` (development) or `https://your-domain.com/elevenlabs/precall` (production)

---

## Endpoints

### Health Check

Check if the service is running and healthy.

**Request:**
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "elevenlabs-precall-webhook"
}
```

**Status Codes:**
- `200 OK`: Service is healthy

---

### Pre-Call Webhook

Process pre-call webhook from ElevenLabs with voice cloning.

**Request:**
```http
POST /webhook
```

**Headers:**
- `elevenlabs-signature` (required): HMAC signature in format `t=timestamp,v0=hash`
- `Content-Type`: `application/json` or `multipart/form-data`

#### JSON Format

**Request Body:**
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

#### Multipart Format

**Request:**
```http
POST /webhook
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="metadata"
Content-Type: application/json

{
  "type": "pre_call",
  "conversation_id": "conv_abc123xyz",
  "agent_id": "agent_def456uvw",
  "caller_metadata": {
    "name": "Ivan",
    "date_of_birth": "11.12.2007"
  }
}
------WebKitFormBoundary
Content-Disposition: form-data; name="voice_sample"; filename="voice.mp3"
Content-Type: audio/mpeg

[binary audio data]
------WebKitFormBoundary--
```

**Success Response (200 OK):**
```json
{
  "status": "success",
  "conversation_id": "conv_abc123xyz",
  "voice_id": "voice_cloned_xyz123",
  "voice_name": "Ivan_Clone_20251210_123456_xyz",
  "agent_updated": true,
  "caller_info": {
    "Name": "Ivan",
    "DateOfBirth": "11.12.2007"
  },
  "processing_time_ms": 2450
}
```

**Error Responses:**

**400 Bad Request** - Invalid payload:
```json
{
  "status": "error",
  "error_code": "VALIDATION_ERROR",
  "error_message": "Missing required field: agent_id",
  "conversation_id": "conv_abc123xyz"
}
```

**401 Unauthorized** - Invalid signature:
```json
{
  "detail": "Invalid signature"
}
```

**422 Unprocessable Entity** - Voice cloning failed:
```json
{
  "status": "error",
  "error_code": "VOICE_CLONING_FAILED",
  "error_message": "Voice sample too short (min 3 seconds required)",
  "conversation_id": "conv_abc123xyz"
}
```

**500 Internal Server Error** - Service error:
```json
{
  "detail": "Internal server error"
}
```

---

## Request Fields

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Must be `"pre_call"` |
| `conversation_id` | string | Unique conversation identifier |
| `agent_id` | string | ElevenLabs agent ID to update |
| `voice_sample` | object | Voice sample data (see below) |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `event_timestamp` | integer | Unix timestamp of event |
| `caller_metadata` | object | Caller information |
| `caller_metadata.name` | string | Caller name |
| `caller_metadata.date_of_birth` | string | Date of birth |
| `caller_metadata.phone_number` | string | Phone number |

### Voice Sample Fields

| Field | Type | Description |
|-------|------|-------------|
| `format` | string | Format type (e.g., "base64") |
| `data` | string | Base64-encoded audio data |
| `duration_seconds` | float | Audio duration (optional) |
| `sample_rate` | integer | Sample rate in Hz (optional) |

---

## Response Fields

### Success Response

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Always `"success"` |
| `conversation_id` | string | Conversation identifier |
| `voice_id` | string | Created voice ID from ElevenLabs |
| `voice_name` | string | Generated voice name |
| `agent_updated` | boolean | Whether agent was successfully updated |
| `caller_info` | object | Formatted caller information |
| `processing_time_ms` | integer | Processing time in milliseconds |

### Error Response

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Always `"error"` |
| `error_code` | string | Error code (e.g., "VALIDATION_ERROR") |
| `error_message` | string | Human-readable error message |
| `conversation_id` | string | Conversation identifier (if available) |

---

## Error Codes

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Invalid request payload or missing required fields |
| `VOICE_CLONING_FAILED` | ElevenLabs voice cloning API error |
| `AGENT_UPDATE_FAILED` | Failed to update agent configuration |

---

## HMAC Signature Validation

All webhook requests must include a valid HMAC signature in the `elevenlabs-signature` header.

**Header Format:**
```
elevenlabs-signature: t=1702425485,v0=a1b2c3d4e5f6...
```

**Signature Generation:**
1. Extract timestamp: `t=<unix_timestamp>`
2. Concatenate: `<timestamp>.<request_body>`
3. HMAC-SHA256 with webhook secret
4. Format: `t=<timestamp>,v0=<hex_digest>`

**Validation Rules:**
- Timestamp must be within 30 minutes (1800 seconds)
- HMAC hash must match expected value
- Constant-time comparison to prevent timing attacks

---

## Audio Requirements

### Supported Formats
- WAV (RIFF header)
- MP3 (ID3 or MPEG sync)
- OGG (OggS header)

### Constraints
- **Minimum Duration**: 3 seconds
- **Maximum File Size**: 10 MB
- **Recommended Sample Rate**: 44.1 kHz or higher
- **Quality**: Clear voice sample without background noise

---

## Rate Limits

Voice cloning typically takes 2-5 seconds. Recommended limits:
- Maximum 10 concurrent requests
- Maximum 100 requests per minute per agent
- Request timeout: 60 seconds

---

## Examples

See `examples/` directory for:
- `precall_payload.json` - Sample JSON payload
- `test_precall_webhook.py` - Python test script

**Test with curl:**
```bash
# Generate signature (use actual webhook secret)
TIMESTAMP=$(date +%s)
PAYLOAD='{"type":"pre_call","conversation_id":"test_123","agent_id":"agent_456"}'
SIGNATURE=$(echo -n "${TIMESTAMP}.${PAYLOAD}" | openssl dgst -sha256 -hmac "your-secret" | sed 's/^.* //')

# Send request
curl -X POST http://localhost:3005/webhook \
  -H "elevenlabs-signature: t=${TIMESTAMP},v0=${SIGNATURE}" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}"
```
