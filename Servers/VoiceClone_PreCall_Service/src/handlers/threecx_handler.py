"""
3CX webhook handler for incoming call notifications.

Processes incoming calls from 3CX PBX and initiates async voice cloning workflow.
"""

import logging
from typing import Dict, Any

from src.models.webhook_models import ThreeCXWebhookPayload, IncomingCallResponse
from src.services.voice_clone_async_service import VoiceCloneAsyncService
from src.utils.exceptions import GreetingCallException
from src.utils.logger import call_context

logger = logging.getLogger(__name__)


class ThreeCXHandler:
    """Handles 3CX webhook events."""
    
    def __init__(self, async_service: VoiceCloneAsyncService):
        """
        Initialize 3CX handler.
        
        Args:
            async_service: Async voice clone service instance
        """
        self.async_service = async_service
    
    async def handle(self, payload: ThreeCXWebhookPayload) -> IncomingCallResponse:
        """
        Handle incoming call webhook from 3CX.
        
        This method processes the webhook and initiates the async greeting workflow:
        1. Validates payload
        2. Triggers greeting call (immediate response)
        3. Starts async voice cloning in background
        4. Returns success response
        
        Args:
            payload: 3CX webhook payload
            
        Returns:
            IncomingCallResponse with greeting call details
            
        Raises:
            GreetingCallException: If greeting call initiation fails
        """
        try:
            # Set call context for logging
            call_context.set(payload.call_id)
            
            logger.info(
                f"Processing 3CX webhook: {payload.event_type} "
                f"for caller {payload.caller_id}"
            )
            
            # Only process IncomingCall events
            if payload.event_type != "IncomingCall":
                logger.warning(
                    f"Ignoring non-incoming call event: {payload.event_type}"
                )
                raise ValueError(f"Unsupported event type: {payload.event_type}")
            
            # Validate caller ID
            if not payload.caller_id:
                raise ValueError("Missing caller_id in webhook payload")
            
            # Process incoming call with async service
            result = await self.async_service.process_incoming_call(
                caller_id=payload.caller_id,
                threecx_call_id=payload.call_id
            )
            
            logger.info(
                f"Successfully processed incoming call from {payload.caller_id}: "
                f"greeting_call_id={result['greeting_call_id']}"
            )
            
            # Return response
            return IncomingCallResponse(
                status="success",
                call_id=result["greeting_call_id"],
                cloned_voice_id="pending",  # Clone is being created asynchronously
                threecx_call_id=payload.call_id,
                message=result.get("message", "Greeting call initiated successfully")
            )
            
        except GreetingCallException as e:
            logger.error(f"Greeting call failed: {e}")
            raise
        
        except ValueError as e:
            logger.error(f"Invalid webhook payload: {e}")
            raise
        
        except Exception as e:
            logger.exception(f"Unexpected error handling 3CX webhook: {e}")
            raise GreetingCallException(f"Unexpected error: {e}")
        
        finally:
            # Clear call context
            call_context.set("N/A")
    
    async def handle_call_state_changed(
        self,
        payload: ThreeCXWebhookPayload
    ) -> Dict[str, Any]:
        """
        Handle CallStateChanged event from 3CX.
        
        This can be used to track call progress and transitions.
        
        Args:
            payload: 3CX webhook payload
            
        Returns:
            Dictionary with processing result
        """
        try:
            call_context.set(payload.call_id)
            
            logger.info(
                f"Call state changed for {payload.caller_id}: "
                f"3CX call {payload.call_id}"
            )
            
            # Log event (can be extended for state tracking)
            return {
                "status": "acknowledged",
                "message": "Call state change logged"
            }
            
        except Exception as e:
            logger.error(f"Error handling call state change: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
        
        finally:
            call_context.set("N/A")
    
    async def handle_call_ended(
        self,
        payload: ThreeCXWebhookPayload
    ) -> Dict[str, Any]:
        """
        Handle CallEnded event from 3CX.
        
        This can be used for cleanup and analytics.
        
        Args:
            payload: 3CX webhook payload
            
        Returns:
            Dictionary with processing result
        """
        try:
            call_context.set(payload.call_id)
            
            logger.info(
                f"Call ended for {payload.caller_id}: "
                f"3CX call {payload.call_id}, duration: {payload.duration}s"
            )
            
            # Log event (can be extended for analytics)
            return {
                "status": "acknowledged",
                "message": "Call end logged"
            }
            
        except Exception as e:
            logger.error(f"Error handling call end: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
        
        finally:
            call_context.set("N/A")
