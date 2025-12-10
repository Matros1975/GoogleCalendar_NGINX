"""
Unit tests for voice clone service.
"""

import pytest
from unittest.mock import AsyncMock

from src.services.voice_clone_service import VoiceCloneService
from src.utils.exceptions import VoiceSampleNotFoundException


@pytest.mark.asyncio
async def test_get_or_create_clone_cached(mock_voice_clone_service):
    """Test getting clone from cache."""
    # Set up mock to return cached clone
    mock_voice_clone_service.get_or_create_clone.return_value = "voice_123abc"
    
    voice_id = await mock_voice_clone_service.get_or_create_clone(
        caller_id="+31612345678"
    )
    
    assert voice_id == "voice_123abc"
    mock_voice_clone_service.get_or_create_clone.assert_called_once()


@pytest.mark.asyncio
async def test_get_cached_clone(mock_voice_clone_service):
    """Test checking for cached clone."""
    voice_id = await mock_voice_clone_service.get_cached_clone("+31612345678")
    assert voice_id is None


@pytest.mark.asyncio
async def test_invalidate_clone_cache(mock_voice_clone_service):
    """Test cache invalidation."""
    result = await mock_voice_clone_service.invalidate_clone_cache("+31612345678")
    assert result is True
