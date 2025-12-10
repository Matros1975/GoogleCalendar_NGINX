"""
Example test script for testing webhooks manually.

Usage:
    python examples/test_webhook.py
"""

import asyncio
import httpx
import json
from datetime import datetime


async def test_3cx_webhook():
    """Test 3CX incoming call webhook."""
    print("Testing 3CX webhook...")
    
    payload = {
        "event_type": "IncomingCall",
        "call_id": "test_call_123",
        "caller_id": "+31612345678",
        "called_number": "+31201234567",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "direction": "In"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:3006/webhook/3cx",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30.0
            )
            
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            
        except Exception as e:
            print(f"Error: {e}")


async def test_postcall_webhook():
    """Test ElevenLabs POST-call webhook."""
    print("\nTesting POST-call webhook...")
    
    payload = {
        "call_id": "test_call_123",
        "agent_id": "agent_test",
        "transcript": "Test conversation",
        "duration_seconds": 60,
        "status": "completed",
        "custom_variables": {
            "caller_id": "+31612345678"
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:3006/webhook/postcall",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30.0
            )
            
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            
        except Exception as e:
            print(f"Error: {e}")


async def test_health_check():
    """Test health check endpoint."""
    print("\nTesting health check...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "http://localhost:3006/health",
                timeout=10.0
            )
            
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            
        except Exception as e:
            print(f"Error: {e}")


async def main():
    """Run all tests."""
    print("Voice Clone Pre-Call Service - Webhook Test Script")
    print("=" * 60)
    
    await test_health_check()
    await test_3cx_webhook()
    await test_postcall_webhook()
    
    print("\n" + "=" * 60)
    print("Tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
