"""
Unit tests for voice cloning service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.voice_cloning_service import VoiceCloningService
from src.services.elevenlabs_client import ElevenLabsAPIClient
from src.utils.file_handler import FileHandler
from src.models.elevenlabs_models import VoiceCreateResponse, AgentUpdateResponse


class TestVoiceCloningService:
    """Test suite for VoiceCloningService."""
    
    @pytest.fixture
    def mock_elevenlabs_client(self):
        """Create mock ElevenLabs client."""
        return MagicMock(spec=ElevenLabsAPIClient)
    
    @pytest.fixture
    def mock_file_handler(self):
        """Create mock file handler."""
        handler = MagicMock(spec=FileHandler)
        handler.validate_audio_size.return_value = (True, None)
        handler.get_audio_format.return_value = "mp3"
        return handler
    
    @pytest.fixture
    def service(self, mock_elevenlabs_client, mock_file_handler):
        """Create voice cloning service with mocks."""
        return VoiceCloningService(
            elevenlabs_client=mock_elevenlabs_client,
            file_handler=mock_file_handler,
            min_duration=3.0,
            max_size_mb=10.0
        )
    
    @pytest.fixture
    def sample_audio_bytes(self):
        """Sample audio bytes."""
        return b"fake audio data" * 1000  # Make it reasonably sized
    
    @pytest.fixture
    def sample_caller_metadata(self):
        """Sample caller metadata."""
        return {
            "name": "John Doe",
            "date_of_birth": "01.01.1990"
        }
    
    def test_generate_voice_name(self, service):
        """Test voice name generation."""
        voice_name = service.generate_voice_name(
            caller_name="John Doe",
            conversation_id="conv_abc123xyz"
        )
        
        assert "John_Doe" in voice_name
        assert "Clone" in voice_name
        assert "bc123xyz" in voice_name  # Last 8 chars of conv_id (without "conv_a")
    
    def test_generate_voice_name_with_special_chars(self, service):
        """Test voice name generation with special characters."""
        voice_name = service.generate_voice_name(
            caller_name="Jöhn Döe!@#",
            conversation_id="conv_123"
        )
        
        # Special chars should be removed
        assert "@" not in voice_name
        assert "#" not in voice_name
        assert "!" not in voice_name
    
    def test_generate_voice_name_long_name(self, service):
        """Test voice name generation with very long name."""
        long_name = "A" * 50
        voice_name = service.generate_voice_name(
            caller_name=long_name,
            conversation_id="conv_123"
        )
        
        # Name should be truncated to 20 chars
        name_part = voice_name.split("_Clone_")[0]
        assert len(name_part) <= 20
    
    def test_validate_voice_sample_valid(self, service, sample_audio_bytes, mock_file_handler):
        """Test validation of valid voice sample."""
        is_valid, error = service.validate_voice_sample(
            audio_data=sample_audio_bytes,
            min_duration=3.0,
            max_size_mb=10.0
        )
        
        assert is_valid is True
        assert error is None
        mock_file_handler.validate_audio_size.assert_called_once()
        mock_file_handler.get_audio_format.assert_called_once()
    
    def test_validate_voice_sample_too_large(self, service, mock_file_handler):
        """Test validation of oversized voice sample."""
        mock_file_handler.validate_audio_size.return_value = (False, "Too large")
        
        is_valid, error = service.validate_voice_sample(
            audio_data=b"x" * 1000,
            max_size_mb=10.0
        )
        
        assert is_valid is False
        assert error == "Too large"
    
    def test_validate_voice_sample_unknown_format(self, service, mock_file_handler):
        """Test validation of unknown audio format."""
        mock_file_handler.get_audio_format.return_value = "unknown"
        
        is_valid, error = service.validate_voice_sample(
            audio_data=b"x" * 10000
        )
        
        assert is_valid is False
        assert "Unsupported audio format" in error
    
    def test_validate_voice_sample_too_short(self, service, mock_file_handler):
        """Test validation of very short audio sample."""
        # Very small file (< 5KB)
        small_audio = b"x" * 1000
        
        is_valid, error = service.validate_voice_sample(audio_data=small_audio)
        
        assert is_valid is False
        assert "too short" in error.lower()
    
    @pytest.mark.asyncio
    async def test_process_precall_webhook_success(
        self, service, mock_elevenlabs_client, sample_audio_bytes, sample_caller_metadata
    ):
        """Test successful pre-call webhook processing."""
        # Mock API responses
        voice_response = VoiceCreateResponse(
            voice_id="voice_new123",
            name="John_Doe_Clone_20251210_123456",
            category="cloned"
        )
        mock_elevenlabs_client.create_instant_voice = AsyncMock(return_value=voice_response)
        
        agent_response = AgentUpdateResponse(
            agent_id="agent_456",
            conversation_config={}
        )
        mock_elevenlabs_client.update_agent_voice = AsyncMock(return_value=agent_response)
        
        # Process webhook
        result = await service.process_precall_webhook(
            conversation_id="conv_123",
            agent_id="agent_456",
            voice_sample=sample_audio_bytes,
            caller_metadata=sample_caller_metadata,
            default_first_message="Hello {name}!"
        )
        
        # Verify result
        assert result["voice_id"] == "voice_new123"
        assert result["agent_updated"] is True
        assert "John Doe" in result["caller_info"]["Name"]
        
        # Verify API calls
        mock_elevenlabs_client.create_instant_voice.assert_called_once()
        mock_elevenlabs_client.update_agent_voice.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_precall_webhook_validation_failure(
        self, service, mock_file_handler, sample_audio_bytes, sample_caller_metadata
    ):
        """Test pre-call processing with validation failure."""
        # Make validation fail
        mock_file_handler.validate_audio_size.return_value = (False, "Too large")
        
        with pytest.raises(ValueError, match="Too large"):
            await service.process_precall_webhook(
                conversation_id="conv_123",
                agent_id="agent_456",
                voice_sample=sample_audio_bytes,
                caller_metadata=sample_caller_metadata
            )
    
    @pytest.mark.asyncio
    async def test_process_precall_webhook_voice_creation_failure(
        self, service, mock_elevenlabs_client, sample_audio_bytes, sample_caller_metadata
    ):
        """Test pre-call processing with voice creation failure."""
        # Mock API failure
        mock_elevenlabs_client.create_instant_voice = AsyncMock(
            side_effect=Exception("API Error")
        )
        
        with pytest.raises(Exception, match="API Error"):
            await service.process_precall_webhook(
                conversation_id="conv_123",
                agent_id="agent_456",
                voice_sample=sample_audio_bytes,
                caller_metadata=sample_caller_metadata
            )
    
    @pytest.mark.asyncio
    async def test_process_precall_webhook_agent_update_failure(
        self, service, mock_elevenlabs_client, sample_audio_bytes, sample_caller_metadata
    ):
        """Test pre-call processing with agent update failure."""
        # Voice creation succeeds
        voice_response = VoiceCreateResponse(
            voice_id="voice_new123",
            name="Test_Voice",
            category="cloned"
        )
        mock_elevenlabs_client.create_instant_voice = AsyncMock(return_value=voice_response)
        
        # Agent update fails
        mock_elevenlabs_client.update_agent_voice = AsyncMock(
            side_effect=Exception("Agent update failed")
        )
        
        # Should not raise exception, but agent_updated should be False
        result = await service.process_precall_webhook(
            conversation_id="conv_123",
            agent_id="agent_456",
            voice_sample=sample_audio_bytes,
            caller_metadata=sample_caller_metadata
        )
        
        assert result["voice_id"] == "voice_new123"
        assert result["agent_updated"] is False
    
    @pytest.mark.asyncio
    async def test_process_precall_webhook_with_first_message(
        self, service, mock_elevenlabs_client, sample_audio_bytes, sample_caller_metadata
    ):
        """Test pre-call processing with custom first message."""
        voice_response = VoiceCreateResponse(
            voice_id="voice_new123",
            name="Test_Voice",
            category="cloned"
        )
        mock_elevenlabs_client.create_instant_voice = AsyncMock(return_value=voice_response)
        mock_elevenlabs_client.update_agent_voice = AsyncMock(
            return_value=AgentUpdateResponse(agent_id="agent_456")
        )
        
        await service.process_precall_webhook(
            conversation_id="conv_123",
            agent_id="agent_456",
            voice_sample=sample_audio_bytes,
            caller_metadata=sample_caller_metadata,
            default_first_message="Hallo {name}, welkom!"
        )
        
        # Verify first message was formatted
        call_args = mock_elevenlabs_client.update_agent_voice.call_args
        assert call_args.kwargs["first_message"] == "Hallo John Doe, welkom!"
    
    @pytest.mark.asyncio
    async def test_process_precall_webhook_no_caller_name(
        self, service, mock_elevenlabs_client, sample_audio_bytes
    ):
        """Test pre-call processing without caller name."""
        voice_response = VoiceCreateResponse(
            voice_id="voice_new123",
            name="Unknown_Clone_123",
            category="cloned"
        )
        mock_elevenlabs_client.create_instant_voice = AsyncMock(return_value=voice_response)
        mock_elevenlabs_client.update_agent_voice = AsyncMock(
            return_value=AgentUpdateResponse(agent_id="agent_456")
        )
        
        result = await service.process_precall_webhook(
            conversation_id="conv_123",
            agent_id="agent_456",
            voice_sample=sample_audio_bytes,
            caller_metadata={}
        )
        
        # Should still work, but with empty caller_info
        assert result["voice_id"] == "voice_new123"
        assert result["caller_info"] == {}
