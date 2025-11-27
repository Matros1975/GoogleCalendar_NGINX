"""
Unit tests for CallFailureHandler.
"""

import pytest

from src.handlers.call_failure_handler import CallFailureHandler


class TestCallFailureHandler:
    """Tests for CallFailureHandler class."""
    
    @pytest.fixture
    def handler(self):
        """Create handler instance for testing."""
        return CallFailureHandler()
    
    @pytest.mark.asyncio
    async def test_handle_valid_payload(self, handler, sample_call_failure_payload):
        """Test handling of valid call failure payload."""
        result = await handler.handle(sample_call_failure_payload)
        
        assert result["status"] == "processed"
        assert result["conversation_id"] == "conv_test_123"
        assert result["agent_id"] == "agent_test_456"
        assert result["error_message"] == "Call failed - line busy"
        assert result["error_code"] == "BUSY"
        assert result["provider"] == "twilio"
    
    @pytest.mark.asyncio
    async def test_handle_minimal_payload(self, handler):
        """Test handling of minimal failure payload."""
        payload = {
            "type": "call_initiation_failure",
            "conversation_id": "conv_minimal",
            "agent_id": "agent_minimal",
            "error_message": "Unknown error"
        }
        
        result = await handler.handle(payload)
        
        assert result["status"] == "processed"
        assert result["error_message"] == "Unknown error"
        assert result["error_code"] is None
        assert result["provider"] is None
    
    @pytest.mark.asyncio
    async def test_handle_sip_provider(self, handler):
        """Test handling of SIP provider failure."""
        payload = {
            "type": "call_initiation_failure",
            "conversation_id": "conv_sip",
            "agent_id": "agent_sip",
            "error_message": "SIP call failed",
            "error_code": "NO_ANSWER",
            "provider": "sip",
            "provider_details": {
                "sip_code": 486,
                "sip_reason": "Busy Here"
            }
        }
        
        result = await handler.handle(payload)
        
        assert result["status"] == "processed"
        assert result["provider"] == "sip"
    
    @pytest.mark.asyncio
    async def test_handle_twilio_provider(self, handler):
        """Test handling of Twilio provider failure."""
        payload = {
            "type": "call_initiation_failure",
            "conversation_id": "conv_twilio",
            "agent_id": "agent_twilio",
            "error_message": "Twilio call failed",
            "error_code": "NO_ANSWER",
            "provider": "twilio",
            "provider_details": {
                "error_code": "31005",
                "error_message": "Call rejected",
                "call_status": "no-answer"
            }
        }
        
        result = await handler.handle(payload)
        
        assert result["status"] == "processed"
        assert result["provider"] == "twilio"
    
    def test_get_failure_description_known_reason(self, handler):
        """Test failure description for known reasons."""
        assert "busy" in handler.get_failure_description("busy").lower()
        assert "answer" in handler.get_failure_description("no-answer").lower()
        assert "rejected" in handler.get_failure_description("rejected").lower()
    
    def test_get_failure_description_unknown_reason(self, handler):
        """Test failure description for unknown reason."""
        description = handler.get_failure_description("some_unknown_reason")
        assert "unknown" in description.lower()
    
    def test_get_failure_description_case_insensitive(self, handler):
        """Test failure description is case insensitive."""
        desc1 = handler.get_failure_description("BUSY")
        desc2 = handler.get_failure_description("busy")
        assert desc1 == desc2
    
    @pytest.mark.asyncio
    async def test_handle_payload_without_provider_details(self, handler):
        """Test handling of payload without provider details."""
        payload = {
            "type": "call_initiation_failure",
            "conversation_id": "conv_no_details",
            "agent_id": "agent_no_details",
            "error_message": "Call failed",
            "provider": "twilio"
        }
        
        result = await handler.handle(payload)
        
        assert result["status"] == "processed"
    
    @pytest.mark.asyncio
    async def test_handle_various_error_codes(self, handler):
        """Test handling of various error codes."""
        error_codes = ["BUSY", "NO_ANSWER", "REJECTED", "INVALID_NUMBER", "NETWORK_ERROR", "UNKNOWN"]
        
        for code in error_codes:
            payload = {
                "type": "call_initiation_failure",
                "conversation_id": f"conv_{code}",
                "agent_id": "agent_test",
                "error_message": f"Error: {code}",
                "error_code": code
            }
            
            result = await handler.handle(payload)
            
            assert result["status"] == "processed"
            assert result["error_code"] == code
