# Task: Extend TranscriptionHandler with TopDesk Integration and AI-Powered Ticket Creation

## Objective
Extend the `TranscriptionHandler` in the ElevenLabs Webhook service to automatically create TopDesk tickets from call transcripts using OpenAI/LangChain for data extraction.

## Context
- **Repository**: GoogleCalendar_NGINX
- **Service**: Servers/ElevenLabsWebhook
- **File to modify**: `src/handlers/transcription_handler.py`
- **Test file**: `tests/unit/test_transcription_handler.py`
- **Reference implementation**: `Servers/TopDeskCustomMCP/` (for TopDesk API integration patterns)
- **Dependencies**: LangChain, OpenAI API, TopDesk API, Gmail SMTP

## Requirements

### 1. Human-Readable Transcript Text Generation

**Extend existing `_generate_formatted_transcript()` method:**
- Already implemented: timestamp formatting `[HH:MM:SS]`, role mapping (`user` → `caller`), tool call logging
- Use this formatted transcript as input for OpenAI extraction

### 2. OpenAI/LangChain Integration

**Add LangChain framework for AI-powered data extraction:**

```python
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import Optional

class TicketDataPayload(BaseModel):
    """Schema for TopDesk ticket creation from transcript."""
    brief_description: str = Field(description="Short summary of the issue (max 80 chars)")
    request: str = Field(description="Detailed description of the customer's request")
    caller_name: Optional[str] = Field(None, description="Caller's name if mentioned")
    caller_email: Optional[str] = Field(None, description="Caller's email if mentioned")
    caller_phone: Optional[str] = Field(None, description="Caller's phone number if mentioned")
    category: Optional[str] = Field(None, description="Issue category (e.g., 'Hardware', 'Software', 'Network')")
    priority: Optional[str] = Field(None, description="Priority level if determinable from urgency")
```

**Implementation in TranscriptionHandler:**

```python
class TranscriptionHandler(BaseToolHandler):
    def __init__(self, storage: Optional[StorageManager] = None):
        super().__init__()
        self.storage = storage
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",  # or gpt-4o for better accuracy
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.topdesk_client = None  # Initialize in async method
        self.email_sender = None  # Initialize with SMTP config
    
    async def _extract_ticket_data(self, transcript: str) -> TicketDataPayload:
        """
        Extract ticket creation data from formatted transcript using OpenAI.
        
        Args:
            transcript: Human-readable formatted transcript
            
        Returns:
            TicketDataPayload with extracted information
        """
        parser = PydanticOutputParser(pydantic_object=TicketDataPayload)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an AI assistant that extracts ticket information from call transcripts.
            Analyze the conversation and extract:
            - A brief description (max 80 characters)
            - Detailed request description
            - Caller information if mentioned
            - Issue category and priority
            
            {format_instructions}"""),
            ("human", "Call transcript:\n\n{transcript}")
        ])
        
        chain = prompt | self.llm | parser
        
        try:
            result = await chain.ainvoke({
                "transcript": transcript,
                "format_instructions": parser.get_format_instructions()
            })
            return result
        except Exception as e:
            logger.error(f"Failed to extract ticket data: {e}")
            # Fallback: create minimal ticket data
            return TicketDataPayload(
                brief_description="Call transcript - AI extraction failed",
                request=transcript[:500]  # First 500 chars
            )
```

### 3. TopDesk API Integration

**Reference implementation from `Servers/TopDeskCustomMCP/src/topdesk_client.py`:**

```python
class TopDeskClient:
    """TopDesk API client (reuse from TopDeskCustomMCP)."""
    
    def __init__(self):
        self.base_url = os.getenv("TOPDESK_URL")
        self.username = os.getenv("TOPDESK_USERNAME")
        self.password = os.getenv("TOPDESK_PASSWORD")
        self.session = None
    
    async def create_incident(self, ticket_data: TicketDataPayload, conversation_id: str) -> dict:
        """
        Create incident in TopDesk.
        
        Args:
            ticket_data: Extracted ticket information
            conversation_id: ElevenLabs conversation ID for reference
            
        Returns:
            dict with 'success', 'ticket_number', 'ticket_id'
        """
        # Implementation pattern from TopDeskCustomMCP
        # Format ticket_number as I0000 000 (7 digits with zero-padding)
        pass
    
    async def add_invisible_action(self, ticket_id: str, transcript: str) -> bool:
        """
        Add transcript as invisible action to ticket.
        
        Args:
            ticket_id: TopDesk ticket ID (number.id from API response)
            transcript: Formatted transcript text
            
        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/tas/api/incidents/id/{ticket_id}/actions"
        payload = {
            "memoText": transcript,
            "invisibleForCaller": True
        }
        # POST to action endpoint
        pass
```

**Environment Variables (.env):**
```env
# OpenAI
OPENAI_API_KEY=sk-...

# TopDesk API (shared with TopDeskCustomMCP)
TOPDESK_URL=https://your-instance.topdesk.net
TOPDESK_USERNAME=api_user
TOPDESK_PASSWORD=api_password

# Gmail SMTP for error notifications
GMAIL_SMTP_HOST=smtp.gmail.com
GMAIL_SMTP_PORT=587
GMAIL_SMTP_USERNAME=your-email@gmail.com
GMAIL_SMTP_PASSWORD=your-app-password
GMAIL_FROM_ADDRESS=your-email@gmail.com
SERVICEDESK_EMAIL=servicedesk@pvforeest.nl
```

### 4. Email Notification on Failure

**Implement email sender for error cases:**

```python
import aiosmtplib
from email.message import EmailMessage

class EmailSender:
    """Send email notifications via Gmail SMTP."""
    
    def __init__(self):
        self.smtp_host = os.getenv("GMAIL_SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("GMAIL_SMTP_PORT", "587"))
        self.username = os.getenv("GMAIL_SMTP_USERNAME")
        self.password = os.getenv("GMAIL_SMTP_PASSWORD")
        self.from_address = os.getenv("GMAIL_FROM_ADDRESS")
    
    async def send_error_notification(
        self, 
        conversation_id: str, 
        transcript: str, 
        error_message: str,
        to_address: str = None
    ) -> bool:
        """
        Send email notification when ticket creation fails.
        
        Args:
            conversation_id: ElevenLabs conversation ID
            transcript: Call transcript
            error_message: Error details
            to_address: Recipient email (defaults to SERVICEDESK_EMAIL)
            
        Returns:
            True if email sent successfully
        """
        to_address = to_address or os.getenv("SERVICEDESK_EMAIL", "servicedesk@pvforeest.nl")
        
        message = EmailMessage()
        message["From"] = self.from_address
        message["To"] = to_address
        message["Subject"] = f"[ElevenLabs] Failed to create ticket - {conversation_id}"
        
        body = f"""
A call transcript could not be processed into a TopDesk ticket.

Conversation ID: {conversation_id}
Error: {error_message}

Call Transcript:
{transcript}

Please create a ticket manually.
        """
        message.set_content(body)
        
        try:
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.username,
                password=self.password,
                start_tls=True
            )
            logger.info(f"Error notification sent to {to_address}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
```

### 5. Updated TranscriptionHandler.handle() Method

**Modify the main handler to orchestrate the workflow:**

```python
async def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process transcription webhook and create TopDesk ticket.
    
    Returns:
        dict with keys:
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
    # 1. Parse payload (existing code)
    transcription = PostCallTranscription(**payload)
    
    # 2. Generate formatted transcript (existing code)
    formatted_transcript = self._generate_formatted_transcript(transcription.data)
    
    # 3. Save to storage (existing code)
    saved_path = None
    if self.storage:
        saved_path = await self.storage.save_transcription(transcription)
    
    # 4. Initialize result dict
    result = {
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
    
    # 5. Skip ticket creation if no transcript
    if not formatted_transcript:
        logger.warning(f"No transcript for {transcription.conversation_id}, skipping ticket creation")
        return result
    
    try:
        # 6. Extract ticket data using OpenAI
        ticket_data = await self._extract_ticket_data(formatted_transcript)
        
        # 7. Initialize TopDesk client if needed
        if not self.topdesk_client:
            self.topdesk_client = TopDeskClient()
        
        # 8. Create TopDesk incident
        ticket_response = await self.topdesk_client.create_incident(
            ticket_data, 
            transcription.conversation_id
        )
        
        if ticket_response["success"]:
            result["ticket_created"] = True
            result["ticket_number"] = ticket_response["ticket_number"]
            result["ticket_id"] = ticket_response["ticket_id"]
            
            logger.info(f"Created ticket {ticket_response['ticket_number']} for {transcription.conversation_id}")
            
            # 9. Add transcript as invisible action
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
                    # Don't send email if ticket was created, just log warning
            except Exception as e:
                logger.error(f"Error adding transcript to ticket: {e}")
                result["transcript_added"] = False
        else:
            # Ticket creation failed
            raise Exception(f"TopDesk API error: {ticket_response.get('error', 'Unknown error')}")
    
    except Exception as e:
        # 10. Send email notification on failure
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
```

### 6. Dependencies Update

**Add to `Servers/ElevenLabsWebhook/requirements.txt`:**

```txt
# Existing dependencies...

# LangChain and OpenAI
langchain>=0.1.0
langchain-openai>=0.0.5
openai>=1.10.0

# Email
aiosmtplib>=3.0.0

# HTTP client for TopDesk API (if not already present)
httpx>=0.25.0
```

### 7. Unit Tests

**Add comprehensive tests to `tests/unit/test_transcription_handler.py`:**

```python
class TestTopDeskIntegration:
    """Tests for TopDesk ticket creation integration."""
    
    @pytest.fixture
    def handler_with_mocks(self, mocker):
        """Create handler with mocked dependencies."""
        handler = TranscriptionHandler(storage=None)
        
        # Mock OpenAI LLM
        mock_llm = mocker.AsyncMock()
        handler.llm = mock_llm
        
        # Mock TopDesk client
        mock_topdesk = mocker.AsyncMock()
        handler.topdesk_client = mock_topdesk
        
        # Mock email sender
        mock_email = mocker.AsyncMock()
        handler.email_sender = mock_email
        
        return handler, mock_llm, mock_topdesk, mock_email
    
    @pytest.mark.asyncio
    async def test_successful_ticket_creation_with_transcript(self, handler_with_mocks):
        """Test successful ticket creation and transcript addition."""
        handler, mock_llm, mock_topdesk, mock_email = handler_with_mocks
        
        # Mock OpenAI extraction
        mock_ticket_data = TicketDataPayload(
            brief_description="Customer needs password reset",
            request="Customer called requesting password reset for email account.",
            caller_name="John Doe",
            caller_email="john@example.com"
        )
        handler._extract_ticket_data = AsyncMock(return_value=mock_ticket_data)
        
        # Mock TopDesk ticket creation
        mock_topdesk.create_incident.return_value = {
            "success": True,
            "ticket_number": "I0001234",
            "ticket_id": "1234-5678"
        }
        
        # Mock transcript addition
        mock_topdesk.add_invisible_action.return_value = True
        
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_test",
            "agent_id": "agent_test",
            "data": {
                "transcript": [
                    {"role": "agent", "message": "How can I help?", "time_in_call_secs": 0},
                    {"role": "user", "message": "I need a password reset", "time_in_call_secs": 2}
                ]
            }
        }
        
        result = await handler.handle(payload)
        
        # Validate results
        assert result["status"] == "processed"
        assert result["ticket_created"] is True
        assert result["ticket_number"] == "I0001234"
        assert result["ticket_id"] == "1234-5678"
        assert result["transcript_added"] is True
        assert result["email_sent"] is False
        assert result["error"] is None
        
        # Verify TopDesk client was called correctly
        mock_topdesk.create_incident.assert_called_once()
        mock_topdesk.add_invisible_action.assert_called_once_with(
            "1234-5678",
            result["formatted_transcript"]
        )
        
        # Verify email was not sent
        mock_email.send_error_notification.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_ticket_creation_failure_sends_email(self, handler_with_mocks):
        """Test email notification when ticket creation fails."""
        handler, mock_llm, mock_topdesk, mock_email = handler_with_mocks
        
        # Mock OpenAI extraction
        mock_ticket_data = TicketDataPayload(
            brief_description="Test issue",
            request="Test request"
        )
        handler._extract_ticket_data = AsyncMock(return_value=mock_ticket_data)
        
        # Mock TopDesk ticket creation failure
        mock_topdesk.create_incident.return_value = {
            "success": False,
            "error": "API authentication failed"
        }
        
        # Mock email sending
        mock_email.send_error_notification.return_value = True
        
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_error",
            "agent_id": "agent_test",
            "data": {
                "transcript": [
                    {"role": "user", "message": "Help needed", "time_in_call_secs": 0}
                ]
            }
        }
        
        result = await handler.handle(payload)
        
        # Validate results
        assert result["ticket_created"] is False
        assert result["ticket_number"] is None
        assert result["email_sent"] is True
        assert result["error"] is not None
        assert "API authentication failed" in result["error"]
        
        # Verify email was sent
        mock_email.send_error_notification.assert_called_once()
        call_args = mock_email.send_error_notification.call_args
        assert call_args[0][0] == "conv_error"  # conversation_id
        assert "Help needed" in call_args[0][1]  # transcript
    
    @pytest.mark.asyncio
    async def test_transcript_addition_failure_no_email(self, handler_with_mocks):
        """Test that email is NOT sent if only transcript addition fails."""
        handler, mock_llm, mock_topdesk, mock_email = handler_with_mocks
        
        handler._extract_ticket_data = AsyncMock(return_value=TicketDataPayload(
            brief_description="Test", request="Test"
        ))
        
        # Ticket created successfully
        mock_topdesk.create_incident.return_value = {
            "success": True,
            "ticket_number": "I0001235",
            "ticket_id": "1235-5678"
        }
        
        # But transcript addition fails
        mock_topdesk.add_invisible_action.return_value = False
        
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_test2",
            "agent_id": "agent_test",
            "data": {
                "transcript": [{"role": "user", "message": "Test", "time_in_call_secs": 0}]
            }
        }
        
        result = await handler.handle(payload)
        
        # Ticket created but transcript not added
        assert result["ticket_created"] is True
        assert result["transcript_added"] is False
        assert result["email_sent"] is False  # No email because ticket was created
    
    @pytest.mark.asyncio
    async def test_openai_extraction_failure_fallback(self, handler_with_mocks):
        """Test fallback behavior when OpenAI extraction fails."""
        handler, mock_llm, mock_topdesk, mock_email = handler_with_mocks
        
        # Mock extraction failure
        async def failing_extract(transcript):
            raise Exception("OpenAI API timeout")
        
        handler._extract_ticket_data = failing_extract
        
        # Mock successful ticket creation with fallback data
        mock_topdesk.create_incident.return_value = {
            "success": True,
            "ticket_number": "I0001236",
            "ticket_id": "1236-5678"
        }
        mock_topdesk.add_invisible_action.return_value = True
        
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_extract_fail",
            "agent_id": "agent_test",
            "data": {
                "transcript": [{"role": "user", "message": "Help", "time_in_call_secs": 0}]
            }
        }
        
        result = await handler.handle(payload)
        
        # Should still create ticket with fallback data
        assert result["error"] is not None
        assert result["email_sent"] is True  # Email sent because extraction failed
    
    @pytest.mark.asyncio
    async def test_empty_transcript_skips_ticket_creation(self, handler):
        """Test that no ticket is created for empty transcripts."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_empty",
            "agent_id": "agent_test",
            "data": {}
        }
        
        result = await handler.handle(payload)
        
        assert result["ticket_created"] is False
        assert result["email_sent"] is False
        assert result["formatted_transcript"] == ""
```

### 8. Integration Tests

**Create `tests/integration/test_topdesk_integration.py`:**

```python
"""Integration tests for TopDesk ticket creation."""

import pytest
import os
from src.handlers.transcription_handler import TranscriptionHandler

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("TOPDESK_URL"),
    reason="TopDesk credentials not configured"
)
class TestTopDeskIntegration:
    """Integration tests requiring actual TopDesk and OpenAI access."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_ticket_creation(self):
        """Test actual ticket creation in TopDesk."""
        handler = TranscriptionHandler(storage=None)
        
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_integration_test",
            "agent_id": "agent_test",
            "data": {
                "transcript": [
                    {"role": "agent", "message": "Support desk, how can I help?", "time_in_call_secs": 0},
                    {"role": "user", "message": "My computer won't turn on", "time_in_call_secs": 2},
                    {"role": "agent", "message": "Let me create a ticket for you", "time_in_call_secs": 5}
                ]
            }
        }
        
        result = await handler.handle(payload)
        
        # Should successfully create ticket
        assert result["ticket_created"] is True
        assert result["ticket_number"] is not None
        assert result["ticket_number"].startswith("I")
        assert result["transcript_added"] is True
        
        print(f"Created ticket: {result['ticket_number']}")
```

### 9. Configuration Files

**Update `.env.example`:**

```env
# ... existing config ...

# OpenAI API
OPENAI_API_KEY=sk-your-key-here

# TopDesk API (shared with TopDeskCustomMCP)
TOPDESK_URL=https://your-instance.topdesk.net
TOPDESK_USERNAME=api_user
TOPDESK_PASSWORD=your_password

# Gmail SMTP for error notifications
GMAIL_SMTP_HOST=smtp.gmail.com
GMAIL_SMTP_PORT=587
GMAIL_SMTP_USERNAME=your-email@gmail.com
GMAIL_SMTP_PASSWORD=your-gmail-app-password
GMAIL_FROM_ADDRESS=your-email@gmail.com
SERVICEDESK_EMAIL=servicedesk@pvforeest.nl
```

### 10. Implementation Checklist

- [ ] Add LangChain, OpenAI, and aiosmtplib to `requirements.txt`
- [ ] Create `TicketDataPayload` Pydantic model
- [ ] Implement `_extract_ticket_data()` method with OpenAI/LangChain
- [ ] Create `TopDeskClient` class (reuse patterns from TopDeskCustomMCP)
- [ ] Implement `create_incident()` method in TopDeskClient
- [ ] Implement `add_invisible_action()` method for transcript attachment
- [ ] Create `EmailSender` class with Gmail SMTP
- [ ] Implement `send_error_notification()` method
- [ ] Update `handle()` method with full workflow orchestration
- [ ] Add environment variables to `.env.example`
- [ ] Create unit tests for all new methods (minimum 10 test cases)
- [ ] Create integration tests for end-to-end workflow
- [ ] Test with actual TopDesk and OpenAI APIs
- [ ] Verify email notifications work correctly
- [ ] Document ticket number format (I0000 000)
- [ ] Ensure backward compatibility (existing tests still pass)

### 11. Success Criteria

✅ All existing tests pass (no regressions)  
✅ New unit tests pass (minimum 10 test cases)  
✅ Integration tests pass with real APIs  
✅ Formatted transcript is used for OpenAI extraction  
✅ TopDesk ticket created with correct format (I0000 000)  
✅ Transcript added as invisible action to ticket  
✅ Email notification sent on ticket creation failure  
✅ Email notification sent on OpenAI extraction failure  
✅ Return dict includes all required fields for validation  
✅ Error handling covers all failure scenarios  
✅ Code follows existing patterns in repository  

## References

- **Existing handler**: `Servers/ElevenLabsWebhook/src/handlers/transcription_handler.py`
- **TopDesk patterns**: `Servers/TopDeskCustomMCP/src/topdesk_client.py`
- **Existing tests**: `Servers/ElevenLabsWebhook/tests/unit/test_transcription_handler.py`
- **LangChain docs**: https://python.langchain.com/docs/get_started/introduction
- **OpenAI docs**: https://platform.openai.com/docs/api-reference
- **TopDesk API**: https://developers.topdesk.com/documentation/index.html
- **aiosmtplib docs**: https://aiosmtplib.readthedocs.io/

## Notes

- **Credentials sharing**: Use same TopDesk credentials as TopDeskCustomMCP (check `.env` for TOPDESK_URL, TOPDESK_USERNAME, TOPDESK_PASSWORD)
- **Ticket number format**: Follow TopDeskCustomMCP pattern - 7 digits with zero-padding, formatted as `I0000 000`
- **Error handling**: Only send email if ticket creation fails, not for transcript addition failures
- **OpenAI model**: Use `gpt-4o-mini` for cost efficiency, or `gpt-4o` for better accuracy
- **Gmail SMTP**: Requires app-specific password for Gmail accounts with 2FA
- **Async patterns**: All API calls must be async (use `httpx.AsyncClient`, `aiosmtplib`, `langchain` async methods)
- **Logging**: Use existing logger for all operations (info, warning, error levels)
- **Testing isolation**: Use `pytest-asyncio` for async tests, `mocker` for mocking dependencies
