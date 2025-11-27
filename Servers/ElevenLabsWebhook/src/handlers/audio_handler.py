"""
Handler for post_call_audio webhooks.

Handles:
- Chunked/streaming requests
- Base64 audio decoding
- Optional audio file storage
- Large file processing
"""

import base64
import logging
from typing import Dict, Any, Optional

from src.models.webhook_models import AudioPayload
from src.utils.storage import StorageManager

logger = logging.getLogger(__name__)


class AudioHandler:
    """Handler for post_call_audio webhook events."""
    
    def __init__(self, storage: Optional[StorageManager] = None):
        """
        Initialize handler.
        
        Args:
            storage: Optional storage manager for persisting audio files
        """
        self.storage = storage or StorageManager.from_env()
    
    async def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a post_call_audio webhook payload.
        
        Args:
            payload: Raw webhook payload dictionary
            
        Returns:
            Processing result dictionary
        """
        logger.info("Processing post_call_audio webhook")
        
        try:
            # Parse payload into typed model
            audio = AudioPayload.from_dict(payload)
            
            # Calculate audio size
            audio_size = self._calculate_audio_size(audio.audio_base64)
            
            logger.info(
                f"Audio received - "
                f"conversation_id: {audio.conversation_id}, "
                f"agent_id: {audio.agent_id}, "
                f"format: {audio.audio_format}, "
                f"size: {audio_size} bytes"
            )
            
            # Store audio if storage is enabled
            saved_path = self.storage.save_audio(
                conversation_id=audio.conversation_id,
                agent_id=audio.agent_id,
                audio_base64=audio.audio_base64,
                audio_format=audio.audio_format
            )
            
            return {
                "status": "processed",
                "conversation_id": audio.conversation_id,
                "agent_id": audio.agent_id,
                "audio_format": audio.audio_format,
                "audio_size_bytes": audio_size,
                "saved_path": saved_path
            }
            
        except Exception as e:
            logger.exception(f"Error processing audio: {e}")
            raise
    
    def _calculate_audio_size(self, audio_base64: str) -> int:
        """
        Calculate the decoded size of base64 audio data.
        
        Args:
            audio_base64: Base64-encoded audio string
            
        Returns:
            Size in bytes of decoded audio
        """
        if not audio_base64:
            return 0
        
        try:
            # Base64 encoding increases size by ~33%
            # Actual decoded size = (len * 3) / 4 - padding
            padding = audio_base64.count("=")
            return (len(audio_base64) * 3) // 4 - padding
        except Exception:
            return 0
    
    def decode_audio(self, audio_base64: str) -> bytes:
        """
        Decode base64 audio data.
        
        Args:
            audio_base64: Base64-encoded audio string
            
        Returns:
            Decoded audio bytes
            
        Raises:
            ValueError: If decoding fails
        """
        try:
            return base64.b64decode(audio_base64)
        except Exception as e:
            logger.error(f"Failed to decode audio: {e}")
            raise ValueError(f"Invalid base64 audio data: {e}")
