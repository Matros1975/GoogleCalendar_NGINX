# TASK: Migrate VoiceClone Service from 3CX to Twilio Integration

**Agent Instructions**: You are an autonomous GitHub Copilot agent tasked with migrating the VoiceClone Pre-Call Service from 3CX PBX to Twilio integration.

**Change Type**: Integration Migration  
**Priority**: HIGH  
**Scope**: VoiceClone Pre-Call Service Configuration & Architecture  
**Date**: December 10, 2025  
**Working Directory**: `/home/ubuntu/GoogleCalendar_NGINX/VoiceClone_PreCall_Service/`

---

## YOUR MISSION

Migrate the VoiceClone Pre-Call Service from 3CX PBX integration to Twilio integration. Replace SIP-based callback pattern with TwiML-based WebSocket streaming. You will modify configuration files, update handlers, remove deprecated code, create database migrations, update tests, and refresh all documentation.

**What You Will Do**: Replace 3CX PBX integration with Twilio integration for inbound-only voice agent calls  
**Why**: Simplify architecture by using Twilio's native TwiML for call control instead of 3CX SIP transfers  
**Impact**: Removes dependency on `ELEVENLABS_PHONE_NUMBER_ID`, eliminates callback-to-join pattern, enables direct call flow control via TwiML

---

## AGENT RESPONSIBILITIES

You must:
1. ✅ **Update all configuration files** (.env, config.py, .env.example)
2. ✅ **Rename and rewrite handler** (threecx_handler.py → twilio_handler.py)
3. ✅ **Remove deprecated code** (trigger_agent_call method, phone number ID logic)
4. ✅ **Update database models** (3cx_call_id → call_sid, create migration)
5. ✅ **Update main application** (router imports, version bump)
6. ✅ **Create test script** (test-twilio-webhook.sh)
7. ✅ **Update all documentation** (README.md, remove 3CX references)
8. ✅ **Write/update tests** (unit tests for Twilio signature, TwiML generation)

**DO NOT:**
- ❌ Skip database migration creation
- ❌ Leave 3CX references in documentation
- ❌ Keep deprecated `ELEVENLABS_PHONE_NUMBER_ID` configuration
- ❌ Use placeholder implementations

**WORKING STYLE:**
- Follow existing patterns from `VoiceClone_PreCall_Service/`
- Use Python 3.11, FastAPI, async/await throughout
- Test locally with `SKIP_WEBHOOK_SIGNATURE_VALIDATION=true`
- Commit changes incrementally with clear messages
- Validate changes before committing

---

## CURRENT ARCHITECTURE (3CX + Callback-to-Join)

### Current Call Flow
```
┌──────────┐      ┌────────────┐      ┌──────────────────┐      ┌──────────────┐
│ Inbound  │─────▶│  3CX PBX   │─────▶│  VoiceClone API  │─────▶│  ElevenLabs  │
│  Caller  │      │            │      │   (Webhook)      │      │  Voice Agent │
└──────────┘      └────────────┘      └──────────────────┘      └──────────────┘
                        │                      │                        │
                        │                      ▼                        │
                        │              Clone voice async                │
                        │              Play greeting + music            │
                        │              Wait for clone ready             │
                        │                      │                        │
                        │                      ▼                        │
                        │         Call ElevenLabs API with              │
                        │         PHONE_NUMBER_ID to trigger            │
                        │         "callback to join" the call           │
                        │                      │                        │
                        └──────────────────────┴────────────────────────┘
                                    ElevenLabs calls back
                                    3CX transfers call via SIP
```

### Current Configuration Requirements
- `ELEVENLABS_PHONE_NUMBER_ID`: Required for ElevenLabs to call back into 3CX
- `3CX_WEBHOOK_SECRET`: For webhook signature validation
- `3CX_TRUSTED_IPS`: IP whitelist for 3CX servers
- **SIP Configuration**: 3CX must handle SIP transfer to ElevenLabs

### Current Limitations
1. **Complex Setup**: Requires 3CX SIP configuration + ElevenLabs phone number registration
2. **Callback Dependency**: ElevenLabs must have ability to call back (phone number ID)
3. **Limited Control**: Once call transferred to ElevenLabs, 3CX loses control
4. **Inbound-Only Waste**: `PHONE_NUMBER_ID` designed for outbound, but we only do inbound

---

## NEW ARCHITECTURE (Twilio + TwiML Direct)

### New Call Flow
```
┌──────────┐      ┌─────────────┐      ┌──────────────────┐      ┌──────────────┐
│ Inbound  │─────▶│   Twilio    │─────▶│  VoiceClone API  │      │  ElevenLabs  │
│  Caller  │      │   Number    │      │   (Webhook)      │      │  Voice Agent │
└──────────┘      └─────────────┘      └──────────────────┘      └──────────────┘
                        │                      │                        ▲
                        │                      ▼                        │
                        │              Clone voice async                │
                        │              Return TwiML:                    │
                        │              <Play>greeting.mp3</Play>        │
                        │                      │                        │
                        │                      ▼                        │
                        │              Monitor clone status             │
                        │              (polling/webhook)                │
                        │                      │                        │
                        │                      ▼                        │
                        │              Clone complete!                  │
                        │              Return TwiML:                    │
                        │              <Connect>                        │
                        │                <Stream url=elevenlabs/>       │
                        │              </Connect>                       │
                        │                      │                        │
                        └──────────────────────┴───────────────────────┘
                                    Twilio streams audio
                                    directly to ElevenLabs
```

### Key Architectural Changes

#### 1. **TwiML-Based Control** (Instead of SIP Transfer)
- **Response 1**: Return TwiML with `<Play>` greeting + music
- **Response 2**: Return TwiML with `<Connect><Stream>` to ElevenLabs WebSocket
- **No SIP**: Twilio handles all call routing via TwiML/WebSocket

#### 2. **WebSocket Streaming** (Instead of Callback)
- Use ElevenLabs WebSocket API for real-time audio streaming
- Twilio → WebSocket → ElevenLabs Voice Agent
- **Remove**: `ELEVENLABS_PHONE_NUMBER_ID` (not needed)

#### 3. **Direct Status Polling** (Instead of Waiting)
```python
# Current: Wait for clone, then trigger callback
clone_voice() → wait_for_complete() → trigger_agent_call(PHONE_NUMBER_ID)

# New: Return immediately, Twilio polls for status
clone_voice_async() → return TwiML(greeting)
# Twilio calls /status-callback?call_sid=XXX every 2s
# When ready: return TwiML(<Connect><Stream>)
```

---

## IMPLEMENTATION TASKS - SEQUENTIAL ORDER

**IMPORTANT**: Execute tasks in this exact order. Complete each task fully before moving to the next.

---

### TASK 1: Update Configuration Files ✅ CRITICAL - DO THIS FIRST

**Objective**: Remove 3CX configuration, add Twilio configuration

**Files to Modify:**
1. `/home/ubuntu/GoogleCalendar_NGINX/.env`
2. `/home/ubuntu/GoogleCalendar_NGINX/VoiceClone_PreCall_Service/.env.example`
#### Step 1.1: Update `/home/ubuntu/GoogleCalendar_NGINX/.env`

**Action**: Replace 3CX/ElevenLabs phone number config with Twilio config

```bash
# FIND AND REMOVE these lines:
ELEVENLABS_PHONE_NUMBER_ID=your-phone-number-id-here
THREECX_WEBHOOK_SECRET=your-3cx-webhook-secret-here
THREECX_TRUSTED_IPS=127.0.0.1,10.0.0.0/8

# ADD these lines in the VOICECLONE PRE-CALL SERVICE section:
# Twilio Configuration (replaces 3CX)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890

# Testing Mode (skip signature validation for local testing)
SKIP_WEBHOOK_SIGNATURE_VALIDATION=false
```

**Validation**: 
```bash
grep -q "TWILIO_ACCOUNT_SID" /home/ubuntu/GoogleCalendar_NGINX/.env && echo "✅ Twilio config added"
! grep -q "ELEVENLABS_PHONE_NUMBER_ID" /home/ubuntu/GoogleCalendar_NGINX/.env && echo "✅ Phone number ID removed"
! grep -q "THREECX_WEBHOOK_SECRET" /home/ubuntu/GoogleCalendar_NGINX/.env && echo "✅ 3CX config removed"
```LIO_WEBHOOK_URL=https://matrosmcp.duckdns.org/voiceclone/webhooks/inbound

# Testing Mode (skip signature validation for local testing)
SKIP_WEBHOOK_SIGNATURE_VALIDATION=false  # Set to true for curl testing
```

#### Step 1.2: Update `src/config.py`

**File**: `/home/ubuntu/GoogleCalendar_NGINX/VoiceClone_PreCall_Service/src/config.py`

**Action**: Replace Config class attributes

```python
# FIND and REMOVE these lines from Config class:
    ELEVENLABS_PHONE_NUMBER_ID: str = os.getenv("ELEVENLABS_PHONE_NUMBER_ID")
    THREECX_WEBHOOK_SECRET: str = os.getenv("3CX_WEBHOOK_SECRET")
    THREECX_TRUSTED_IPS: List[str] = os.getenv("3CX_TRUSTED_IPS", "").split(",")

# ADD these lines to Config class:
    # Twilio Configuration
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    TWILIO_WEBHOOK_URL: str = os.getenv("TWILIO_WEBHOOK_URL", "")
    
    # Testing Mode
    SKIP_WEBHOOK_SIGNATURE_VALIDATION: bool = os.getenv(
        "SKIP_WEBHOOK_SIGNATURE_VALIDATION", "false"
---

### TASK 2: Create Twilio Webhook Handler ✅ CRITICAL - DO THIS SECOND

**Objective**: Replace 3CX webhook handler with Twilio TwiML-based handler

**Files to Create/Modify:**
1. Rename: `src/handlers/threecx_handler.py` → `src/handlers/twilio_handler.py`
2. Update: `src/models/webhook_models.py` (Twilio payload models)

**Actions:**

#### Step 2.1: Rename Handler File

```bash
cd /home/ubuntu/GoogleCalendar_NGINX/VoiceClone_PreCall_Service
git mv src/handlers/threecx_handler.py src/handlers/twilio_handler.py
```

#### Step 2.2: Rewrite `src/handlers/twilio_handler.py`

**File**: `/home/ubuntu/GoogleCalendar_NGINX/VoiceClone_PreCall_Service/src/handlers/twilio_handler.py`

**Action**: Replace entire file content with Twilio implementation

**Purpose**: Handle Twilio inbound call webhooks and return TwiML responses
**Action**: Update example configuration template

```bash
# REMOVE these lines:
ELEVENLABS_PHONE_NUMBER_ID=your-phone-number-id-here
3CX_WEBHOOK_SECRET=your-3cx-webhook-secret-here
3CX_TRUSTED_IPS=127.0.0.1,10.0.0.0/8

# ADD these lines:
# Twilio Configuration
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_WEBHOOK_URL=https://your-domain.com/voiceclone/webhooks/inbound

# Testing Mode (set to true for local testing without real Twilio)
SKIP_WEBHOOK_SIGNATURE_VALIDATION=false
```

**Commit After Task 1**:
```bash
git add .env src/config.py .env.example
git commit -m "config: migrate from 3CX to Twilio configuration

- Remove ELEVENLABS_PHONE_NUMBER_ID (no longer needed)
- Remove 3CX_WEBHOOK_SECRET and 3CX_TRUSTED_IPS
- Add TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
- Add SKIP_WEBHOOK_SIGNATURE_VALIDATION for testing
- Update .env.example template"
```

---

### TASK 2: Implement Twilio Webhook Handler ✅ REQUIRED

**File**: `src/handlers/twilio_handler.py` (rename from `threecx_handler.py`)

**Purpose**: Handle Twilio inbound call webhooks and return TwiML responses

#### Twilio Webhook Payload Structure
```python
# Twilio sends these parameters (form-urlencoded)
{
    "CallSid": "CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "AccountSid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "From": "+31612345678",           # Caller phone number
    "To": "+31201234567",             # Twilio number called
    "CallStatus": "ringing",          # ringing, in-progress, completed
    "Direction": "inbound",
    "ApiVersion": "2010-04-01",
    "ForwardedFrom": null,
    "CallerName": null
}
```

#### Implementation Structure
```python
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import PlainTextResponse
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
from twilio.request_validator import RequestValidator
from src.services.voice_clone_async_service import VoiceCloneAsyncService
from src.services.database_service import DatabaseService
from src.config import config
import logging

router = APIRouter(prefix="/webhooks", tags=["twilio"])
logger = logging.getLogger(__name__)


async def validate_twilio_signature(request: Request) -> bool:
    """Validate Twilio webhook signature using X-Twilio-Signature header."""
    if config.SKIP_WEBHOOK_SIGNATURE_VALIDATION:
        logger.warning("⚠️  Skipping Twilio signature validation (testing mode)")
        return True
    
    validator = RequestValidator(config.TWILIO_AUTH_TOKEN)
    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)
    
    # Twilio sends form data, not JSON
    form_data = await request.form()
    params = dict(form_data)
    
    return validator.validate(url, params, signature)


@router.post("/inbound", response_class=PlainTextResponse)
async def handle_inbound_call(request: Request):
    """
    Handle inbound call from Twilio.
    
    Flow:
    1. Validate Twilio signature
    2. Extract caller information
    3. Start async voice cloning
    4. Return TwiML with greeting + music
    5. Twilio will poll /status-callback for completion
    """
    # 1. Validate signature
    if not await validate_twilio_signature(request):
        logger.error("❌ Invalid Twilio signature")
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    # 2. Extract call data
    form_data = await request.form()
    call_sid = form_data.get("CallSid")
    caller_number = form_data.get("From")
    twilio_number = form_data.get("To")
    call_status = form_data.get("CallStatus")
    
    logger.info(f"📞 Inbound call: {call_sid} from {caller_number} to {twilio_number}")
    
    # 3. Start async voice cloning
    clone_service = VoiceCloneAsyncService()
    await clone_service.start_clone_async(
        call_sid=call_sid,
        caller_number=caller_number,
        twilio_number=twilio_number
    )
    
    # 4. Return TwiML with greeting
    response = VoiceResponse()
    response.say(
        config.GREETING_MESSAGE,
        voice=config.GREETING_VOICE_ID,
        language="en-US"
    )
    
    if config.GREETING_MUSIC_ENABLED:
        response.play(config.GREETING_MUSIC_URL, loop=10)  # Loop while cloning
    else:
        response.pause(length=config.CLONE_MAX_WAIT_SECONDS)
    
    # 5. Set status callback for polling
    response.redirect(
        url=f"/webhooks/status-callback?call_sid={call_sid}",
        method="POST"
    )
    
    return str(response)


@router.post("/status-callback", response_class=PlainTextResponse)
async def handle_status_callback(call_sid: str, request: Request):
    """
    Twilio polls this endpoint to check if voice clone is ready.
    
    Returns:
    - If clone ready: TwiML with <Connect><Stream> to ElevenLabs
    - If still processing: TwiML to continue waiting (redirect back)
    - If failed: TwiML to hangup with error message
    """
    # Validate signature
    if not await validate_twilio_signature(request):
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    # Check clone status
    db_service = DatabaseService()
    clone_status = await db_service.get_clone_status(call_sid)
    
    response = VoiceResponse()
    
    if clone_status["status"] == "completed":
        logger.info(f"✅ Clone ready for {call_sid}, connecting to ElevenLabs")
        
        # Connect to ElevenLabs WebSocket
        connect = Connect()
        stream = Stream(
            url=f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={config.ELEVENLABS_AGENT_ID}",
            track="inbound_track"
        )
        stream.parameter(name="voice_id", value=clone_status["voice_clone_id"])
        stream.parameter(name="api_key", value=config.ELEVENLABS_API_KEY)
        
        connect.append(stream)
        response.append(connect)
        
    elif clone_status["status"] == "processing":
        logger.info(f"⏳ Clone still processing for {call_sid}, continuing to wait")
        
        # Continue playing music/waiting
        if config.GREETING_MUSIC_ENABLED:
            response.play(config.GREETING_MUSIC_URL, loop=5)
    return str(response)
```

**Dependencies Required**: Add to `requirements.txt`:
```
twilio>=8.10.0
```

**Commit After Task 2**:
```bash
git add src/handlers/twilio_handler.py src/models/webhook_models.py requirements.txt
git commit -m "feat: implement Twilio webhook handler with TwiML responses

- Replace threecx_handler.py with twilio_handler.py
- Implement /webhooks/inbound endpoint (accepts Twilio form data)
- Implement /webhooks/status-callback endpoint (polling for clone completion)
- Add Twilio signature validation with skip mode for testing
- Generate TwiML responses for greeting, music, and WebSocket streaming
- Add twilio dependency to requirements.txt"
```

---

### TASK 3: Update Voice Clone Service ✅ CRITICAL - DO THIS THIRD

**Objective**: Remove phone number ID callback logic, update for Twilio call tracking
**Files to Modify:**
1. `/home/ubuntu/GoogleCalendar_NGINX/VoiceClone_PreCall_Service/src/services/elevenlabs_client.py`
2. `/home/ubuntu/GoogleCalendar_NGINX/VoiceClone_PreCall_Service/src/services/voice_clone_async_service.py`

**Actions:**

#### Step 3.1: Remove `trigger_agent_call()` from ElevenLabs Client

**File**: `src/services/elevenlabs_client.py`

**Action**: Delete the entire `trigger_agent_call()` method that uses `ELEVENLABS_PHONE_NUMBER_ID`
    else:  # failed or timeout
        logger.error(f"❌ Clone failed for {call_sid}: {clone_status.get('error')}")
        
        # Error message and hangup
        response.say(
            "We're sorry, we encountered an error. Please try again later.",
            voice="alice"
        )
        response.hangup()
    
    return str(response)
```

---

### TASK 3: Update Voice Clone Service (Remove Phone Number ID) ✅ REQUIRED

**File**: `src/services/elevenlabs_client.py`

**Changes**: Remove all `trigger_agent_call()` methods that use `ELEVENLABS_PHONE_NUMBER_ID`

```python
# REMOVE this entire method:
async def trigger_agent_call(
    self,
    phone_number_id: str,
    agent_id: str,
    voice_clone_id: str,
    caller_number: str
) -> Dict[str, Any]:
# KEEP these methods (still needed for voice cloning):
async def create_voice_clone(...)  # Still needed
async def get_voice_clone(...)     # Still needed
async def delete_voice_clone(...)  # Still needed
```

**Search Pattern**: Look for method definition containing:
- `def trigger_agent_call`
- `phone_number_id` parameter
- ElevenLabs callback API call

**Delete**: Entire method including docstring

#### Step 3.2: Update Voice Clone Async Service

**File**: `src/services/voice_clone_async_service.py`

**Action**: Update method signatures and implementation for Twilio:
async def create_voice_clone(...)  # Still needed
async def get_voice_clone(...)     # Still needed
async def delete_voice_clone(...)  # Still needed
```

**File**: `src/services/voice_clone_async_service.py`

**Changes**: Update to work with Twilio call tracking

```python
async def start_clone_async(
    self,
    call_sid: str,           # Changed from 3cx_call_id
    caller_number: str,
    twilio_number: str       # Changed from 3cx_extension
) -> None:
    """
    Start async voice cloning for Twilio inbound call.
    
    Flow:
    1. Save call to database with status="processing"
    2. Retrieve voice sample for caller_number
    3. Start cloning in background task
    4. When complete: update database status="completed"
    5. Twilio polls /status-callback to detect completion
    """
    # Save initial state
    await self.db_service.save_call_record(
        call_sid=call_sid,
        caller_number=caller_number,
        twilio_number=twilio_number,
        status="processing"
    )
    
    # Start background cloning
    asyncio.create_task(self._clone_and_update(call_sid, caller_number))


async def _clone_and_update(self, call_sid: str, caller_number: str):
    """Background task: clone voice and update status."""
    try:
        # 1. Get voice sample
        voice_sample = await self.storage_service.get_voice_sample(caller_number)
        
        # 2. Clone voice
        clone_result = await self.elevenlabs_client.create_voice_clone(
            audio_data=voice_sample,
            name=f"caller_{caller_number}",
            description=f"Auto-cloned for {call_sid}"
            error=str(e)
        )
```

**Important Changes**:
- Replace `3cx_call_id` parameter with `call_sid`
- Replace `3cx_extension` parameter with `twilio_number`
- Remove any `trigger_agent_call()` invocations
- Keep async background cloning logic

**Commit After Task 3**:
```bash
git add src/services/elevenlabs_client.py src/services/voice_clone_async_service.py
git commit -m "refactor: remove phone number ID callback logic

- Delete trigger_agent_call() method from ElevenLabs client
**Files to Modify:**
1. `/home/ubuntu/GoogleCalendar_NGINX/VoiceClone_PreCall_Service/src/models/database_models.py`

**Actions:**

#### Step 4.1: Update Database Models

**File**: `src/models/database_models.py`

**Action**: Update column names in VoiceCloneCall model
- Remove ElevenLabs callback-to-join pattern"
```

---

### TASK 4: Update Database Models & Create Migration ✅ CRITICAL - DO THIS FOURTH

**Objective**: Rename database columns from 3CX to Twilio naming conventionse_id"],
            clone_metadata=clone_result
        )
        
        logger.info(f"✅ Voice clone completed for {call_sid}")
        
    except Exception as e:
        logger.error(f"❌ Clone failed for {call_sid}: {e}")
        await self.db_service.update_clone_status(
            call_sid=call_sid,
            status="failed",
            error=str(e)
        )
```

---

### TASK 4: Update Database Models ✅ REQUIRED

**File**: `src/models/database_models.py`

**Changes**: Replace `3cx_call_id` with `call_sid` (Twilio's identifier)

```python
from sqlalchemy import Column, String, Integer, DateTime, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()

class CloneStatus(str, enum.Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VoiceCloneCall(Base):
    """Track voice cloning for each inbound call."""
    __tablename__ = "voice_clone_calls"
    
    updated_at = Column(DateTime, nullable=False)
```

**Key Changes**:
- `3cx_call_id` → `call_sid` (primary key, indexed)
- `3cx_extension` → `twilio_number`
- Keep all other columns unchanged

#### Step 4.2: Create Alembic Migration

**Commands**:
```bash
cd /home/ubuntu/GoogleCalendar_NGINX/VoiceClone_PreCall_Service

# Generate migration
alembic revision --autogenerate -m "migrate_from_3cx_to_twilio"

# Review migration file in migrations/versions/
# Ensure it contains:
#   - RENAME COLUMN 3cx_call_id TO call_sid
#   - RENAME COLUMN 3cx_extension TO twilio_number

# Apply migration
**Files to Modify:**
1. `/home/ubuntu/GoogleCalendar_NGINX/VoiceClone_PreCall_Service/src/main.py`

**Actions:**

#### Step 5.1: Update Main Application

**File**: `src/main.py`

**Action**: Replace threecx_handler import with twilio_handler, update metadata
**Validation**:
```bash
# Check migration applied
alembic current

# Verify table schema
docker compose exec postgres psql -U postgres -d voice_clones \
  -c "\d voice_clone_calls"
```

**Commit After Task 4**:
```bash
git add src/models/database_models.py migrations/versions/*
git commit -m "refactor(db): migrate database schema from 3CX to Twilio

- Rename 3cx_call_id to call_sid in VoiceCloneCall model
- Rename 3cx_extension to twilio_number
- Create Alembic migration for schema changes
- Apply migration to update database"
```

---

### TASK 5: Update Main Application ✅ DO THIS FIFTH

**Objective**: Update FastAPI app to use Twilio handler and bump version
    error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Metadata
    clone_metadata = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


        "health": "/health"
    }
```

**Key Changes**:
- Import `twilio_handler` instead of `threecx_handler`
- Update app description to mention Twilio
- Bump version to `2.0.0`
- Update health check response

**Commit After Task 5**:
```bash
git add src/main.py
git commit -m "feat: update main app for Twilio integration

- Replace threecx_handler with twilio_handler
- Update app description: Twilio → ElevenLabs
- Bump version to 2.0.0 for Twilio migration
- Update health check to indicate Twilio integration"
```

---

### TASK 6: Create Test Script ✅ DO THIS SIXTH

**Objective**: Create bash script to test Twilio webhooks locally without real Twilioble=True)
    sample_size_bytes = Column(Integer, nullable=True)
    
**Files to Create:**
1. `/home/ubuntu/GoogleCalendar_NGINX/VoiceClone_PreCall_Service/test-twilio-webhook.sh`

**Actions:**

#### Step 6.1: Create Test Script

**File**: `test-twilio-webhook.sh` in service root directory

**Purpose**: Enable testing without real Twilio webhookse_from_3cx_to_twilio"
alembic upgrade head
```

---

### TASK 5: Update API Endpoints ✅ REQUIRED

**File**: `src/main.py`

**Changes**: Update endpoint paths and include Twilio handler

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.handlers import twilio_handler  # Changed from threecx_handler
from src.handlers import postcall_handler
from src.config import config
import logging

app = FastAPI(
    title="VoiceClone Pre-Call Service",
    description="Twilio → ElevenLabs Voice Clone Integration",  # Updated
    version="2.0.0"  # Version bump for Twilio migration
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(twilio_handler.router)  # Changed from threecx_handler
app.include_router(postcall_handler.router)

echo "✅ Done! Check logs in Docker: docker compose logs -f voiceclone-precall"
```

#### Step 6.2: Make Script Executable

```bash
chmod +x test-twilio-webhook.sh
```

#### Step 6.3: Test Locally

**Instructions for Testing**:
1. Set `SKIP_WEBHOOK_SIGNATURE_VALIDATION=true` in `.env`
2. Start service: `docker compose up -d voiceclone-precall`
3. Run test: `./test-twilio-webhook.sh`
4. Check logs: `docker compose logs -f voiceclone-precall`

**Commit After Task 6**:
```bash
**Files to Modify:**
1. `/home/ubuntu/GoogleCalendar_NGINX/VoiceClone_PreCall_Service/README.md`
2. `/home/ubuntu/GoogleCalendar_NGINX/VoiceClone_PreCall_Service/docs/DEPLOYMENT.md`
3. `/home/ubuntu/GoogleCalendar_NGINX/VoiceClone_PreCall_Service/docs/ARCHITECTURE.md`
4. `/home/ubuntu/GoogleCalendar_NGINX/VoiceClone_PreCall_Service/docs/API.md`

**Actions:**

#### Step 7.1: Rewrite README.md

**File**: `README.md`

**Action**: Complete rewrite to reflect Twilio integration
- Create test-twilio-webhook.sh for local testing
- Mimics Twilio inbound call webhook payload
- Tests status-callback polling endpoint
- Uses SKIP_WEBHOOK_SIGNATURE_VALIDATION for local dev
- Includes instructions and validation steps"
```

---

### TASK 7: Update All Documentation ✅ CRITICAL - DO THIS SEVENTH

**Objective**: Remove all 3CX references, add Twilio setup instructions
    return {
        "message": "VoiceClone Pre-Call Service - Twilio Integration",
        "docs": "/docs",
        "health": "/health"
    }
```

---

### TASK 6: Update Testing Configuration ✅ REQUIRED

**Purpose**: Enable testing without real Twilio webhooks

#### Add to `.env` for Local Testing
```bash
# Testing Mode (for local development)
SKIP_WEBHOOK_SIGNATURE_VALIDATION=true
TWILIO_ACCOUNT_SID=test_account_sid
TWILIO_AUTH_TOKEN=test_auth_token
TWILIO_PHONE_NUMBER=+1234567890
```

#### Test Script: `test-twilio-webhook.sh`
```bash
#!/bin/bash

# Test Twilio inbound webhook (mimics real Twilio request)

VOICECLONE_URL="http://localhost:8000"

echo "📞 Testing Twilio Inbound Webhook..."

curl -X POST "${VOICECLONE_URL}/webhooks/inbound" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-Twilio-Signature: test-signature-skip-validation" \
  --data-urlencode "CallSid=CAtest123456789abcdef" \
  --data-urlencode "AccountSid=ACtest123456789abcdef" \
  --data-urlencode "From=+31612345678" \
  --data-urlencode "To=+31201234567" \
  --data-urlencode "CallStatus=ringing" \
  --data-urlencode "Direction=inbound" \
  --data-urlencode "ApiVersion=2010-04-01"

echo ""
echo "✅ Check response above for TwiML output"
echo ""

# Test status callback polling
echo "⏳ Waiting 3 seconds..."
sleep 3

echo "🔄 Testing Status Callback..."
curl -X POST "${VOICECLONE_URL}/webhooks/status-callback?call_sid=CAtest123456789abcdef" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-Twilio-Signature: test-signature-skip-validation" \
  --data-urlencode "CallSid=CAtest123456789abcdef" \
  --data-urlencode "CallStatus=in-progress"

echo ""
echo "✅ Done! Check logs in Docker: docker compose logs -f voiceclone-precall"
```

Make executable:
```bash
chmod +x test-twilio-webhook.sh
```

---

### TASK 7: Update Documentation ✅ REQUIRED

**File**: `README.md`

**Changes**: Replace all 3CX references with Twilio

```markdown
# VoiceClone Pre-Call Service - Twilio Integration

## Overview
Microservice that integrates **Twilio** with **ElevenLabs Voice Agent API** for dynamic voice cloning on inbound calls.

## Architecture
- **PBX**: Twilio Phone Numbers (inbound call handling)
- **Voice Clone**: ElevenLabs API (instant voice cloning)
- **Call Control**: TwiML (Twilio Markup Language)
- **Audio Streaming**: WebSocket (Twilio → ElevenLabs)

## Call Flow
1. **Caller dials Twilio number** → Twilio webhook to `/webhooks/inbound`
2. **Service starts voice cloning** (background task)
3. **Returns TwiML** with greeting message + music
4. **Twilio polls** `/webhooks/status-callback` every 2-5 seconds
5. **When clone ready** → Return TwiML with `<Connect><Stream>` to ElevenLabs WebSocket
6. **ElevenLabs Voice Agent** takes over with cloned voice

## Configuration

### Required Environment Variables
```bash
# Twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# ElevenLabs
ELEVENLABS_API_KEY=sk_...
ELEVENLABS_AGENT_ID=agent_...

# Greeting
GREETING_MESSAGE=Hello, please hold while we prepare your experience
GREETING_MUSIC_ENABLED=true
GREETING_MUSIC_URL=https://your-domain.com/hold-music.mp3

# Database
- **Returns**: `{"status": "healthy", "integration": "twilio"}`
```

#### Step 7.2: Update Other Documentation Files

**Files to Update**:
- `docs/DEPLOYMENT.md`: Replace 3CX setup with Twilio phone number configuration
- `docs/ARCHITECTURE.md`: Update call flow diagrams (remove SIP, add TwiML/WebSocket)
- `docs/API.md`: Update webhook endpoint documentation

**Search and Replace Across All Docs**:
```bash
# Find all 3CX references
grep -r "3CX\|3cx\|threecx" docs/ README.md

# Replace with Twilio equivalents:
# "3CX PBX" → "Twilio"
# "3CX webhook" → "Twilio webhook"
# "SIP transfer" → "TwiML WebSocket streaming"
# "callback-to-join" → "WebSocket streaming"
```

**Commit After Task 7**:
```bash
git add README.md docs/
git commit -m "docs: update all documentation for Twilio integration

- Rewrite README.md with Twilio setup instructions
- Remove all 3CX references from documentation
- Update DEPLOYMENT.md with Twilio configuration
- Update ARCHITECTURE.md with TwiML call flow
- Update API.md with new webhook endpoints
- Add Twilio console instructions
- Document SKIP_WEBHOOK_SIGNATURE_VALIDATION testing mode"
```

---
## FINAL VALIDATION CHECKLIST - AGENT MUST VERIFY

**Before marking task complete, verify ALL of these:**

### ✅ Configuration
- [ ] `.env` has `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`
- [ ] `.env` does NOT have `ELEVENLABS_PHONE_NUMBER_ID`
- [ ] `.env` does NOT have `THREECX_WEBHOOK_SECRET` or `THREECX_TRUSTED_IPS`
- [ ] `.env.example` updated with Twilio variables
- [ ] `src/config.py` has Twilio config class attributes
- [ ] `src/config.py` does NOT have 3CX attributes

### ✅ Code Changes
- [ ] `src/handlers/twilio_handler.py` exists (renamed from threecx_handler.py)
- [ ] `twilio_handler.py` has `/webhooks/inbound` endpoint
- [ ] `twilio_handler.py` has `/webhooks/status-callback` endpoint
- [ ] `twilio_handler.py` returns TwiML responses (PlainTextResponse)
- [ ] `src/services/elevenlabs_client.py` does NOT have `trigger_agent_call()` method
- [ ] `src/services/voice_clone_async_service.py` uses `call_sid` (not `3cx_call_id`)
- [ ] `src/models/database_models.py` has `call_sid` and `twilio_number` columns
- [ ] `src/main.py` imports `twilio_handler` (not `threecx_handler`)
- [ ] `src/main.py` version is `2.0.0`

### ✅ Database
- [ ] Alembic migration created in `migrations/versions/`
- [ ] Migration renames `3cx_call_id` → `call_sid`
- [ ] Migration renames `3cx_extension` → `twilio_number`
- [ ] Migration applied: `alembic upgrade head` successful
- [ ] Database schema verified with `\d voice_clone_calls`

### ✅ Testing
- [ ] `test-twilio-webhook.sh` exists and is executable
- [ ] `tests/unit/test_twilio_signature.py` created
- [ ] `tests/unit/test_twiml_responses.py` created
- [ ] Integration tests updated for Twilio
- [ ] Can run: `./test-twilio-webhook.sh` successfully
- [ ] All unit tests pass: `pytest tests/unit/`

### ✅ Documentation
- [ ] `README.md` mentions Twilio (not 3CX)
- [ ] `README.md` has Twilio setup instructions
- [ ] `docs/DEPLOYMENT.md` updated for Twilio
- [ ] `docs/ARCHITECTURE.md` shows TwiML call flow
- [ ] `docs/API.md` documents new webhook endpoints
- [ ] No files contain "3CX" or "3cx" or "threecx" (except git history)

### ✅ Dependencies
- [ ] `requirements.txt` includes `twilio>=8.10.0`
- [ ] All dependencies install: `pip install -r requirements.txt`

### ✅ Git Commits
- [ ] At least 8 commits (one per task)
- [ ] Commit messages follow conventional format
- [ ] All changes committed (no uncommitted files)
- [ ] No secrets in git history

### ✅ Deployment Readiness
- [ ] Service starts: `docker compose up -d voiceclone-precall`
- [ ] Health check passes: `curl http://localhost:8000/health`
- [ ] Returns: `{"integration": "twilio"}`
- [ ] Logs show no errors: `docker compose logs voiceclone-precall`
```python
"""Unit tests for TwiML response generation."""
import pytest
from twilio.twiml.voice_response import VoiceResponse


def test_greeting_twiml():
    """Test TwiML greeting response structure."""
    # TODO: Test that greeting includes <Say> and <Play>
    pass


def test_status_callback_completed():
    """Test TwiML when clone is completed."""
    # TODO: Verify <Connect><Stream> to ElevenLabs
    pass


def test_status_callback_processing():
    """Test TwiML when clone still processing."""
    # TODO: Verify <Redirect> back to status-callback
    pass


def test_status_callback_failed():
    """Test TwiML when clone failed."""
    # TODO: Verify error message and <Hangup>
    pass
```

#### Step 8.3: Update Integration Tests

**File**: `tests/integration/test_webhook_endpoint.py`

**Action**: Update to test Twilio endpoints instead of 3CX

```python
# Update test to POST to /webhooks/inbound with Twilio payload
# Update test to check /webhooks/status-callback polling
# Remove 3CX-specific tests
```

**Commit After Task 8**:
## IMPLEMENTATION SUMMARY FOR AGENT

**Total Tasks**: 8 (must be completed in order)
**Estimated Time**: ~4 hours
**Commits Required**: Minimum 8 (one per task)

### Task Sequence:
1. ✅ **Task 1**: Update configuration files (`.env`, `config.py`, `.env.example`)
2. ✅ **Task 2**: Create Twilio webhook handler (`twilio_handler.py`)
3. ✅ **Task 3**: Update services (remove phone number ID logic)
4. ✅ **Task 4**: Update database models + create migration
5. ✅ **Task 5**: Update main application (`main.py`)
6. ✅ **Task 6**: Create test script (`test-twilio-webhook.sh`)
7. ✅ **Task 7**: Update all documentation
8. ✅ **Task 8**: Write/update tests

### Success Criteria:
- All 8 tasks completed in order
- All validation checks pass
- Service starts without errors
- Health check returns `{"integration": "twilio"}`
- Test script runs successfully
- All unit tests pass
- Documentation complete and accurate
- No 3CX references remain in code/docs
---

## TROUBLESHOOTING FOR AGENT

### Common Issues:

**Issue**: Database migration fails
```bash
# Solution: Check connection and reset
alembic downgrade -1
alembic upgrade head
```

**Issue**: Import errors after renaming handler
```bash
# Solution: Update all imports
grep -r "threecx_handler" src/ tests/
# Replace all with twilio_handler
```

**Issue**: Tests fail with signature validation
```bash
# Solution: Enable skip mode for testing
export SKIP_WEBHOOK_SIGNATURE_VALIDATION=true
pytest tests/
```

**Issue**: Service won't start
```bash
# Solution: Check logs and dependencies
docker compose logs voiceclone-precall
pip install -r requirements.txt
```

---

## AGENT COMPLETION REPORT TEMPLATE

When finished, provide this report:

```
# Twilio Migration Completion Report

## Tasks Completed:
- [x] Task 1: Configuration files updated
- [x] Task 2: Twilio handler created
- [x] Task 3: Services updated
- [x] Task 4: Database migrated
- [x] Task 5: Main app updated
- [x] Task 6: Test script created
- [x] Task 7: Documentation updated
- [x] Task 8: Tests written

## Validation Results:
- Configuration: ✅ PASS
- Code Changes: ✅ PASS
- Database: ✅ PASS
- Testing: ✅ PASS
- Documentation: ✅ PASS
- Dependencies: ✅ PASS
- Git Commits: ✅ PASS (8 commits)
- Deployment: ✅ PASS

## Service Status:
- Health Check: ✅ {"status": "healthy", "integration": "twilio"}
- Test Script: ✅ Returns valid TwiML
- Unit Tests: ✅ All passing
- Integration Tests: ✅ All passing

## Files Changed:
- Configuration: 3 files
- Handlers: 1 renamed, 1 updated
- Services: 2 updated
- Models: 1 updated
- Migrations: 1 created
- Tests: 4 files
- Documentation: 5 files
- Total: 17 files modified

## Commits:
1. config: migrate from 3CX to Twilio configuration
2. feat: implement Twilio webhook handler with TwiML responses
3. refactor: remove phone number ID callback logic
4. refactor(db): migrate database schema from 3CX to Twilio
5. feat: update main app for Twilio integration
6. test: add Twilio webhook testing script
7. docs: update all documentation for Twilio integration
8. test: add Twilio-specific unit and integration tests

## Next Steps for User:
1. Review all changes in git history
2. Update production .env with real Twilio credentials
3. Buy Twilio phone number and configure webhook
4. Deploy to production: docker compose up -d voiceclone-precall
5. Test with real phone call
6. Monitor logs for first 10-20 calls
```

---

**END OF AGENT TASK SPECIFICATION**wilio signature validation)

## Twilio Setup

### 1. Buy Twilio Phone Number
```bash
# Via Twilio Console: https://console.twilio.com/us1/develop/phone-numbers/manage/incoming
# Select country → Buy number → Copy number to TWILIO_PHONE_NUMBER
```

### 2. Configure Webhook
```
Phone Number Configuration:
- Voice & Fax → A CALL COMES IN
- Webhook: https://matrosmcp.duckdns.org/voiceclone/webhooks/inbound
- HTTP POST
```

### 3. Get Credentials
```bash
# Account SID and Auth Token from:
# https://console.twilio.com/us1/account/keys-credentials/api-keys
```

## Testing Without Twilio

Set `SKIP_WEBHOOK_SIGNATURE_VALIDATION=true` in `.env`, then:

```bash
./test-twilio-webhook.sh
```

## Deployment
```bash
docker compose up -d voiceclone-precall
docker compose logs -f voiceclone-precall
```

## API Endpoints

### `POST /webhooks/inbound`
- **Purpose**: Receive inbound call from Twilio
- **Returns**: TwiML (greeting + music)
- **Headers**: `X-Twilio-Signature` (validated)

### `POST /webhooks/status-callback?call_sid={sid}`
- **Purpose**: Twilio polls to check if clone ready
- **Returns**: TwiML (continue waiting OR connect to ElevenLabs)

### `GET /health`
- **Purpose**: Health check
- **Returns**: `{"status": "healthy", "integration": "twilio"}`
```

---

## TESTING STRATEGY

### Unit Tests
```bash
# Test Twilio signature validation
pytest tests/unit/test_twilio_signature.py

# Test TwiML generation
pytest tests/unit/test_twiml_responses.py

# Test async cloning service
pytest tests/unit/test_voice_clone_async_service.py
```

### Integration Tests
```bash
# Test with SKIP_WEBHOOK_SIGNATURE_VALIDATION=true
SKIP_WEBHOOK_SIGNATURE_VALIDATION=true pytest tests/integration/

# Test full flow
./test-twilio-webhook.sh
```

### Manual Testing
1. **Start service**: `docker compose up -d voiceclone-precall`
2. **Configure Twilio webhook** to point to your public URL
3. **Call Twilio number** from phone
4. **Listen to greeting** + music
5. **Verify automatic transition** to voice agent when clone ready

---

## MIGRATION CHECKLIST

### Configuration Updates
- [ ] Remove `ELEVENLABS_PHONE_NUMBER_ID` from `.env`
- [ ] Remove `3CX_WEBHOOK_SECRET` from `.env`
- [ ] Remove `3CX_TRUSTED_IPS` from `.env`
- [ ] Add `TWILIO_ACCOUNT_SID` to `.env`
- [ ] Add `TWILIO_AUTH_TOKEN` to `.env`
- [ ] Add `TWILIO_PHONE_NUMBER` to `.env`
- [ ] Add `SKIP_WEBHOOK_SIGNATURE_VALIDATION=false` (production) or `true` (testing)

### Code Changes
- [ ] Rename `src/handlers/threecx_handler.py` → `twilio_handler.py`
- [ ] Update `twilio_handler.py` with TwiML responses
- [ ] Remove `trigger_agent_call()` from `elevenlabs_client.py`
- [ ] Update `voice_clone_async_service.py` for Twilio call tracking
- [ ] Update `database_models.py`: `3cx_call_id` → `call_sid`
- [ ] Create Alembic migration for database schema
- [ ] Update `src/main.py` to use `twilio_handler`
- [ ] Update `src/config.py` with Twilio settings
- [ ] Update `src/auth/hmac_validator.py` for Twilio signature validation

### Testing
- [ ] Create `test-twilio-webhook.sh` script
- [ ] Write unit tests for TwiML generation
- [ ] Write unit tests for Twilio signature validation
- [ ] Update integration tests for Twilio flow
- [ ] Test with `SKIP_WEBHOOK_SIGNATURE_VALIDATION=true`
- [ ] Test with real Twilio webhook (production)

### Documentation
- [ ] Update `README.md` with Twilio setup instructions
- [ ] Update `docs/DEPLOYMENT.md` with Twilio configuration
- [ ] Update `docs/ARCHITECTURE.md` with new call flow diagram
- [ ] Update `.env.example` with Twilio variables
- [ ] Remove 3CX references from all documentation

### Deployment
- [ ] Run database migration: `alembic upgrade head`
- [ ] Update `.env` on production server
- [ ] Restart service: `docker compose up -d voiceclone-precall`
- [ ] Configure Twilio webhook URL
- [ ] Test inbound call flow
- [ ] Monitor logs for errors
- [ ] Verify voice cloning works end-to-end

### Rollback Plan (If Issues)
- [ ] Keep 3CX configuration backed up
- [ ] Keep old `threecx_handler.py` in git history
- [ ] Document database rollback migration
- [ ] Have `ELEVENLABS_PHONE_NUMBER_ID` ready if needed

---

## BENEFITS OF TWILIO MIGRATION

### Simplified Architecture
- ✅ **No SIP Configuration**: Twilio handles all call routing via TwiML
- ✅ **No Phone Number ID**: Removed `ELEVENLABS_PHONE_NUMBER_ID` dependency
- ✅ **Direct Control**: Full control over call flow via TwiML responses

### Better Call Flow
- ✅ **Instant Greeting**: Return TwiML immediately (no delay)
- ✅ **Dynamic Control**: Change call flow based on clone status
- ✅ **Graceful Errors**: Handle clone failures with custom messages

### Easier Testing
- ✅ **Local Testing**: Use `SKIP_WEBHOOK_SIGNATURE_VALIDATION=true`
- ✅ **Curl Testing**: Mimic Twilio webhooks with curl
- ✅ **No PBX Required**: Test without 3CX infrastructure

### Scalability
- ✅ **Twilio Handles Load**: No PBX resource limits
- ✅ **Global Numbers**: Buy numbers in any country
- ✅ **Cloud-Native**: No on-premise PBX maintenance

---

## QUESTIONS & ANSWERS

**Q: Why remove `ELEVENLABS_PHONE_NUMBER_ID`?**  
A: With Twilio, we use WebSocket streaming (`<Connect><Stream>`) instead of callback-to-join pattern. ElevenLabs doesn't need to "call back" - Twilio streams audio directly to ElevenLabs WebSocket.

**Q: How does Twilio know when clone is ready?**  
A: We return TwiML with `<Redirect>` to `/status-callback`. Twilio polls this URL every 2-5 seconds until we return `<Connect><Stream>` instead of another `<Redirect>`.

**Q: Can I still test locally without Twilio?**  
A: Yes! Set `SKIP_WEBHOOK_SIGNATURE_VALIDATION=true` and use the `test-twilio-webhook.sh` script to mimic Twilio requests with curl.

**Q: What if voice cloning fails?**  
A: Status callback returns TwiML with error message + `<Hangup>`, providing graceful degradation.

**Q: How is this different from 3CX integration?**  
A: 3CX required SIP transfer + callback pattern. Twilio uses native WebSocket streaming with TwiML control - simpler and more direct.

---

## IMPLEMENTATION ORDER

1. **Update Configuration** (`.env`, `config.py`) - 15 min
2. **Rename & Update Handler** (`twilio_handler.py`) - 45 min
3. **Update Services** (remove phone number ID logic) - 30 min
4. **Update Database Models** (migration) - 20 min
5. **Update Main App** (`main.py` router) - 10 min
6. **Create Test Script** (`test-twilio-webhook.sh`) - 15 min
7. **Update Documentation** (`README.md`, docs/) - 30 min
8. **Write Tests** (unit + integration) - 60 min
9. **Deploy & Test** (production verification) - 30 min

**Total Estimated Time**: ~4 hours

---

## NEXT STEPS

After migration is complete:
1. **Monitor First Calls**: Watch logs closely for first 10-20 calls
2. **Measure Metrics**: Track clone duration, success rate, time-to-agent
3. **Optimize Greeting**: Test different messages/music based on user feedback
4. **Add Features**: Consider adding voice sample upload API, pre-cloning scheduler
5. **Scale**: If successful, consider multi-region Twilio numbers

---

**END OF SPECIFICATION**
