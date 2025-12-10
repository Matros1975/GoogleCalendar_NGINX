# Voice Cloning Workflow

## Overview

The ElevenLabs Pre-Call Webhook Service performs real-time voice cloning before a call begins. This document explains the complete workflow from webhook receipt to agent activation.

---

## Workflow Diagram

```
┌─────────────────┐
│  ElevenLabs     │
│  Voice Agent    │
└────────┬────────┘
         │ 1. Pre-call webhook
         │ (voice sample + caller info)
         ▼
┌─────────────────────────────────────────┐
│  Pre-Call Webhook Service               │
│                                         │
│  ┌────────────────────────────────┐    │
│  │  1. HMAC Validation            │    │
│  │     - Verify signature         │    │
│  │     - Check timestamp          │    │
│  └─────────────┬──────────────────┘    │
│                ▼                        │
│  ┌────────────────────────────────┐    │
│  │  2. Voice Sample Validation    │    │
│  │     - Check format (WAV/MP3)   │    │
│  │     - Validate size (<10MB)    │    │
│  │     - Verify duration (≥3s)    │    │
│  └─────────────┬──────────────────┘    │
│                ▼                        │
│  ┌────────────────────────────────┐    │
│  │  3. Create Voice Clone         │────┼──► ElevenLabs API
│  │     - Generate unique name     │    │   POST /v1/voices/add
│  │     - Upload voice sample      │    │   
│  │     - Get voice_id             │◄───┼──┐
│  └─────────────┬──────────────────┘    │   │ voice_id
│                ▼                        │   │
│  ┌────────────────────────────────┐    │   │
│  │  4. Update Agent Config        │────┼───┘
│  │     - Set new voice_id         │────┼──► ElevenLabs API
│  │     - Custom greeting          │    │   PATCH /v1/convai/agents/{id}
│  │     - Return caller info       │◄───┼───
│  └─────────────┬──────────────────┘    │
│                ▼                        │
│  ┌────────────────────────────────┐    │
│  │  5. Return Response            │    │
│  │     - voice_id                 │    │
│  │     - caller_info              │    │
│  │     - processing_time          │    │
│  └────────────┬───────────────────┘    │
└───────────────┼─────────────────────────┘
                │ Response (200 OK)
                ▼
        ┌───────────────┐
        │  ElevenLabs   │
        │  Voice Agent  │
        │  (Updated)    │
        └───────────────┘
```

---

## Step-by-Step Process

### 1. Webhook Receipt & Validation

**Input:**
- POST request to `/webhook`
- Headers: `elevenlabs-signature`
- Body: JSON or multipart with voice sample

**Processing:**
1. Extract signature from header
2. Validate HMAC signature
3. Check timestamp (max 30 minutes old)
4. Parse payload (JSON or multipart)

**Output:**
- Valid payload or error response (401/400)

---

### 2. Voice Sample Extraction

**JSON Format:**
```python
voice_sample_data = payload["voice_sample"]["data"]
audio_bytes = base64.b64decode(voice_sample_data)
```

**Multipart Format:**
```python
voice_sample_file = request.files["voice_sample"]
audio_bytes = voice_sample_file.read()
```

**Validation:**
- Size: Must be ≤ 10 MB
- Format: WAV, MP3, or OGG
- Duration: ≥ 3 seconds (estimated from size)

---

### 3. Instant Voice Cloning

**Voice Name Generation:**
```python
# Format: {CallerName}_Clone_{Timestamp}_{ConvID}
"Ivan_Clone_20251210_123456_abc123xyz"
```

**ElevenLabs API Call:**
```http
POST https://api.elevenlabs.io/v1/voices/add
Headers:
  xi-api-key: {API_KEY}
  Content-Type: multipart/form-data

Form Data:
  name: "Ivan_Clone_20251210_123456_abc123xyz"
  files: [voice_sample.mp3]
  description: "Instant clone for conversation conv_abc123xyz"
  labels: {"conversation_id": "conv_abc123xyz", "type": "instant_clone"}
```

**Response:**
```json
{
  "voice_id": "voice_new_cloned_xyz",
  "name": "Ivan_Clone_20251210_123456_abc123xyz",
  "category": "cloned",
  "samples": [...]
}
```

**Timing:** 2-5 seconds typically

---

### 4. Agent Configuration Update

**Personalized Greeting:**
```python
# Template: "Hallo {name}, fijn dat je belt!"
# Result: "Hallo Ivan, fijn dat je belt!"
first_message = template.format(name=caller_name)
```

**ElevenLabs API Call:**
```http
PATCH https://api.elevenlabs.io/v1/convai/agents/{agent_id}
Headers:
  xi-api-key: {API_KEY}
  Content-Type: application/json

Body:
{
  "conversation_config": {
    "agent": {
      "first_message": "Hallo Ivan, fijn dat je belt!",
      "voice": {
        "voice_id": "voice_new_cloned_xyz"
      }
    }
  }
}
```

**Response:**
```json
{
  "agent_id": "agent_def456uvw",
  "name": "Customer Service Agent",
  "conversation_config": { ... }
}
```

---

### 5. Response Formatting

**Caller Info:**
```python
caller_info = {
    "Name": caller_metadata.get("name"),
    "DateOfBirth": caller_metadata.get("date_of_birth")
}
```

**Complete Response:**
```json
{
  "status": "success",
  "conversation_id": "conv_abc123xyz",
  "voice_id": "voice_new_cloned_xyz",
  "voice_name": "Ivan_Clone_20251210_123456_abc123xyz",
  "agent_updated": true,
  "caller_info": {
    "Name": "Ivan",
    "DateOfBirth": "11.12.2007"
  },
  "processing_time_ms": 2450
}
```

---

## Error Handling

### Voice Cloning Failures

**Scenario:** ElevenLabs API returns error

**Response:**
```json
{
  "status": "error",
  "error_code": "VOICE_CLONING_FAILED",
  "error_message": "Voice sample quality too low",
  "conversation_id": "conv_abc123xyz"
}
```

**HTTP Status:** 422 Unprocessable Entity

---

### Agent Update Failures

**Scenario:** Voice created but agent update fails

**Behavior:**
- Voice ID is still returned
- `agent_updated: false` in response
- Call can proceed with default voice

**Response:**
```json
{
  "status": "success",
  "conversation_id": "conv_abc123xyz",
  "voice_id": "voice_new_cloned_xyz",
  "voice_name": "Ivan_Clone_20251210_123456_abc123xyz",
  "agent_updated": false,
  "caller_info": {...}
}
```

---

## Performance Optimization

### Processing Time Breakdown

| Step | Typical Duration |
|------|-----------------|
| HMAC Validation | < 10 ms |
| Voice Sample Validation | < 50 ms |
| Voice Cloning API | 2000-5000 ms |
| Agent Update API | 200-500 ms |
| Response Formatting | < 10 ms |
| **Total** | **2.3-5.6 seconds** |

### Optimization Tips

1. **Audio Quality**: Higher quality samples clone faster
2. **Sample Duration**: 3-5 seconds optimal (not too long)
3. **Async Processing**: Service uses async/await throughout
4. **Timeout Settings**: 60 seconds for complete workflow

---

## Voice Cleanup (Future Enhancement)

**Auto-Delete Option:**
```env
VOICE_CLONE_AUTO_DELETE=true
```

**Implementation:**
- Listen for post-call webhook
- Delete voice after conversation ends
- Reduce ElevenLabs account clutter

**API Call:**
```http
DELETE https://api.elevenlabs.io/v1/voices/{voice_id}
```

---

## Security Considerations

### Voice Sample Security

1. **No Persistent Storage** (by default)
   - Voice samples not saved to disk
   - Processed in memory only
   - Optional storage for debugging

2. **API Key Protection**
   - Stored in environment variables
   - Never logged or exposed
   - Separate from webhook secret

3. **HMAC Validation**
   - Prevents replay attacks (timestamp)
   - Prevents tampering (signature)
   - Constant-time comparison

---

## Monitoring & Logging

**Key Log Events:**

```python
# Start
logger.info("Voice cloning initiated",
    conversation_id="conv_123",
    caller_name="Ivan",
    event_type="voice_clone_start")

# Success
logger.info("Voice cloned successfully",
    conversation_id="conv_123",
    voice_id="voice_xyz",
    event_type="voice_clone_success")

# Agent Updated
logger.info("Agent updated successfully",
    conversation_id="conv_123",
    agent_id="agent_456",
    voice_id="voice_xyz",
    event_type="agent_update_success")

# Complete
logger.info("Pre-call webhook processed",
    conversation_id="conv_123",
    processing_time_ms=2450,
    event_type="webhook_complete")
```

**Metrics to Track:**
- Voice cloning success rate
- Average processing time
- Agent update success rate
- Error rates by type
- API response times

---

## Testing

**Unit Tests:**
- Voice sample validation
- Name generation
- Error handling
- HMAC validation

**Integration Tests:**
- Full workflow with real API
- Multipart file uploads
- Error scenarios

**Example Test:**
```python
# Test successful voice cloning
response = await service.process_precall_webhook(
    conversation_id="test_123",
    agent_id="agent_456",
    voice_sample=audio_bytes,
    caller_metadata={"name": "Test User"}
)

assert response["voice_id"].startswith("voice_")
assert response["agent_updated"] is True
```

---

## Best Practices

1. **Voice Sample Quality**
   - Clear speech, minimal background noise
   - Consistent volume level
   - Natural speaking pace

2. **Error Recovery**
   - Graceful degradation (voice creation fails, use default)
   - Retry logic for transient failures
   - Detailed error logging

3. **Resource Management**
   - Async processing for concurrent requests
   - Connection pooling for API calls
   - Timeout handling

4. **Caller Privacy**
   - Don't log voice sample data
   - Sanitize caller info in logs
   - Comply with data retention policies
