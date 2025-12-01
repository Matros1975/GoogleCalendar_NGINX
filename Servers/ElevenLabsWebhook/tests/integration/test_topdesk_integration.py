"""
Integration tests for TopDesk ticket creation.

These tests require actual TopDesk and OpenAI API access.
Skip if credentials are not configured.
"""

import os
import json
import pytest
from pathlib import Path

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


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("TOPDESK_URL"),
    reason="TopDesk credentials not configured"
)
class TestCustomPayload:
    """Integration test for custom payload from JSON file."""
    
    @pytest.mark.asyncio
    async def test_custom_payload_create_ticket(self):
        """
        Test ticket creation using custom payload from custom_payload.json file.
        
        This test allows debugging with your own custom webhook payloads.
        Place your payload in: tests/integration/custom_payload.json
        
        Example payload structure:
        {
            "type": "post_call_transcription",
            "conversation_id": "conv_custom_123",
            "agent_id": "agent_custom",
            "data": {
                "transcript": [
                    {"role": "agent", "message": "Hello", "time_in_call_secs": 0},
                    {"role": "user", "message": "Hi", "time_in_call_secs": 2}
                ]
            }
        }
        """
        # Locate custom_payload.json
        payload_file = Path(__file__).parent / "custom_payload.json"
        
        if not payload_file.exists():
            pytest.skip(f"Custom payload file not found: {payload_file}")
        
        # Load custom payload
        with open(payload_file, 'r') as f:
            payload = json.load(f)
        
        print(f"\n=== CUSTOM PAYLOAD TEST ===")
        print(f"Loaded from: {payload_file}")
        print(f"Conversation ID: {payload.get('conversation_id', 'N/A')}")
        print(f"Agent ID: {payload.get('agent_id', 'N/A')}")
        
        # Process with handler
        handler = TranscriptionHandler(storage=None)
        result = await handler.handle(payload)
        
        # Display results
        print(f"\n=== PROCESSING RESULTS ===")
        print(f"Status: {result['status']}")
        print(f"Ticket created: {result['ticket_created']}")
        print(f"Ticket number: {result['ticket_number']}")
        print(f"Ticket ID: {result['ticket_id']}")
        print(f"Transcript added: {result['transcript_added']}")
        print(f"Email sent: {result['email_sent']}")
        if result.get('error'):
            print(f"Error: {result['error']}")
        print(f"==========================\n")
        
        # Basic assertions
        assert result["status"] == "processed"
        
        # If ticket creation succeeded, verify ticket details
        if result["ticket_created"]:
            assert result["ticket_number"] is not None
            assert result["ticket_number"].startswith("I")
            print(f"✅ Successfully created ticket: {result['ticket_number']}")
        else:
            print(f"⚠️  Ticket not created. Check error message above.")


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OpenAI API key not configured"
)
class TestOpenAIIntegration:
    """Integration tests requiring actual OpenAI API access."""
    
    @pytest.mark.asyncio
    async def test_extract_ticket_data_with_openai(self):
        """Test ticket data extraction using actual OpenAI API."""
        handler = TranscriptionHandler(storage=None)
        
        transcript = """[00:00:00] - agent: Support desk, how can I help you today?
[00:00:03] - caller: Hi, my name is John Smith and my email is john.smith@example.com
[00:00:08] - caller: My laptop screen is flickering and I can't work
[00:00:12] - agent: I understand, that sounds frustrating. Let me help you with that.
[00:00:18] - agent: Can you tell me the laptop model?
[00:00:22] - caller: It's a Dell Latitude 5520
[00:00:25] - agent: Thank you. I'll create a ticket for our hardware team to look into this."""
        
        result = await handler._extract_ticket_data(transcript)
        
        # Should extract meaningful data
        assert result.brief_description is not None
        assert len(result.brief_description) <= 80
        assert result.request is not None
        
        # Should extract caller info if mentioned
        # Note: This depends on OpenAI's extraction quality
        print(f"\n=== OPENAI EXTRACTION RESULTS ===")
        print(f"Brief description: {result.brief_description}")
        print(f"Request: {result.request}")
        print(f"Caller name: {result.caller_name}")
        print(f"Caller email: {result.caller_email}")
        print(f"Caller phone: {result.caller_phone}")
        print(f"Category: {result.category}")
        print(f"Priority: {result.priority}")
        print(f"=================================\n")
        
        # Verify caller info was extracted
        assert result.caller_name == "John Smith", f"Expected 'John Smith', got {result.caller_name}"
        assert result.caller_email == "john.smith@example.com", f"Expected email, got {result.caller_email}"
        assert result.category is not None, "Category should be extracted"
        assert "laptop" in result.request.lower() or "screen" in result.request.lower(), "Request should mention the issue"


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("GMAIL_SMTP_USERNAME"),
    reason="Gmail SMTP credentials not configured"
)
class TestEmailIntegration:
    """Integration tests requiring actual Gmail SMTP access."""
    
    @pytest.mark.asyncio
    async def test_send_error_notification(self):
        """Test sending actual error notification email."""
        from src.utils.email_sender import EmailSender
        
        sender = EmailSender()
        
        # Only run if sender is configured
        if not sender.is_configured():
            pytest.skip("Email sender not configured")
        
        result = await sender.send_error_notification(
            conversation_id="conv_integration_test",
            transcript="[00:00:00] - agent: Test transcript\n[00:00:02] - caller: Test message",
            error_message="Integration test - this is a test error notification",
            to_address=os.getenv("SERVICEDESK_EMAIL", "test@example.com")
        )
        
        # Should successfully send email
        assert result is True
        print("Error notification email sent successfully")
