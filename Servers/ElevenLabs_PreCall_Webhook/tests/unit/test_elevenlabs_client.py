"""
Unit tests for ElevenLabs API client.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from src.services.elevenlabs_client import ElevenLabsAPIClient
from src.models.elevenlabs_models import (
    VoiceCreateResponse,
    VoiceInfo,
    AgentUpdateResponse
)


class TestElevenLabsAPIClient:
    """Test suite for ElevenLabsAPIClient."""
    
    @pytest.fixture
    def client(self):
        """Create API client with test credentials."""
        return ElevenLabsAPIClient(api_key="test_api_key_12345")
    
    @pytest.fixture
    def sample_voice_bytes(self):
        """Sample voice audio bytes."""
        return b"fake audio data for testing"
    
    @pytest.mark.asyncio
    async def test_create_instant_voice_success(self, client, sample_voice_bytes):
        """Test successful voice creation."""
        mock_response = {
            "voice_id": "voice_abc123",
            "name": "Test_Voice",
            "category": "cloned",
            "samples": []
        }
        
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_response
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp
            
            result = await client.create_instant_voice(
                voice_sample=sample_voice_bytes,
                voice_name="Test_Voice",
                description="Test voice",
                labels={"test": "true"}
            )
            
            assert isinstance(result, VoiceCreateResponse)
            assert result.voice_id == "voice_abc123"
            assert result.name == "Test_Voice"
            
            # Verify API was called correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "xi-api-key" in call_args.kwargs["headers"]
    
    @pytest.mark.asyncio
    async def test_create_instant_voice_api_error(self, client, sample_voice_bytes):
        """Test voice creation with API error."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "API Error", request=MagicMock(), response=MagicMock()
            )
            mock_post.return_value = mock_resp
            
            with pytest.raises(httpx.HTTPStatusError):
                await client.create_instant_voice(
                    voice_sample=sample_voice_bytes,
                    voice_name="Test_Voice"
                )
    
    @pytest.mark.asyncio
    async def test_update_agent_voice_success(self, client):
        """Test successful agent voice update."""
        mock_response = {
            "agent_id": "agent_123",
            "name": "Test Agent",
            "conversation_config": {
                "agent": {
                    "voice": {
                        "voice_id": "voice_abc123"
                    }
                }
            }
        }
        
        with patch("httpx.AsyncClient.patch") as mock_patch:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_response
            mock_resp.raise_for_status = MagicMock()
            mock_patch.return_value = mock_resp
            
            result = await client.update_agent_voice(
                agent_id="agent_123",
                voice_id="voice_abc123",
                first_message="Hello there!"
            )
            
            assert isinstance(result, AgentUpdateResponse)
            assert result.agent_id == "agent_123"
            
            # Verify request payload
            call_args = mock_patch.call_args
            assert "json" in call_args.kwargs
            payload = call_args.kwargs["json"]
            assert "conversation_config" in payload
    
    @pytest.mark.asyncio
    async def test_update_agent_voice_without_first_message(self, client):
        """Test agent update without custom first message."""
        mock_response = {
            "agent_id": "agent_123",
            "conversation_config": {}
        }
        
        with patch("httpx.AsyncClient.patch") as mock_patch:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_response
            mock_resp.raise_for_status = MagicMock()
            mock_patch.return_value = mock_resp
            
            result = await client.update_agent_voice(
                agent_id="agent_123",
                voice_id="voice_abc123"
            )
            
            assert result.agent_id == "agent_123"
            
            # Verify first_message was not included
            call_args = mock_patch.call_args
            payload = call_args.kwargs["json"]
            agent_config = payload["conversation_config"]["agent"]
            assert "first_message" not in agent_config or agent_config.get("first_message") is None
    
    @pytest.mark.asyncio
    async def test_get_voice_info_success(self, client):
        """Test getting voice information."""
        mock_response = {
            "voice_id": "voice_abc123",
            "name": "Test Voice",
            "category": "cloned",
            "description": "Test description"
        }
        
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_response
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp
            
            result = await client.get_voice_info("voice_abc123")
            
            assert isinstance(result, VoiceInfo)
            assert result.voice_id == "voice_abc123"
            assert result.name == "Test Voice"
    
    @pytest.mark.asyncio
    async def test_get_voice_info_not_found(self, client):
        """Test getting voice info for non-existent voice."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found", request=MagicMock(), response=MagicMock()
            )
            mock_get.return_value = mock_resp
            
            with pytest.raises(httpx.HTTPStatusError):
                await client.get_voice_info("invalid_voice_id")
    
    @pytest.mark.asyncio
    async def test_delete_voice_success(self, client):
        """Test successful voice deletion."""
        with patch("httpx.AsyncClient.delete") as mock_delete:
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_delete.return_value = mock_resp
            
            result = await client.delete_voice("voice_abc123")
            
            assert result is True
            mock_delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_voice_error(self, client):
        """Test voice deletion with error."""
        with patch("httpx.AsyncClient.delete") as mock_delete:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Error", request=MagicMock(), response=MagicMock()
            )
            mock_delete.return_value = mock_resp
            
            with pytest.raises(httpx.HTTPStatusError):
                await client.delete_voice("voice_abc123")
    
    def test_client_initialization(self):
        """Test client initialization with custom base URL."""
        custom_url = "https://custom.api.com/v1"
        client = ElevenLabsAPIClient(
            api_key="test_key",
            base_url=custom_url
        )
        
        assert client.api_key == "test_key"
        assert client.base_url == custom_url
        assert client.headers["xi-api-key"] == "test_key"
    
    def test_client_default_base_url(self, client):
        """Test that default base URL is set correctly."""
        assert client.base_url == "https://api.elevenlabs.io/v1"
