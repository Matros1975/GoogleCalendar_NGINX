"""
POST-call webhook handler for ElevenLabs voice agent events.

Processes post-call events from ElevenLabs including transcripts and call completion.
"""

import logging
from typing import Dict, Any

from src.models.webhook_models import PostCallWebhookPayload
from src.services.database_service import DatabaseService
from src.utils.logger import call_context

logger = logging.getLogger(__name__)


class PostCallHandler:
    """Handles ElevenLabs POST-call webhook events."""
    
    def __init__(self, database_service: DatabaseService):
        """
        Initialize POST-call handler.
        
        Args:
            database_service: Database service instance
        """
        self.db = database_service
    
    async def handle(self, payload: PostCallWebhookPayload) -> Dict[str, Any]:
        """
        Handle POST-call webhook from ElevenLabs.
        
        Processes call completion events and updates call logs with:
        - Call transcript
        - Duration
        - Status
        - Metadata
        
        Args:
            payload: POST-call webhook payload
            
        Returns:
            Dictionary with processing result
        """
        try:
            # Set call context for logging
            call_context.set(payload.call_id)
            
            logger.info(
                f"Processing POST-call webhook: {payload.status} "
                f"for call {payload.call_id}"
            )
            
            # Extract caller ID from custom variables if available
            caller_id = None
            if payload.custom_variables:
                caller_id = payload.custom_variables.get("caller_id")
            
            # Update call log in database
            try:
                await self.db.log_call_completed(
                    call_id=payload.call_id,
                    duration_seconds=payload.duration_seconds or 0,
                    transcript=payload.transcript,
                    status=payload.status
                )
                
                logger.info(
                    f"Call log updated: {payload.call_id} "
                    f"(duration: {payload.duration_seconds}s, status: {payload.status})"
                )
                
            except Exception as db_error:
                # Log but don't fail if database update fails
                logger.error(f"Failed to update call log: {db_error}")
            
            # Log transcript if available
            if payload.transcript:
                transcript_length = len(payload.transcript)
                logger.info(
                    f"Call transcript received: {transcript_length} characters "
                    f"for call {payload.call_id}"
                )
            
            return {
                "status": "success",
                "message": "POST-call event processed successfully",
                "call_id": payload.call_id
            }
            
        except Exception as e:
            logger.exception(f"Error handling POST-call webhook: {e}")
            return {
                "status": "error",
                "message": str(e),
                "call_id": payload.call_id
            }
        
        finally:
            # Clear call context
            call_context.set("N/A")
    
    async def handle_transcript(self, payload: PostCallWebhookPayload) -> Dict[str, Any]:
        """
        Handle transcript-specific processing.
        
        This can be extended for transcript analysis, sentiment analysis, etc.
        
        Args:
            payload: POST-call webhook payload
            
        Returns:
            Dictionary with transcript processing result
        """
        try:
            if not payload.transcript:
                return {
                    "status": "skipped",
                    "message": "No transcript available"
                }
            
            logger.info(
                f"Processing transcript for call {payload.call_id}: "
                f"{len(payload.transcript)} characters"
            )
            
            # TODO: Extend with transcript analysis
            # - Sentiment analysis
            # - Key phrase extraction
            # - Issue categorization
            # - Quality scoring
            
            return {
                "status": "success",
                "message": "Transcript processed",
                "length": len(payload.transcript)
            }
            
        except Exception as e:
            logger.error(f"Error processing transcript: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def handle_call_failure(
        self,
        payload: PostCallWebhookPayload
    ) -> Dict[str, Any]:
        """
        Handle failed call events.
        
        Processes calls that failed or were missed.
        
        Args:
            payload: POST-call webhook payload
            
        Returns:
            Dictionary with failure processing result
        """
        try:
            logger.warning(
                f"Call failure detected: {payload.call_id} "
                f"(status: {payload.status})"
            )
            
            # Log failure details
            failure_reason = "unknown"
            if payload.custom_variables:
                failure_reason = payload.custom_variables.get("failure_reason", "unknown")
            
            logger.info(
                f"Call failure reason for {payload.call_id}: {failure_reason}"
            )
            
            # TODO: Extend with failure handling
            # - Retry logic
            # - Notification to admin
            # - Fallback handling
            
            return {
                "status": "acknowledged",
                "message": "Call failure logged",
                "call_id": payload.call_id,
                "failure_reason": failure_reason
            }
            
        except Exception as e:
            logger.error(f"Error handling call failure: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
