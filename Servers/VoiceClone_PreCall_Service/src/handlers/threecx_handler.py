"""
3CX webhook handler for incoming call notifications.
"""

from datetime import datetime
from typing import Dict, Any

from src.models.webhook_models import ThreeCXWebhookPayload, IncomingCallResponse
from src.services.voice_clone_async_service import VoiceCloneAsyncService
from src.utils.logger import get_logger, set_call_context
from src.utils.exceptions import ValidationException

logger = get_logger(__name__)


class ThreeCXHandler:
    """
    Handles incoming call webhooks from 3CX PBX.
    """
    
    def __init__(self, async_service: VoiceCloneAsyncService):
        """
        Initialize 3CX handler.
        
        Args:
            async_service: Async voice cloning service
        """
        self.async_service = async_service
    
    async def handle_incoming_call(
        self,
        payload: ThreeCXWebhookPayload
    ) -> IncomingCallResponse:
        """
        Handle incoming call webhook from 3CX.
        
        Args:
            payload: Webhook payload from 3CX
            
        Returns:
            IncomingCallResponse with status and call IDs
            
        Raises:
            ValidationException: If payload is invalid
        """
        try:
            # Set logging context
            set_call_context(payload.call_id, payload.caller_id)
            
            logger.info(f"Received incoming call from {payload.caller_id} (3CX call: {payload.call_id})")
            
            # Validate event type
            if payload.event_type not in ["IncomingCall", "CallStateChanged"]:
                logger.warning(f"Ignoring non-incoming call event: {payload.event_type}")
                raise ValidationException(f"Invalid event type: {payload.event_type}")
            
            # Validate direction
            if payload.direction != "In":
                logger.warning(f"Ignoring outbound call: {payload.direction}")
                raise ValidationException(f"Invalid direction: {payload.direction}")
            
            # Trigger async voice cloning workflow
            result = await self.async_service.handle_incoming_call_async(
                caller_id=payload.caller_id,
                threecx_call_id=payload.call_id,
            )
            
            # Return response
            return IncomingCallResponse(
                status="success",
                call_id=result["greeting_call_id"],
                cloned_voice_id="pending",  # Will be set asynchronously
                threecx_call_id=payload.call_id,
                message="Greeting initiated, voice cloning in progress"
            )
            
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Error handling incoming call: {e}")
            raise
    
    async def handle_call_ended(
        self,
        payload: ThreeCXWebhookPayload
    ) -> Dict[str, Any]:
        """
        Handle call ended webhook from 3CX.
        
        Args:
            payload: Webhook payload from 3CX
            
        Returns:
            Status dictionary
        """
        try:
            logger.info(f"Call ended: {payload.call_id} (duration: {payload.duration}s)")
            
            # Could log call metadata to database here
            # For now, just acknowledge
            
            return {
                "status": "acknowledged",
                "call_id": payload.call_id,
            }
            
        except Exception as e:
            logger.error(f"Error handling call ended: {e}")
            raise
