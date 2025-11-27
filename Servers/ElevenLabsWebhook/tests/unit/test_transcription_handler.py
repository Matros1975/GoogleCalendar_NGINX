"""
Unit tests for TranscriptionHandler.
"""

import pytest

from src.handlers.transcription_handler import TranscriptionHandler


class TestTranscriptionHandler:
    """Tests for TranscriptionHandler class."""
    
    @pytest.fixture
    def handler(self):
        """Create handler instance for testing."""
        return TranscriptionHandler(storage=None)
    
    @pytest.mark.asyncio
    async def test_handle_valid_payload(self, handler, sample_transcription_payload):
        """Test handling of valid transcription payload."""
        result = await handler.handle(sample_transcription_payload)
        
        assert result["status"] == "processed"
        assert result["conversation_id"] == "conv_test_123"
        assert result["agent_id"] == "agent_test_456"
    
    @pytest.mark.asyncio
    async def test_handle_minimal_payload(self, handler):
        """Test handling of minimal payload without data."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_minimal",
            "agent_id": "agent_minimal"
        }
        
        result = await handler.handle(payload)
        
        assert result["status"] == "processed"
        assert result["conversation_id"] == "conv_minimal"
    
    @pytest.mark.asyncio
    async def test_handle_payload_with_empty_data(self, handler):
        """Test handling of payload with empty data object."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_empty",
            "agent_id": "agent_empty",
            "data": {}
        }
        
        result = await handler.handle(payload)
        
        assert result["status"] == "processed"
    
    @pytest.mark.asyncio
    async def test_handle_payload_with_analysis(self, handler, sample_transcription_payload):
        """Test handling of payload with analysis results."""
        result = await handler.handle(sample_transcription_payload)
        
        # Should process without error
        assert result["status"] == "processed"
    
    @pytest.mark.asyncio
    async def test_handle_payload_with_audio_availability_fields(self, handler):
        """Test handling of payload with new audio availability fields (August 2025)."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_audio",
            "agent_id": "agent_audio",
            "data": {
                "conversation_id": "conv_audio",
                "agent_id": "agent_audio",
                "has_audio": True,
                "has_user_audio": True,
                "has_response_audio": True,
                "transcript": []
            }
        }
        
        result = await handler.handle(payload)
        
        assert result["status"] == "processed"
    
    @pytest.mark.asyncio
    async def test_handle_payload_with_metadata(self, handler):
        """Test handling of payload with dynamic variables/metadata."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_meta",
            "agent_id": "agent_meta",
            "data": {
                "conversation_id": "conv_meta",
                "agent_id": "agent_meta",
                "metadata": {
                    "customer_id": "cust_123",
                    "order_number": "12345",
                    "custom_field": "custom_value"
                }
            }
        }
        
        result = await handler.handle(payload)
        
        assert result["status"] == "processed"
    
    @pytest.mark.asyncio
    async def test_handle_payload_with_long_transcript(self, handler):
        """Test handling of payload with many transcript entries."""
        transcript = [
            {"role": "agent" if i % 2 == 0 else "user", "message": f"Message {i}", "time_in_call_secs": i * 2.0}
            for i in range(100)
        ]
        
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_long",
            "agent_id": "agent_long",
            "data": {
                "conversation_id": "conv_long",
                "agent_id": "agent_long",
                "transcript": transcript
            }
        }
        
        result = await handler.handle(payload)
        
        assert result["status"] == "processed"


class TestFormattedTranscript:
    """Tests for formatted transcript generation."""
    
    @pytest.fixture
    def handler(self):
        """Create handler instance for testing."""
        return TranscriptionHandler(storage=None)
    
    @pytest.mark.asyncio
    async def test_formatted_transcript_basic(self, handler):
        """Test basic transcript formatting without tool calls."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_format_test",
            "agent_id": "agent_test",
            "data": {
                "transcript": [
                    {
                        "role": "agent",
                        "message": "Hello! How can I help?",
                        "time_in_call_secs": 0.5
                    },
                    {
                        "role": "user",
                        "message": "I need assistance",
                        "time_in_call_secs": 3.2
                    }
                ]
            }
        }
        
        result = await handler.handle(payload)
        
        assert "formatted_transcript" in result
        transcript = result["formatted_transcript"]
        
        # Validate format
        assert "[00:00:00] - agent: Hello! How can I help?" in transcript
        assert "[00:00:03] - caller: I need assistance" in transcript
    
    @pytest.mark.asyncio
    async def test_formatted_transcript_with_tool_calls(self, handler):
        """Test transcript formatting with tool calls."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_tool_test",
            "agent_id": "agent_test",
            "data": {
                "transcript": [
                    {
                        "role": "agent",
                        "message": "Let me check that for you",
                        "time_in_call_secs": 8.1,
                        "tool_call": {
                            "name": "get_order_status",
                            "arguments": "{\"order_id\": \"12345\"}"
                        }
                    },
                    {
                        "role": "agent",
                        "message": "",
                        "time_in_call_secs": 10.5,
                        "tool_result": {
                            "output": "{\"status\": \"shipped\", \"tracking\": \"ABC123\"}"
                        }
                    }
                ]
            }
        }
        
        result = await handler.handle(payload)
        transcript = result["formatted_transcript"]
        
        # Validate tool call formatting
        assert "toolcall: get_order_status" in transcript
        assert 'order_id="12345"' in transcript
        assert "toolcall_result:" in transcript
        assert '"status": "shipped"' in transcript
    
    @pytest.mark.asyncio
    async def test_formatted_transcript_timestamp_conversion(self, handler):
        """Test timestamp formatting (seconds to HH:MM:SS)."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_time_test",
            "agent_id": "agent_test",
            "data": {
                "transcript": [
                    {"role": "agent", "message": "Start", "time_in_call_secs": 0},
                    {"role": "agent", "message": "One minute", "time_in_call_secs": 65},
                    {"role": "agent", "message": "One hour", "time_in_call_secs": 3665}
                ]
            }
        }
        
        result = await handler.handle(payload)
        transcript = result["formatted_transcript"]
        
        assert "[00:00:00]" in transcript
        assert "[00:01:05]" in transcript
        assert "[01:01:05]" in transcript
    
    @pytest.mark.asyncio
    async def test_formatted_transcript_empty(self, handler):
        """Test handling of missing or empty transcript."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_empty",
            "agent_id": "agent_test",
            "data": {}
        }
        
        result = await handler.handle(payload)
        
        # Should handle gracefully
        assert result["formatted_transcript"] == ""
    
    @pytest.mark.asyncio
    async def test_formatted_transcript_role_mapping(self, handler):
        """Test that 'user' role is mapped to 'caller'."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_role_test",
            "agent_id": "agent_test",
            "data": {
                "transcript": [
                    {"role": "user", "message": "Hello", "time_in_call_secs": 1.0}
                ]
            }
        }
        
        result = await handler.handle(payload)
        transcript = result["formatted_transcript"]
        
        # 'user' should be displayed as 'caller'
        assert "caller:" in transcript
        assert "user:" not in transcript
    
    @pytest.mark.asyncio
    async def test_formatted_transcript_no_data(self, handler):
        """Test handling when data is None."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_no_data",
            "agent_id": "agent_test"
        }
        
        result = await handler.handle(payload)
        
        assert result["formatted_transcript"] == ""
    
    @pytest.mark.asyncio
    async def test_formatted_transcript_tool_call_with_dict_arguments(self, handler):
        """Test tool call formatting when arguments are already a dict."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_dict_args",
            "agent_id": "agent_test",
            "data": {
                "transcript": [
                    {
                        "role": "agent",
                        "message": "Checking",
                        "time_in_call_secs": 5.0,
                        "tool_call": {
                            "name": "search_orders",
                            "arguments": {"customer_id": "cust_123", "limit": 10}
                        }
                    }
                ]
            }
        }
        
        result = await handler.handle(payload)
        transcript = result["formatted_transcript"]
        
        assert "toolcall: search_orders" in transcript
        assert 'customer_id="cust_123"' in transcript
        assert 'limit="10"' in transcript
    
    @pytest.mark.asyncio
    async def test_formatted_transcript_tool_result_with_dict_output(self, handler):
        """Test tool result formatting when output is already a dict."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_dict_output",
            "agent_id": "agent_test",
            "data": {
                "transcript": [
                    {
                        "role": "agent",
                        "message": "",
                        "time_in_call_secs": 10.0,
                        "tool_result": {
                            "output": {"status": "success", "count": 5}
                        }
                    }
                ]
            }
        }
        
        result = await handler.handle(payload)
        transcript = result["formatted_transcript"]
        
        assert "toolcall_result:" in transcript
        # Dict should be serialized to JSON
        assert "status" in transcript
        assert "success" in transcript
    
    @pytest.mark.asyncio
    async def test_formatted_transcript_tool_call_with_quotes_in_value(self, handler):
        """Test tool call formatting when arguments contain quotes."""
        payload = {
            "type": "post_call_transcription",
            "conversation_id": "conv_quotes",
            "agent_id": "agent_test",
            "data": {
                "transcript": [
                    {
                        "role": "agent",
                        "message": "Searching",
                        "time_in_call_secs": 5.0,
                        "tool_call": {
                            "name": "search",
                            "arguments": {"query": 'test "quoted" value'}
                        }
                    }
                ]
            }
        }
        
        result = await handler.handle(payload)
        transcript = result["formatted_transcript"]
        
        # Quotes should be escaped
        assert "toolcall: search" in transcript
        assert '\\"quoted\\"' in transcript
