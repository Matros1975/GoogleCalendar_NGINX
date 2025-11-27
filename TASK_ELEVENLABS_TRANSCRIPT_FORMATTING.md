# Task: Extend TranscriptionHandler with Formatted Transcript Generation

## Objective
Extend the `TranscriptionHandler.handle()` method in the ElevenLabs Webhook service to generate a formatted text transcript from the webhook payload.

## Context
- **Repository**: GoogleCalendar_NGINX
- **Service**: Servers/ElevenLabsWebhook
- **File to modify**: `src/handlers/transcription_handler.py`
- **Test file**: `tests/unit/test_transcription_handler.py`
- **Input schema**: ElevenLabs `post_call_transcription` webhook (see reference below)

## Requirements

### 1. Formatted Transcript Generation

**Format Specification:**
```
[HH:MM:SS] - agent: Hello! How can I help you?
[HH:MM:SS] - caller: I need help with my order.
[HH:MM:SS] - toolcall: get_order_status(order_id="12345")
[HH:MM:SS] - toolcall_result: {"status": "shipped", "tracking": "ABC123"}
[HH:MM:SS] - agent: Your order has been shipped with tracking number ABC123.
```

**Components:**
- **Timestamp**: `[HH:MM:SS]` - derived from `time_in_call_secs` (convert to hours:minutes:seconds)
- **Separator**: ` - `
- **Speaker**: `agent` or `caller` (map from `role` field)
- **Separator**: `: `
- **Text**: The message content or tool call data

**Tool Call Format:**
- Tool invocation: `toolcall: function_name(arg1="value1", arg2="value2")`
- Tool result: `toolcall_result: {json_data}`
- Insert tool calls chronologically based on their timestamp in the transcript

### 2. Implementation Details

**Modify `TranscriptionHandler.handle()` method:**

```python
async def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
    # ... existing code ...
    
    # NEW: Generate formatted transcript
    formatted_transcript = self._generate_formatted_transcript(transcription.data)
    
    return {
        "status": "processed",
        "conversation_id": transcription.conversation_id,
        "agent_id": transcription.agent_id,
        "saved_path": saved_path,
        "formatted_transcript": formatted_transcript  # NEW: Add for unit test validation
    }
```

**Add new private method:**

```python
def _generate_formatted_transcript(self, data: Optional[ConversationData]) -> str:
    """
    Generate formatted text transcript from conversation data.
    
    Format: [HH:MM:SS] - speaker: message
    Tool calls are included as 'toolcall' entries.
    
    Args:
        data: Conversation data containing transcript
        
    Returns:
        Formatted transcript string with timestamps
    """
    # Implementation here
    # 1. Check if data and transcript exist
    # 2. Process each transcript entry
    # 3. Convert time_in_call_secs to [HH:MM:SS] format
    # 4. Map role to speaker (agent/caller)
    # 5. Handle tool calls if present
    # 6. Sort chronologically and format
    # 7. Return formatted string
```

**Helper method for timestamp conversion:**

```python
def _format_timestamp(self, seconds: float) -> str:
    """
    Convert seconds to [HH:MM:SS] format.
    
    Args:
        seconds: Time in seconds (can be float)
        
    Returns:
        Formatted timestamp string [HH:MM:SS]
        
    Examples:
        0.5 -> [00:00:00]
        65.0 -> [00:01:05]
        3665.5 -> [01:01:05]
    """
    # Implementation here
```

### 3. Input Data Schema (ElevenLabs Reference)

**Transcript Entry Structure:**
```python
{
    "role": "agent" | "user",  # Map "user" to "caller"
    "message": "string",
    "time_in_call_secs": float,
    "tool_call": {  # Optional - present when agent calls a tool
        "name": "function_name",
        "arguments": "JSON string or dict"
    },
    "tool_result": {  # Optional - present when tool returns
        "output": "string or dict"
    }
}
```

**Full Payload Example:**
```python
{
    "type": "post_call_transcription",
    "conversation_id": "conv_abc123",
    "agent_id": "agent_xyz789",
    "data": {
        "transcript": [
            {
                "role": "agent",
                "message": "Hello! How can I help?",
                "time_in_call_secs": 0.5
            },
            {
                "role": "user",
                "message": "I need help with order 12345",
                "time_in_call_secs": 3.2
            },
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
                "message": "",  # May be empty when tool returns
                "time_in_call_secs": 10.5,
                "tool_result": {
                    "output": "{\"status\": \"shipped\", \"tracking\": \"ABC123\"}"
                }
            },
            {
                "role": "agent",
                "message": "Your order has shipped with tracking ABC123",
                "time_in_call_secs": 12.0
            }
        ],
        "status": "completed",
        "call_duration_secs": 45.5,
        "message_count": 5
    }
}
```

### 4. Unit Tests

**Create tests in `tests/unit/test_transcription_handler.py`:**

```python
class TestFormattedTranscript:
    """Tests for formatted transcript generation."""
    
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
            # ... with tool_call and tool_result entries
        }
        
        result = await handler.handle(payload)
        transcript = result["formatted_transcript"]
        
        # Validate tool call formatting
        assert "toolcall: get_order_status" in transcript
        assert "toolcall_result:" in transcript
    
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
        assert result["formatted_transcript"] == "" or result["formatted_transcript"] is None
    
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
```

### 5. Edge Cases to Handle

1. **Missing transcript**: Return empty string or None
2. **Empty messages**: Skip or show as empty line
3. **Tool calls without results**: Log tool call only
4. **Tool results without preceding calls**: Log as standalone result
5. **Malformed tool arguments**: Log raw string or error message
6. **Fractional seconds**: Round to nearest second for display
7. **Very long calls**: Handle timestamps > 24 hours gracefully

### 6. Model Updates (if needed)

Check `src/models/webhook_models.py` for transcript entry model. Ensure it supports:
- `tool_call` field (optional)
- `tool_result` field (optional)

If not present, add to the model:

```python
@dataclass
class TranscriptEntry:
    role: str
    message: str
    time_in_call_secs: float
    tool_call: Optional[Dict[str, Any]] = None
    tool_result: Optional[Dict[str, Any]] = None
```

### 7. Testing Commands

**Run unit tests:**
```bash
cd /home/ubuntu/GoogleCalendar_NGINX/Servers/ElevenLabsWebhook
pytest tests/unit/test_transcription_handler.py::TestFormattedTranscript -v
```

**Run all handler tests:**
```bash
pytest tests/unit/test_transcription_handler.py -v
```

**Coverage check:**
```bash
pytest tests/unit/test_transcription_handler.py --cov=src.handlers.transcription_handler --cov-report=term-missing
```

### 8. Expected Output Example

**Input:** Webhook payload with 5 transcript entries (2 with tool calls)

**Output in `result["formatted_transcript"]`:**
```
[00:00:00] - agent: Hello! How can I help you today?
[00:00:03] - caller: I need help with my order number 12345
[00:00:08] - agent: Let me check that for you
[00:00:08] - toolcall: get_order_status(order_id="12345")
[00:00:10] - toolcall_result: {"status": "shipped", "tracking": "ABC123"}
[00:00:12] - agent: Your order has been shipped with tracking number ABC123
[00:00:15] - caller: Thank you!
```

### 9. Implementation Checklist

- [ ] Add `_format_timestamp()` helper method
- [ ] Add `_generate_formatted_transcript()` method
- [ ] Update `handle()` to call new method and include result in return dict
- [ ] Update `ConversationData` or `TranscriptEntry` model if needed for tool call fields
- [ ] Create `TestFormattedTranscript` test class with all test cases
- [ ] Test with sample payloads (basic, tool calls, edge cases)
- [ ] Verify return structure includes `formatted_transcript` key
- [ ] Run full test suite to ensure no regressions
- [ ] Update docstrings for new/modified methods

### 10. Success Criteria

✅ All existing tests pass  
✅ New unit tests pass (minimum 5 test cases)  
✅ Formatted transcript correctly shows timestamps in [HH:MM:SS] format  
✅ Role mapping: "user" → "caller", "agent" → "agent"  
✅ Tool calls are logged with function name and arguments  
✅ Tool results are logged chronologically  
✅ Empty/missing transcripts handled gracefully  
✅ Return dict includes `formatted_transcript` for validation  
✅ Code follows existing patterns in the repository  

## References

- Existing handler: `src/handlers/transcription_handler.py`
- Existing tests: `tests/unit/test_transcription_handler.py`
- Models: `src/models/webhook_models.py`
- Test fixtures: `tests/conftest.py`
- ElevenLabs docs: https://elevenlabs.io/docs/api-reference/webhooks

## Notes

- Maintain backward compatibility - existing return fields must remain unchanged
- Follow existing code style (2-space indentation, type hints, docstrings)
- Log any errors during formatting but don't fail the webhook processing
- Consider adding the formatted transcript to the saved file (optional enhancement)
