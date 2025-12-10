"""
Async voice cloning service with Twilio integration.

Implements the async voice cloning pattern for Twilio TwiML-based call flow.
"""

import asyncio
import time
from typing import Optional, Dict, Any

from src.services.voice_clone_service import VoiceCloneService
from src.services.elevenlabs_client import ElevenLabsService
from src.services.database_service import DatabaseService
from src.config import get_settings
from src.utils.logger import get_logger, set_call_context
from src.utils.exceptions import VoiceCloneTimeoutException

logger = get_logger(__name__)


class VoiceCloneAsyncService:
    """
    Async voice cloning for Twilio integration.
    
    Handles voice cloning in background while Twilio plays greeting.
    """
    
    def __init__(
        self,
        voice_clone_service: VoiceCloneService,
        elevenlabs_service: ElevenLabsService,
        db_service: DatabaseService,
    ):
        """
        Initialize async voice clone service.
        
        Args:
            voice_clone_service: Voice cloning orchestration service
            elevenlabs_service: ElevenLabs API client
            db_service: Database service
        """
        self.voice_clone = voice_clone_service
        self.elevenlabs = elevenlabs_service
        self.db = db_service
        self.settings = get_settings()
    
    async def start_clone_async(
        self,
        call_sid: str,
        caller_number: str,
        twilio_number: str,
    ) -> None:
        """
        Start async voice cloning for Twilio inbound call.
        
        Flow:
        1. Save call to database with status="processing"
        2. Retrieve voice sample for caller_number
        3. Start cloning in background task
        4. When complete: update database status="completed"
        5. Twilio polls /status-callback to detect completion
        
        Args:
            call_sid: Twilio call SID
            caller_number: Caller phone number (E.164)
            twilio_number: Twilio number that was called
        """
        try:
            # Set logging context
            set_call_context(call_sid, caller_number)
            
            logger.info(f"📞 Starting async clone for {call_sid} from {caller_number}")
            
            # Save initial call record
            await self.db.save_call_record(
                call_sid=call_sid,
                caller_number=caller_number,
                twilio_number=twilio_number,
                status="processing"
            )
            
            # Start background cloning task
            asyncio.create_task(
                self._clone_and_update(
                    call_sid=call_sid,
                    caller_number=caller_number
                )
            )
            
        except Exception as e:
            logger.error(f"Error starting async clone for {call_sid}: {e}")
            # Don't raise - we want TwiML response to be sent
            # Error will be logged and status will remain in processing
    
    async def _clone_and_update(
        self,
        call_sid: str,
        caller_number: str,
    ) -> None:
        """
        Background task: clone voice and update status in database.
        
        Args:
            call_sid: Twilio call SID
            caller_number: Caller phone number
        """
        start_time = time.time()
        
        try:
            logger.info(f"🎤 Cloning voice for {caller_number} (call {call_sid})")
            
            # Clone voice with timeout
            clone_task = self.voice_clone.get_or_create_clone(caller_number)
            cloned_voice_id = await asyncio.wait_for(
                clone_task,
                timeout=self.settings.clone_max_wait_seconds
            )
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.info(f"✅ Voice clone ready: {cloned_voice_id} ({elapsed_ms}ms)")
            
            # Update database with completed status
            await self.db.update_clone_status(
                call_sid=call_sid,
                status="completed",
                voice_clone_id=cloned_voice_id,
                clone_duration_ms=elapsed_ms
            )
            
            # Log clone ready event
            await self.db.log_clone_ready_event(
                caller_id=caller_number,
                greeting_call_id=call_sid,
                cloned_voice_id=cloned_voice_id,
                clone_duration_ms=elapsed_ms,
            )
            
        except asyncio.TimeoutError:
            elapsed_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Voice clone timeout after {elapsed_ms}ms"
            logger.error(f"❌ {error_msg} for {call_sid}")
            
            # Update database with failed status
            await self.db.update_clone_status(
                call_sid=call_sid,
                status="failed",
                error=error_msg
            )
            
            # Log failure event
            await self.db.log_clone_failed_event(
                caller_id=caller_number,
                greeting_call_id=call_sid,
                error_message=error_msg,
            )
            
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Voice clone failed: {str(e)}"
            logger.error(f"❌ {error_msg} for {call_sid}")
            
            # Update database with failed status
            await self.db.update_clone_status(
                call_sid=call_sid,
                status="failed",
                error=error_msg
            )
            
            # Log failure event
            await self.db.log_clone_failed_event(
                caller_id=caller_number,
                greeting_call_id=call_sid,
                error_message=error_msg,
            )
