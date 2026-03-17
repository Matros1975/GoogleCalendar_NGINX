"""
Pytest configuration and fixtures for VoiceClone Pre-Call Service tests.
"""

import pytest
import asyncio
from typing import Generator

from src.config import get_settings


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def settings():
    """Get application settings."""
    return get_settings()


@pytest.fixture
async def db_service():
    """Create database service for testing."""
    from src.services.database_service import DatabaseService
    
    db = DatabaseService()
    await db.init()
    yield db
    await db.close()


@pytest.fixture
def elevenlabs_service():
    """Create ElevenLabs service for testing."""
    from src.services.elevenlabs_client import ElevenLabsService
    return ElevenLabsService()


@pytest.fixture
def storage_service():
    """Create storage service for testing."""
    from src.services.storage_service import StorageService
    return StorageService()
