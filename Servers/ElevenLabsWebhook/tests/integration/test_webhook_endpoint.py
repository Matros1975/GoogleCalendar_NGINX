"""
Integration tests for webhook endpoint.
"""

import json
import pytest
from httpx import AsyncClient, ASGITransport
from contextlib import asynccontextmanager

import src.main as main_module
from src.auth.hmac_validator import HMACValidator
from src.handlers.transcription_handler import TranscriptionHandler
from src.handlers.audio_handler import AudioHandler
from src.handlers.call_failure_handler import CallFailureHandler


@pytest.fixture(autouse=True)
def setup_app(webhook_secret):
    """Initialize app components before tests."""
    # Manually initialize the global components that startup_event would set
    main_module.hmac_validator = HMACValidator(secret=webhook_secret)
    main_module.transcription_handler = TranscriptionHandler()
    main_module.audio_handler = AudioHandler()
    main_module.call_failure_handler = CallFailureHandler()
    yield
    # Cleanup
    main_module.hmac_validator = None
    main_module.transcription_handler = None
    main_module.audio_handler = None
    main_module.call_failure_handler = None


class TestWebhookEndpoint:
    """Integration tests for the /webhook endpoint."""
    
    @pytest.fixture
    def validator(self, webhook_secret):
        """Create HMAC validator for generating signatures."""
        return HMACValidator(secret=webhook_secret)
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test health check endpoint."""
        transport = ASGITransport(app=main_module.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "elevenlabs-webhook"
    
    @pytest.mark.asyncio
    async def test_webhook_transcription(self, validator, sample_transcription_payload):
        """Test webhook endpoint with transcription payload."""
        payload_bytes = json.dumps(sample_transcription_payload).encode("utf-8")
        signature = validator.generate_signature(payload_bytes)
        
        transport = ASGITransport(app=main_module.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/webhook",
                content=payload_bytes,
                headers={
                    "elevenlabs-signature": signature,
                    "content-type": "application/json"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
    
    @pytest.mark.asyncio
    async def test_webhook_audio(self, validator, sample_audio_payload):
        """Test webhook endpoint with audio payload."""
        payload_bytes = json.dumps(sample_audio_payload).encode("utf-8")
        signature = validator.generate_signature(payload_bytes)
        
        transport = ASGITransport(app=main_module.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/webhook",
                content=payload_bytes,
                headers={
                    "elevenlabs-signature": signature,
                    "content-type": "application/json"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
    
    @pytest.mark.asyncio
    async def test_webhook_call_failure(self, validator, sample_call_failure_payload):
        """Test webhook endpoint with call failure payload."""
        payload_bytes = json.dumps(sample_call_failure_payload).encode("utf-8")
        signature = validator.generate_signature(payload_bytes)
        
        transport = ASGITransport(app=main_module.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/webhook",
                content=payload_bytes,
                headers={
                    "elevenlabs-signature": signature,
                    "content-type": "application/json"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
    
    @pytest.mark.asyncio
    async def test_webhook_invalid_signature(self):
        """Test webhook endpoint rejects invalid signature."""
        import time
        payload = {"type": "post_call_transcription", "conversation_id": "test", "agent_id": "test"}
        payload_bytes = json.dumps(payload).encode("utf-8")
        
        # Use current timestamp but invalid hash
        current_timestamp = int(time.time())
        
        transport = ASGITransport(app=main_module.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/webhook",
                content=payload_bytes,
                headers={
                    "elevenlabs-signature": f"t={current_timestamp},v0=invalid_hash",
                    "content-type": "application/json"
                }
            )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_webhook_missing_signature(self):
        """Test webhook endpoint rejects missing signature."""
        payload = {"type": "post_call_transcription", "conversation_id": "test", "agent_id": "test"}
        payload_bytes = json.dumps(payload).encode("utf-8")
        
        transport = ASGITransport(app=main_module.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/webhook",
                content=payload_bytes,
                headers={"content-type": "application/json"}
            )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_webhook_invalid_json(self, validator):
        """Test webhook endpoint rejects invalid JSON."""
        invalid_payload = b"not valid json {"
        signature = validator.generate_signature(invalid_payload)
        
        transport = ASGITransport(app=main_module.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/webhook",
                content=invalid_payload,
                headers={
                    "elevenlabs-signature": signature,
                    "content-type": "application/json"
                }
            )
        
        assert response.status_code == 400
        assert "Invalid JSON" in response.text
    
    @pytest.mark.asyncio
    async def test_webhook_unknown_type(self, validator):
        """Test webhook endpoint rejects unknown webhook type."""
        payload = {"type": "unknown_webhook_type", "conversation_id": "test", "agent_id": "test"}
        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = validator.generate_signature(payload_bytes)
        
        transport = ASGITransport(app=main_module.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/webhook",
                content=payload_bytes,
                headers={
                    "elevenlabs-signature": signature,
                    "content-type": "application/json"
                }
            )
        
        assert response.status_code == 400
        assert "Unknown webhook type" in response.text
