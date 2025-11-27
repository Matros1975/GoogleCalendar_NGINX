#!/usr/bin/env python3
"""
Test utility to send webhook payloads to the ElevenLabs webhook service.

Usage:
    python test_webhook.py <payload_file> [secret] [endpoint]

Examples:
    python test_webhook.py test_payload_transcription.json my-secret
    python test_webhook.py test_payload_audio.json my-secret http://localhost:3004/webhook
"""

import sys
import json
import time
import hmac
import asyncio
from hashlib import sha256
from pathlib import Path

try:
    import httpx
except ImportError:
    print("httpx not installed. Run: pip install httpx")
    sys.exit(1)


def generate_signature(payload_bytes: bytes, secret: str, timestamp: int = None) -> str:
    """
    Generate a valid HMAC signature for the payload.
    
    Args:
        payload_bytes: Request body bytes
        secret: HMAC secret
        timestamp: Unix timestamp (defaults to current time)
        
    Returns:
        Signature header value "t=timestamp,v0=hash"
    """
    if timestamp is None:
        timestamp = int(time.time())
    
    payload_str = payload_bytes.decode("utf-8")
    full_payload = f"{timestamp}.{payload_str}"
    
    mac = hmac.new(
        key=secret.encode("utf-8"),
        msg=full_payload.encode("utf-8"),
        digestmod=sha256
    )
    
    return f"t={timestamp},v0={mac.hexdigest()}"


async def test_webhook(
    payload_file: str,
    secret: str,
    endpoint: str = "http://localhost:3004/webhook"
) -> dict:
    """
    Test webhook endpoint with a payload file.
    
    Args:
        payload_file: Path to JSON payload file
        secret: HMAC secret for signature generation
        endpoint: Webhook endpoint URL
        
    Returns:
        Dictionary with status and response data
    """
    # Resolve payload file path
    payload_path = Path(payload_file)
    if not payload_path.exists():
        # Try looking in examples directory
        examples_dir = Path(__file__).parent
        payload_path = examples_dir / payload_file
    
    if not payload_path.exists():
        return {"error": f"Payload file not found: {payload_file}"}
    
    # Load payload
    with open(payload_path, "r") as f:
        payload = json.load(f)
    
    # Convert to bytes
    payload_bytes = json.dumps(payload).encode("utf-8")
    
    # Generate HMAC signature
    signature = generate_signature(payload_bytes, secret)
    
    print(f"Sending webhook to: {endpoint}")
    print(f"Payload type: {payload.get('type')}")
    print(f"Signature: {signature[:50]}...")
    
    # Send request
    async with httpx.AsyncClient() as client:
        response = await client.post(
            endpoint,
            content=payload_bytes,
            headers={
                "elevenlabs-signature": signature,
                "content-type": "application/json"
            },
            timeout=30.0
        )
    
    result = {
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "body": response.text
    }
    
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Body: {response.text}")
    
    return result


async def test_invalid_signature(
    endpoint: str = "http://localhost:3004/webhook"
) -> dict:
    """
    Test that invalid signatures are rejected.
    
    Args:
        endpoint: Webhook endpoint URL
        
    Returns:
        Dictionary with status and response data
    """
    payload = {"type": "post_call_transcription", "conversation_id": "test", "agent_id": "test"}
    payload_bytes = json.dumps(payload).encode("utf-8")
    
    print("Testing invalid signature...")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            endpoint,
            content=payload_bytes,
            headers={
                "elevenlabs-signature": "t=1234567890,v0=invalid_hash",
                "content-type": "application/json"
            },
            timeout=30.0
        )
    
    print(f"Response Status: {response.status_code} (expected 401)")
    print(f"Response Body: {response.text}")
    
    return {
        "status_code": response.status_code,
        "body": response.text
    }


async def test_health_check(
    endpoint: str = "http://localhost:3004/health"
) -> dict:
    """
    Test health check endpoint.
    
    Args:
        endpoint: Health check endpoint URL
        
    Returns:
        Dictionary with status and response data
    """
    print(f"Testing health check: {endpoint}")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(endpoint, timeout=10.0)
    
    print(f"Response Status: {response.status_code}")
    print(f"Response Body: {response.text}")
    
    return {
        "status_code": response.status_code,
        "body": response.text
    }


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nQuick tests:")
        print("  python test_webhook.py --health          # Test health endpoint")
        print("  python test_webhook.py --invalid         # Test invalid signature")
        sys.exit(1)
    
    if sys.argv[1] == "--health":
        endpoint = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:3004/health"
        asyncio.run(test_health_check(endpoint))
    elif sys.argv[1] == "--invalid":
        endpoint = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:3004/webhook"
        asyncio.run(test_invalid_signature(endpoint))
    else:
        payload_file = sys.argv[1]
        secret = sys.argv[2] if len(sys.argv) > 2 else "test-secret-key"
        endpoint = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:3004/webhook"
        asyncio.run(test_webhook(payload_file, secret, endpoint))


if __name__ == "__main__":
    main()
