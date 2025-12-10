"""
Unit tests for pre-call webhook handler.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.handlers.precall_handler import PreCallHandler
from src.services.voice_cloning_service import VoiceCloningService
from src.utils.file_handler import FileHandler


class TestPreCallHandler:
    """Test suite for PreCallHandler."""
    
    @pytest.fixture
    def mock_voice_service(self):
        """Create mock voice cloning service."""
        return MagicMock(spec=VoiceCloningService)
    
    @pytest.fixture
    def mock_file_handler(self):
        """Create mock file handler."""
        handler = MagicMock(spec=FileHandler)
        handler.decode_base64_audio.return_value = b"decoded audio data"
        return handler
    
    @pytest.fixture
    def handler(self, mock_voice_service, mock_file_handler):
        """Create pre-call handler with mocks."""
        return PreCallHandler(
            voice_cloning_service=mock_voice_service,
            file_handler=mock_file_handler,
            default_first_message="Hello {name}!"
        )
    
    @pytest.fixture
    def sample_payload(self):
        """Sample webhook payload."""
        return {
            "type": "pre_call",
            "conversation_id": "conv_123",
            "agent_id": "agent_456",
            "caller_metadata": {
                "name": "Jane Doe",
                "date_of_birth": "15.03.1985"
            },
            "voice_sample": {
                "format": "base64",
                "data": "dGVzdCBhdWRpbyBkYXRh",  # base64 for "test audio data"
                "duration_seconds": 5.0
            }
        }
    
    @pytest.mark.asyncio
    async def test_handle_with_embedded_voice_sample(self, handler, mock_voice_service, sample_payload):
        """Test handling payload with embedded base64 voice sample."""
        # Mock service response
        mock_voice_service.process_precall_webhook = AsyncMock(return_value={
            "voice_id": "voice_123",
            "voice_name": "Jane_Clone",
            "agent_updated": True,
            "caller_info": {"Name": "Jane Doe"}
        })
        
        result = await handler.handle(sample_payload)
        
        assert result["conversation_id"] == "conv_123"
        assert result["voice_id"] == "voice_123"
        assert result["agent_updated"] is True
        assert "processing_time_ms" in result
        
        # Verify service was called
        mock_voice_service.process_precall_webhook.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_with_provided_voice_bytes(self, handler, mock_voice_service, sample_payload):
        """Test handling with pre-decoded voice sample bytes."""
        voice_bytes = b"raw audio bytes"
        
        mock_voice_service.process_precall_webhook = AsyncMock(return_value={
            "voice_id": "voice_123",
            "voice_name": "Jane_Clone",
            "agent_updated": True,
            "caller_info": {}
        })
        
        result = await handler.handle(sample_payload, voice_sample_bytes=voice_bytes)
        
        # Should use provided bytes, not decode from payload
        call_args = mock_voice_service.process_precall_webhook.call_args
        assert call_args.kwargs["voice_sample"] == voice_bytes
    
    @pytest.mark.asyncio
    async def test_handle_missing_agent_id(self, handler):
        """Test handling payload with missing agent_id."""
        payload = {
            "type": "pre_call",
            "conversation_id": "conv_123",
            "caller_metadata": {}
        }
        
        with pytest.raises(ValueError, match="Missing required field: agent_id"):
            await handler.handle(payload)
    
    @pytest.mark.asyncio
    async def test_handle_missing_voice_sample(self, handler):
        """Test handling payload with missing voice sample."""
        payload = {
            "type": "pre_call",
            "conversation_id": "conv_123",
            "agent_id": "agent_456",
            "caller_metadata": {}
        }
        
        with pytest.raises(ValueError, match="Missing voice sample data"):
            await handler.handle(payload)
    
    @pytest.mark.asyncio
    async def test_handle_decode_error(self, handler, mock_file_handler, sample_payload):
        """Test handling with voice sample decode error."""
        mock_file_handler.decode_base64_audio.side_effect = Exception("Decode failed")
        
        with pytest.raises(ValueError, match="Failed to decode voice sample"):
            await handler.handle(sample_payload)
    
    @pytest.mark.asyncio
    async def test_handle_processing_error(self, handler, mock_voice_service, sample_payload):
        """Test handling with processing error."""
        mock_voice_service.process_precall_webhook = AsyncMock(
            side_effect=Exception("Processing failed")
        )
        
        with pytest.raises(Exception, match="Processing failed"):
            await handler.handle(sample_payload)
    
    @pytest.mark.asyncio
    async def test_handle_sets_conversation_context(self, handler, mock_voice_service, sample_payload):
        """Test that conversation context is set for logging."""
        mock_voice_service.process_precall_webhook = AsyncMock(return_value={
            "voice_id": "voice_123",
            "voice_name": "Test",
            "agent_updated": True,
            "caller_info": {}
        })
        
        with patch("src.handlers.precall_handler.conversation_context") as mock_context:
            await handler.handle(sample_payload)
            
            # Verify conversation_id was set
            mock_context.set.assert_called_once_with("conv_123")
    
    @pytest.mark.asyncio
    async def test_handle_unknown_conversation_id(self, handler, mock_voice_service):
        """Test handling payload without conversation_id."""
        payload = {
            "type": "pre_call",
            "agent_id": "agent_456",
            "voice_sample": {
                "data": "dGVzdA=="
            }
        }
        
        mock_voice_service.process_precall_webhook = AsyncMock(return_value={
            "voice_id": "voice_123",
            "voice_name": "Test",
            "agent_updated": True,
            "caller_info": {}
        })
        
        result = await handler.handle(payload)
        
        # Should use "unknown" as conversation_id
        assert result["conversation_id"] == "unknown"
    
    @pytest.mark.asyncio
    async def test_handle_processing_time_measurement(self, handler, mock_voice_service, sample_payload):
        """Test that processing time is measured."""
        # Mock with slight delay
        async def slow_process(*args, **kwargs):
            import asyncio
            await asyncio.sleep(0.1)  # 100ms
            return {
                "voice_id": "voice_123",
                "voice_name": "Test",
                "agent_updated": True,
                "caller_info": {}
            }
        
        mock_voice_service.process_precall_webhook = slow_process
        
        result = await handler.handle(sample_payload)
        
        # Processing time should be at least 100ms
        assert result["processing_time_ms"] >= 100
    
    @pytest.mark.asyncio
    async def test_handle_uses_default_first_message(self, handler, mock_voice_service, sample_payload):
        """Test that default first message is passed to service."""
        mock_voice_service.process_precall_webhook = AsyncMock(return_value={
            "voice_id": "voice_123",
            "voice_name": "Test",
            "agent_updated": True,
            "caller_info": {}
        })
        
        await handler.handle(sample_payload)
        
        call_args = mock_voice_service.process_precall_webhook.call_args
        assert call_args.kwargs["default_first_message"] == "Hello {name}!"
    
    def test_handler_initialization_default_message(self, mock_voice_service, mock_file_handler):
        """Test handler initialization with default message."""
        handler = PreCallHandler(
            voice_cloning_service=mock_voice_service,
            file_handler=mock_file_handler
        )
        
        assert handler.default_first_message == "Hello {name}, thank you for calling!"
    
    def test_handler_initialization_custom_message(self, mock_voice_service, mock_file_handler):
        """Test handler initialization with custom message."""
        custom_message = "Bonjour {name}!"
        handler = PreCallHandler(
            voice_cloning_service=mock_voice_service,
            file_handler=mock_file_handler,
            default_first_message=custom_message
        )
        
        assert handler.default_first_message == custom_message
