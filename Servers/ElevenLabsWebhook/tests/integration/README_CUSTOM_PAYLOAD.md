# Custom Payload Testing

This directory contains the `custom_payload.json` file for testing webhook handling with your own payloads.

## How to Use

1. **Edit `custom_payload.json`** with your custom webhook data
2. **Set a breakpoint** in `transcription_handler.py` (e.g., line 170)
3. **Run the debug configuration**: "Debug Integration Test (Custom Payload, Create TopDesk Ticket)"
4. **Step through** the code to see how your payload is processed

## Payload Structure

The payload must follow the ElevenLabs webhook format:

```json
{
  "type": "post_call_transcription",
  "conversation_id": "your_conversation_id",
  "agent_id": "your_agent_id",
  "data": {
    "transcript": [
      {
        "role": "agent",
        "message": "Your message here",
        "time_in_call_secs": 0
      },
      {
        "role": "user",
        "message": "User response",
        "time_in_call_secs": 5
      }
    ]
  }
}
```

## What Happens During Test

1. **Payload is loaded** from `custom_payload.json`
2. **OpenAI extracts** ticket data from the transcript
3. **TopDesk ticket** is created with extracted information
4. **Full transcript** is attached as invisible action
5. **Results are logged** to `/home/ubuntu/GoogleCalendar_NGINX/logs/webhook.log`

## Debugging Tips

- **Watch Variables**: Inspect `payload`, `formatted_transcript`, `ticket_data`, `result`
- **Monitor Logs**: `tail -f /home/ubuntu/GoogleCalendar_NGINX/logs/webhook.log`
- **Check Output**: Debug console shows detailed extraction results

## Example Payloads

The default `custom_payload.json` includes:
- User with laptop power failure issue
- Caller info (name, email)
- High urgency scenario
- Hardware category

Modify it to test:
- Different issue types
- Various caller information formats
- Edge cases (missing data, unusual requests)
- Long/short transcripts

## Logs Location

All logs are written to: `/home/ubuntu/GoogleCalendar_NGINX/logs/webhook.log`

Logs include:
- Payload parsing
- OpenAI API calls
- TopDesk ticket creation
- Email notifications (on error)
