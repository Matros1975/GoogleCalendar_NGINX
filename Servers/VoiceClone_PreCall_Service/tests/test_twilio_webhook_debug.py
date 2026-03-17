"""
Baseline tests for Twilio webhook handlers.

These tests ensure the refactored code maintains compatibility with
the original Twilio integration.
"""

import pytest
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Set environment variables before importing modules
os.environ["ELEVENLABS_API_KEY"] = "test_key"
os.environ["ELEVENLABS_AGENT_ID"] = "test_agent"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost/test"
os.environ["WEBHOOK_SECRET"] = "test_secret"
os.environ["SKIP_WEBHOOK_SIGNATURE_VALIDATION"] = "true"

from src.models.call_context import CallContext
from src.models.call_instructions import (
    CallInstructions,
    SpeechInstruction,
    AudioInstruction,
    StatusPollInstruction,
    WebSocketInstruction,
)


@pytest.fixture
def mock_call_controller():
    """Create a mock call controller."""
    controller = MagicMock()
    controller.handle_inbound_call = AsyncMock()
    controller.check_clone_status = AsyncMock()
    return controller


@pytest.fixture
def test_client(mock_call_controller):
    """Create test client with mocked dependencies."""
    # Mock the database and services to avoid actual DB connection
    with patch("src.services.database_service.DatabaseService") as mock_db:
        mock_db.return_value.init = AsyncMock()
        mock_db.return_value.close = AsyncMock()
        mock_db.return_value.health_check = AsyncMock(return_value=True)
        
        with patch("src.services.elevenlabs_client.ElevenLabsService") as mock_el:
            mock_el.return_value.health_check = AsyncMock(return_value=True)
            
            # Import app after mocking services
            from src.main import app
            from fastapi.testclient import TestClient
            
            # Patch the global call_controller in twilio_handler
            with patch("src.handlers.twilio_handler.call_controller", mock_call_controller):
                with patch("src.handlers.twilio_handler.validate_twilio_signature", AsyncMock(return_value=True)):
                    yield TestClient(app)


class TestTwilioInboundWebhook:
    """Tests for Twilio inbound call webhook."""
    
    def test_inbound_call_processing_status(self, test_client, mock_call_controller):
        """Test inbound call returns TwiML with greeting and hold music."""
        # Setup mock response
        mock_call_controller.handle_inbound_call.return_value = CallInstructions(
            call_id="CA123456",
            clone_status="processing",
            greeting_audio=SpeechInstruction(
                text="Hello thanks for calling. Please hold.",
                voice="alice",
                language="en-US"
            ),
            hold_audio=AudioInstruction(
                url="https://example.com/hold.mp3",
                loop=10
            ),
            status_poll=StatusPollInstruction(
                poll_url="/webhooks/status-callback?call_sid=CA123456",
                interval_seconds=10
            ),
        )
        
        # Make request
        response = test_client.post(
            "/webhooks/inbound",
            data={
                "CallSid": "CA123456",
                "From": "+1234567890",
                "To": "+0987654321",
                "CallStatus": "in-progress"
            }
        )
        
        # Assertions
        assert response.status_code == 200
        assert "application/xml" in response.headers["content-type"]
        
        # Check TwiML content
        content = response.text
        assert "<Response>" in content
        assert "<Say" in content
        assert "Hello thanks for calling" in content
        assert "<Play" in content
        assert "hold.mp3" in content
        assert "<Redirect" in content
        assert "status-callback" in content
        
        # Verify controller was called correctly
        mock_call_controller.handle_inbound_call.assert_called_once()
        call_context = mock_call_controller.handle_inbound_call.call_args[0][0]
        assert call_context.call_id == "CA123456"
        assert call_context.caller_number == "+1234567890"
        assert call_context.recipient_number == "+0987654321"
        assert call_context.protocol == "twilio"
    
    def test_inbound_call_without_hold_music(self, test_client, mock_call_controller):
        """Test inbound call without hold music."""
        # Setup mock response without hold audio
        mock_call_controller.handle_inbound_call.return_value = CallInstructions(
            call_id="CA123456",
            clone_status="processing",
            greeting_audio=SpeechInstruction(
                text="Hello thanks for calling.",
                voice="alice",
                language="en-US"
            ),
            status_poll=StatusPollInstruction(
                poll_url="/webhooks/status-callback?call_sid=CA123456",
                interval_seconds=10
            ),
        )
        
        # Make request
        response = test_client.post(
            "/webhooks/inbound",
            data={
                "CallSid": "CA123456",
                "From": "+1234567890",
                "To": "+0987654321",
            }
        )
        
        # Assertions
        assert response.status_code == 200
        content = response.text
        assert "<Say" in content
        assert "<Play" not in content
        assert "<Redirect" in content


class TestTwilioStatusCallback:
    """Tests for Twilio status callback webhook."""
    
    def test_status_callback_completed(self, test_client, mock_call_controller):
        """Test status callback when clone is completed."""
        # Setup mock response for completed status
        mock_call_controller.check_clone_status.return_value = CallInstructions(
            call_id="CA123456",
            clone_status="completed",
            websocket=WebSocketInstruction(
                url="wss://api.elevenlabs.io/v1/convai/conversation?agent_id=AGENT123",
                voice_id="voice123",
                api_key="test_api_key",
                track="inbound_track"
            ),
        )
        
        # Make request
        response = test_client.post(
            "/webhooks/status-callback",
            data={
                "call_sid": "CA123456",
            }
        )
        
        # Assertions
        assert response.status_code == 200
        content = response.text
        assert "<Connect>" in content
        assert "<Stream" in content
        assert "elevenlabs.io" in content
        assert "voice_id" in content
        assert "voice123" in content
        
        # Verify controller was called
        mock_call_controller.check_clone_status.assert_called_once_with("CA123456")
    
    def test_status_callback_processing(self, test_client, mock_call_controller):
        """Test status callback when clone is still processing."""
        # Setup mock response for processing status
        mock_call_controller.check_clone_status.return_value = CallInstructions(
            call_id="CA123456",
            clone_status="processing",
            hold_audio=AudioInstruction(
                url="https://example.com/hold.mp3",
                loop=5
            ),
            status_poll=StatusPollInstruction(
                poll_url="/webhooks/status-callback?call_sid=CA123456",
                interval_seconds=10
            ),
        )
        
        # Make request
        response = test_client.post(
            "/webhooks/status-callback",
            data={
                "CallSid": "CA123456",
            }
        )
        
        # Assertions
        assert response.status_code == 200
        content = response.text
        assert "<Play" in content
        assert "hold.mp3" in content
        assert "<Redirect" in content
        assert "status-callback" in content
    
    def test_status_callback_failed(self, test_client, mock_call_controller):
        """Test status callback when clone failed."""
        # Setup mock response for failed status
        mock_call_controller.check_clone_status.return_value = CallInstructions(
            call_id="CA123456",
            clone_status="failed",
            error_message="We're sorry, we encountered an error.",
            should_hangup=True,
        )
        
        # Make request
        response = test_client.post(
            "/webhooks/status-callback",
            data={
                "call_sid": "CA123456",
            }
        )
        
        # Assertions
        assert response.status_code == 200
        content = response.text
        assert "<Say" in content
        assert "error" in content.lower()
        assert "<Hangup" in content
    
    def test_status_callback_missing_call_sid(self, test_client, mock_call_controller):
        """Test status callback with missing call_sid."""
        # Make request without call_sid
        response = test_client.post(
            "/webhooks/status-callback",
            data={}
        )
        
        # Should return error
        assert response.status_code == 400


class TestTwiMLConversion:
    """Tests for TwiML conversion logic."""
    
    def test_convert_all_instructions(self, test_client, mock_call_controller):
        """Test conversion of all instruction types to TwiML."""
        # Setup comprehensive instructions
        mock_call_controller.handle_inbound_call.return_value = CallInstructions(
            call_id="CA123456",
            clone_status="processing",
            greeting_audio=SpeechInstruction(
                text="Welcome!",
                voice="alice",
                language="en-US"
            ),
            hold_audio=AudioInstruction(
                url="https://example.com/music.mp3",
                loop=3
            ),
            status_poll=StatusPollInstruction(
                poll_url="/webhooks/status-callback?call_sid=CA123456",
                interval_seconds=5
            ),
        )
        
        # Make request
        response = test_client.post(
            "/webhooks/inbound",
            data={
                "CallSid": "CA123456",
                "From": "+1234567890",
                "To": "+0987654321",
            }
        )
        
        # Check all elements are present
        content = response.text
        assert "<Response>" in content
        assert "<Say" in content and "Welcome!" in content
        assert "<Play" in content and "music.mp3" in content
        assert "<Redirect" in content
        assert "</Response>" in content
