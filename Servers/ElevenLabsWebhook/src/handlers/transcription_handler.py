"""
Handler for post_call_transcription webhooks.

Processes full conversation data including:
- Transcripts
- Metadata (duration, cost, timestamps)
- Analysis results (evaluation, summary)
- Dynamic variables
"""

import logging
from typing import Dict, Any, Optional

from src.models.webhook_models import TranscriptionPayload, ConversationData
from src.utils.storage import StorageManager

logger = logging.getLogger(__name__)


class TranscriptionHandler:
    """Handler for post_call_transcription webhook events."""
    
    def __init__(self, storage: Optional[StorageManager] = None):
        """
        Initialize handler.
        
        Args:
            storage: Optional storage manager for persisting transcripts
        """
        self.storage = storage or StorageManager.from_env()
    
    async def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a post_call_transcription webhook payload.
        
        Args:
            payload: Raw webhook payload dictionary
            
        Returns:
            Processing result dictionary
        """
        logger.info("Processing post_call_transcription webhook")
        
        try:
            # Parse payload into typed model
            transcription = TranscriptionPayload.from_dict(payload)
            
            logger.info(
                f"Transcription received - "
                f"conversation_id: {transcription.conversation_id}, "
                f"agent_id: {transcription.agent_id}"
            )
            
            # Process conversation data if present
            if transcription.data:
                self._process_conversation_data(transcription.data)
            
            # Store transcript if storage is enabled
            saved_path = self.storage.save_transcript(
                conversation_id=transcription.conversation_id,
                agent_id=transcription.agent_id,
                data=payload.get("data", {})
            )
            
            return {
                "status": "processed",
                "conversation_id": transcription.conversation_id,
                "agent_id": transcription.agent_id,
                "saved_path": saved_path
            }
            
        except Exception as e:
            logger.exception(f"Error processing transcription: {e}")
            raise
    
    def _process_conversation_data(self, data: ConversationData) -> None:
        """
        Process and log conversation data details.
        
        Args:
            data: Parsed conversation data
        """
        # Log basic metadata
        logger.info(
            f"Conversation details - "
            f"duration: {data.call_duration_secs}s, "
            f"messages: {data.message_count}, "
            f"status: {data.status}"
        )
        
        # Log timestamps if available
        if data.start_time:
            logger.debug(f"Call started: {data.start_time.isoformat()}")
        if data.end_time:
            logger.debug(f"Call ended: {data.end_time.isoformat()}")
        
        # Log audio availability (new fields coming August 2025)
        if data.has_audio is not None:
            logger.debug(
                f"Audio availability - "
                f"has_audio: {data.has_audio}, "
                f"has_user_audio: {data.has_user_audio}, "
                f"has_response_audio: {data.has_response_audio}"
            )
        
        # Log transcript summary
        if data.transcript:
            agent_msgs = sum(1 for t in data.transcript if t.role == "agent")
            user_msgs = sum(1 for t in data.transcript if t.role == "user")
            logger.info(f"Transcript: {agent_msgs} agent messages, {user_msgs} user messages")
        
        # Log analysis results if present
        if data.analysis:
            if data.analysis.summary:
                logger.info(f"Call summary: {data.analysis.summary[:100]}...")
            if data.analysis.evaluation:
                logger.debug(f"Evaluation criteria: {list(data.analysis.evaluation.keys())}")
            if data.analysis.data_collection:
                logger.debug(f"Data collected: {list(data.analysis.data_collection.keys())}")
        
        # Log metadata/dynamic variables
        if data.metadata:
            logger.debug(f"Dynamic variables: {list(data.metadata.keys())}")
