"""
Integration tests for TopDesk ticket creation.

These tests require actual TopDesk and OpenAI API access.
Skip if credentials are not configured.
"""

import os
import pytest

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
        print(f"Brief description: {result.brief_description}")
        print(f"Caller name: {result.caller_name}")
        print(f"Caller email: {result.caller_email}")
        print(f"Category: {result.category}")


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
