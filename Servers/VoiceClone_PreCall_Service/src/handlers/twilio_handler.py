"""
Twilio webhook handler for incoming call notifications.

Implements TwiML-based call control for Twilio integration.
"""

import asyncio
from typing import Dict, Any

from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
from twilio.request_validator import RequestValidator

from src.config import get_settings
from src.services.voice_clone_async_service import VoiceCloneAsyncService
from src.services.database_service import DatabaseService
from src.utils.logger import get_logger, set_call_context
from src.utils.exceptions import ValidationException

logger = get_logger(__name__)
router = APIRouter(prefix="/webhooks", tags=["twilio"])

# Global service instances (injected on startup)
async_service: VoiceCloneAsyncService = None
db_service: DatabaseService = None


def init_handler(voice_clone_async_service: VoiceCloneAsyncService, database_service: DatabaseService):
    """
    Initialize handler with service dependencies.
    
    Args:
        voice_clone_async_service: Async voice cloning service
        database_service: Database service
    """
    global async_service, db_service
    async_service = voice_clone_async_service
    db_service = database_service


async def validate_twilio_signature(request: Request) -> bool:
    """
    Validate Twilio webhook signature using X-Twilio-Signature header.
    
    Args:
        request: FastAPI request object
        
    Returns:
        True if signature is valid or validation is skipped
        
    Raises:
        HTTPException: If signature validation fails
    """
    settings = get_settings()
    
    # Allow skipping validation for testing
    if settings.skip_webhook_signature_validation:
        logger.warning("⚠️  Skipping Twilio signature validation (testing mode)")
        return True
    
    # Get signature from header
    signature = request.headers.get("X-Twilio-Signature", "")
    if not signature:
        logger.error("Missing X-Twilio-Signature header")
        raise HTTPException(status_code=401, detail="Missing signature header")
    
    # Validate signature
    validator = RequestValidator(settings.twilio_auth_token)
    url = str(request.url)
    
    # Get form data as dict
    form_data = await request.form()
    params = {key: value for key, value in form_data.items()}
    
    is_valid = validator.validate(url, params, signature)
    
    if not is_valid:
        logger.error("❌ Invalid Twilio signature")
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    return True


@router.post("/inbound")
async def handle_inbound_call(
    request: Request,
    CallSid: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
    CallStatus: str = Form(None),
):
    """
    Handle inbound call from Twilio.
    
    Flow:
    1. Validate Twilio signature
    2. Extract caller information
    3. Start async voice cloning
    4. Return TwiML with greeting + music
    5. Redirect to status-callback for completion check
    
    Args:
        request: FastAPI request object
        CallSid: Twilio call SID
        From: Caller phone number
        To: Twilio phone number called
        CallStatus: Call status (ringing, in-progress, etc.)
        
    Returns:
        TwiML XML response
    """
    try:
        # Validate signature
        await validate_twilio_signature(request)
        
        # Set logging context
        set_call_context(CallSid, From)
        
        logger.info(f"📞 Inbound call: {CallSid} from {From} to {To} (status: {CallStatus})")
        
        # Start async voice cloning workflow
        asyncio.create_task(
            async_service.start_clone_async(
                call_sid=CallSid,
                caller_number=From,
                twilio_number=To
            )
        )
        
        # Generate TwiML response with greeting
        settings = get_settings()
        response = VoiceResponse()
        
        # Play greeting message
        response.say(
            settings.greeting_message,
            voice="alice",
            language="en-US"
        )
        
        # Play hold music while cloning (if enabled)
        if settings.greeting_music_enabled and settings.greeting_music_url:
            response.play(settings.greeting_music_url, loop=10)
        else:
            # Fallback: pause for max wait time
            response.pause(length=settings.clone_max_wait_seconds)
        
        # Redirect to status callback to check if clone is ready
        response.redirect(
            url=f"/webhooks/status-callback?call_sid={CallSid}",
            method="POST"
        )
        
        logger.info(f"✅ TwiML response sent for {CallSid} (greeting initiated)")
        
        return Response(content=str(response), media_type="application/xml")
        
    except HTTPException:
        raise
    except ValidationException as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error handling inbound call: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/status-callback")
async def handle_status_callback(
    request: Request,
    call_sid: str = Form(None),
    CallSid: str = Form(None),
):
    """
    Twilio polls this endpoint to check if voice clone is ready.
    
    Returns:
    - If clone ready: TwiML with <Connect><Stream> to ElevenLabs
    - If still processing: TwiML to continue waiting (redirect back)
    - If failed: TwiML to hangup with error message
    
    Args:
        request: FastAPI request object
        call_sid: Call SID from query parameter
        CallSid: Call SID from form data
        
    Returns:
        TwiML XML response
    """
    try:
        # Validate signature
        await validate_twilio_signature(request)
        
        # Get call_sid from either query param or form data
        sid = call_sid or CallSid
        if not sid:
            raise HTTPException(status_code=400, detail="Missing call_sid parameter")
        
        logger.info(f"🔍 Status callback for {sid}")
        
        # Check clone status
        clone_status = await db_service.get_clone_status(sid)
        
        response = VoiceResponse()
        settings = get_settings()
        
        if clone_status and clone_status["status"] == "completed":
            logger.info(f"✅ Clone ready for {sid}, connecting to ElevenLabs")
            
            # Connect to ElevenLabs WebSocket
            connect = Connect()
            stream = Stream(
                url=f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={settings.elevenlabs_agent_id}",
                track="inbound_track"
            )
            
            # Pass voice clone ID to ElevenLabs
            stream.parameter(name="voice_id", value=clone_status["voice_clone_id"])
            stream.parameter(name="api_key", value=settings.elevenlabs_api_key)
            
            connect.append(stream)
            response.append(connect)
            
        elif clone_status and clone_status["status"] == "processing":
            logger.info(f"⏳ Clone still processing for {sid}, continuing to wait")
            
            # Continue playing music/waiting
            if settings.greeting_music_enabled and settings.greeting_music_url:
                response.play(settings.greeting_music_url, loop=5)
            else:
                response.pause(length=10)
            
            # Redirect back to check again
            response.redirect(
                url=f"/webhooks/status-callback?call_sid={sid}",
                method="POST"
            )
            
        else:  # failed, timeout, or not found
            error_msg = clone_status.get("error", "Unknown error") if clone_status else "Clone not found"
            logger.error(f"❌ Clone failed for {sid}: {error_msg}")
            
            # Error message and hangup
            response.say(
                "We're sorry, we encountered an error preparing your call. Please try again later.",
                voice="alice"
            )
            response.hangup()
        
        return Response(content=str(response), media_type="application/xml")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in status callback: {e}")
        
        # Return error TwiML
        response = VoiceResponse()
        response.say("We're sorry, an error occurred. Goodbye.", voice="alice")
        response.hangup()
        return Response(content=str(response), media_type="application/xml")

