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
