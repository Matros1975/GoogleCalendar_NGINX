"""
Unit tests for TranscriptionHandler.
"""

import pytest

from src.handlers.transcription_handler import TranscriptionHandler


class TestTranscriptionHandler:
    """Tests for TranscriptionHandler class."""
    
    @pytest.fixture
    def handler(self):
        """Create handler instance for testing."""
        return TranscriptionHandler(storage=None)
    
    @pytest.mark.asyncio
    async def test_handle_valid_payload(self, handler, sample_transcription_payload):
        """Test handling of valid transcription payload."""
        result = await handler.handle(sample_transcription_payload)
        
        assert result["status"] == "processed"
        assert result["conversation_id"] == "conv_test_123"
        assert result["agent_id"] == "agent_test_456"
    
    @pytest.mark.asyncio
    async def test_handle_minimal_payload(self, handler):
        """Test handling of minimal payload without data."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_minimal",
            "agent_id": "agent_minimal"
        }
        
        result = await handler.handle(payload)
        
        assert result["status"] == "processed"
        assert result["conversation_id"] == "conv_minimal"
    
    @pytest.mark.asyncio
    async def test_handle_payload_with_empty_data(self, handler):
        """Test handling of payload with empty data object."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_empty",
            "agent_id": "agent_empty",
            "data": {}
        }
        
        result = await handler.handle(payload)
        
        assert result["status"] == "processed"
    
    @pytest.mark.asyncio
    async def test_handle_payload_with_analysis(self, handler, sample_transcription_payload):
        """Test handling of payload with analysis results."""
        result = await handler.handle(sample_transcription_payload)
        
        # Should process without error
        assert result["status"] == "processed"
    
    @pytest.mark.asyncio
    async def test_handle_payload_with_audio_availability_fields(self, handler):
        """Test handling of payload with new audio availability fields (August 2025)."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_audio",
            "agent_id": "agent_audio",
            "data": {
                "conversation_id": "conv_audio",
                "agent_id": "agent_audio",
                "has_audio": True,
                "has_user_audio": True,
                "has_response_audio": True,
                "transcript": []
            }
        }
        
        result = await handler.handle(payload)
        
        assert result["status"] == "processed"
    
    @pytest.mark.asyncio
    async def test_handle_payload_with_metadata(self, handler):
        """Test handling of payload with dynamic variables/metadata."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_meta",
            "agent_id": "agent_meta",
            "data": {
                "conversation_id": "conv_meta",
                "agent_id": "agent_meta",
                "metadata": {
                    "customer_id": "cust_123",
                    "order_number": "12345",
                    "custom_field": "custom_value"
                }
            }
        }
        
        result = await handler.handle(payload)
        
        assert result["status"] == "processed"
    
    @pytest.mark.asyncio
    async def test_handle_payload_with_long_transcript(self, handler):
        """Test handling of payload with many transcript entries."""
        transcript = [
            {"role": "agent" if i % 2 == 0 else "user", "message": f"Message {i}", "time_in_call_secs": i * 2.0}
            for i in range(100)
        ]
        
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_long",
            "agent_id": "agent_long",
            "data": {
                "conversation_id": "conv_long",
                "agent_id": "agent_long",
                "transcript": transcript
            }
        }
        
        result = await handler.handle(payload)
        
        assert result["status"] == "processed"


class TestFormattedTranscript:
    """Tests for formatted transcript generation."""
    
    @pytest.fixture
    def handler(self):
        """Create handler instance for testing."""
        return TranscriptionHandler(storage=None)
    
    @pytest.mark.asyncio
    async def test_formatted_transcript_basic(self, handler):
        """Test basic transcript formatting without tool calls."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_format_test",
            "agent_id": "agent_test",
            "data": {
                "transcript": [
                    {
                        "role": "agent",
                        "message": "Hello! How can I help?",
                        "time_in_call_secs": 0.5
                    },
                    {
                        "role": "user",
                        "message": "I need assistance",
                        "time_in_call_secs": 3.2
                    }
                ]
            }
        }
        
        result = await handler.handle(payload)
        
        assert "formatted_transcript" in result
        transcript = result["formatted_transcript"]
        
        # Validate format
        assert "[00:00:00] - agent: Hello! How can I help?" in transcript
        assert "[00:00:03] - caller: I need assistance" in transcript
    
    @pytest.mark.asyncio
    async def test_formatted_transcript_with_tool_calls(self, handler):
        """Test transcript formatting with tool calls."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_tool_test",
            "agent_id": "agent_test",
            "data": {
                "transcript": [
                    {
                        "role": "agent",
                        "message": "Let me check that for you",
                        "time_in_call_secs": 8.1,
                        "tool_call": {
                            "name": "get_order_status",
                            "arguments": "{\"order_id\": \"12345\"}"
                        }
                    },
                    {
                        "role": "agent",
                        "message": "",
                        "time_in_call_secs": 10.5,
                        "tool_result": {
                            "output": "{\"status\": \"shipped\", \"tracking\": \"ABC123\"}"
                        }
                    }
                ]
            }
        }
        
        result = await handler.handle(payload)
        transcript = result["formatted_transcript"]
        
        # Validate tool call formatting
        assert "toolcall: get_order_status" in transcript
        assert 'order_id="12345"' in transcript
        assert "toolcall_result:" in transcript
        assert '"status": "shipped"' in transcript
    
    @pytest.mark.asyncio
    async def test_formatted_transcript_timestamp_conversion(self, handler):
        """Test timestamp formatting (seconds to HH:MM:SS)."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_time_test",
            "agent_id": "agent_test",
            "data": {
                "transcript": [
                    {"role": "agent", "message": "Start", "time_in_call_secs": 0},
                    {"role": "agent", "message": "One minute", "time_in_call_secs": 65},
                    {"role": "agent", "message": "One hour", "time_in_call_secs": 3665}
                ]
            }
        }
        
        result = await handler.handle(payload)
        transcript = result["formatted_transcript"]
        
        assert "[00:00:00]" in transcript
        assert "[00:01:05]" in transcript
        assert "[01:01:05]" in transcript
    
    @pytest.mark.asyncio
    async def test_formatted_transcript_empty(self, handler):
        """Test handling of missing or empty transcript."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_empty",
            "agent_id": "agent_test",
            "data": {}
        }
        
        result = await handler.handle(payload)
        
        # Should handle gracefully
        assert result["formatted_transcript"] == ""
    
    @pytest.mark.asyncio
    async def test_formatted_transcript_role_mapping(self, handler):
        """Test that 'user' role is mapped to 'caller'."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_role_test",
            "agent_id": "agent_test",
            "data": {
                "transcript": [
                    {"role": "user", "message": "Hello", "time_in_call_secs": 1.0}
                ]
            }
        }
        
        result = await handler.handle(payload)
        transcript = result["formatted_transcript"]
        
        # 'user' should be displayed as 'caller'
        assert "caller:" in transcript
        assert "user:" not in transcript
    
    @pytest.mark.asyncio
    async def test_formatted_transcript_no_data(self, handler):
        """Test handling when data is None."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_no_data",
            "agent_id": "agent_test"
        }
        
        result = await handler.handle(payload)
        
        assert result["formatted_transcript"] == ""
    
    @pytest.mark.asyncio
    async def test_formatted_transcript_tool_call_with_dict_arguments(self, handler):
        """Test tool call formatting when arguments are already a dict."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_dict_args",
            "agent_id": "agent_test",
            "data": {
                "transcript": [
                    {
                        "role": "agent",
                        "message": "Checking",
                        "time_in_call_secs": 5.0,
                        "tool_call": {
                            "name": "search_orders",
                            "arguments": {"customer_id": "cust_123", "limit": 10}
                        }
                    }
                ]
            }
        }
        
        result = await handler.handle(payload)
        transcript = result["formatted_transcript"]
        
        assert "toolcall: search_orders" in transcript
        assert 'customer_id="cust_123"' in transcript
        assert 'limit="10"' in transcript
    
    @pytest.mark.asyncio
    async def test_formatted_transcript_tool_result_with_dict_output(self, handler):
        """Test tool result formatting when output is already a dict."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_dict_output",
            "agent_id": "agent_test",
            "data": {
                "transcript": [
                    {
                        "role": "agent",
                        "message": "",
                        "time_in_call_secs": 10.0,
                        "tool_result": {
                            "output": {"status": "success", "count": 5}
                        }
                    }
                ]
            }
        }
        
        result = await handler.handle(payload)
        transcript = result["formatted_transcript"]
        
        assert "toolcall_result:" in transcript
        # Dict should be serialized to JSON
        assert "status" in transcript
        assert "success" in transcript
    
    @pytest.mark.asyncio
    async def test_formatted_transcript_tool_call_with_quotes_in_value(self, handler):
        """Test tool call formatting when arguments contain quotes."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_quotes",
            "agent_id": "agent_test",
            "data": {
                "transcript": [
                    {
                        "role": "agent",
                        "message": "Searching",
                        "time_in_call_secs": 5.0,
                        "tool_call": {
                            "name": "search",
                            "arguments": {"query": 'test "quoted" value'}
                        }
                    }
                ]
            }
        }
        
        result = await handler.handle(payload)
        transcript = result["formatted_transcript"]
        
        # Quotes should be escaped
        assert "toolcall: search" in transcript
        assert '\\"quoted\\"' in transcript


class TestTopDeskIntegration:
    """Tests for TopDesk ticket creation integration."""
    
    @pytest.fixture
    def handler(self):
        """Create handler instance for testing."""
        return TranscriptionHandler(storage=None)
    
    @pytest.fixture
    def handler_with_mocks(self, mocker):
        """Create handler with mocked dependencies."""
        handler = TranscriptionHandler(storage=None)
        
        # Mock TopDesk client
        mock_topdesk = mocker.AsyncMock()
        handler.topdesk_client = mock_topdesk
        
        # Mock email sender
        mock_email = mocker.AsyncMock()
        handler.email_sender = mock_email
        
        return handler, mock_topdesk, mock_email
    
    @pytest.mark.asyncio
    async def test_successful_ticket_creation_with_transcript(self, handler_with_mocks, mocker):
        """Test successful ticket creation and transcript addition."""
        handler, mock_topdesk, mock_email = handler_with_mocks
        
        # Mock OpenAI extraction with fallback
        from src.handlers.transcription_handler import TicketDataPayload
        mock_ticket_data = TicketDataPayload(
            brief_description="Customer needs password reset",
            request="Customer called requesting password reset for email account.",
            caller_name="John Doe",
            caller_email="john@example.com"
        )
        handler._extract_ticket_data = mocker.AsyncMock(return_value=mock_ticket_data)
        
        # Mock TopDesk ticket creation
        mock_topdesk.create_incident.return_value = {
            "success": True,
            "ticket_number": "I0001 234",
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
        assert result["ticket_number"] == "I0001 234"
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
    async def test_ticket_creation_failure_sends_email(self, handler_with_mocks, mocker):
        """Test email notification when ticket creation fails."""
        handler, mock_topdesk, mock_email = handler_with_mocks
        
        # Mock OpenAI extraction with fallback
        from src.handlers.transcription_handler import TicketDataPayload
        mock_ticket_data = TicketDataPayload(
            brief_description="Test issue",
            request="Test request"
        )
        handler._extract_ticket_data = mocker.AsyncMock(return_value=mock_ticket_data)
        
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
    async def test_transcript_addition_failure_no_email(self, handler_with_mocks, mocker):
        """Test that email is NOT sent if only transcript addition fails."""
        handler, mock_topdesk, mock_email = handler_with_mocks
        
        from src.handlers.transcription_handler import TicketDataPayload
        handler._extract_ticket_data = mocker.AsyncMock(return_value=TicketDataPayload(
            brief_description="Test", request="Test"
        ))
        
        # Ticket created successfully
        mock_topdesk.create_incident.return_value = {
            "success": True,
            "ticket_number": "I0001 235",
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
    
    @pytest.mark.asyncio
    async def test_result_contains_all_required_fields(self, handler):
        """Test that result dict contains all required fields."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_fields",
            "agent_id": "agent_test",
            "data": {}
        }
        
        result = await handler.handle(payload)
        
        # Verify all required fields exist
        required_fields = [
            "status", "conversation_id", "agent_id", "saved_path",
            "formatted_transcript", "ticket_created", "ticket_number",
            "ticket_id", "transcript_added", "email_sent", "error"
        ]
        
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
    
    @pytest.mark.asyncio
    async def test_fallback_ticket_extraction_no_openai(self, handler):
        """Test fallback extraction when OpenAI is not configured."""
        # No OPENAI_API_KEY set
        transcript = "[00:00:00] - agent: Hello\n[00:00:02] - caller: I need help with my password"
        
        result = await handler._extract_ticket_data(transcript)
        
        # Should return valid TicketDataPayload
        assert result.brief_description is not None
        assert result.request is not None
        assert len(result.brief_description) <= 80
    
    @pytest.mark.asyncio
    async def test_fallback_extraction_extracts_caller_message(self, handler):
        """Test that fallback extraction extracts caller message as brief description."""
        transcript = "[00:00:00] - agent: How can I help?\n[00:00:02] - caller: My computer won't start"
        
        result = handler._fallback_ticket_extraction(transcript)
        
        assert "My computer won't start" in result.brief_description
        assert transcript in result.request
    
    @pytest.mark.asyncio
    async def test_ticket_data_payload_validation(self):
        """Test TicketDataPayload model validation."""
        from src.handlers.transcription_handler import TicketDataPayload
        
        # Valid minimal payload
        payload = TicketDataPayload(
            brief_description="Test issue",
            request="Detailed test request"
        )
        assert payload.brief_description == "Test issue"
        assert payload.request == "Detailed test request"
        assert payload.caller_name is None
        
        # Valid full payload
        full_payload = TicketDataPayload(
            brief_description="Full test",
            request="Full request",
            caller_name="John Doe",
            caller_email="john@example.com",
            caller_phone="+31612345678",
            category="Hardware",
            priority="High"
        )
        assert full_payload.caller_name == "John Doe"
        assert full_payload.category == "Hardware"


class TestTopDeskClient:
    """Tests for TopDeskClient class."""
    
    @pytest.fixture
    def client(self, mocker):
        """Create TopDeskClient with mocked environment."""
        mocker.patch.dict('os.environ', {
            'TOPDESK_URL': 'https://test.topdesk.net',
            'TOPDESK_USERNAME': 'test_user',
            'TOPDESK_PASSWORD': 'test_pass'
        })
        from src.utils.topdesk_client import TopDeskClient
        return TopDeskClient()
    
    def test_client_initialization(self, client):
        """Test TopDeskClient initializes correctly from env."""
        assert client.base_url == 'https://test.topdesk.net'
        assert client.username == 'test_user'
        assert client.auth_header.startswith('Basic ')
    
    @pytest.mark.asyncio
    async def test_create_incident_no_url(self, mocker):
        """Test create_incident returns error when URL not configured."""
        mocker.patch.dict('os.environ', {
            'TOPDESK_URL': '',
            'TOPDESK_USERNAME': '',
            'TOPDESK_PASSWORD': ''
        }, clear=True)
        from src.utils.topdesk_client import TopDeskClient
        client = TopDeskClient()
        
        result = await client.create_incident(
            brief_description="Test",
            request="Test request",
            conversation_id="conv_123"
        )
        
        assert result["success"] is False
        assert "not configured" in result["error"]
    
    @pytest.mark.asyncio
    async def test_add_invisible_action_no_ticket_id(self, client):
        """Test add_invisible_action returns False when no ticket_id."""
        result = await client.add_invisible_action("", "transcript")
        assert result is False


class TestEmailSender:
    """Tests for EmailSender class."""
    
    @pytest.fixture
    def sender(self, mocker):
        """Create EmailSender with mocked environment."""
        mocker.patch.dict('os.environ', {
            'GMAIL_SMTP_HOST': 'smtp.gmail.com',
            'GMAIL_SMTP_PORT': '587',
            'GMAIL_SMTP_USERNAME': 'test@gmail.com',
            'GMAIL_SMTP_PASSWORD': 'test_password',
            'GMAIL_FROM_ADDRESS': 'test@gmail.com',
            'SERVICEDESK_EMAIL': 'servicedesk@test.nl'
        })
        from src.utils.email_sender import EmailSender
        return EmailSender()
    
    def test_sender_initialization(self, sender):
        """Test EmailSender initializes correctly from env."""
        assert sender.smtp_host == 'smtp.gmail.com'
        assert sender.smtp_port == 587
        assert sender.username == 'test@gmail.com'
        assert sender.is_configured() is True
    
    def test_sender_not_configured(self, mocker):
        """Test is_configured returns False when not configured."""
        mocker.patch.dict('os.environ', {
            'GMAIL_SMTP_USERNAME': '',
            'GMAIL_SMTP_PASSWORD': ''
        }, clear=True)
        from src.utils.email_sender import EmailSender
        sender = EmailSender()
        
        assert sender.is_configured() is False
    
    @pytest.mark.asyncio
    async def test_send_error_notification_not_configured(self, mocker):
        """Test send_error_notification returns False when not configured."""
        mocker.patch.dict('os.environ', {
            'GMAIL_SMTP_USERNAME': '',
            'GMAIL_SMTP_PASSWORD': ''
        }, clear=True)
        from src.utils.email_sender import EmailSender
        sender = EmailSender()
        
        result = await sender.send_error_notification(
            conversation_id="conv_123",
            transcript="test transcript",
            error_message="test error"
        )
        
        assert result is False
