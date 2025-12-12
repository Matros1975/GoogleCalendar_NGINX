"""
Unit tests for CallController.

Tests the protocol-agnostic business logic of the call controller.
"""

import pytest
import os
from unittest.mock import Mock, AsyncMock, patch

# Set environment variables before importing
os.environ["ELEVENLABS_API_KEY"] = "test_key"
os.environ["ELEVENLABS_AGENT_ID"] = "test_agent"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost/test"
os.environ["WEBHOOK_SECRET"] = "test_secret"

from src.models.call_context import CallContext
from src.models.call_instructions import CallInstructions
from src.services.call_controller import CallController


@pytest.fixture
def mock_voice_clone_service():
    """Create mock voice clone async service."""
    service = Mock()
    service.start_clone_async = AsyncMock()
    return service


@pytest.fixture
def mock_database_service():
    """Create mock database service."""
    service = Mock()
    service.get_clone_status = AsyncMock()
    return service


@pytest.fixture
def call_controller(mock_voice_clone_service, mock_database_service):
    """Create call controller with mocked dependencies."""
    return CallController(
        voice_clone_service=mock_voice_clone_service,
        database_service=mock_database_service
    )


class TestHandleInboundCall:
    """Tests for handle_inbound_call method."""
    
    @pytest.mark.asyncio
    async def test_handle_inbound_call_twilio(self, call_controller):
        """Test handling inbound Twilio call."""
        # Create context
        context = CallContext(
            call_id="CA123456",
            caller_number="+1234567890",
            recipient_number="+0987654321",
            protocol="twilio",
            status="in-progress"
        )
        
        # Call handler
        instructions = await call_controller.handle_inbound_call(context)
        
        # Assertions
        assert instructions.call_id == "CA123456"
        assert instructions.clone_status == "processing"
        assert instructions.greeting_audio is not None
        assert instructions.greeting_audio.text != ""
        assert instructions.status_poll is not None
        assert instructions.status_poll.poll_url.startswith("/webhooks/status-callback")
        assert instructions.should_hangup is False
        
        # Verify async clone was started
        call_controller.voice_clone_service.start_clone_async.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_inbound_call_sip(self, call_controller):
        """Test handling inbound SIP call."""
        # Create context
        context = CallContext(
            call_id="SIP-789",
            caller_number="+1234567890",
            recipient_number="+0987654321",
            protocol="sip",
            status="ringing"
        )
        
        # Call handler
        instructions = await call_controller.handle_inbound_call(context)
        
        # Assertions
        assert instructions.call_id == "SIP-789"
        assert instructions.clone_status == "processing"
        assert instructions.greeting_audio is not None
        assert instructions.status_poll is not None
    
    @pytest.mark.asyncio
    async def test_handle_inbound_call_with_hold_music(self, call_controller):
        """Test that hold music is included when enabled."""
        context = CallContext(
            call_id="CA123",
            caller_number="+1234567890",
            recipient_number="+0987654321",
            protocol="twilio"
        )
        
        # Mock settings with hold music enabled
        with patch.object(call_controller.settings, 'greeting_music_enabled', True):
            with patch.object(call_controller.settings, 'greeting_music_url', 'https://example.com/hold.mp3'):
                instructions = await call_controller.handle_inbound_call(context)
        
        # Should have hold audio
        assert instructions.hold_audio is not None
        assert instructions.hold_audio.url == 'https://example.com/hold.mp3'
        assert instructions.hold_audio.loop > 1
    
    @pytest.mark.asyncio
    async def test_handle_inbound_call_without_hold_music(self, call_controller):
        """Test that hold music is not included when disabled."""
        context = CallContext(
            call_id="CA123",
            caller_number="+1234567890",
            recipient_number="+0987654321",
            protocol="twilio"
        )
        
        # Mock settings with hold music disabled
        with patch.object(call_controller.settings, 'greeting_music_enabled', False):
            instructions = await call_controller.handle_inbound_call(context)
        
        # Should not have hold audio
        assert instructions.hold_audio is None
    
    @pytest.mark.asyncio
    async def test_handle_inbound_call_error(self, call_controller):
        """Test error handling in handle_inbound_call."""
        # Make voice clone service raise exception
        call_controller.voice_clone_service.start_clone_async.side_effect = Exception("Test error")
        
        context = CallContext(
            call_id="CA123",
            caller_number="+1234567890",
            recipient_number="+0987654321",
            protocol="twilio"
        )
        
        # Should not raise, but return error instructions
        instructions = await call_controller.handle_inbound_call(context)
        
        # Should still return valid instructions (error case)
        assert instructions.clone_status == "processing"  # Still processes despite error


class TestCheckCloneStatus:
    """Tests for check_clone_status method."""
    
    @pytest.mark.asyncio
    async def test_check_clone_status_completed(self, call_controller, mock_database_service):
        """Test checking clone status when completed."""
        # Mock database response
        mock_database_service.get_clone_status.return_value = {
            "status": "completed",
            "voice_clone_id": "voice123",
            "error": None
        }
        
        # Call method
        instructions = await call_controller.check_clone_status("CA123456")
        
        # Assertions
        assert instructions.call_id == "CA123456"
        assert instructions.clone_status == "completed"
        assert instructions.websocket is not None
        assert instructions.websocket.voice_id == "voice123"
        assert "elevenlabs.io" in instructions.websocket.url
        assert instructions.should_hangup is False
        
        # Verify DB was queried
        mock_database_service.get_clone_status.assert_called_once_with("CA123456")
    
    @pytest.mark.asyncio
    async def test_check_clone_status_processing(self, call_controller, mock_database_service):
        """Test checking clone status when still processing."""
        # Mock database response
        mock_database_service.get_clone_status.return_value = {
            "status": "processing",
            "voice_clone_id": None,
            "error": None
        }
        
        # Call method
        instructions = await call_controller.check_clone_status("CA123456")
        
        # Assertions
        assert instructions.call_id == "CA123456"
        assert instructions.clone_status == "processing"
        assert instructions.status_poll is not None
        assert instructions.websocket is None
        assert instructions.should_hangup is False
    
    @pytest.mark.asyncio
    async def test_check_clone_status_processing_with_hold_music(self, call_controller, mock_database_service):
        """Test processing status includes hold music when enabled."""
        # Mock database response
        mock_database_service.get_clone_status.return_value = {
            "status": "processing",
            "voice_clone_id": None,
            "error": None
        }
        
        # Mock settings
        with patch.object(call_controller.settings, 'greeting_music_enabled', True):
            with patch.object(call_controller.settings, 'greeting_music_url', 'https://example.com/hold.mp3'):
                instructions = await call_controller.check_clone_status("CA123456")
        
        # Should have hold audio
        assert instructions.hold_audio is not None
        assert instructions.hold_audio.url == 'https://example.com/hold.mp3'
    
    @pytest.mark.asyncio
    async def test_check_clone_status_failed(self, call_controller, mock_database_service):
        """Test checking clone status when failed."""
        # Mock database response
        mock_database_service.get_clone_status.return_value = {
            "status": "failed",
            "voice_clone_id": None,
            "error": "Test error"
        }
        
        # Call method
        instructions = await call_controller.check_clone_status("CA123456")
        
        # Assertions
        assert instructions.call_id == "CA123456"
        assert instructions.clone_status == "failed"
        assert instructions.error_message is not None
        assert instructions.should_hangup is True
        assert instructions.websocket is None
    
    @pytest.mark.asyncio
    async def test_check_clone_status_not_found(self, call_controller, mock_database_service):
        """Test checking clone status when call not found."""
        # Mock database response (None)
        mock_database_service.get_clone_status.return_value = None
        
        # Call method
        instructions = await call_controller.check_clone_status("CA999999")
        
        # Assertions
        assert instructions.call_id == "CA999999"
        assert instructions.clone_status == "failed"
        assert instructions.error_message is not None
        assert instructions.should_hangup is True
    
    @pytest.mark.asyncio
    async def test_check_clone_status_database_error(self, call_controller, mock_database_service):
        """Test error handling when database query fails."""
        # Make database raise exception
        mock_database_service.get_clone_status.side_effect = Exception("DB error")
        
        # Call method (should not raise)
        instructions = await call_controller.check_clone_status("CA123456")
        
        # Should return error instructions
        assert instructions.clone_status == "failed"
        assert instructions.should_hangup is True


class TestCallInstructionsIntegrity:
    """Tests for instruction data integrity."""
    
    @pytest.mark.asyncio
    async def test_completed_instructions_have_websocket(self, call_controller, mock_database_service):
        """Test that completed status always includes WebSocket instructions."""
        mock_database_service.get_clone_status.return_value = {
            "status": "completed",
            "voice_clone_id": "voice123",
            "error": None
        }
        
        instructions = await call_controller.check_clone_status("CA123")
        
        # Must have WebSocket for completed status
        assert instructions.websocket is not None
        assert instructions.websocket.voice_id
        assert instructions.websocket.url
        assert instructions.websocket.api_key
    
    @pytest.mark.asyncio
    async def test_failed_instructions_have_error_or_hangup(self, call_controller, mock_database_service):
        """Test that failed status includes error message or hangup."""
        mock_database_service.get_clone_status.return_value = {
            "status": "failed",
            "voice_clone_id": None,
            "error": "Test error"
        }
        
        instructions = await call_controller.check_clone_status("CA123")
        
        # Must have error message or hangup for failed status
        assert instructions.error_message is not None or instructions.should_hangup is True
    
    @pytest.mark.asyncio
    async def test_processing_instructions_have_poll(self, call_controller, mock_database_service):
        """Test that processing status includes status poll instructions."""
        mock_database_service.get_clone_status.return_value = {
            "status": "processing",
            "voice_clone_id": None,
            "error": None
        }
        
        instructions = await call_controller.check_clone_status("CA123")
        
        # Must have status poll for processing status
        assert instructions.status_poll is not None
        assert instructions.status_poll.poll_url
