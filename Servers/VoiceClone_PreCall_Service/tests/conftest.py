"""
Pytest configuration and fixtures for Voice Clone Pre-Call Service tests.
"""

import pytest
import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

from src.config import Settings
from src.services.database_service import DatabaseService
from src.services.cache_service import CacheService
from src.services.storage_service import StorageService
from src.services.elevenlabs_client import ElevenLabsClient
from src.services.voice_clone_service import VoiceCloneService
from src.services.voice_clone_async_service import VoiceCloneAsyncService


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    return Settings(
        elevenlabs_api_key="test_api_key",
        elevenlabs_agent_id="test_agent_id",
        elevenlabs_phone_number_id="test_phone_number_id",
        database_url="postgresql+asyncpg://test:test@localhost:5432/test_db",
        redis_url="redis://localhost:6379/1",
        threecx_webhook_secret="test_3cx_secret",
        webhook_secret="test_webhook_secret",
        voice_sample_storage="local",
        local_voice_samples_path="/tmp/test_voices"
    )


@pytest.fixture
async def mock_database_service():
    """Mock database service for testing."""
    mock = AsyncMock(spec=DatabaseService)
    mock.init = AsyncMock()
    mock.close = AsyncMock()
    mock.health_check = AsyncMock(return_value=True)
    mock.get_voice_sample_for_caller = AsyncMock(return_value="/path/to/sample.mp3")
    mock.save_caller_voice_mapping = AsyncMock()
    mock.get_cached_clone = AsyncMock(return_value=None)
    mock.save_clone_cache = AsyncMock()
    mock.log_call_initiated = AsyncMock()
    mock.log_call_completed = AsyncMock()
    mock.log_clone_creation = AsyncMock()
    mock.log_clone_ready = AsyncMock()
    mock.log_clone_failed = AsyncMock()
    mock.log_clone_transfer = AsyncMock()
    return mock


@pytest.fixture
async def mock_cache_service():
    """Mock cache service for testing."""
    mock = AsyncMock(spec=CacheService)
    mock.connect = AsyncMock()
    mock.disconnect = AsyncMock()
    mock.health_check = AsyncMock(return_value=True)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.exists = AsyncMock(return_value=False)
    return mock


@pytest.fixture
async def mock_storage_service():
    """Mock storage service for testing."""
    mock = AsyncMock(spec=StorageService)
    mock.get_voice_sample = AsyncMock(return_value=b"fake_audio_data")
    mock.save_voice_sample = AsyncMock(return_value="/path/to/saved/sample.mp3")
    mock.health_check = AsyncMock(return_value=True)
    return mock


@pytest.fixture
async def mock_elevenlabs_client():
    """Mock ElevenLabs client for testing."""
    mock = AsyncMock(spec=ElevenLabsClient)
    mock.connect = AsyncMock()
    mock.disconnect = AsyncMock()
    mock.health_check = AsyncMock(return_value=True)
    mock.create_voice_clone = AsyncMock(return_value="voice_123abc")
    mock.trigger_voice_agent_call = AsyncMock(return_value="call_123abc")
    mock.get_voice_details = AsyncMock()
    mock.list_voices = AsyncMock(return_value=[])
    return mock


@pytest.fixture
async def mock_voice_clone_service(
    mock_database_service,
    mock_cache_service,
    mock_storage_service,
    mock_elevenlabs_client
):
    """Mock voice clone service for testing."""
    mock = AsyncMock(spec=VoiceCloneService)
    mock.db = mock_database_service
    mock.cache = mock_cache_service
    mock.storage = mock_storage_service
    mock.elevenlabs = mock_elevenlabs_client
    mock.get_or_create_clone = AsyncMock(return_value="voice_123abc")
    mock.get_cached_clone = AsyncMock(return_value=None)
    mock.invalidate_clone_cache = AsyncMock(return_value=True)
    mock.cleanup_expired_clones = AsyncMock(return_value=0)
    mock.get_clone_statistics = AsyncMock(return_value={})
    return mock


@pytest.fixture
async def mock_async_voice_service(
    mock_database_service,
    mock_voice_clone_service,
    mock_elevenlabs_client
):
    """Mock async voice clone service for testing."""
    mock = AsyncMock(spec=VoiceCloneAsyncService)
    mock.db = mock_database_service
    mock.voice_clone_service = mock_voice_clone_service
    mock.elevenlabs = mock_elevenlabs_client
    mock.process_incoming_call = AsyncMock(return_value={
        "status": "success",
        "greeting_call_id": "greeting_123",
        "message": "Greeting call initiated"
    })
    mock.get_clone_status = AsyncMock(return_value={
        "caller_id": "+31612345678",
        "status": "ready",
        "cloned_voice_id": "voice_123abc"
    })
    return mock


@pytest.fixture
def sample_3cx_webhook_payload():
    """Sample 3CX webhook payload for testing."""
    return {
        "event_type": "IncomingCall",
        "call_id": "3cx_call_123",
        "caller_id": "+31612345678",
        "called_number": "+31201234567",
        "timestamp": "2025-12-10T12:00:00Z",
        "direction": "In"
    }


@pytest.fixture
def sample_postcall_webhook_payload():
    """Sample POST-call webhook payload for testing."""
    return {
        "call_id": "elevenlabs_call_123",
        "agent_id": "agent_abc",
        "transcript": "Hello, how can I help you?",
        "duration_seconds": 120,
        "status": "completed",
        "custom_variables": {"caller_id": "+31612345678"},
        "timestamp": "2025-12-10T12:02:00Z"
    }
