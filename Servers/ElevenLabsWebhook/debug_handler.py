#!/usr/bin/env python3
"""
Debug script for TranscriptionHandler.
Run this with VS Code debugger to step through handler logic with custom payloads.

Set breakpoints in:
- src/handlers/transcription_handler.py
- src/utils/topdesk_client.py (if exists)
- src/utils/email_sender.py (if exists)
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from src.handlers.transcription_handler import TranscriptionHandler


# Example payload - customize this for your debugging needs
SAMPLE_PAYLOAD = {
    "type": "post_call_transcription",
    "conversation_id": "conv_debug_12345",
    "agent_id": "agent_debug_001",
    "data": {
        "transcript": [
            {
                "role": "agent",
                "message": "Hello! How can I help you today?",
                "time_in_call_secs": 0.0
            },
            {
                "role": "user",
                "message": "Hi, I need help with my password reset",
                "time_in_call_secs": 2.5
            },
            {
                "role": "agent",
                "message": "I can help you with that. Let me create a ticket.",
                "time_in_call_secs": 5.0
            },
            {
                "role": "user",
                "message": "Thank you. My email is john.doe@example.com",
                "time_in_call_secs": 8.0
            }
        ],
        "metadata": {
            "duration_secs": 15.5,
            "cost": 0.05
        }
    }
}

# Payload with tool calls
PAYLOAD_WITH_TOOLS = {
    "type": "post_call_transcription",
    "conversation_id": "conv_debug_tools",
    "agent_id": "agent_debug_002",
    "data": {
        "transcript": [
            {
                "role": "agent",
                "message": "Let me check your account status",
                "time_in_call_secs": 0.0
            },
            {
                "role": "tool_call",
                "message": "check_account_status",
                "tool_call_id": "call_123",
                "time_in_call_secs": 2.0
            },
            {
                "role": "tool_result",
                "message": '{"status": "active", "last_login": "2025-11-28"}',
                "tool_call_id": "call_123",
                "time_in_call_secs": 2.5
            },
            {
                "role": "agent",
                "message": "Your account is active. Last login was yesterday.",
                "time_in_call_secs": 3.0
            }
        ]
    }
}

# Minimal payload (no transcript data)
MINIMAL_PAYLOAD = {
    "type": "post_call_transcription",
    "conversation_id": "conv_debug_minimal",
    "agent_id": "agent_debug_003",
    "data": {}
}


async def main():
    """Run handler with sample payload."""
    print("=" * 80)
    print("TranscriptionHandler Debug Script")
    print("=" * 80)
    
    # Choose which payload to use
    # Modify this to test different scenarios
    payload = SAMPLE_PAYLOAD
    # payload = PAYLOAD_WITH_TOOLS
    # payload = MINIMAL_PAYLOAD
    
    print(f"\nUsing payload: {payload['conversation_id']}")
    print(f"Transcript entries: {len(payload.get('data', {}).get('transcript', []))}")
    
    # Set breakpoint on next line to inspect payload before processing
    handler = TranscriptionHandler(storage=None)
    
    print("\n--- Starting handler processing ---\n")
    
    # Set breakpoint here to step through handler.handle()
    result = await handler.handle(payload)
    
    print("\n--- Handler processing complete ---\n")
    print("Result:")
    print(f"  Status: {result.get('status')}")
    print(f"  Conversation ID: {result.get('conversation_id')}")
    print(f"  Formatted Transcript Length: {len(result.get('formatted_transcript', ''))}")
    
    if result.get('ticket_created'):
        print(f"  ✓ Ticket Created: {result.get('ticket_number')}")
        print(f"  ✓ Transcript Added: {result.get('transcript_added')}")
    else:
        print(f"  ✗ Ticket Not Created")
        if result.get('error'):
            print(f"  Error: {result.get('error')}")
        if result.get('email_sent'):
            print(f"  ✓ Error Email Sent")
    
    print("\nFormatted Transcript:")
    print("-" * 80)
    print(result.get('formatted_transcript', '(empty)'))
    print("-" * 80)
    
    return result


if __name__ == "__main__":
    # Run the async function
    result = asyncio.run(main())
    
    # Exit code based on result
    if result.get('status') == 'processed':
        sys.exit(0)
    else:
        sys.exit(1)
