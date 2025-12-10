# Voice Clone Pre-Call Service - API Documentation

## Overview

The Voice Clone Pre-Call Service provides webhook endpoints for integrating 3CX PBX with ElevenLabs Voice Agent API for dynamic voice cloning.

**Base URL**: `https://matrosmcp.duckdns.org/voiceclone`

---

## Endpoints

### Health Check

Check service health and connectivity to dependencies.

**Endpoint**: `GET /health`

**Authentication**: None

**Response**: `200 OK`

```json
{
  "status": "ok",
  "database": "ok",
  "redis": "ok",
  "elevenlabs": "ok",
  "timestamp": "2025-12-10T12:00:00.000000Z"
}
```

**Status Values**:
- `ok`: Service is fully operational
- `degraded`: Some non-critical components are down
- `error`: Critical components are down

---

### 3CX Incoming Call Webhook

Receives incoming call notifications from 3CX PBX and initiates async voice cloning workflow.

**Endpoint**: `POST /webhook/3cx`

**Authentication**: HMAC signature validation via `X-Signature` header

**Request Headers**:
```
Content-Type: application/json
X-Signature: t=<timestamp>,v0=<hash>
```

**Request Body**:
```json
{
  "event_type": "IncomingCall",
  "call_id": "abc123-def456-ghi789",
  "caller_id": "+31612345678",
  "called_number": "+31201234567",
  "timestamp": "2025-12-10T12:00:00Z",
  "direction": "In",
  "duration": null,
  "recording_url": null
}
```

**Response**: `200 OK`

```json
{
  "status": "success",
  "call_id": "greeting_call_123",
  "cloned_voice_id": "pending",
  "3cx_call_id": "abc123-def456-ghi789",
  "message": "Greeting call initiated successfully"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid payload or expired signature
- `401 Unauthorized`: Invalid signature
- `500 Internal Server Error`: Processing failure

**Event Types**:
- `IncomingCall`: New incoming call (triggers voice cloning workflow)
- `CallStateChanged`: Call state change notification (logged only)
- `CallEnded`: Call completion notification (logged only)

---

### POST-Call Webhook

Receives post-call events from ElevenLabs with call transcripts and metadata.

**Endpoint**: `POST /webhook/postcall`

**Authentication**: HMAC signature validation via `elevenlabs-signature` header

**Request Headers**:
```
Content-Type: application/json
elevenlabs-signature: t=<timestamp>,v0=<hash>
```

**Request Body**:
```json
{
  "call_id": "elevenlabs_call_123",
  "agent_id": "agent_abc",
  "transcript": "Agent: Hello, how can I help you?\nUser: I need help with my account.",
  "duration_seconds": 185,
  "status": "completed",
  "custom_variables": {
    "caller_id": "+31612345678",
    "threecx_call_id": "abc123-def456-ghi789",
    "cloned_voice_id": "voice_789xyz"
  },
  "timestamp": "2025-12-10T12:03:05Z"
}
```

**Response**: `200 OK`

```json
{
  "status": "success",
  "message": "POST-call event processed successfully",
  "call_id": "elevenlabs_call_123"
}
```

**Call Status Values**:
- `completed`: Call completed successfully
- `failed`: Call failed
- `missed`: Call was not answered

---

## Async Greeting Workflow

The service implements an innovative async greeting pattern to eliminate perceived wait time:

### Workflow Steps

1. **Immediate Greeting** (< 100ms)
   - Service receives 3CX incoming call webhook
   - Immediately triggers ElevenLabs call with prerecorded greeting
   - Returns success response to 3CX

2. **Background Processing** (5-30 seconds)
   - Voice cloning runs asynchronously while greeting plays
   - Retrieves caller's voice sample from storage
   - Creates instant voice clone via ElevenLabs API
   - Caches clone for future use

3. **Automatic Transition** (seamless)
   - When clone is ready, service automatically initiates Voice Agent call
   - Call transfers from greeting to cloned voice
   - User experiences zero perceived wait time

### Configuration

```env
GREETING_VOICE_ID=default_greeting_voice
GREETING_MESSAGE="Hello thanks for calling. Please hold..."
GREETING_MUSIC_ENABLED=true
GREETING_MUSIC_URL=https://your-domain.com/hold-music.mp3
CLONE_MAX_WAIT_SECONDS=35
AUTO_TRANSITION_ENABLED=true
```

---

## HMAC Signature Validation

Both webhook endpoints use HMAC-SHA256 signature validation for security.

### Header Format

```
X-Signature: t=1733832000,v0=abc123def456...
```

### Validation Process

1. Extract timestamp `t` and hash `v0` from header
2. Construct payload: `{timestamp}.{request_body}`
3. Compute HMAC-SHA256: `HMAC(secret, payload)`
4. Compare computed hash with received hash (constant-time comparison)
5. Verify timestamp is within tolerance (default: 30 minutes)

### Example (Python)

```python
import hmac
import time
from hashlib import sha256

def validate_signature(signature_header, body, secret):
    parts = signature_header.split(",")
    timestamp = parts[0].split("=")[1]
    received_hash = parts[1]
    
    payload = f"{timestamp}.{body.decode()}"
    expected_hash = "v0=" + hmac.new(
        secret.encode(),
        payload.encode(),
        sha256
    ).hexdigest()
    
    return hmac.compare_digest(received_hash, expected_hash)
```

---

## Rate Limiting

Rate limiting is handled by NGINX reverse proxy:

- **General API**: 20 requests/second burst
- **Webhook endpoints**: No rate limit (handled by HMAC validation)

---

## Error Handling

All endpoints return consistent error responses:

```json
{
  "detail": "Error message here"
}
```

**HTTP Status Codes**:
- `200`: Success
- `400`: Bad Request (invalid payload, expired signature)
- `401`: Unauthorized (invalid signature)
- `404`: Not Found (endpoint doesn't exist)
- `500`: Internal Server Error (processing failure)

---

## Monitoring

### Health Check Monitoring

Monitor the `/health` endpoint for service health:

```bash
curl https://matrosmcp.duckdns.org/voiceclone/health
```

**Recommended Monitoring**:
- Check every 30 seconds
- Alert if `status` is not `ok` for > 2 minutes
- Alert if any dependency status is `error`

### Metrics

The service logs the following metrics:

- Voice clone creation time (ms)
- Cache hit/miss rates
- Call duration and status
- API response times
- Error rates

Access logs at: `/var/log/mcp-services/voiceclone.log`

---

## Testing

### Manual Testing

Use the provided test script:

```bash
cd Servers/VoiceClone_PreCall_Service
python examples/test_webhook.py
```

### Sample Payloads

Sample webhook payloads are available in:
```
examples/sample_payloads/3cx_incoming_call.json
examples/sample_payloads/elevenlabs_postcall.json
```

### cURL Examples

**Health Check**:
```bash
curl https://matrosmcp.duckdns.org/voiceclone/health
```

**3CX Webhook** (with HMAC):
```bash
curl -X POST https://matrosmcp.duckdns.org/voiceclone/webhook/3cx \
  -H "Content-Type: application/json" \
  -H "X-Signature: t=1733832000,v0=abc123..." \
  -d @examples/sample_payloads/3cx_incoming_call.json
```

---

## Support

For issues, questions, or contributions, please refer to the main repository README.
