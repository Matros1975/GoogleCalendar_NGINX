"""
ElevenLabs POST-call webhook handler.
"""

from datetime import datetime

from src.models.webhook_models import PostCallWebhookPayload
from src.services.database_service import DatabaseService
from src.utils.logger import get_logger, set_call_context

logger = get_logger(__name__)


class PostCallHandler:
    """
    Handles POST-call webhooks from ElevenLabs.
    """
    
    def __init__(self, db_service: DatabaseService):
        """
        Initialize POST-call handler.
        
        Args:
            db_service: Database service
        """
        self.db = db_service
    
    async def handle(self, payload: PostCallWebhookPayload) -> dict:
        """
        Handle POST-call webhook from ElevenLabs.
        
        Args:
            payload: POST-call webhook payload
            
        Returns:
            Status dictionary
        """
        try:
            # Set logging context
            set_call_context(payload.call_id, "N/A")
            
            logger.info(f"Received POST-call webhook for call {payload.call_id} ({payload.status})")
            
            # Update call log with completion details
            if payload.duration_seconds:
                await self.db.log_call_completed(
                    call_id=payload.call_id,
                    duration_seconds=payload.duration_seconds,
                    transcript=payload.transcript,
                    status=payload.status,
                )
                logger.info(f"Updated call log for {payload.call_id}")
            else:
                logger.warning(f"No duration in POST-call webhook for {payload.call_id}")
            
            # Could trigger additional actions here:
            # - Send transcript to TopDesk
            # - Generate analytics
            # - Send notifications
            
            return {
                "status": "processed",
                "call_id": payload.call_id,
            }
            
        except Exception as e:
            logger.error(f"Error handling POST-call webhook: {e}")
            raise
