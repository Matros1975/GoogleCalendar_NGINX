#!/usr/bin/env python3
"""
Test script for ElevenLabs Pre-Call Webhook.

Usage:
    python test_precall_webhook.py [options]
    
Options:
    --health              Test health endpoint only
    --invalid            Test invalid signature rejection
    payload.json secret  Send payload with signature
    
Examples:
    # Test health endpoint
    python test_precall_webhook.py --health
    
    # Test with valid signature
    python test_precall_webhook.py examples/precall_payload.json your-webhook-secret
    
    # Test with custom endpoint
    python test_precall_webhook.py examples/precall_payload.json secret http://localhost:3005/webhook
"""

import sys
import json
import time
import hmac
import hashlib
import argparse
import requests


def generate_signature(payload_bytes: bytes, secret: str) -> str:
    """Generate HMAC signature for payload."""
    timestamp = int(time.time())
    payload_str = payload_bytes.decode("utf-8")
    full_payload = f"{timestamp}.{payload_str}"
    
    mac = hmac.new(
        key=secret.encode("utf-8"),
        msg=full_payload.encode("utf-8"),
        digestmod=hashlib.sha256
    )
    
    return f"t={timestamp},v0={mac.hexdigest()}"


def test_health(endpoint_url: str = "http://localhost:3005"):
    """Test health endpoint."""
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{endpoint_url}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_invalid_signature(endpoint_url: str = "http://localhost:3005"):
    """Test that invalid signature is rejected."""
    print("\nTesting invalid signature rejection...")
    
    payload = {
        "type": "pre_call",
        "conversation_id": "test_123",
        "agent_id": "agent_456"
    }
    
    payload_bytes = json.dumps(payload).encode("utf-8")
    invalid_signature = "t=123456789,v0=invalid_hash"
    
    try:
        response = requests.post(
            f"{endpoint_url}/webhook",
            headers={
                "elevenlabs-signature": invalid_signature,
                "Content-Type": "application/json"
            },
            data=payload_bytes
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        # Should return 401 or 400
        return response.status_code in [400, 401]
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_webhook(payload_file: str, secret: str, endpoint_url: str = "http://localhost:3005"):
    """Test webhook with valid signature."""
    print(f"\nTesting webhook with payload: {payload_file}")
    
    # Load payload
    try:
        with open(payload_file, 'r') as f:
            payload = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {payload_file}")
        return False
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file: {e}")
        return False
    
    payload_bytes = json.dumps(payload).encode("utf-8")
    
    # Generate signature
    signature = generate_signature(payload_bytes, secret)
    print(f"Generated signature: {signature[:50]}...")
    
    # Send request
    try:
        response = requests.post(
            f"{endpoint_url}/webhook",
            headers={
                "elevenlabs-signature": signature,
                "Content-Type": "application/json"
            },
            data=payload_bytes
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response:")
        try:
            print(json.dumps(response.json(), indent=2))
        except:
            print(response.text)
        
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test ElevenLabs Pre-Call Webhook",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--health', action='store_true',
                       help='Test health endpoint')
    parser.add_argument('--invalid', action='store_true',
                       help='Test invalid signature rejection')
    parser.add_argument('payload_file', nargs='?',
                       help='Path to JSON payload file')
    parser.add_argument('secret', nargs='?',
                       help='Webhook secret')
    parser.add_argument('endpoint', nargs='?',
                       default='http://localhost:3005',
                       help='Webhook endpoint URL (default: http://localhost:3005)')
    
    args = parser.parse_args()
    
    # Determine base URL
    if args.endpoint.endswith('/webhook'):
        endpoint_url = args.endpoint.rsplit('/webhook', 1)[0]
    else:
        endpoint_url = args.endpoint
    
    success = True
    
    if args.health:
        success = test_health(endpoint_url)
    elif args.invalid:
        success = test_invalid_signature(endpoint_url)
    elif args.payload_file and args.secret:
        success = test_webhook(args.payload_file, args.secret, endpoint_url)
    else:
        parser.print_help()
        return 1
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
