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
import os
from typing import Dict, Any, Optional, List

from pydantic import BaseModel, Field

from src.models.webhook_models import TranscriptionPayload, ConversationData, TranscriptEntry
from src.utils.storage import StorageManager
from src.utils.topdesk_client import TopDeskClient
from src.utils.email_sender import EmailSender
from src.utils.logger import setup_logger
from datetime import datetime, timezone
import re


def format_unix_time(ts: int | None) -> str:
    if not ts:
        return "Unknown"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )


logger = setup_logger()

# Configuration constants
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
MAX_FALLBACK_REQUEST_LENGTH = 2000


# Valid TopDesk categories (must match TopDesk instance configuration)
VALID_TOPDESK_CATEGORIES = [
    "Core applicaties",
    "Werkplek hardware",
    "Netwerk",
    "Wachtwoord wijziging"
]

# Valid TopDesk priorities (must match TopDesk instance configuration)
VALID_TOPDESK_PRIORITIES = [
    "P1 (I&A)",  # Critical
    "P2 (I&A)",  # High
    "P3 (I&A)",  # Medium
    "P4 (I&A)"   # Low
]


class TicketDataPayload(BaseModel):
    """Schema for TopDesk ticket creation from transcript."""
    brief_description: str = Field(description="Short summary of the issue (max 80 chars)")
    request: str = Field(description="Detailed description of the customer's request")
    summary: str = Field(description="Structured summary with: Issue reported, Steps already performed, Steps suggested by agent, Next steps planned")
    employee_number: str = Field(description="Employee number - MUST be 'UNKNOWN' if not mentioned in conversation")
    category: Optional[str] = Field(None, description=f"Issue category. Must be one of: {', '.join(VALID_TOPDESK_CATEGORIES)}")
    priority: Optional[str] = Field(None, description=f"Priority level. Must be one of: {', '.join(VALID_TOPDESK_PRIORITIES)}")


class TranscriptionHandler:
    """
    Handler for post_call_transcription webhook events with TopDesk integration.
    
    This handler processes ElevenLabs conversation transcripts and automatically creates
    support tickets in TopDesk using AI-powered data extraction. It provides:
    
    **Core Features:**
    - Webhook payload parsing and validation
    - Transcript storage and formatting
    - AI-powered ticket data extraction (OpenAI/LangChain)
    - TopDesk incident creation with full transcript
    - Email notifications on failure
    
    **Processing Workflow:**
    1. Parse and validate incoming webhook payload
    2. Log conversation metadata (duration, message count, etc.)
    3. Store transcript to disk (if storage enabled)
    4. Format transcript with timestamps and speaker labels
    5. Extract ticket data using OpenAI (or fallback to basic extraction)
    6. Create TopDesk incident with extracted information
    7. Attach full transcript as invisible action
    8. Send email notification if ticket creation fails
    
    **Components:**
    - storage: Manages transcript persistence to disk
    - topdesk_client: Handles TopDesk API interactions
    - email_sender: Sends error notifications via SMTP
    - _llm: Lazy-loaded LangChain ChatOpenAI instance
    
    **Environment Variables:**
    - OPENAI_API_KEY: Required for AI extraction (falls back to basic if missing)
    - OPENAI_MODEL: Model to use (default: gpt-4o-mini)
    - TOPDESK_URL, TOPDESK_USERNAME, TOPDESK_PASSWORD: TopDesk credentials
    - GMAIL_SMTP_*: Email notification settings
    """
    
    def __init__(self, storage: Optional[StorageManager] = None):
        """
        Initialize the transcription handler with lazy-loaded dependencies.
        
        The handler initializes with minimal components and lazily loads TopDesk client,
        email sender, and LLM only when needed. This reduces startup overhead and allows
        the service to run even if some integrations are not configured.
        
        Args:
            storage: Optional storage manager for persisting transcripts to disk.
                    If None, creates default StorageManager from environment variables.
                    Storage can be disabled by setting STORAGE_ENABLED=false in env.
        
        Attributes Initialized:
            storage: StorageManager instance (always initialized)
            topdesk_client: None (initialized on first ticket creation)
            email_sender: None (initialized on first error notification)
            _llm: None (initialized on first OpenAI extraction call)
        
        Note:
            This method does not perform any API calls or validate credentials.
            Validation happens during first use of each component.
        """
        self.storage = storage or StorageManager.from_env()
        self.topdesk_client: Optional[TopDeskClient] = None
        self.email_sender: Optional[EmailSender] = None
        self._llm = None  # Lazy-loaded LangChain LLM
    
    async def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a post_call_transcription webhook payload and create TopDesk ticket.
        
        This is the main entry point for webhook processing. It orchestrates the entire
        workflow from payload parsing to ticket creation and error handling.
        
        **Processing Steps:**
        1. Parse payload into TranscriptionPayload model (validates structure)
        2. Log conversation metadata and statistics
        3. Save transcript to disk (if storage enabled)
        4. Generate formatted transcript with timestamps
        5. Extract ticket data using OpenAI/LangChain
        6. Create TopDesk incident with extracted data
        7. Attach transcript as invisible action to ticket
        8. Send email notification if ticket creation fails
        
        **Error Handling:**
        - Validation errors: Raised immediately (invalid payload structure)
        - Storage errors: Logged but processing continues
        - OpenAI errors: Falls back to basic extraction
        - TopDesk errors: Triggers email notification, sets error in result
        - Email errors: Logged but does not fail the request
        
        Args:
            payload: Raw webhook payload dictionary from ElevenLabs containing:
                - type: "post_call_transcription"
                - conversation_id: Unique conversation identifier
                - agent_id: ElevenLabs agent identifier
                - data: Conversation data with transcript, metadata, analysis
        
        Returns:
            Processing result dictionary with keys:
            - status: Always "processed"
            - conversation_id: Conversation identifier from payload
            - agent_id: Agent identifier from payload
            - saved_path: File path where transcript was saved (or None)
            - formatted_transcript: Human-readable transcript with timestamps
            - ticket_created: True if TopDesk ticket was created successfully
            - ticket_number: TopDesk ticket number (e.g., "I 240001") or None
            - ticket_id: TopDesk internal ticket ID (UUID) or None
            - transcript_added: True if transcript attached to ticket successfully
            - email_sent: True if error notification email was sent
            - error: Error message if ticket creation failed, None otherwise
        
        Raises:
            Exception: If payload parsing fails or critical error occurs.
                      TopDesk/email errors are caught and returned in result dict.
        
        Examples:
            >>> handler = TranscriptionHandler()
            >>> result = await handler.handle(webhook_payload)
            >>> if result["ticket_created"]:
            ...     print(f"Created ticket {result['ticket_number']}")
            >>> else:
            ...     print(f"Error: {result['error']}")
        
        Note:
            - Empty transcripts skip ticket creation (returns early with ticket_created=False)
            - Costs ~$0.01 per call when using OpenAI extraction
            - Processing time: 2-5 seconds depending on transcript length
        """
        logger.info("Processing post_call_transcription webhook")
        def topdesk_format(text: str) -> str:
            """
            Converts a structured markdown summary into TOPdesk-safe HTML:
            - Headers: → <strong>Headers:</strong>
            - * bullets → <ul><li>
            - Newlines → <br>
            """

            # Convert markdown headers (e.g., **Header:**) to <strong>
            text = re.sub(r"\*\*(.+?):\*\*", r"<strong>\1:</strong>", text)

            lines = text.splitlines()
            html = []
            in_list = False

            for line in lines:
                stripped = line.strip()

                # Bullet list support
                if stripped.startswith("* "):
                    if not in_list:
                        html.append("<ul>")
                        in_list = True
                    html.append(f"<li>{stripped[2:].strip()}</li>")
                else:
                    if in_list:
                        html.append("</ul>")
                        in_list = False

                    if stripped:
                        html.append(f"{stripped}<br>")
                    else:
                        html.append("<br>")

            if in_list:
                html.append("</ul>")

            return "".join(html)
        
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
                logger.info(f"Starting employee number extraction for conversation: {transcription.conversation_id}")
                ticket_data = await self._extract_ticket_data(formatted_transcript, transcription.data)
                logger.info(f"Ticket data extracted - Employee number: '{ticket_data.employee_number}' (Brief: '{ticket_data.brief_description}')")
                
                # Initialize TopDesk client if needed
                if not self.topdesk_client:
                    self.topdesk_client = TopDeskClient()
                
                # Prepend summary to request for structured ticket data
                formatted_summary = topdesk_format(ticket_data.summary)

                conversation_id = transcription.conversation_id or "Onbekend"

                conversation_block = (
                    f"<strong>Conversation ID:</strong> {conversation_id}<br><br>"
                )

                separator = "<br>-----------------------------------------------------------------------------<br>"

                full_request = (
                    conversation_block +
                    formatted_summary +
                    separator +
                    "<strong>Aanvullende Beschrijving:</strong><br>" +
                    ticket_data.request
                )

                # Check if employee number exists and validate it
                employee_person = None
                if ticket_data.employee_number:
                    logger.info(f"Validating employee number: '{ticket_data.employee_number}' in TopDesk")
                    try:
                        employee_person = await self.topdesk_client.validate_employee_number(
                            ticket_data.employee_number
                        )
                        if employee_person:
                            logger.info(f"Employee number '{ticket_data.employee_number}' validated successfully. Found person: {employee_person.get('id', 'N/A')}")
                        else:
                            logger.warning(f"Employee number '{ticket_data.employee_number}' not found in TopDesk")
                    except Exception as validation_error:
                        logger.error(f"Error validating employee number {ticket_data.employee_number}: {validation_error}")
                        employee_person = None

                if not employee_person:
                    # Employee number not found or not provided - skip ticket creation and send fallback email
                    error_msg = f"Employee number {ticket_data.employee_number or 'not provided'} not found in TopDesk or validation failed"
                    result["error"] = error_msg
                    logger.warning(f"Employee validation failed for {transcription.conversation_id}: {error_msg}")
                    
                    # Send fallback email to service desk
                    if not self.email_sender:
                        self.email_sender = EmailSender()
                    
                    try:
                        data_dict = payload.get("data", {}) or {}
                        metadata = data_dict.get("metadata", {}) or {}
                        phone_call = metadata.get("phone_call", {}) or {}
                        
                        call_number = phone_call.get("external_number")
                        
                        start_time = metadata.get("start_time_unix_secs")
                        call_time = format_unix_time(start_time) if start_time else "Unknown"

                        email_sent = await self.email_sender.send_error_notification(
                            conversation_id=transcription.conversation_id,
                            transcript=formatted_transcript,
                            error_message=f"Employee number validation failed: {error_msg}",
                            ticket_data=ticket_data.dict() if ticket_data else {},
                            payload=payload,
                            call_number=call_number,
                            call_time=call_time
                        )

                        result["email_sent"] = email_sent
                        
                    except Exception as email_error:
                        logger.error(f"Failed to send fallback notification email: {email_error}")
                        result["email_sent"] = False
                    
                    return result  # Skip ticket creation

                # Employee number validated successfully - create ticket
                ticket_response = await self.topdesk_client.create_incident(
                    brief_description=ticket_data.brief_description,
                    request=full_request,
                    conversation_id=transcription.conversation_id,
                    employee_number=ticket_data.employee_number,
                    category=ticket_data.category,
                    priority=ticket_data.priority
                )
                
                if not ticket_response or not isinstance(ticket_response, dict):
                    raise Exception("TopDesk create_incident returned no response")

                if ticket_response.get("success"):
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
                logger.error(
                    f"Ticket creation failed for {transcription.conversation_id}: {error_msg}"
                )

                if not self.email_sender:
                    self.email_sender = EmailSender()

                try:
                    data_dict = payload.get("data", {}) or {}
                    metadata = data_dict.get("metadata", {}) or {}
                    phone_call = metadata.get("phone_call", {}) or {}
                    
                    call_number = phone_call.get("external_number")
                    
                    start_time = metadata.get("start_time_unix_secs")
                    call_time = format_unix_time(start_time) if start_time else "Unknown"

                    email_sent = await self.email_sender.send_error_notification(
                        conversation_id=transcription.conversation_id,
                        transcript=formatted_transcript,
                        error_message=error_msg,
                        ticket_data=ticket_data.dict() if ticket_data else {},
                        payload=payload,
                        call_number=call_number,
                        call_time=call_time
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
        Process and log conversation metadata and statistics for observability.
        
        This method does NOT modify any data or make API calls. It only extracts
        and logs useful information from the conversation data for debugging and
        monitoring purposes.
        
        **Logged Information:**
        - Basic metadata: duration, message count, call status
        - Timestamps: start time, end time (if available)
        - Audio availability: flags for audio presence (future ElevenLabs feature)
        - Transcript statistics: agent message count, user message count
        - Analysis results: call summary, evaluation criteria, collected data
        - Dynamic variables: custom metadata fields set during conversation
        
        **Log Levels Used:**
        - INFO: Call duration, message counts, transcript statistics, summaries
        - DEBUG: Timestamps, audio flags, evaluation criteria, dynamic variables
        
        Args:
            data: Parsed conversation data containing transcript, metadata, and analysis.
                  See ConversationData model for full structure.
        
        Returns:
            None. All output is logged via the logger instance.
        
        Side Effects:
            - Writes log messages at INFO and DEBUG levels
            - No state changes, no API calls, no file I/O
        
        Examples:
            Log output:
            INFO - Conversation details - duration: 127.5s, messages: 8, status: completed
            INFO - Transcript: 4 agent messages, 4 user messages
            INFO - Call summary: Customer reported laptop screen flickering...
            DEBUG - Dynamic variables: ['customer_email', 'issue_type']
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
    
    async def _extract_ticket_data(self, transcript: str, conversation_data: Optional['ConversationData'] = None) -> TicketDataPayload:
        """
        Extract structured ticket data from transcript using AI or fallback extraction.
        
        This method uses OpenAI's LLM (via LangChain) to intelligently extract ticket
        information from the conversation transcript. If OpenAI is unavailable or fails,
        it falls back to basic text parsing.
        
        **AI Extraction (Primary):**
        - Uses ChatOpenAI with gpt-4o-mini (configurable via OPENAI_MODEL)
        - Temperature 0 for consistent, deterministic output
        - Pydantic parser ensures valid TicketDataPayload structure
        - Extracts: brief description, request details, caller info, category, priority
        - Fetches valid categories and priorities from TopDesk API dynamically
        
        **Fallback Extraction (When OpenAI unavailable):**
        - Uses first caller message as brief description
        - Truncates full transcript to MAX_FALLBACK_REQUEST_LENGTH (2000 chars)
        - Sets all optional fields (caller info, category, priority) to None
        
        **LLM Prompt Instructions:**
        - Brief description: max 80 chars, main issue summary
        - Request: detailed explanation of caller's needs
        - Caller info: name, email, phone (if mentioned in conversation)
        - **IMPORTANT: Extract employee number if mentioned**
        - Category: Fetched from TopDesk API (e.g., "Core applicaties", "Werkplek hardware")
        - Priority: Fetched from TopDesk API (e.g., "P1 (I&A)", "P2 (I&A)")
        
        Args:
            transcript: Human-readable formatted transcript with timestamps and speaker labels.
                       Format: "[HH:MM:SS] - speaker: message"
        
        Returns:
            TicketDataPayload: Pydantic model with extracted fields:
                - brief_description: Short summary (max 80 chars)
                - request: Detailed description
                - caller_name: Extracted name or None
                - caller_email: Extracted email or None
                - caller_phone: Extracted phone or None
                - employee_number: Extracted employee number or None
                - category: Issue category or None
                - priority: Priority level or None
        
        Raises:
            No exceptions raised. All errors are caught and logged:
            - ImportError: LangChain not installed → fallback extraction
            - API errors: OpenAI call failed → fallback extraction
            - Parsing errors: Invalid LLM response → fallback extraction
        
        Side Effects:
            - May make OpenAI API call (costs ~$0.005-$0.01 per call)
            - Initializes self._llm on first call (cached for subsequent calls)
            - Fetches categories/priorities from TopDesk on first call (cached)
            - Logs warnings/errors for failures
        
        Performance:
            - AI extraction: 1-3 seconds (depends on transcript length)
            - Fallback extraction: <10ms (simple text parsing)
        
        Examples:
            >>> transcript = "[00:00:05] - caller: My laptop won't boot\n[00:00:10] - agent: Let me help"
            >>> data = await handler._extract_ticket_data(transcript)
            >>> print(data.brief_description)
            "Laptop boot failure"
            >>> print(data.category)
            "Werkplek hardware"
        """
        # Check if OpenAI API key is configured
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not configured, using fallback extraction")
            return self._fallback_ticket_extraction(transcript, conversation_data)
        
        try:
            # Lazy import LangChain to avoid import errors if not installed
            from langchain_openai import ChatOpenAI
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import PydanticOutputParser
            
            # Initialize LLM if not already done
            if self._llm is None:
                model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
                self._llm = ChatOpenAI(
                    model=model,
                    temperature=0,
                    api_key=api_key
                )
            
            # Initialize TopDesk client if needed to fetch categories/priorities
            if not self.topdesk_client:
                self.topdesk_client = TopDeskClient()
            
            # Fetch valid categories and priorities from TopDesk API
            valid_categories = await self.topdesk_client.get_categories()
            valid_priorities = await self.topdesk_client.get_priorities()
            
            # Use fallback lists if API fetch failed
            if not valid_categories:
                logger.warning("Using fallback category list (TopDesk API unavailable)")
                valid_categories = VALID_TOPDESK_CATEGORIES
            if not valid_priorities:
                logger.warning("Using fallback priority list (TopDesk API unavailable)")
                valid_priorities = VALID_TOPDESK_PRIORITIES
            
            parser = PydanticOutputParser(pydantic_object=TicketDataPayload)
            
            # Build prompt with valid TopDesk categories and priorities
            categories_list = "\n".join([f"  - {cat}" for cat in valid_categories])
            priorities_list = "\n".join([f"  - {pri}" for pri in valid_priorities])
            
            prompt = ChatPromptTemplate.from_messages([
    ("system", f"""Je bent een ervaren IT-servicedesk medewerker.

Analyseer het onderstaande telefoongesprek en genereer ticketinformatie voor TopDesk.

BELANGRIJK:
- ALLE output moet volledig in het Nederlands zijn.
- Gebruik GEEN Engels.
- Gebruik professionele servicedesk-taal.
- Maak geen aannames die niet expliciet in het gesprek genoemd worden.
- Schrijf helder, zakelijk en gestructureerd.

Genereer de volgende velden:

1) brief_description  
   - Maximaal 80 tekens  
   - Korte duidelijke omschrijving van het probleem  

2) request  
   - Gedetailleerde beschrijving van het probleem en wat de gebruiker vraagt  

3) summary  
   Gebruik exact deze structuur:

**Gemeld Probleem:**  
[Beschrijving van het gemelde probleem]

**Reeds Uitgevoerde Stappen:**  
[Welke stappen heeft de gebruiker al uitgevoerd]

**Voorgestelde Acties door Servicedesk:**  
[Welke adviezen of acties gaf de agent]

**Vervolgstappen:**  
[Vervolgacties of wat er nog moet gebeuren]

4) employee_number  
   - Extract het personeelsnummer indien genoemd  
   - Zet gesproken cijfers om naar numerieke vorm  
     Bijvoorbeeld: "drie twee nul twee twee vijf vijf" → "3202255"  
   - Indien NIET genoemd: zet exact "UNKNOWN"

5) category  
   - MOET exact één van onderstaande waarden zijn:
{categories_list}
   - Kies de best passende categorie  
   - Gebruik "{valid_categories[0]}" indien twijfel  

6) priority  
   Bepaal prioriteit op basis van urgentie en impact:

  • Urgentie "Kan niet werken":
    - Impact op Organisatie/Vestiging/Afdeling → "P1 (I&A)"
    - Impact op Persoon → "P2 (I&A)"

  • Urgentie "Kan deels werken":
    - Impact op Organisatie/Vestiging/Afdeling → "P2 (I&A)"
    - Impact op Persoon → "P3 (I&A)"

  • Urgentie "Kan werken":
    - Impact op Organisatie/Vestiging/Afdeling → "P3 (I&A)"
    - Impact op Persoon → "P4 (I&A)"

Geldige prioriteiten:
{', '.join(valid_priorities)}

Zorg dat ALLE gegenereerde tekst volledig in het Nederlands is.

{{format_instructions}}"""),
    ("human", "Call transcript:\n\n{transcript}")])
            
            chain = prompt | self._llm | parser
            
            result = await chain.ainvoke({
                "transcript": transcript,
                "format_instructions": parser.get_format_instructions()
            })
            
            logger.info("Successfully extracted ticket data using OpenAI")
            return result
            
        except ImportError as e:
            logger.warning(f"LangChain not available: {e}, using fallback extraction")
            return self._fallback_ticket_extraction(transcript, conversation_data)
        except Exception as e:
            logger.error(f"Failed to extract ticket data with OpenAI: {e}")
            return self._fallback_ticket_extraction(transcript, conversation_data)
    
    def _fallback_ticket_extraction(self, transcript: str, conversation_data: Optional['ConversationData'] = None) -> TicketDataPayload:
        """
        Simple text-based ticket extraction when AI is unavailable.
        
        This fallback method provides basic ticket data extraction without using AI.
        It's used when OPENAI_API_KEY is not configured or when AI extraction fails.
        If ElevenLabs provided a summary in the payload, it will be used instead of the placeholder.
        
        **Extraction Algorithm:**
        1. Split transcript into lines
        2. Find first line containing "caller:" (case-insensitive)
        3. Extract text after second colon (skips timestamp)
        4. Use first 80 chars as brief description
        5. Use full transcript (up to 2000 chars) as request
        6. All optional fields (caller info, category, priority) set to None
        
        **Limitations:**
        - No semantic understanding of conversation
        - Cannot extract caller information (name, email, phone)
        - Cannot determine category or priority
        - Brief description may not be meaningful
        - Long transcripts truncated to 2000 chars
        
        Args:
            transcript: Human-readable formatted transcript.
                       Expected format: "[HH:MM:SS] - speaker: message"
        
        Returns:
            TicketDataPayload with:
                - brief_description: First caller message (max 80 chars) or "Call transcript"
                - request: Full transcript (max 2000 chars)
                - caller_name: None
                - caller_email: None
                - caller_phone: None
                - employee_number: None
                - category: None
                - priority: None
        
        Examples:
            >>> transcript = "[00:00:00] - agent: Hello\n[00:00:03] - caller: My computer is broken"
            >>> data = handler._fallback_ticket_extraction(transcript)
            >>> print(data.brief_description)
            "My computer is broken"
            >>> print(data.caller_name)
            None
        
        Performance:
            - Execution time: <10ms (simple string operations)
            - No API calls, no AI processing
        
        Note:
            This method is deterministic and will always produce the same output
            for the same input transcript.
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
        
        # Use ElevenLabs summary if available, otherwise create basic summary
        if conversation_data and conversation_data.analysis and conversation_data.analysis.summary:
            elevenlabs_summary = conversation_data.analysis.summary
            logger.info("Using ElevenLabs call summary for fallback extraction")
            # Format the ElevenLabs summary into our structured format
            fallback_summary = f"""**Gemeld Probleem:**
            {elevenlabs_summary}

            **Reeds Uitgevoerde Stappen:**
            Zie transcript voor details.

            **Voorgestelde Acties door Servicedesk:**
            Zie transcript voor details.

            **Vervolgstappen:**
            Controleer samenvatting en transcript voor vervolgacties."""

        else:
            # No ElevenLabs summary available, use placeholder
            logger.info("No ElevenLabs summary available, using placeholder")
            fallback_summary = """**Gemeld Probleem:**
            Zie volledig transcript hieronder voor details.

            **Reeds Uitgevoerde Stappen:**
            Niet automatisch te bepalen - raadpleeg transcript.

            **Voorgestelde Acties door Servicedesk:**
            Niet automatisch te bepalen - raadpleeg transcript.

            **Vervolgstappen:**
            Vervolgactie vereist - controleer volledig transcript."""
        
        return TicketDataPayload(
            brief_description=brief_desc,
            request=transcript[:MAX_FALLBACK_REQUEST_LENGTH] if len(transcript) > MAX_FALLBACK_REQUEST_LENGTH else transcript,
            summary=fallback_summary
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
        Format a tool invocation entry for human-readable transcript display.
        
        ElevenLabs agents can invoke tools during conversations (e.g., check calendar,
        create tasks). This method formats those invocations into a readable format
        suitable for inclusion in transcripts.
        
        **Formatting Rules:**
        - Tool name is preserved as-is
        - Dictionary arguments formatted as key="value" pairs
        - String values are properly escaped (quotes and backslashes)
        - JSON string arguments are parsed before formatting
        - Non-dict arguments converted to string representation
        
        Args:
            tool_call: Tool call dictionary from ElevenLabs webhook containing:
                - name: Tool name (e.g., "check_calendar", "send_email")
                - arguments: Tool arguments as dict or JSON string
        
        Returns:
            Formatted string in format: toolcall: name(key="value", key2="value2")
            Or: toolcall: name(unknown) if name is missing
        
        Examples:
            >>> tool_call = {"name": "send_email", "arguments": {"to": "user@example.com", "subject": "Test"}}
            >>> handler._format_tool_call(tool_call)
            'toolcall: send_email(to="user@example.com", subject="Test")'
            
            >>> tool_call = {"name": "get_time", "arguments": {}}
            >>> handler._format_tool_call(tool_call)
            'toolcall: get_time()'
        
        Note:
            - Handles malformed JSON gracefully (keeps as string)
            - Escapes special characters to prevent transcript corruption
            - Arguments order may not be preserved (dict iteration)
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
        Format a tool execution result for human-readable transcript display.
        
        After a tool is invoked, ElevenLabs provides the result of that invocation.
        This method formats the result for inclusion in the transcript, handling
        both simple string outputs and complex structured data.
        
        **Formatting Rules:**
        - String outputs: Used directly without modification
        - Complex outputs (dict, list, etc.): JSON serialized
        - Missing output field: Empty string used
        
        Args:
            tool_result: Tool result dictionary from ElevenLabs webhook containing:
                - output: The result of the tool execution (any type)
        
        Returns:
            Formatted string in format: toolcall_result: {output}
        
        Examples:
            >>> tool_result = {"output": "Email sent successfully"}
            >>> handler._format_tool_result(tool_result)
            'toolcall_result: Email sent successfully'
            
            >>> tool_result = {"output": {"status": "ok", "count": 3}}
            >>> handler._format_tool_result(tool_result)
            'toolcall_result: {"status": "ok", "count": 3}'
            
            >>> tool_result = {}
            >>> handler._format_tool_result(tool_result)
            'toolcall_result: '
        
        Note:
            - JSON serialization uses default settings (no pretty printing)
            - Non-serializable objects will raise JSONDecodeError
            - Empty results produce valid but empty output
        """
        output = tool_result.get("output", "")
        
        # If output is a string, use it directly
        if isinstance(output, str):
            return f"toolcall_result: {output}"
        
        # Otherwise, serialize the output
        return f"toolcall_result: {json.dumps(output)}"
    
    def _generate_formatted_transcript(self, data: Optional[ConversationData]) -> str:
        """
        Generate human-readable transcript from conversation data with timestamps.
        
        This method transforms the raw transcript data from ElevenLabs into a
        well-formatted, timestamped text document suitable for human reading
        and AI processing. It handles regular messages, tool calls, and tool results.
        
        **Format Specification:**
        - Timestamp format: [HH:MM:SS] (24-hour format)
        - Speaker labels: "agent" or "caller" (user → caller mapping)
        - Entry format: [timestamp] - speaker: message
        - Tool calls: [timestamp] - toolcall: name(args)
        - Tool results: [timestamp] - toolcall_result: output
        - Entries separated by newlines
        
        **Processing Rules:**
        1. Each transcript entry can have message, tool_call, and/or tool_result
        2. All present components are included as separate lines
        3. User role is mapped to "caller" for clarity
        4. Timestamps default to 0 if missing
        5. Empty/null data returns empty string
        
        Args:
            data: Optional conversation data containing:
                - transcript: List of TranscriptEntry objects
                - Each entry may have: role, message, timestamp, tool_call, tool_result
                Returns empty string if None or if transcript is empty.
        
        Returns:
            Multi-line formatted transcript string with timestamps.
            Empty string if no data or no transcript entries.
        
        Examples:
            Input:
            ```python
            data.transcript = [
                {"role": "agent", "message": "Hello", "timestamp": 0},
                {"role": "user", "message": "Hi", "timestamp": 2.5},
                {"role": "agent", "tool_call": {"name": "get_time"}, "timestamp": 5}
            ]
            ```
            
            Output:
            ```
            [00:00:00] - agent: Hello
            [00:00:02] - caller: Hi
            [00:00:05] - toolcall: get_time()
            ```
        
        Performance:
            - Linear time complexity: O(n) where n is number of transcript entries
            - Typical execution: <50ms for 100 entries
            - No API calls, pure string processing
        
        Note:
            - Timestamps are converted to integers (fractional seconds discarded)
            - Tool calls and results use helper methods _format_tool_call/_format_tool_result
            - Output suitable for LLM processing (consistent, structured format)
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
