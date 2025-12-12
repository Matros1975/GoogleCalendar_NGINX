"""
Twilio webhook handler for incoming call notifications.

Implements TwiML-based call control for Twilio integration.
"""

from typing import Dict, Any

from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
from twilio.request_validator import RequestValidator

from src.config import get_settings
from src.models.call_context import CallContext
from src.models.call_instructions import CallInstructions
from src.services.call_controller import CallController
from src.utils.logger import get_logger, set_call_context
from src.utils.exceptions import ValidationException

logger = get_logger(__name__)
router = APIRouter(prefix="/webhooks", tags=["twilio"])

# Global service instance (injected on startup)
call_controller: CallController = None


def init_handler(controller: CallController):
    """
    Initialize handler with call controller.
    
    Args:
        controller: Call controller for business logic
    """
    global call_controller
    call_controller = controller


def _convert_to_twiml(instructions: CallInstructions) -> VoiceResponse:
    """
    Convert protocol-agnostic CallInstructions to Twilio TwiML.
    
    Args:
        instructions: Call instructions from business logic
        
    Returns:
        TwiML VoiceResponse object
    """
    response = VoiceResponse()
    
    # Add greeting if present
    if instructions.greeting_audio:
        response.say(
            instructions.greeting_audio.text,
            voice=instructions.greeting_audio.voice,
            language=instructions.greeting_audio.language
        )
    
    # Add hold music if present
    if instructions.hold_audio:
        response.play(instructions.hold_audio.url, loop=instructions.hold_audio.loop)
    
    # Handle status polling
    if instructions.status_poll:
        response.redirect(
            url=instructions.status_poll.poll_url,
            method="POST"
        )
    
    # Handle WebSocket connection (completed state)
    if instructions.websocket:
        connect = Connect()
        stream = Stream(
            url=instructions.websocket.url,
            track=instructions.websocket.track
        )
        stream.parameter(name="voice_id", value=instructions.websocket.voice_id)
        stream.parameter(name="api_key", value=instructions.websocket.api_key)
        connect.append(stream)
        response.append(connect)
    
    # Handle error/hangup
    if instructions.error_message:
        response.say(instructions.error_message, voice="alice")
    
    if instructions.should_hangup:
        response.hangup()
    
    return response


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
    2. Create call context
    3. Get instructions from call controller
    4. Convert to TwiML and return
    
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
        
        # Create call context
        context = CallContext(
            call_id=CallSid,
            caller_number=From,
            recipient_number=To,
            status="in-progress" if CallStatus == "in-progress" else "initiated",
            protocol="twilio"
        )
        
        # Get instructions from controller
        instructions = await call_controller.handle_inbound_call(context)
        
        # Convert to TwiML
        twiml_response = _convert_to_twiml(instructions)
        
        logger.info(f"✅ TwiML response sent for {CallSid} (greeting initiated)")
        
        return Response(content=str(twiml_response), media_type="application/xml")
        
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
        
        # Get instructions from controller
        instructions = await call_controller.check_clone_status(sid)
        
        # Convert to TwiML
        twiml_response = _convert_to_twiml(instructions)
        
        return Response(content=str(twiml_response), media_type="application/xml")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in status callback: {e}")
        
        # Return error TwiML
        response = VoiceResponse()
        response.say("We're sorry, an error occurred. Goodbye.", voice="alice")
        response.hangup()
        return Response(content=str(response), media_type="application/xml")

