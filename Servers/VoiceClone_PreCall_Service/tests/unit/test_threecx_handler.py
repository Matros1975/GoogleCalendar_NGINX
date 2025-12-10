"""
Unit tests for 3CX handler.
"""

import pytest
from src.models.webhook_models import ThreeCXWebhookPayload
from src.handlers.threecx_handler import ThreeCXHandler


@pytest.mark.asyncio
async def test_handle_incoming_call(
    mock_async_voice_service,
    sample_3cx_webhook_payload
):
    """Test handling incoming call webhook."""
    handler = ThreeCXHandler(async_service=mock_async_voice_service)
    
    payload = ThreeCXWebhookPayload(**sample_3cx_webhook_payload)
    
    response = await handler.handle(payload)
    
    assert response.status == "success"
    assert response.call_id == "greeting_123"
    assert response.threecx_call_id == "3cx_call_123"
    
    mock_async_voice_service.process_incoming_call.assert_called_once()


@pytest.mark.asyncio
async def test_handle_invalid_event_type(
    mock_async_voice_service,
    sample_3cx_webhook_payload
):
    """Test handling invalid event type."""
    handler = ThreeCXHandler(async_service=mock_async_voice_service)
    
    # Modify payload to have invalid event type
    sample_3cx_webhook_payload["event_type"] = "InvalidEvent"
    payload = ThreeCXWebhookPayload(**sample_3cx_webhook_payload)
    
    with pytest.raises(ValueError):
        await handler.handle(payload)
