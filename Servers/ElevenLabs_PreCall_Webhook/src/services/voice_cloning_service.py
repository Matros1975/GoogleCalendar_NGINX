"""
Voice cloning service orchestrator.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

from src.services.elevenlabs_client import ElevenLabsAPIClient
from src.utils.file_handler import FileHandler

logger = logging.getLogger(__name__)


class VoiceCloningService:
    """Orchestrates voice cloning workflow."""
    
    def __init__(
        self,
        elevenlabs_client: ElevenLabsAPIClient,
        file_handler: FileHandler,
        min_duration: float = 3.0,
        max_size_mb: float = 10.0
    ):
        """
        Initialize voice cloning service.
        
        Args:
            elevenlabs_client: ElevenLabs API client
            file_handler: File handler for voice samples
            min_duration: Minimum audio duration in seconds
            max_size_mb: Maximum file size in MB
        """
        self.client = elevenlabs_client
        self.file_handler = file_handler
        self.min_duration = min_duration
        self.max_size_mb = max_size_mb
    
    async def process_precall_webhook(
        self,
        conversation_id: str,
        agent_id: str,
        voice_sample: bytes,
        caller_metadata: Dict[str, Any],
        default_first_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete pre-call processing workflow.
        
        1. Validate voice sample
        2. Create instant voice clone
        3. Update agent configuration
        4. Return caller metadata
        
        Args:
            conversation_id: Conversation identifier
            agent_id: Agent identifier
            voice_sample: Audio bytes
            caller_metadata: Caller information
            default_first_message: Template for first message
            
        Returns:
            Processing result with voice_id and caller_info
            
        Raises:
            ValueError: If voice sample validation fails
            Exception: If API calls fail
        """
        logger.info(
            f"Starting pre-call processing",
            extra={
                "conversation_id": conversation_id,
                "agent_id": agent_id,
                "event_type": "voice_clone_start"
            }
        )
        
        # Step 1: Validate voice sample
        is_valid, error_message = self.validate_voice_sample(
            voice_sample,
            self.min_duration,
            self.max_size_mb
        )
        
        if not is_valid:
            logger.error(
                f"Voice sample validation failed: {error_message}",
                extra={"conversation_id": conversation_id}
            )
            raise ValueError(error_message)
        
        # Step 2: Generate voice name
        caller_name = caller_metadata.get("name", "Unknown")
        voice_name = self.generate_voice_name(caller_name, conversation_id)
        
        # Step 3: Create instant voice clone
        try:
            voice_response = await self.client.create_instant_voice(
                voice_sample=voice_sample,
                voice_name=voice_name,
                description=f"Instant clone for conversation {conversation_id}",
                labels={
                    "conversation_id": conversation_id,
                    "type": "instant_clone"
                }
            )
            
            voice_id = voice_response.voice_id
            
            logger.info(
                f"Voice cloned successfully: {voice_id}",
                extra={
                    "conversation_id": conversation_id,
                    "voice_id": voice_id,
                    "event_type": "voice_clone_success"
                }
            )
            
        except Exception as e:
            logger.error(
                f"Voice cloning failed: {str(e)}",
                extra={
                    "conversation_id": conversation_id,
                    "event_type": "voice_clone_failed"
                }
            )
            raise
        
        # Step 4: Update agent configuration
        try:
            # Generate personalized first message
            first_message = None
            if default_first_message and caller_name:
                first_message = default_first_message.format(name=caller_name)
            
            await self.client.update_agent_voice(
                agent_id=agent_id,
                voice_id=voice_id,
                first_message=first_message
            )
            
            logger.info(
                f"Agent updated successfully",
                extra={
                    "conversation_id": conversation_id,
                    "agent_id": agent_id,
                    "voice_id": voice_id,
                    "event_type": "agent_update_success"
                }
            )
            
            agent_updated = True
            
        except Exception as e:
            logger.error(
                f"Agent update failed: {str(e)}",
                extra={
                    "conversation_id": conversation_id,
                    "event_type": "agent_update_failed"
                }
            )
            # Continue even if agent update fails - voice was created
            agent_updated = False
        
        # Step 5: Format caller info for response
        caller_info = {}
        if caller_metadata.get("name"):
            caller_info["Name"] = caller_metadata["name"]
        if caller_metadata.get("date_of_birth"):
            caller_info["DateOfBirth"] = caller_metadata["date_of_birth"]
        
        return {
            "voice_id": voice_id,
            "voice_name": voice_name,
            "agent_updated": agent_updated,
            "caller_info": caller_info
        }
    
    def validate_voice_sample(
        self,
        audio_data: bytes,
        min_duration: float = 3.0,
        max_size_mb: float = 10.0
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate voice sample quality.
        
        Args:
            audio_data: Audio bytes
            min_duration: Minimum duration in seconds
            max_size_mb: Maximum size in MB
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate size
        is_valid, error_msg = self.file_handler.validate_audio_size(audio_data, max_size_mb)
        if not is_valid:
            return False, error_msg
        
        # Validate format
        audio_format = self.file_handler.get_audio_format(audio_data)
        if audio_format == "unknown":
            return False, "Unsupported audio format (must be WAV, MP3, or OGG)"
        
        # Note: We can't easily validate duration without decoding the audio
        # This would require additional dependencies like pydub or soundfile
        # For now, we rely on ElevenLabs API to validate duration
        
        # Validate minimum size (rough check for duration)
        # Assuming ~16kbps MP3, 3 seconds ≈ 6KB minimum
        min_size_bytes = 5000  # 5KB minimum
        if len(audio_data) < min_size_bytes:
            return False, f"Audio sample too short (minimum {min_duration} seconds required)"
        
        logger.debug(f"Voice sample validation passed: {audio_format}, {len(audio_data)} bytes")
        return True, None
    
    def generate_voice_name(
        self,
        caller_name: str,
        conversation_id: str
    ) -> str:
        """
        Generate unique voice name.
        
        Args:
            caller_name: Caller's name
            conversation_id: Conversation identifier
            
        Returns:
            Unique voice name
        """
        # Clean caller name (remove special characters)
        safe_name = "".join(c for c in caller_name if c.isalnum() or c in (' ', '-', '_'))
        safe_name = safe_name.replace(' ', '_')[:20]  # Limit length
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Add conversation ID suffix (last 8 chars)
        conv_suffix = conversation_id[-8:] if len(conversation_id) >= 8 else conversation_id
        
        voice_name = f"{safe_name}_Clone_{timestamp}_{conv_suffix}"
        
        logger.debug(f"Generated voice name: {voice_name}")
        return voice_name
