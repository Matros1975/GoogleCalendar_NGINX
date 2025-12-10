#!/usr/bin/env python3
"""
Test script for VoiceClone Pre-Call Service webhooks.

Usage:
    python examples/test_webhook.py
"""

import requests
import json
from datetime import datetime


# Service URL (adjust as needed)
BASE_URL = "http://localhost:8000"  # Direct to service
# BASE_URL = "https://matrosmcp.duckdns.org/voiceclone"  # Via NGINX


def test_health_check():
    """Test health check endpoint."""
    print("Testing health check...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()


def test_3cx_webhook():
    """Test 3CX incoming call webhook."""
    print("Testing 3CX incoming call webhook...")
    
    payload = {
        "event_type": "IncomingCall",
        "call_id": "test-3cx-call-12345",
        "caller_id": "+31612345678",
        "called_number": "+31201234567",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "direction": "In",
        "duration": None,
        "recording_url": None
    }
    
    response = requests.post(
        f"{BASE_URL}/webhook/3cx",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()


def test_statistics():
    """Test statistics endpoint."""
    print("Testing statistics endpoint...")
    
    response = requests.get(
        f"{BASE_URL}/api/v1/statistics",
        headers={"Authorization": "Bearer your-token-here"}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"Response: {response.text}")
    print()


def main():
    """Run all tests."""
    print("=" * 60)
    print("VoiceClone Pre-Call Service - Test Script")
    print("=" * 60)
    print()
    
    try:
        test_health_check()
        # test_3cx_webhook()  # Uncomment to test webhook
        # test_statistics()   # Uncomment to test statistics (requires auth)
        
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to service. Is it running?")
    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    main()
