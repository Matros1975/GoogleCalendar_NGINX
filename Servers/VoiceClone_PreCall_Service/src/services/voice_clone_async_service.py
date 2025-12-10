"""
Async voice cloning service with greeting workflow.

Implements the asynchronous greeting pattern:
1. Immediately trigger greeting call with background music
2. Clone voice asynchronously while greeting plays
3. Automatically transition to voice agent when clone is ready
"""

import asyncio
import logging
import time
from typing import Optional
from datetime import datetime

from src.services.database_service import DatabaseService
from src.services.voice_clone_service import VoiceCloneService
from src.services.elevenlabs_client import ElevenLabsClient
from src.utils.exceptions import (
    GreetingCallException,
    VoiceCloneException,
    CloneTimeoutException
)
from src.config import get_settings

logger = logging.getLogger(__name__)


class VoiceCloneAsyncService:
    """Manages async voice cloning with greeting workflow."""
    
    def __init__(
        self,
        database_service: DatabaseService,
        voice_clone_service: VoiceCloneService,
        elevenlabs_client: ElevenLabsClient
    ):
        """
        Initialize async voice clone service.
        
        Args:
            database_service: Database service instance
            voice_clone_service: Voice clone service instance
            elevenlabs_client: ElevenLabs API client
        """
        self.db = database_service
        self.voice_clone_service = voice_clone_service
        self.elevenlabs = elevenlabs_client
        self.settings = get_settings()
        
        # Track active clone operations
        self.active_clones: dict = {}
    
    async def process_incoming_call(
        self,
        caller_id: str,
        threecx_call_id: str
    ) -> dict:
        """
        Process incoming call with async greeting workflow.
        
        Implementation:
        1. Immediately trigger greeting call (< 100ms)
        2. Start async voice cloning task in background
        3. Return greeting call ID immediately
        4. Clone completes in background and triggers automatic transfer
        
        Args:
            caller_id: Caller phone number
            threecx_call_id: 3CX call ID
            
        Returns:
            Dictionary with greeting_call_id and status
            
        Raises:
            GreetingCallException: If greeting call fails
        """
        try:
            logger.info(
                f"Processing incoming call for {caller_id} "
                f"(3CX call: {threecx_call_id})"
            )
            
            # Step 1: Immediately trigger greeting call
            greeting_call_id = await self._trigger_greeting_call(
                caller_id=caller_id,
                threecx_call_id=threecx_call_id
            )
            
            logger.info(f"Greeting call initiated: {greeting_call_id}")
            
            # Step 2: Start async voice cloning in background
            # Do NOT await - let it run asynchronously
            asyncio.create_task(
                self._async_clone_and_transfer(
                    caller_id=caller_id,
                    threecx_call_id=threecx_call_id,
                    greeting_call_id=greeting_call_id
                )
            )
            
            # Step 3: Return immediately with greeting call ID
            return {
                "status": "success",
                "greeting_call_id": greeting_call_id,
                "message": "Greeting call initiated, cloning voice in background"
            }
            
        except Exception as e:
            logger.error(f"Failed to process incoming call for {caller_id}: {e}")
            raise GreetingCallException(f"Failed to process incoming call: {e}")
    
    async def _trigger_greeting_call(
        self,
        caller_id: str,
        threecx_call_id: str
    ) -> str:
        """
        Trigger greeting call with prerecorded message and music.
        
        Args:
            caller_id: Caller phone number
            threecx_call_id: 3CX call ID
            
        Returns:
            Greeting call ID
            
        Raises:
            GreetingCallException: If greeting call fails
        """
        try:
            # Use configured greeting voice and message
            greeting_voice_id = self.settings.greeting_voice_id
            greeting_message = self.settings.greeting_message
            
            # Trigger greeting call via ElevenLabs
            custom_variables = {
                "caller_id": caller_id,
                "threecx_call_id": threecx_call_id,
                "is_greeting": True,
                "message": greeting_message
            }
            
            # Add music URL if enabled
            if self.settings.greeting_music_enabled and self.settings.greeting_music_url:
                custom_variables["background_music_url"] = self.settings.greeting_music_url
            
            greeting_call_id = await self.elevenlabs.trigger_voice_agent_call(
                phone_number=caller_id,
                voice_id=greeting_voice_id,
                custom_variables=custom_variables
            )
            
            return greeting_call_id
            
        except Exception as e:
            logger.error(f"Failed to trigger greeting call for {caller_id}: {e}")
            raise GreetingCallException(f"Greeting call failed: {e}")
    
    async def _async_clone_and_transfer(
        self,
        caller_id: str,
        threecx_call_id: str,
        greeting_call_id: str
    ) -> None:
        """
        Asynchronously clone voice and trigger transfer when ready.
        
        This runs in background while greeting plays.
        
        Args:
            caller_id: Caller phone number
            threecx_call_id: 3CX call ID
            greeting_call_id: Greeting call ID
        """
        start_time = time.time()
        clone_task_id = f"{caller_id}_{int(start_time)}"
        
        try:
            logger.info(
                f"Starting async voice clone for {caller_id} "
                f"(task: {clone_task_id})"
            )
            
            # Track active clone
            self.active_clones[clone_task_id] = {
                "caller_id": caller_id,
                "started_at": start_time,
                "status": "cloning"
            }
            
            # Clone voice (this may take 5-30 seconds)
            cloned_voice_id = await self.voice_clone_service.get_or_create_clone(
                caller_id=caller_id
            )
            
            clone_duration_ms = int((time.time() - start_time) * 1000)
            logger.info(
                f"Voice clone ready: {cloned_voice_id} "
                f"for {caller_id} (took {clone_duration_ms}ms)"
            )
            
            # Log clone ready event
            await self.db.log_clone_ready(
                caller_id=caller_id,
                greeting_call_id=greeting_call_id,
                cloned_voice_id=cloned_voice_id,
                clone_duration_ms=clone_duration_ms
            )
            
            # Check if clone took longer than max wait
            if clone_duration_ms > (self.settings.clone_max_wait_seconds * 1000):
                logger.warning(
                    f"Clone creation exceeded max wait time: "
                    f"{clone_duration_ms}ms > {self.settings.clone_max_wait_seconds}s"
                )
            
            # Trigger automatic transfer if enabled
            if self.settings.auto_transition_enabled:
                await self._trigger_agent_call_with_clone(
                    caller_id=caller_id,
                    threecx_call_id=threecx_call_id,
                    greeting_call_id=greeting_call_id,
                    cloned_voice_id=cloned_voice_id
                )
            
            # Update active clone status
            self.active_clones[clone_task_id]["status"] = "completed"
            self.active_clones[clone_task_id]["cloned_voice_id"] = cloned_voice_id
            
        except CloneTimeoutException as e:
            logger.error(f"Clone creation timed out for {caller_id}: {e}")
            
            # Log failed event
            await self.db.log_clone_failed(
                caller_id=caller_id,
                greeting_call_id=greeting_call_id,
                error_message=f"Timeout: {str(e)}"
            )
            
            # Update active clone status
            self.active_clones[clone_task_id]["status"] = "timeout"
            
        except VoiceCloneException as e:
            logger.error(f"Clone creation failed for {caller_id}: {e}")
            
            # Log failed event
            await self.db.log_clone_failed(
                caller_id=caller_id,
                greeting_call_id=greeting_call_id,
                error_message=str(e)
            )
            
            # Update active clone status
            self.active_clones[clone_task_id]["status"] = "failed"
            
        except Exception as e:
            logger.exception(f"Unexpected error in async clone for {caller_id}: {e}")
            
            # Log failed event
            await self.db.log_clone_failed(
                caller_id=caller_id,
                greeting_call_id=greeting_call_id,
                error_message=f"Unexpected error: {str(e)}"
            )
            
            # Update active clone status
            self.active_clones[clone_task_id]["status"] = "error"
        
        finally:
            # Clean up after some time
            await asyncio.sleep(300)  # 5 minutes
            if clone_task_id in self.active_clones:
                del self.active_clones[clone_task_id]
    
    async def _trigger_agent_call_with_clone(
        self,
        caller_id: str,
        threecx_call_id: str,
        greeting_call_id: str,
        cloned_voice_id: str
    ) -> None:
        """
        Trigger voice agent call with cloned voice.
        
        This automatically transitions from greeting to cloned voice.
        
        Args:
            caller_id: Caller phone number
            threecx_call_id: 3CX call ID
            greeting_call_id: Greeting call ID
            cloned_voice_id: Cloned voice ID
        """
        try:
            logger.info(
                f"Triggering agent call with cloned voice {cloned_voice_id} "
                f"for {caller_id}"
            )
            
            # Trigger voice agent call
            custom_variables = {
                "caller_id": caller_id,
                "threecx_call_id": threecx_call_id,
                "greeting_call_id": greeting_call_id,
                "cloned_voice_id": cloned_voice_id
            }
            
            agent_call_id = await self.elevenlabs.trigger_voice_agent_call(
                phone_number=caller_id,
                voice_id=cloned_voice_id,
                custom_variables=custom_variables
            )
            
            logger.info(
                f"Agent call initiated: {agent_call_id} "
                f"(transitioning from greeting {greeting_call_id})"
            )
            
            # Log call initiation
            await self.db.log_call_initiated(
                call_id=agent_call_id,
                threecx_call_id=threecx_call_id,
                caller_id=caller_id,
                cloned_voice_id=cloned_voice_id
            )
            
            # Log transfer event
            await self.db.log_clone_transfer(
                greeting_call_id=greeting_call_id,
                agent_call_id=agent_call_id,
                cloned_voice_id=cloned_voice_id
            )
            
        except Exception as e:
            logger.error(
                f"Failed to trigger agent call for {caller_id}: {e}"
            )
            # Don't raise exception - greeting is still active
    
    async def get_clone_status(self, caller_id: str) -> dict:
        """
        Check status of ongoing clone operation.
        
        Args:
            caller_id: Caller phone number
            
        Returns:
            Dictionary with clone status
        """
        # Find active clone for caller
        for task_id, clone_info in self.active_clones.items():
            if clone_info["caller_id"] == caller_id:
                return {
                    "caller_id": caller_id,
                    "status": clone_info["status"],
                    "started_at": clone_info["started_at"],
                    "cloned_voice_id": clone_info.get("cloned_voice_id")
                }
        
        # Check if cached clone exists
        cached_voice_id = await self.voice_clone_service.get_cached_clone(caller_id)
        if cached_voice_id:
            return {
                "caller_id": caller_id,
                "status": "ready",
                "cloned_voice_id": cached_voice_id,
                "cached": True
            }
        
        return {
            "caller_id": caller_id,
            "status": "not_started"
        }
