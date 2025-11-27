"""
Unit tests for AudioHandler.
"""

import base64
import pytest

from src.handlers.audio_handler import AudioHandler


class TestAudioHandler:
    """Tests for AudioHandler class."""
    
    @pytest.fixture
    def handler(self):
        """Create handler instance for testing."""
        return AudioHandler(storage=None)
    
    @pytest.mark.asyncio
    async def test_handle_valid_payload(self, handler, sample_audio_payload):
        """Test handling of valid audio payload."""
        result = await handler.handle(sample_audio_payload)
        
        assert result["status"] == "processed"
        assert result["conversation_id"] == "conv_test_123"
        assert result["agent_id"] == "agent_test_456"
        assert result["audio_format"] == "mp3"
        assert result["audio_size_bytes"] > 0
    
    @pytest.mark.asyncio
    async def test_handle_empty_audio(self, handler):
        """Test handling of payload with empty audio."""
        payload = {
            "type": "post_call_audio",
            "conversation_id": "conv_empty",
            "agent_id": "agent_empty",
            "audio_base64": "",
            "audio_format": "mp3"
        }
        
        result = await handler.handle(payload)
        
        assert result["status"] == "processed"
        assert result["audio_size_bytes"] == 0
    
    @pytest.mark.asyncio
    async def test_handle_large_audio(self, handler):
        """Test handling of large audio payload."""
        # Generate large base64 string (simulating ~100KB audio)
        large_data = b"A" * 100000
        large_base64 = base64.b64encode(large_data).decode("utf-8")
        
        payload = {
            "type": "post_call_audio",
            "conversation_id": "conv_large",
            "agent_id": "agent_large",
            "audio_base64": large_base64,
            "audio_format": "mp3"
        }
        
        result = await handler.handle(payload)
        
        assert result["status"] == "processed"
        assert result["audio_size_bytes"] == 100000
    
    @pytest.mark.asyncio
    async def test_handle_different_audio_formats(self, handler):
        """Test handling of different audio formats."""
        formats = ["mp3", "wav", "ogg", "m4a"]
        
        for fmt in formats:
            payload = {
                "type": "post_call_audio",
                "conversation_id": f"conv_{fmt}",
                "agent_id": "agent_test",
                "audio_base64": "SGVsbG8=",  # "Hello" in base64
                "audio_format": fmt
            }
            
            result = await handler.handle(payload)
            
            assert result["status"] == "processed"
            assert result["audio_format"] == fmt
    
    def test_calculate_audio_size(self, handler):
        """Test audio size calculation."""
        # "Hello World!" = 12 bytes
        base64_str = base64.b64encode(b"Hello World!").decode("utf-8")
        
        size = handler._calculate_audio_size(base64_str)
        
        assert size == 12
    
    def test_calculate_audio_size_empty(self, handler):
        """Test audio size calculation with empty string."""
        size = handler._calculate_audio_size("")
        assert size == 0
    
    def test_calculate_audio_size_with_padding(self, handler):
        """Test audio size calculation with base64 padding."""
        # "A" = 1 byte, base64 = "QQ==" (2 padding chars)
        base64_str = base64.b64encode(b"A").decode("utf-8")
        
        size = handler._calculate_audio_size(base64_str)
        
        assert size == 1
    
    def test_decode_audio(self, handler):
        """Test audio decoding."""
        original = b"Hello World!"
        base64_str = base64.b64encode(original).decode("utf-8")
        
        decoded = handler.decode_audio(base64_str)
        
        assert decoded == original
    
    def test_decode_audio_invalid(self, handler):
        """Test audio decoding with invalid base64."""
        with pytest.raises(ValueError):
            handler.decode_audio("not-valid-base64!!!")
    
    @pytest.mark.asyncio
    async def test_handle_missing_format(self, handler):
        """Test handling of payload with missing format (should default to mp3)."""
        payload = {
            "type": "post_call_audio",
            "conversation_id": "conv_no_format",
            "agent_id": "agent_no_format",
            "audio_base64": "SGVsbG8="
        }
        
        result = await handler.handle(payload)
        
        assert result["status"] == "processed"
        assert result["audio_format"] == "mp3"
