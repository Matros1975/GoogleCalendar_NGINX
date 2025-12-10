"""
Async voice cloning service with greeting workflow.

Implements the async greeting pattern to eliminate wait time during voice cloning.
"""

import asyncio
import time
from typing import Optional

from src.services.voice_clone_service import VoiceCloneService
from src.services.elevenlabs_client import ElevenLabsService
from src.services.database_service import DatabaseService
from src.config import get_settings
from src.utils.logger import get_logger, set_call_context
from src.utils.exceptions import VoiceCloneTimeoutException

logger = get_logger(__name__)


class VoiceCloneAsyncService:
    """
    Async voice cloning with prerecorded greeting workflow.
    
    Eliminates perceived wait time by playing greeting while cloning voice.
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
    
    async def handle_incoming_call_async(
        self,
        caller_id: str,
        threecx_call_id: str,
    ) -> dict:
        """
        Handle incoming call with async greeting workflow.
        
        Workflow:
        1. Immediately trigger greeting with hold music
        2. Clone voice asynchronously in background
        3. When clone ready, trigger voice agent call
        4. Log all events for analytics
        
        Args:
            caller_id: Caller phone number
            threecx_call_id: 3CX call ID
            
        Returns:
            Dictionary with greeting_call_id and status
        """
        try:
            # Set logging context
            set_call_context(threecx_call_id, caller_id)
            
            # Step 1: Trigger greeting immediately (100ms target)
            logger.info(f"Triggering greeting for caller {caller_id}")
            greeting_call_id = await self._trigger_greeting(caller_id)
            
            # Step 2: Clone voice asynchronously
            logger.info(f"Starting async voice clone for caller {caller_id}")
            clone_task = asyncio.create_task(
                self._clone_voice_async(
                    caller_id=caller_id,
                    greeting_call_id=greeting_call_id,
                    threecx_call_id=threecx_call_id,
                )
            )
            
            # Return immediately - cloning happens in background
            return {
                "status": "greeting_initiated",
                "greeting_call_id": greeting_call_id,
                "threecx_call_id": threecx_call_id,
                "caller_id": caller_id,
            }
            
        except Exception as e:
            logger.error(f"Error handling async call for {caller_id}: {e}")
            raise
    
    async def _trigger_greeting(self, caller_id: str) -> str:
        """
        Trigger prerecorded greeting with hold music.
        
        Args:
            caller_id: Caller phone number
            
        Returns:
            greeting_call_id: ElevenLabs call ID for greeting
        """
        try:
            # Use configured greeting voice
            greeting_voice_id = self.settings.greeting_voice_id
            
            # Build custom variables with greeting message
            custom_variables = {
                "greeting_message": self.settings.greeting_message,
                "play_music": self.settings.greeting_music_enabled,
            }
            
            if self.settings.greeting_music_enabled and self.settings.greeting_music_url:
                custom_variables["music_url"] = self.settings.greeting_music_url
            
            # Trigger greeting call
            greeting_call_id = await self.elevenlabs.trigger_voice_agent_call(
                phone_number=caller_id,
                voice_id=greeting_voice_id,
                custom_variables=custom_variables,
            )
            
            logger.info(f"Greeting triggered: {greeting_call_id}")
            return greeting_call_id
            
        except Exception as e:
            logger.error(f"Error triggering greeting: {e}")
            raise
    
    async def _clone_voice_async(
        self,
        caller_id: str,
        greeting_call_id: str,
        threecx_call_id: str,
    ) -> None:
        """
        Clone voice asynchronously in background.
        
        Args:
            caller_id: Caller phone number
            greeting_call_id: Greeting call ID
            threecx_call_id: 3CX call ID
        """
        start_time = time.time()
        
        try:
            # Clone voice with timeout
            clone_task = self.voice_clone.get_or_create_clone(caller_id)
            cloned_voice_id = await asyncio.wait_for(
                clone_task,
                timeout=self.settings.clone_max_wait_seconds
            )
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.info(f"Voice clone ready: {cloned_voice_id} ({elapsed_ms}ms)")
            
            # Log clone ready event
            await self.db.log_clone_ready_event(
                caller_id=caller_id,
                greeting_call_id=greeting_call_id,
                cloned_voice_id=cloned_voice_id,
                clone_duration_ms=elapsed_ms,
            )
            
            # Trigger voice agent call if auto-transition enabled
            if self.settings.auto_transition_enabled:
                await self._transfer_to_agent(
                    caller_id=caller_id,
                    greeting_call_id=greeting_call_id,
                    cloned_voice_id=cloned_voice_id,
                    threecx_call_id=threecx_call_id,
                )
            
        except asyncio.TimeoutError:
            elapsed_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Voice clone timeout after {elapsed_ms}ms"
            logger.error(error_msg)
            
            # Log failure event
            await self.db.log_clone_failed_event(
                caller_id=caller_id,
                greeting_call_id=greeting_call_id,
                error_message=error_msg,
            )
            
            # Fall back to default voice
            await self._fallback_to_default_voice(
                caller_id=caller_id,
                threecx_call_id=threecx_call_id,
            )
            
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Voice clone failed: {str(e)}"
            logger.error(error_msg)
            
            # Log failure event
            await self.db.log_clone_failed_event(
                caller_id=caller_id,
                greeting_call_id=greeting_call_id,
                error_message=error_msg,
            )
            
            # Fall back to default voice
            await self._fallback_to_default_voice(
                caller_id=caller_id,
                threecx_call_id=threecx_call_id,
            )
    
    async def _transfer_to_agent(
        self,
        caller_id: str,
        greeting_call_id: str,
        cloned_voice_id: str,
        threecx_call_id: str,
    ) -> None:
        """
        Transfer call from greeting to voice agent with cloned voice.
        
        Args:
            caller_id: Caller phone number
            greeting_call_id: Original greeting call ID
            cloned_voice_id: Cloned voice ID to use
            threecx_call_id: 3CX call ID
        """
        try:
            logger.info(f"Transferring to voice agent with cloned voice: {cloned_voice_id}")
            
            # Trigger voice agent call with cloned voice
            agent_call_id = await self.elevenlabs.trigger_voice_agent_call(
                phone_number=caller_id,
                voice_id=cloned_voice_id,
                custom_variables={
                    "threecx_call_id": threecx_call_id,
                    "caller_id": caller_id,
                }
            )
            
            # Log transfer event
            await self.db.log_clone_transfer_event(
                greeting_call_id=greeting_call_id,
                agent_call_id=agent_call_id,
                cloned_voice_id=cloned_voice_id,
            )
            
            # Log call initiation
            await self.db.log_call_initiated(
                call_id=agent_call_id,
                threecx_call_id=threecx_call_id,
                caller_id=caller_id,
                cloned_voice_id=cloned_voice_id,
            )
            
            logger.info(f"Successfully transferred to agent call: {agent_call_id}")
            
        except Exception as e:
            logger.error(f"Error transferring to agent: {e}")
            raise
    
    async def _fallback_to_default_voice(
        self,
        caller_id: str,
        threecx_call_id: str,
    ) -> None:
        """
        Fall back to default voice if cloning fails.
        
        Args:
            caller_id: Caller phone number
            threecx_call_id: 3CX call ID
        """
        try:
            logger.info("Falling back to default voice")
            
            # Use greeting voice as fallback
            default_voice_id = self.settings.greeting_voice_id
            
            # Trigger call with default voice
            call_id = await self.elevenlabs.trigger_voice_agent_call(
                phone_number=caller_id,
                voice_id=default_voice_id,
                custom_variables={
                    "threecx_call_id": threecx_call_id,
                    "fallback_mode": True,
                }
            )
            
            # Log call
            await self.db.log_call_initiated(
                call_id=call_id,
                threecx_call_id=threecx_call_id,
                caller_id=caller_id,
                cloned_voice_id=default_voice_id,
            )
            
            logger.info(f"Fallback call initiated: {call_id}")
            
        except Exception as e:
            logger.error(f"Error in fallback to default voice: {e}")
