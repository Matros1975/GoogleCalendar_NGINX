# Conversation ID Logging

## Overview

All log entries now include the `conversation_id` automatically, making it easy to filter and analyze logs for specific webhook calls.

## Log Format

```
2025-11-30 09:28:09 - [conv_custom_001] - handler - INFO - Processing webhook
                       ^^^^^^^^^^^^^^^
                       conversation_id
```

## Usage

### Automatic Injection

The conversation_id is automatically added to all log entries within each webhook handler:

```python
# In transcription_handler.py
async def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
    transcription = TranscriptionPayload.from_dict(payload)
    
    # Set conversation context (done once at the start)
    conversation_context.set(transcription.conversation_id)
    
    # All subsequent logs automatically include conversation_id
    logger.info("Processing webhook")  # [conv_001] included automatically
    logger.info("Creating ticket")     # [conv_001] included automatically
```

### Filtering Logs

**View all logs for a specific conversation:**
```bash
grep 'conv_custom_001' /home/ubuntu/GoogleCalendar_NGINX/logs/webhook.log
```

**Count tickets created per conversation:**
```bash
grep "Ticket created" webhook.log | cut -d'[' -f2 | cut -d']' -f1 | sort | uniq -c
```

**Timeline for one conversation:**
```bash
grep 'conv_custom_001' webhook.log | less
```

**Find errors for specific conversation:**
```bash
grep 'conv_custom_001' webhook.log | grep ERROR
```

**All conversations with errors:**
```bash
grep ERROR webhook.log | grep -oP '\[conv_[^\]]+\]' | sort | uniq
```

## Concurrent Calls

When multiple webhooks arrive simultaneously, logs are interleaved but easily filterable:

```
2025-11-30 09:28:09 - [conv_001] - handler - INFO - Processing webhook
2025-11-30 09:28:09 - [conv_002] - handler - INFO - Processing webhook
2025-11-30 09:28:09 - [conv_003] - handler - INFO - Processing webhook
2025-11-30 09:28:10 - [conv_001] - handler - INFO - Ticket created
2025-11-30 09:28:10 - [conv_002] - handler - INFO - Ticket created
2025-11-30 09:28:10 - [conv_003] - handler - INFO - Ticket created
```

Filter by conversation_id to see only one conversation's timeline:
```bash
$ grep 'conv_001' webhook.log
2025-11-30 09:28:09 - [conv_001] - handler - INFO - Processing webhook
2025-11-30 09:28:10 - [conv_001] - handler - INFO - Ticket created
```

## JSON Format (Optional)

Set `LOG_FORMAT=json` in `.env` for structured logging:

```json
{
  "timestamp": "2025-11-30T09:28:09Z",
  "level": "INFO",
  "logger": "src.handlers.transcription_handler",
  "message": "Processing webhook",
  "conversation_id": "conv_custom_001"
}
```

Filter with jq:
```bash
jq '.conversation_id == "conv_001"' webhook.log
```

## Implementation Details

- **ContextVar**: Uses Python `contextvars` for async-safe storage
- **ConversationFilter**: Logging filter that injects conversation_id into each record
- **Default Value**: `N/A` when no conversation context is set
- **Handlers**: Filter applied to both console and file handlers
- **All handlers**: Works for transcription, audio, and call_failure webhooks

## Benefits

✅ **Easy debugging**: Trace entire conversation flow  
✅ **Concurrent safe**: Multiple webhooks don't interfere  
✅ **Single log file**: No file explosion, manageable rotation  
✅ **Fast filtering**: Simple grep commands  
✅ **Analytics ready**: Easy to aggregate and analyze  
✅ **No performance impact**: Filter is lightweight  

## Comparison

| Approach | Pros | Cons |
|----------|------|------|
| **Per-session files** | Complete isolation | File explosion, no rotation |
| **conversation_id in logs** ✅ | Best of both worlds | Requires grep/filtering |
| **No identification** | Simplest | Impossible to trace conversations |
