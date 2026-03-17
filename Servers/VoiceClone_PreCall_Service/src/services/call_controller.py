"""
Call controller for protocol-agnostic business logic.

Orchestrates voice cloning workflow independent of protocol (Twilio/SIP).
"""

import asyncio
from typing import Optional

from src.models.call_context import CallContext
from src.models.call_instructions import (
    CallInstructions,
    SpeechInstruction,
    AudioInstruction,
    StatusPollInstruction,
    WebSocketInstruction,
)
from src.services.voice_clone_async_service import VoiceCloneAsyncService
from src.services.database_service import DatabaseService
from src.config import get_settings
from src.utils.logger import get_logger, set_call_context

logger = get_logger(__name__)


class CallController:
    """
    Protocol-agnostic call controller.
    
    Contains business logic for voice cloning workflow that is independent
    of the underlying protocol (Twilio TwiML or SIP).
    """
    
    def __init__(
        self,
        voice_clone_service: VoiceCloneAsyncService,
        database_service: DatabaseService,
    ):
        """
        Initialize call controller.
        
        Args:
            voice_clone_service: Async voice cloning service
            database_service: Database service
        """
        self.voice_clone_service = voice_clone_service
        self.db_service = database_service
        self.settings = get_settings()
    
    async def handle_inbound_call(self, context: CallContext) -> CallInstructions:
        """
        Handle inbound call - start voice cloning and return initial instructions.
        
        Extracted from twilio_handler.py lines 85-168.
        
        Flow:
        1. Validate caller information
        2. Start async voice cloning in background
        3. Return instructions for greeting + hold music + status polling
        
        Args:
            context: Call context with caller information
            
        Returns:
            CallInstructions with greeting and hold music
        """
        try:
            # Set logging context
            set_call_context(context.call_id, context.caller_number)
            
            logger.info(
                f"📞 Inbound call: {context.call_id} from {context.caller_number} "
                f"to {context.recipient_number} (protocol: {context.protocol})"
            )
            
            # Start async voice cloning workflow
            asyncio.create_task(
                self.voice_clone_service.start_clone_async(
                    call_sid=context.call_id,
                    caller_number=context.caller_number,
                    twilio_number=context.recipient_number
                )
            )
            
            # Create greeting instruction
            greeting = SpeechInstruction(
                text=self.settings.greeting_message,
                voice="alice",
                language="en-US"
            )
            
            # Create hold music instruction (if enabled)
            hold_audio = None
            if self.settings.greeting_music_enabled and self.settings.greeting_music_url:
                hold_audio = AudioInstruction(
                    url=self.settings.greeting_music_url,
                    loop=10
                )
            
            # Create status poll instruction
            # Protocol handlers will convert this to their specific format
            status_poll = StatusPollInstruction(
                poll_url=f"/webhooks/status-callback?call_sid={context.call_id}",
                interval_seconds=10
            )
            
            instructions = CallInstructions(
                call_id=context.call_id,
                clone_status="processing",
                greeting_audio=greeting,
                hold_audio=hold_audio,
                status_poll=status_poll,
            )
            
            logger.info(f"✅ Initial instructions created for {context.call_id}")
            return instructions
            
        except Exception as e:
            logger.exception(f"Error handling inbound call {context.call_id}: {e}")
            
            # Return error instructions
            return CallInstructions(
                call_id=context.call_id,
                clone_status="failed",
                error_message="We're sorry, we encountered an error. Please try again later.",
                should_hangup=True,
            )
    
    async def check_clone_status(self, call_id: str) -> CallInstructions:
        """
        Check clone status and return appropriate instructions.
        
        Extracted from twilio_handler.py lines 171-270.
        
        Returns:
        - If processing: continue hold music + poll again
        - If completed: WebSocket connection instructions
        - If failed: error message + hangup
        
        Args:
            call_id: Call identifier (Twilio CallSid or SIP call ID)
            
        Returns:
            CallInstructions based on clone status
        """
        try:
            logger.info(f"🔍 Checking clone status for {call_id}")
            
            # Query database for clone status
            clone_status = await self.db_service.get_clone_status(call_id)
            
            if not clone_status:
                logger.error(f"❌ Clone status not found for {call_id}")
                return CallInstructions(
                    call_id=call_id,
                    clone_status="failed",
                    error_message="We're sorry, we couldn't find your call information.",
                    should_hangup=True,
                )
            
            status = clone_status["status"]
            
            if status == "completed":
                # Clone is ready - connect to ElevenLabs
                logger.info(f"✅ Clone ready for {call_id}, returning WebSocket instructions")
                
                voice_clone_id = clone_status["voice_clone_id"]
                
                # Create WebSocket connection instruction
                websocket = WebSocketInstruction(
                    url=f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={self.settings.elevenlabs_agent_id}",
                    voice_id=voice_clone_id,
                    api_key=self.settings.elevenlabs_api_key,
                    track="inbound_track"
                )
                
                return CallInstructions(
                    call_id=call_id,
                    clone_status="completed",
                    websocket=websocket,
                )
                
            elif status == "processing":
                # Still processing - continue waiting
                logger.info(f"⏳ Clone still processing for {call_id}")
                
                # Continue hold music
                hold_audio = None
                if self.settings.greeting_music_enabled and self.settings.greeting_music_url:
                    hold_audio = AudioInstruction(
                        url=self.settings.greeting_music_url,
                        loop=5
                    )
                
                # Poll again
                status_poll = StatusPollInstruction(
                    poll_url=f"/webhooks/status-callback?call_sid={call_id}",
                    interval_seconds=10
                )
                
                return CallInstructions(
                    call_id=call_id,
                    clone_status="processing",
                    hold_audio=hold_audio,
                    status_poll=status_poll,
                )
                
            else:  # failed, timeout, or unknown status
                error_msg = clone_status.get("error", "Unknown error")
                logger.error(f"❌ Clone failed for {call_id}: {error_msg}")
                
                return CallInstructions(
                    call_id=call_id,
                    clone_status="failed",
                    error_message="We're sorry, we encountered an error preparing your call. Please try again later.",
                    should_hangup=True,
                )
                
        except Exception as e:
            logger.exception(f"Error checking clone status for {call_id}: {e}")
            
            return CallInstructions(
                call_id=call_id,
                clone_status="failed",
                error_message="We're sorry, an error occurred. Goodbye.",
                should_hangup=True,
            )
