# Dual Protocol Implementation Spec - Autonomous Agent

## Mission
Refactor Twilio-based VoiceClone service to support **Twilio + Native SIP** by extracting business logic from `twilio_handler.py` into protocol-agnostic `CallController`.

**Working Dir**: `/home/ubuntu/GoogleCalendar_NGINX/Servers/VoiceClone_PreCall_Service`

---

## Quick Start
```bash
cd /home/ubuntu/GoogleCalendar_NGINX/Servers/VoiceClone_PreCall_Service
git checkout -b feature/dual-protocol-refactor
source .venv/bin/activate
pytest tests/test_twilio_webhook_debug.py -v  # Baseline (must pass)
```

---

## Architecture

**Layers**:
1. Protocol Handlers (Twilio/SIP) → Entry points
2. CallController → Business logic (protocol-agnostic)
3. Services (VoiceClone, DB, Audio) → Shared
4. WebSocket Bridge → ElevenLabs audio

**Flow**: Handler → CallController → CallInstructions → Handler converts to protocol response

---

## Phase 1: Models (2-3h)

### Task 1.1: CallInstructions
**File**: `src/models/call_instructions.py`

**Classes**: `CallAction(Enum)`, `AudioInstruction`, `SpeechInstruction`, `StatusPollInstruction`, `WebSocketInstruction`, `CallInstructions`

**Key**: `CallInstructions` has: `greeting_audio`, `hold_audio`, `status_poll`, `websocket`, `error_message`, `should_hangup`, `call_id`, `clone_status`

```bash
python -m py_compile src/models/call_instructions.py
git add src/models/call_instructions.py
git commit -m "feat(models): add CallInstructions data model"
```

### Task 1.2: CallContext
**File**: `src/models/call_context.py`

**Fields**: `call_id`, `session_id`, `caller_number`, `recipient_number`, `status`, `protocol` ("twilio"/"sip")

```bash
python -m py_compile src/models/call_context.py
git add src/models/call_context.py
git commit -m "feat(models): add CallContext data model"
```

### Task 1.3: AudioService
**File**: `src/services/audio_service.py`

**Methods**: `get_audio_file(url)` → Download, cache, return Path

```bash
python -m py_compile src/services/audio_service.py
git add src/services/audio_service.py
git commit -m "feat(services): add AudioService"
```

---

## Phase 2: Extract Business Logic (4-6h)

### Task 2.1: CallController
**File**: `src/services/call_controller.py`

**Extract FROM `twilio_handler.py`**:
- Lines 85-168 → `handle_inbound_call(context: CallContext) -> CallInstructions`
- Lines 171-270 → `check_clone_status(call_id: str) -> CallInstructions`

**Logic**:
1. `handle_inbound_call()`: Start `voice_clone_service.start_clone_async()`, return greeting+hold+poll instructions
2. `check_clone_status()`: Query DB, return instructions based on status:
   - `processing` → continue hold music + poll
   - `completed` → WebSocket URL
   - `failed` → error message + hangup

```bash
python -m py_compile src/services/call_controller.py
git add src/services/call_controller.py
git commit -m "feat(services): extract business logic to CallController"
```

### Task 2.2: Refactor Twilio Handler
**File**: `src/handlers/twilio_handler.py` (MODIFY)

**Changes**:
1. Replace global `async_service`, `db_service` with `call_controller`
2. `init_handler(controller: CallController)`
3. `handle_inbound_call()`:
   ```python
   context = CallContext(call_id=CallSid, ..., protocol="twilio")
   instructions = await call_controller.handle_inbound_call(context)
   return Response(content=str(_convert_to_twiml(instructions)), media_type="application/xml")
   ```
4. `handle_status_callback()`:
   ```python
   instructions = await call_controller.check_clone_status(call_sid)
   return Response(content=str(_convert_to_twiml(instructions)), media_type="application/xml")
   ```
5. Add `_convert_to_twiml(instructions: CallInstructions) -> VoiceResponse`
6. Keep signature validation unchanged

```bash
python -m py_compile src/handlers/twilio_handler.py
git add src/handlers/twilio_handler.py
git commit -m "refactor(handlers): use CallController in twilio_handler"
```

### Task 2.3: Update main.py
**File**: `src/main.py` (MODIFY)

**Changes**:
```python
from src.services.call_controller import CallController
# In startup:
call_controller = CallController(voice_clone_service, database_service)
twilio_handler.init_handler(call_controller)
```

```bash
git add src/main.py
git commit -m "refactor(main): initialize CallController"
```

### CRITICAL: Validate Phase 2
```bash
pytest tests/test_twilio_webhook_debug.py -v
# ALL 5 TESTS MUST PASS - if any fail, DO NOT PROCEED
git tag phase-2-complete
```

---

## Phase 3: SIP Handler (8-12h)

### Task 3.1: Dependencies
```bash
echo "pjsua2>=2.13" >> requirements.txt
echo "websockets>=12.0" >> requirements.txt
pip install -r requirements.txt
git add requirements.txt && git commit -m "chore(deps): add SIP dependencies"
```

### Task 3.2: SIP Handler
**File**: `src/handlers/sip_handler.py` (NEW)

**Classes**:
1. `VoiceCloneCall(pj.Call)`:
   - `onCallState()`: INCOMING→answer, CONFIRMED→handle, DISCONNECTED→cleanup
   - `_handle_incoming()`: Create CallContext, answer call
   - `_handle_confirmed()`: `await controller.handle_inbound_call(context)`
   - `_execute_instructions()`: Play audio via RTP, handle instructions
   - `_poll_status()`: Internal loop calling `controller.check_clone_status()`
   - `_connect_websocket()`: Create WebSocketBridge

2. `WebSocketBridge`: RTP ↔ WebSocket audio streaming

3. `SIPServer`: PJSUA2 endpoint, UDP transport on port 5060

```bash
python -m py_compile src/handlers/sip_handler.py
git add src/handlers/sip_handler.py
git commit -m "feat(handlers): add SIP handler with WebSocket bridge"
```

### Task 3.3: Configuration
**.env**:
```bash
ENABLE_SIP_HANDLER=true
SIP_HOST=0.0.0.0
SIP_PORT=5060
```

**src/config.py**: Add `enable_sip_handler`, `sip_host`, `sip_port` fields

```bash
git add .env src/config.py
git commit -m "feat(config): add SIP configuration"
```

### Task 3.4: Docker
**Dockerfile**:
```dockerfile
RUN apt-get update && apt-get install -y \
    build-essential libpjproject-dev python3-pjsua2
EXPOSE 8000 5060/udp
```

**docker-compose.yml**:
```yaml
ports:
  - "8000:8000"
  - "5060:5060/udp"
  - "16384-32768:16384-32768/udp"
```

```bash
git add Dockerfile docker-compose.yml
git commit -m "chore(docker): add PJSUA2 and SIP ports"
```

### Task 3.5: Integrate SIP Server
**src/main.py**:
```python
from src.handlers.sip_handler import SIPServer
# In startup (if settings.enable_sip_handler):
sip_server = SIPServer(call_controller, audio_service)
await sip_server.start()
# In shutdown:
await sip_server.stop()
```

```bash
git add src/main.py && git commit -m "feat(main): integrate SIP server"
git tag phase-3-complete
```

---

## Phase 4: Testing (4-6h)

### Unit Tests
**File**: `tests/unit/test_call_controller.py`

```python
async def test_handle_inbound_call():
    controller = CallController(mock_voice_service, mock_db_service)
    context = CallContext(call_id="CA123", protocol="twilio", ...)
    instructions = await controller.handle_inbound_call(context)
    assert instructions.greeting_audio is not None
    assert instructions.status_poll is not None
```

```bash
pytest tests/unit/test_call_controller.py -v
git add tests/unit/test_call_controller.py
git commit -m "test(services): add CallController unit tests"
```

### Integration Tests
```bash
pytest tests/test_twilio_webhook_debug.py -v  # Must pass (regression)
pytest -v --cov=src
git tag phase-4-complete
```

---

## Phase 5: Documentation (2-3h)

### Files to Create/Update
1. `docs/SIP_TESTING_GUIDE.md` - Linphone softphone setup
2. `docs/MIGRATION_GUIDE.md` - Upgrade instructions
3. `README.md` - Add dual protocol section

```bash
git add docs/*.md README.md
git commit -m "docs: add dual protocol documentation"
```

---

## Final Validation
```bash
pytest -v
pytest --cov=src --cov-report=term-missing
docker build -t voiceclone-precall:test .
docker-compose up -d && sleep 5 && curl -f http://localhost:8000/health
docker-compose down
git rebase main
git push origin feature/dual-protocol-refactor
```

---

## Validation Checklist

**Phase 1**:
- [ ] All 3 model files compile
- [ ] Imports work
- [ ] Atomic commits

**Phase 2**:
- [ ] CallController compiles
- [ ] twilio_handler refactored
- [ ] main.py updated
- [ ] **ALL existing Twilio tests pass**

**Phase 3**:
- [ ] PJSUA2 installs
- [ ] sip_handler compiles
- [ ] Docker builds
- [ ] SIP server starts

**Phase 4**:
- [ ] Unit tests pass
- [ ] Regression tests pass
- [ ] Coverage ≥80%

**Phase 5**:
- [ ] Documentation complete
- [ ] Docker container runs
- [ ] Health check passes

---

## Commit Message Format
```
<type>(<scope>): <subject>

<body>
```
**Types**: feat, refactor, test, docs, fix, chore

---

## Critical Rules
- ✅ Commit after EACH file
- ✅ Run tests after EACH phase
- ✅ Extract business logic FIRST
- ❌ NEVER break existing Twilio tests
- ❌ NEVER skip validation
