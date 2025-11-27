"""
Handler for post_call_transcription webhooks.

Processes full conversation data including:
- Transcripts
- Metadata (duration, cost, timestamps)
- Analysis results (evaluation, summary)
- Dynamic variables
"""

import json
import logging
from typing import Dict, Any, Optional, List

from src.models.webhook_models import TranscriptionPayload, ConversationData, TranscriptEntry
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
            
            # Generate formatted transcript
            formatted_transcript = self._generate_formatted_transcript(transcription.data)
            
            return {
                "status": "processed",
                "conversation_id": transcription.conversation_id,
                "agent_id": transcription.agent_id,
                "saved_path": saved_path,
                "formatted_transcript": formatted_transcript
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
    
    def _format_timestamp(self, seconds: float) -> str:
        """
        Convert seconds to [HH:MM:SS] format.
        
        Args:
            seconds: Time in seconds (can be float)
            
        Returns:
            Formatted timestamp string [HH:MM:SS]
            
        Examples:
            0.5 -> [00:00:00]
            65.0 -> [00:01:05]
            3665.5 -> [01:01:05]
        """
        total_seconds = int(seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        return f"[{hours:02d}:{minutes:02d}:{secs:02d}]"
    
    def _format_tool_call(self, tool_call: Dict[str, Any]) -> str:
        """
        Format a tool call entry for the transcript.
        
        Args:
            tool_call: Tool call dictionary with 'name' and 'arguments'
            
        Returns:
            Formatted tool call string
        """
        name = tool_call.get("name", "unknown")
        arguments = tool_call.get("arguments", "")
        
        # Parse arguments if they are a JSON string
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except (json.JSONDecodeError, TypeError):
                pass  # Keep as string if not valid JSON
        
        # Format arguments as key="value" pairs
        if isinstance(arguments, dict):
            arg_parts = [f'{k}="{v}"' for k, v in arguments.items()]
            args_str = ", ".join(arg_parts)
        else:
            args_str = str(arguments)
        
        return f"toolcall: {name}({args_str})"
    
    def _format_tool_result(self, tool_result: Dict[str, Any]) -> str:
        """
        Format a tool result entry for the transcript.
        
        Args:
            tool_result: Tool result dictionary with 'output'
            
        Returns:
            Formatted tool result string
        """
        output = tool_result.get("output", "")
        
        # If output is already a string that looks like JSON, use it directly
        if isinstance(output, str):
            return f"toolcall_result: {output}"
        
        # Otherwise, serialize the output
        return f"toolcall_result: {json.dumps(output)}"
    
    def _generate_formatted_transcript(self, data: Optional[ConversationData]) -> str:
        """
        Generate formatted text transcript from conversation data.
        
        Format: [HH:MM:SS] - speaker: message
        Tool calls are included as 'toolcall' entries.
        
        Args:
            data: Conversation data containing transcript
            
        Returns:
            Formatted transcript string with timestamps
        """
        if not data or not data.transcript:
            return ""
        
        lines: List[str] = []
        
        for entry in data.transcript:
            timestamp = self._format_timestamp(entry.timestamp or 0)
            
            # Map role: "user" -> "caller", keep "agent" as is
            speaker = "caller" if entry.role == "user" else entry.role
            
            # Add regular message if present
            if entry.message:
                lines.append(f"{timestamp} - {speaker}: {entry.message}")
            
            # Add tool call if present
            if entry.tool_call:
                tool_line = self._format_tool_call(entry.tool_call)
                lines.append(f"{timestamp} - {tool_line}")
            
            # Add tool result if present
            if entry.tool_result:
                result_line = self._format_tool_result(entry.tool_result)
                lines.append(f"{timestamp} - {result_line}")
        
        return "\n".join(lines)
