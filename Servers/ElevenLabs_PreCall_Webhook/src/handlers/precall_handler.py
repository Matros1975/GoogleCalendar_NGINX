"""
Pre-call webhook handler.
"""

import logging
import time
from typing import Dict, Any

from src.services.voice_cloning_service import VoiceCloningService
from src.utils.file_handler import FileHandler
from src.utils.logger import conversation_context

logger = logging.getLogger(__name__)


class PreCallHandler:
    """Handles pre-call webhook events."""
    
    def __init__(
        self,
        voice_cloning_service: VoiceCloningService,
        file_handler: FileHandler,
        default_first_message: str = None
    ):
        """
        Initialize pre-call handler.
        
        Args:
            voice_cloning_service: Voice cloning service
            file_handler: File handler for voice samples
            default_first_message: Template for agent's first message
        """
        self.voice_service = voice_cloning_service
        self.file_handler = file_handler
        self.default_first_message = default_first_message or "Hello {name}, thank you for calling!"
    
    async def handle(self, payload: Dict[str, Any], voice_sample_bytes: bytes = None) -> Dict[str, Any]:
        """
        Handle pre-call webhook event.
        
        Args:
            payload: Webhook payload
            voice_sample_bytes: Optional pre-decoded voice sample bytes
            
        Returns:
            Processing result
            
        Raises:
            ValueError: If payload is invalid or processing fails
        """
        start_time = time.time()
        
        # Extract fields
        conversation_id = payload.get("conversation_id", "unknown")
        agent_id = payload.get("agent_id")
        caller_metadata = payload.get("caller_metadata", {})
        voice_sample_data = payload.get("voice_sample", {})
        
        # Set conversation context for logging
        conversation_context.set(conversation_id)
        
        logger.info(
            "Pre-call webhook received",
            extra={
                "conversation_id": conversation_id,
                "agent_id": agent_id,
                "event_type": "webhook_received"
            }
        )
        
        # Validate required fields
        if not agent_id:
            raise ValueError("Missing required field: agent_id")
        
        # Extract or decode voice sample
        if voice_sample_bytes is None:
            # Try to get from payload
            if voice_sample_data and voice_sample_data.get("data"):
                try:
                    voice_sample_bytes = self.file_handler.decode_base64_audio(
                        voice_sample_data["data"]
                    )
                except Exception as e:
                    raise ValueError(f"Failed to decode voice sample: {str(e)}")
            else:
                raise ValueError("Missing voice sample data")
        
        # Process pre-call workflow
        try:
            result = await self.voice_service.process_precall_webhook(
                conversation_id=conversation_id,
                agent_id=agent_id,
                voice_sample=voice_sample_bytes,
                caller_metadata=caller_metadata,
                default_first_message=self.default_first_message
            )
            
            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                "Pre-call webhook processed successfully",
                extra={
                    "conversation_id": conversation_id,
                    "voice_id": result.get("voice_id"),
                    "processing_time_ms": processing_time_ms,
                    "event_type": "webhook_complete"
                }
            )
            
            return {
                "conversation_id": conversation_id,
                "voice_id": result["voice_id"],
                "voice_name": result["voice_name"],
                "agent_updated": result["agent_updated"],
                "caller_info": result["caller_info"],
                "processing_time_ms": processing_time_ms
            }
            
        except Exception as e:
            logger.error(
                f"Pre-call webhook processing failed: {str(e)}",
                extra={
                    "conversation_id": conversation_id,
                    "event_type": "webhook_failed"
                }
            )
            raise
