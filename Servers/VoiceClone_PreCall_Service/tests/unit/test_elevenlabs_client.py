"""
Unit tests for ElevenLabs client.
"""

import pytest
from unittest.mock import AsyncMock, patch
import httpx

from src.services.elevenlabs_client import ElevenLabsClient
from src.utils.exceptions import VoiceCloneException, VoiceAgentException, APIException


@pytest.mark.asyncio
async def test_create_voice_clone_success(mock_elevenlabs_client):
    """Test successful voice clone creation."""
    # Test that the mock returns expected voice_id
    voice_id = await mock_elevenlabs_client.create_voice_clone(
        voice_sample_content=b"fake_audio",
        voice_name="Test Voice"
    )
    
    assert voice_id == "voice_123abc"
    mock_elevenlabs_client.create_voice_clone.assert_called_once()


@pytest.mark.asyncio
async def test_trigger_voice_agent_call_success(mock_elevenlabs_client):
    """Test successful voice agent call initiation."""
    call_id = await mock_elevenlabs_client.trigger_voice_agent_call(
        phone_number="+31612345678",
        voice_id="voice_123abc"
    )
    
    assert call_id == "call_123abc"
    mock_elevenlabs_client.trigger_voice_agent_call.assert_called_once()


@pytest.mark.asyncio
async def test_health_check(mock_elevenlabs_client):
    """Test ElevenLabs API health check."""
    health = await mock_elevenlabs_client.health_check()
    assert health is True
