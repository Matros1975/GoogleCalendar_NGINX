# Migration Guide: Dual Protocol Refactor

This guide helps you upgrade from the original Twilio-only implementation to the dual protocol architecture.

## Overview

The VoiceClone Pre-Call Service has been refactored to support **both Twilio and native SIP** protocols through a protocol-agnostic business logic layer.

### What Changed

#### ✅ Backward Compatible (No Changes Required)
- Twilio webhook endpoints unchanged
- TwiML responses identical
- Database schema compatible (one field renamed internally)
- Environment variables remain the same
- Docker container works as before

#### 🆕 New Features
- Protocol-agnostic business logic (`CallController`)
- Optional SIP handler support
- Cleaner separation of concerns
- Better testability

## Migration Steps

### Step 1: Review Code Changes

#### New Models

**CallContext** (`src/models/call_context.py`)
- Represents call information independent of protocol
- Used by both Twilio and SIP handlers

**CallInstructions** (`src/models/call_instructions.py`)
- Protocol-agnostic call control instructions
- Converted to TwiML or SIP commands by handlers

**AudioService** (`src/services/audio_service.py`)
- Handles audio file downloading and caching
- Used by SIP handler (future enhancement)

#### Refactored Components

**CallController** (`src/services/call_controller.py`)
- Contains all business logic extracted from `twilio_handler.py`
- Methods:
  - `handle_inbound_call(context)` - Process new calls
  - `check_clone_status(call_id)` - Poll clone status

**Twilio Handler** (`src/handlers/twilio_handler.py`)
- Now uses `CallController` for business logic
- New helper: `_convert_to_twiml(instructions)` - Converts instructions to TwiML
- Signature validation unchanged

#### Database Change

**CallLog Model** (`src/models/database_models.py`)
- Field renamed: `metadata` → `extra_data` (Python attribute)
- Database column name remains `metadata` (no migration needed)
- Fixes SQLAlchemy reserved attribute conflict

### Step 2: Update Dependencies (Optional - Only if Using SIP)

If enabling SIP support:

```bash
# Install system packages
sudo apt-get install -y python3-pjsua2 libpjproject-dev

# Install Python package
pip install websockets>=12.0
```

### Step 3: Environment Configuration

#### Existing Twilio Configuration
No changes required - all existing variables work:
```bash
ELEVENLABS_API_KEY=your_key
ELEVENLABS_AGENT_ID=your_agent_id
DATABASE_URL=postgresql+asyncpg://...
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
# ... etc
```

#### Optional SIP Configuration
To enable SIP (optional):
```bash
# Add these to .env
ENABLE_SIP_HANDLER=true
SIP_HOST=0.0.0.0
SIP_PORT=5060
```

### Step 4: Testing

#### Run Existing Tests
```bash
cd Servers/VoiceClone_PreCall_Service
source .venv/bin/activate
pytest tests/test_twilio_webhook_debug.py -v
```

All 7 baseline Twilio tests should pass.

#### Run New Unit Tests
```bash
pytest tests/unit/test_call_controller.py -v
```

All 14 CallController tests should pass.

#### Run Full Test Suite
```bash
pytest tests/ -v
```

All 21 tests should pass.

### Step 5: Deploy

#### Docker Build
```bash
cd Servers/VoiceClone_PreCall_Service
docker build -t voiceclone-precall:v2 .
```

#### Docker Compose
```bash
# From repository root
docker-compose up -d voiceclone-precall
```

#### Verify Health
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "database": "ok",
  "elevenlabs": "ok",
  "timestamp": "..."
}
```

## Rollback Plan

If you encounter issues:

### Quick Rollback
```bash
# Revert to previous commit
git checkout <previous-commit-hash>

# Rebuild and restart
docker-compose build voiceclone-precall
docker-compose restart voiceclone-precall
```

### Database Rollback
No database migration needed - the field rename is transparent.

## Compatibility Matrix

| Component | v1 (Before) | v2 (After) | Compatible? |
|-----------|-------------|------------|-------------|
| Twilio Webhooks | ✅ | ✅ | ✅ Yes |
| TwiML Responses | ✅ | ✅ | ✅ Yes |
| Database Schema | ✅ | ✅ | ✅ Yes |
| Environment Vars | ✅ | ✅ | ✅ Yes |
| Docker Container | ✅ | ✅ | ✅ Yes |
| API Endpoints | ✅ | ✅ | ✅ Yes |
| SIP Support | ❌ | ✅ | 🆕 New |

## Verification Checklist

After migration:

- [ ] All Twilio tests pass
- [ ] Health endpoint returns `ok`
- [ ] Test call from Twilio works
- [ ] Database connections work
- [ ] ElevenLabs integration works
- [ ] Logs show no errors
- [ ] Docker container starts cleanly
- [ ] (Optional) SIP handler starts if enabled

## Performance Impact

Expected changes:
- **Response Time**: Minimal change (~5ms additional for instruction conversion)
- **Memory**: +10-20MB for additional models
- **CPU**: No significant change
- **Database**: No schema changes, no additional queries

## Breaking Changes

### None for Twilio Users

If you're only using Twilio, **no breaking changes**.

### SIP Users (New Feature)

If enabling SIP:
- **Port 5060/UDP** must be opened
- **RTP ports 16384-32768/UDP** needed for media (future)
- **PJSUA2** library required

## Common Issues

### Issue: Tests Fail

**Symptom**: `sqlalchemy.exc.InvalidRequestError: Attribute name 'metadata' is reserved`

**Solution**: Already fixed - upgrade to v2

### Issue: SIP Not Starting

**Symptom**: `pjsua2 library not available`

**Solution**: 
```bash
sudo apt-get install -y python3-pjsua2 libpjproject-dev
```

### Issue: Import Errors

**Symptom**: `ModuleNotFoundError: No module named 'src.models.call_context'`

**Solution**: Ensure you're running from the correct directory:
```bash
cd Servers/VoiceClone_PreCall_Service
python -m src.main
```

## Code Examples

### Before (v1)
```python
# twilio_handler.py - business logic mixed with protocol handling
async_service.start_clone_async(...)
response = VoiceResponse()
response.say(settings.greeting_message)
# ... more TwiML generation
```

### After (v2)
```python
# Protocol-agnostic business logic
context = CallContext(call_id=CallSid, protocol="twilio")
instructions = await call_controller.handle_inbound_call(context)

# Protocol-specific conversion
twiml_response = _convert_to_twiml(instructions)
```

## Benefits

1. **Testability**: Business logic can be unit tested independently
2. **Flexibility**: Easy to add new protocols (WebRTC, etc.)
3. **Maintainability**: Clear separation of concerns
4. **Reliability**: Comprehensive test coverage (95% for CallController)
5. **Extensibility**: Protocol handlers are pluggable

## Future Enhancements

Planned for future releases:
- Complete SIP audio streaming implementation
- SIP authentication
- WebRTC support
- Call recording
- Advanced call routing

## Support

For issues:
1. Check logs: `/var/log/mcp-services/voiceclone.log`
2. Review test results: `pytest -v`
3. Check GitHub issues
4. Contact: development team

## Appendix: File Mapping

| Old Location | New Location | Notes |
|--------------|--------------|-------|
| `twilio_handler.py` | `twilio_handler.py` | Refactored to use CallController |
| N/A | `call_controller.py` | New - extracted business logic |
| N/A | `call_context.py` | New - protocol-agnostic call data |
| N/A | `call_instructions.py` | New - protocol-agnostic instructions |
| N/A | `audio_service.py` | New - audio file handling |
| N/A | `sip_handler.py` | New - SIP protocol support |
| `database_models.py` | `database_models.py` | Minor change - field renamed |
| `main.py` | `main.py` | Updated - initializes CallController |
