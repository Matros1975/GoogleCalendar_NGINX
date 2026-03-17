"""
Pytest configuration for ElevenLabs Webhook tests.
"""

import os
import pytest

# Set test environment variables BEFORE importing anything
os.environ.setdefault("ELEVENLABS_WEBHOOK_SECRET", "test-secret-key")
os.environ.setdefault("LOG_LEVEL", "DEBUG")
os.environ.setdefault("ENABLE_AUDIO_STORAGE", "false")
os.environ.setdefault("ENABLE_TRANSCRIPT_STORAGE", "false")

# Configure logging directories for tests
from src.utils.logger import get_logger
logger = get_logger(__name__)
# Use centralized logging location if not already set
os.environ.setdefault("LOG_DIR", "/home/ubuntu/GoogleCalendar_NGINX/logs")
os.environ.setdefault("LOG_FILENAME", "webhook.log")

# Initialize logger at module level (before any test imports)
from src.utils.logger import setup_logger
setup_logger()  # Configure root logger for all tests


@pytest.fixture
def webhook_secret():
    """Provide test webhook secret."""
    return "test-secret-key"


@pytest.fixture
def sample_transcription_payload():
    """Provide sample transcription webhook payload."""
    return {
        "type": "post_call_transcription",
        "conversation_id": "conv_test_123",
        "agent_id": "agent_test_456",
        "data": {
            "conversation_id": "conv_test_123",
            "agent_id": "agent_test_456",
            "status": "completed",
            "call_duration_secs": 120.5,
            "message_count": 6,
            "start_time_unix_secs": 1700000000,
            "end_time_unix_secs": 1700000120,
            "transcript": [
                {"role": "agent", "message": "Hello!", "time_in_call_secs": 0.5},
                {"role": "user", "message": "Hi there", "time_in_call_secs": 2.0}
            ],
            "analysis": {
                "call_summary": "Test call summary",
                "evaluation": {"sentiment": "positive"},
                "data_collection": {"test_field": "test_value"}
            },
            "metadata": {"test_var": "test_value"}
        }
    }


@pytest.fixture
def sample_audio_payload():
    """Provide sample audio webhook payload."""
    return {
        "type": "post_call_audio",
        "conversation_id": "conv_test_123",
        "agent_id": "agent_test_456",
        "audio_base64": "SGVsbG8gV29ybGQh",  # "Hello World!" in base64
        "audio_format": "mp3"
    }


@pytest.fixture
def sample_call_failure_payload():
    """Provide sample call failure webhook payload."""
    return {
        "type": "call_initiation_failure",
        "conversation_id": "conv_test_123",
        "agent_id": "agent_test_456",
        "error_message": "Call failed - line busy",
        "error_code": "BUSY",
        "provider": "twilio",
        "provider_details": {
            "error_code": "31005",
            "call_status": "busy"
        }
    }
