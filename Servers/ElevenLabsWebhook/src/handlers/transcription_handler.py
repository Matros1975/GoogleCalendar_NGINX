"""
Handler for post_call_transcription webhooks.

Processes full conversation data including:
- Transcripts
- Metadata (duration, cost, timestamps)
- Analysis results (evaluation, summary)
- Dynamic variables
- TopDesk ticket creation (AI-powered)
- Email notifications on failure
"""

import json
import logging
import os
from typing import Dict, Any, Optional, List

from pydantic import BaseModel, Field

from src.models.webhook_models import TranscriptionPayload, ConversationData, TranscriptEntry
from src.utils.storage import StorageManager
from src.utils.topdesk_client import TopDeskClient
from src.utils.email_sender import EmailSender

logger = logging.getLogger(__name__)

# Configuration constants
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
MAX_FALLBACK_REQUEST_LENGTH = 2000


class TicketDataPayload(BaseModel):
    """Schema for TopDesk ticket creation from transcript."""
    brief_description: str = Field(description="Short summary of the issue (max 80 chars)")
    request: str = Field(description="Detailed description of the customer's request")
    caller_name: Optional[str] = Field(None, description="Caller's name if mentioned")
    caller_email: Optional[str] = Field(None, description="Caller's email if mentioned")
    caller_phone: Optional[str] = Field(None, description="Caller's phone number if mentioned")
    category: Optional[str] = Field(None, description="Issue category (e.g., 'Hardware', 'Software', 'Network')")
    priority: Optional[str] = Field(None, description="Priority level if determinable from urgency")


class TranscriptionHandler:
    """Handler for post_call_transcription webhook events with TopDesk integration."""
    
    def __init__(self, storage: Optional[StorageManager] = None):
        """
        Initialize handler.
        
        Args:
            storage: Optional storage manager for persisting transcripts
        """
        self.storage = storage or StorageManager.from_env()
        self.topdesk_client: Optional[TopDeskClient] = None
        self.email_sender: Optional[EmailSender] = None
        self._llm = None  # Lazy-loaded LangChain LLM
    
    async def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a post_call_transcription webhook payload and create TopDesk ticket.
        
        Args:
            payload: Raw webhook payload dictionary
            
        Returns:
            Processing result dictionary with keys:
            - status: "processed"
            - conversation_id: str
            - agent_id: str
            - saved_path: str (if storage enabled)
            - formatted_transcript: str
            - ticket_created: bool
            - ticket_number: Optional[str]
            - ticket_id: Optional[str]
            - transcript_added: bool
            - email_sent: bool (if ticket creation failed)
            - error: Optional[str]
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
            
            # Initialize result dict with all required fields
            result: Dict[str, Any] = {
                "status": "processed",
                "conversation_id": transcription.conversation_id,
                "agent_id": transcription.agent_id,
                "saved_path": saved_path,
                "formatted_transcript": formatted_transcript,
                "ticket_created": False,
                "ticket_number": None,
                "ticket_id": None,
                "transcript_added": False,
                "email_sent": False,
                "error": None
            }
            
            # Skip ticket creation if no transcript
            if not formatted_transcript:
                logger.warning(f"No transcript for {transcription.conversation_id}, skipping ticket creation")
                return result
            
            # Attempt TopDesk ticket creation
            try:
                # Extract ticket data using OpenAI/LangChain
                ticket_data = await self._extract_ticket_data(formatted_transcript)
                
                # Initialize TopDesk client if needed
                if not self.topdesk_client:
                    self.topdesk_client = TopDeskClient()
                
                # Create TopDesk incident
                ticket_response = await self.topdesk_client.create_incident(
                    brief_description=ticket_data.brief_description,
                    request=ticket_data.request,
                    conversation_id=transcription.conversation_id,
                    caller_name=ticket_data.caller_name,
                    caller_email=ticket_data.caller_email,
                    category=ticket_data.category,
                    priority=ticket_data.priority
                )
                
                if ticket_response["success"]:
                    result["ticket_created"] = True
                    result["ticket_number"] = ticket_response["ticket_number"]
                    result["ticket_id"] = ticket_response["ticket_id"]
                    
                    logger.info(f"Created ticket {ticket_response['ticket_number']} for {transcription.conversation_id}")
                    
                    # Add transcript as invisible action
                    try:
                        transcript_added = await self.topdesk_client.add_invisible_action(
                            ticket_response["ticket_id"],
                            formatted_transcript
                        )
                        result["transcript_added"] = transcript_added
                        
                        if transcript_added:
                            logger.info(f"Added transcript to ticket {ticket_response['ticket_number']}")
                        else:
                            logger.warning(f"Failed to add transcript to ticket {ticket_response['ticket_number']}")
                    except Exception as e:
                        logger.error(f"Error adding transcript to ticket: {e}")
                        result["transcript_added"] = False
                else:
                    # Ticket creation failed
                    raise Exception(f"TopDesk API error: {ticket_response.get('error', 'Unknown error')}")
            
            except Exception as e:
                # Send email notification on failure
                error_msg = str(e)
                result["error"] = error_msg
                logger.error(f"Ticket creation failed for {transcription.conversation_id}: {error_msg}")
                
                if not self.email_sender:
                    self.email_sender = EmailSender()
                
                try:
                    email_sent = await self.email_sender.send_error_notification(
                        transcription.conversation_id,
                        formatted_transcript,
                        error_msg
                    )
                    result["email_sent"] = email_sent
                except Exception as email_error:
                    logger.error(f"Failed to send error notification email: {email_error}")
            
            return result
            
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
    
    async def _extract_ticket_data(self, transcript: str) -> TicketDataPayload:
        """
        Extract ticket creation data from formatted transcript using OpenAI/LangChain.
        
        Args:
            transcript: Human-readable formatted transcript
            
        Returns:
            TicketDataPayload with extracted information
        """
        # Check if OpenAI API key is configured
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not configured, using fallback extraction")
            return self._fallback_ticket_extraction(transcript)
        
        try:
            # Lazy import LangChain to avoid import errors if not installed
            from langchain_openai import ChatOpenAI
            from langchain.prompts import ChatPromptTemplate
            from langchain.output_parsers import PydanticOutputParser
            
            # Initialize LLM if not already done
            if self._llm is None:
                model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
                self._llm = ChatOpenAI(
                    model=model,
                    temperature=0,
                    api_key=api_key
                )
            
            parser = PydanticOutputParser(pydantic_object=TicketDataPayload)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an AI assistant that extracts ticket information from call transcripts.
Analyze the conversation and extract:
- A brief description (max 80 characters) summarizing the main issue
- Detailed request description explaining what the caller needs
- Caller information if mentioned (name, email, phone)
- Issue category if determinable (e.g., 'Hardware', 'Software', 'Network', 'Account')
- Priority level if determinable from urgency (e.g., 'High', 'Medium', 'Low')

{format_instructions}"""),
                ("human", "Call transcript:\n\n{transcript}")
            ])
            
            chain = prompt | self._llm | parser
            
            result = await chain.ainvoke({
                "transcript": transcript,
                "format_instructions": parser.get_format_instructions()
            })
            
            logger.info("Successfully extracted ticket data using OpenAI")
            return result
            
        except ImportError as e:
            logger.warning(f"LangChain not available: {e}, using fallback extraction")
            return self._fallback_ticket_extraction(transcript)
        except Exception as e:
            logger.error(f"Failed to extract ticket data with OpenAI: {e}")
            return self._fallback_ticket_extraction(transcript)
    
    def _fallback_ticket_extraction(self, transcript: str) -> TicketDataPayload:
        """
        Fallback ticket data extraction when OpenAI is not available.
        
        Args:
            transcript: Human-readable formatted transcript
            
        Returns:
            TicketDataPayload with basic extracted information
        """
        # Extract first meaningful message as brief description
        lines = transcript.strip().split('\n')
        brief_desc = "Call transcript"
        
        for line in lines:
            if "caller:" in line.lower():
                # Extract caller message
                parts = line.split(':', 2)
                if len(parts) >= 3:
                    message = parts[2].strip()[:80]
                    if message:
                        brief_desc = message
                        break
        
        return TicketDataPayload(
            brief_description=brief_desc,
            request=transcript[:MAX_FALLBACK_REQUEST_LENGTH] if len(transcript) > MAX_FALLBACK_REQUEST_LENGTH else transcript
        )
    
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
        
        # Format arguments as key="value" pairs with proper escaping
        if isinstance(arguments, dict):
            arg_parts = []
            for k, v in arguments.items():
                # Convert value to string and escape quotes
                v_str = str(v).replace('\\', '\\\\').replace('"', '\\"')
                arg_parts.append(f'{k}="{v_str}"')
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
        
        # If output is a string, use it directly
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
