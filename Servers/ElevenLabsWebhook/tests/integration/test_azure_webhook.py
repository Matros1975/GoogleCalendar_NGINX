#!/usr/bin/env python3
"""
Test ElevenLabs webhook endpoint hosted on Azure.
Loads payload from custom_payload.json and sends with HMAC signature.

Usage:
    python test_azure_webhook.py <webhook_url> <hmac_secret>
    
    Or set environment variables:
    export WEBHOOK_URL="https://your-app.azurecontainerapps.io/elevenlabs/webhook"
    export HMAC_SECRET="your_secret_key"
    python test_azure_webhook.py

Examples:
    # Using command line arguments
    python test_azure_webhook.py https://elevenlabs.app.io/elevenlabs/webhook mySecretKey123
    
    # Using environment variables
    export WEBHOOK_URL="https://20.93.45.123/elevenlabs/webhook"
    export HMAC_SECRET="prod_secret_xyz"
    python test_azure_webhook.py
    
    # Using IP address directly
    python test_azure_webhook.py https://20.93.45.123/elevenlabs/webhook mySecret
"""

import asyncio
import json
import os
import sys
import time
import hmac
from hashlib import sha256
from pathlib import Path
from typing import Tuple, Optional

try:
    import httpx
except ImportError:
    print("❌ ERROR: httpx not installed. Run: pip install httpx")
    sys.exit(1)


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(message: str):
    """Print colored header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{message}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")


def print_success(message: str):
    """Print success message."""
    print(f"{Colors.GREEN}✅ {message}{Colors.RESET}")


def print_error(message: str):
    """Print error message."""
    print(f"{Colors.RED}❌ {message}{Colors.RESET}")


def print_warning(message: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.RESET}")


def print_info(message: str):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.RESET}")


def load_payload(payload_path: Optional[str] = None) -> dict:
    """
    Load payload from custom_payload.json.
    
    Args:
        payload_path: Path to payload file. If None, searches in current dir and script dir.
        
    Returns:
        Parsed JSON payload
        
    Raises:
        FileNotFoundError: If payload file not found
        json.JSONDecodeError: If payload is invalid JSON
    """
    if payload_path:
        # Use provided path
        path = Path(payload_path)
    else:
        # Try current directory first
        path = Path("custom_payload.json")
        
        if not path.exists():
            # Try script directory
            script_dir = Path(__file__).parent
            path = script_dir / "custom_payload.json"
            
        if not path.exists():
            # Try one level up (if in tests/integration)
            path = script_dir.parent.parent / "tests/integration/custom_payload.json"
    
    if not path.exists():
        raise FileNotFoundError(
            f"Payload file not found: {path}\n"
            f"Search locations:\n"
            f"  - ./custom_payload.json\n"
            f"  - {Path(__file__).parent}/custom_payload.json\n"
            f"  - tests/integration/custom_payload.json"
        )
    
    print_info(f"Loading payload from: {path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        payload = json.load(f)
    
    print_success(f"Payload loaded: {len(json.dumps(payload))} bytes")
    return payload


def generate_elevenlabs_signature(payload_bytes: bytes, secret: str) -> str:
    """
    Generate HMAC signature for ElevenLabs webhook.
    
    ElevenLabs signature format: t={timestamp},v0={hmac_hex}
    The signature is computed over: "{timestamp}.{payload_json}"
    
    Args:
        payload_bytes: JSON payload as bytes
        secret: HMAC secret key
        
    Returns:
        Signature string in format: "t=1234567890,v0=abc123..."
    """
    timestamp = int(time.time())
    payload_str = payload_bytes.decode("utf-8")
    
    # ElevenLabs format: timestamp.payload
    full_payload = f"{timestamp}.{payload_str}"
    
    # Compute HMAC-SHA256
    mac = hmac.new(
        key=secret.encode("utf-8"),
        msg=full_payload.encode("utf-8"),
        digestmod=sha256
    )
    
    signature = f"t={timestamp},v0={mac.hexdigest()}"
    
    print_info(f"Generated signature: t={timestamp},v0={mac.hexdigest()[:16]}...")
    
    return signature


async def test_health_endpoint(webhook_url: str) -> bool:
    """
    Test health check endpoint (no authentication).
    
    Args:
        webhook_url: Full webhook URL (will replace /webhook with /health)
        
    Returns:
        True if health check passed
    """
    print_header("Testing Health Check Endpoint")
    
    # Convert webhook URL to health URL
    health_url = webhook_url.replace("/webhook", "/health")
    
    print_info(f"URL: {health_url}")
    
    async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
        try:
            response = await client.get(health_url)
            
            print_info(f"Status Code: {response.status_code}")
            print_info(f"Response: {response.text}")
            
            if response.status_code == 200:
                print_success("Health check passed")
                return True
            else:
                print_error(f"Health check failed with status {response.status_code}")
                return False
                
        except httpx.ConnectError as e:
            print_error(f"Connection failed: {e}")
            print_warning("Check if webhook URL is correct and service is running")
            return False
        except Exception as e:
            print_error(f"Health check error: {e}")
            return False


async def test_webhook_endpoint(
    webhook_url: str,
    hmac_secret: str,
    payload: dict
) -> bool:
    """
    Test webhook endpoint with custom payload and HMAC signature.
    
    Args:
        webhook_url: Full webhook URL
        hmac_secret: HMAC secret for signature generation
        payload: JSON payload to send
        
    Returns:
        True if webhook accepted payload
    """
    print_header("Testing Webhook Endpoint")
    
    print_info(f"URL: {webhook_url}")
    print_info(f"Payload type: {payload.get('type', 'unknown')}")
    
    # Serialize payload
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode("utf-8")
    print_info(f"Payload size: {len(payload_bytes):,} bytes")
    
    # Generate HMAC signature
    signature = generate_elevenlabs_signature(payload_bytes, hmac_secret)
    
    # Prepare headers
    headers = {
        "Content-Type": "application/json",
        "elevenlabs-signature": signature,
        "User-Agent": "ElevenLabs-Webhook-Test/1.0"
    }
    
    print_info("Sending POST request...")
    
    async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
        try:
            start_time = time.time()
            
            response = await client.post(
                webhook_url,
                content=payload_bytes,
                headers=headers
            )
            
            elapsed = time.time() - start_time
            
            print_info(f"Response time: {elapsed:.2f}s")
            print_info(f"Status Code: {response.status_code}")
            
            # Print response details
            try:
                response_json = response.json()
                print_info(f"Response JSON: {json.dumps(response_json, indent=2)}")
            except:
                print_info(f"Response Text: {response.text[:500]}")
            
            # Check status
            if response.status_code == 200:
                print_success("Webhook accepted payload successfully")
                
                # Try to parse response
                try:
                    result = response.json()
                    if result.get("ticket_created"):
                        print_success(f"Ticket created: {result.get('ticket_number')}")
                    if result.get("saved_path"):
                        print_info(f"Transcript saved: {result.get('saved_path')}")
                except:
                    pass
                
                return True
            elif response.status_code == 401:
                print_error("Authentication failed - Invalid HMAC signature")
                print_warning("Check if HMAC_SECRET matches the service configuration")
                return False
            elif response.status_code == 422:
                print_error("Validation error - Invalid payload format")
                return False
            else:
                print_error(f"Request failed with status {response.status_code}")
                return False
                
        except httpx.ConnectError as e:
            print_error(f"Connection failed: {e}")
            print_warning("Check if webhook URL is correct and service is running")
            return False
        except httpx.TimeoutException:
            print_error("Request timed out after 30 seconds")
            print_warning("Service may be processing but taking too long")
            return False
        except Exception as e:
            print_error(f"Request error: {e}")
            return False


async def test_invalid_signature(webhook_url: str, payload: dict) -> bool:
    """
    Test that invalid signatures are rejected.
    
    Args:
        webhook_url: Full webhook URL
        payload: JSON payload to send
        
    Returns:
        True if invalid signature was correctly rejected
    """
    print_header("Testing Invalid Signature (Should Reject)")
    
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode("utf-8")
    
    # Use invalid signature
    invalid_signature = "t=1234567890,v0=invalid_hash_abc123"
    
    headers = {
        "Content-Type": "application/json",
        "elevenlabs-signature": invalid_signature,
        "User-Agent": "ElevenLabs-Webhook-Test/1.0"
    }
    
    print_info("Sending request with invalid signature...")
    
    async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
        try:
            response = await client.post(
                webhook_url,
                content=payload_bytes,
                headers=headers
            )
            
            print_info(f"Status Code: {response.status_code}")
            
            if response.status_code == 401:
                print_success("Invalid signature correctly rejected (401 Unauthorized)")
                return True
            else:
                print_warning(f"Expected 401, got {response.status_code}")
                print_warning("Service may not be validating signatures properly")
                return False
                
        except Exception as e:
            print_error(f"Test error: {e}")
            return False


def parse_arguments() -> Tuple[str, str]:
    """
    Parse command line arguments or environment variables.
    
    Priority:
    1. Command line arguments
    2. Environment variables
    3. Prompt user
    
    Returns:
        Tuple of (webhook_url, hmac_secret)
    """
    webhook_url = None
    hmac_secret = None
    
    # Try command line arguments
    if len(sys.argv) >= 3:
        webhook_url = sys.argv[1]
        hmac_secret = sys.argv[2]
        print_info(f"Using command line arguments")
    elif len(sys.argv) == 2:
        webhook_url = sys.argv[1]
        print_warning("HMAC secret not provided in arguments")
    
    # Try environment variables
    if not webhook_url:
        webhook_url = os.getenv("WEBHOOK_URL")
        if webhook_url:
            print_info("Using WEBHOOK_URL from environment")
    
    if not hmac_secret:
        hmac_secret = os.getenv("HMAC_SECRET")
        if hmac_secret:
            print_info("Using HMAC_SECRET from environment")
    
    # Prompt if still missing
    if not webhook_url:
        print_error("Webhook URL not provided")
        print("\nUsage:")
        print("  python test_azure_webhook.py <webhook_url> <hmac_secret>")
        print("\nOr set environment variables:")
        print("  export WEBHOOK_URL='https://your-app.io/elevenlabs/webhook'")
        print("  export HMAC_SECRET='your_secret'")
        sys.exit(1)
    
    if not hmac_secret:
        print_error("HMAC secret not provided")
        print("\nProvide as second argument or set HMAC_SECRET environment variable")
        sys.exit(1)
    
    # Normalize URL (ensure it ends with /webhook)
    if not webhook_url.endswith("/webhook"):
        if not webhook_url.endswith("/"):
            webhook_url += "/elevenlabs/webhook"
        else:
            webhook_url += "elevenlabs/webhook"
    
    # Ensure https:// prefix
    if not webhook_url.startswith("http://") and not webhook_url.startswith("https://"):
        webhook_url = f"https://{webhook_url}"
    
    return webhook_url, hmac_secret


async def main():
    """Main test execution."""
    print_header("ElevenLabs Webhook Azure Test")
    
    # Parse arguments
    webhook_url, hmac_secret = parse_arguments()
    
    print_info(f"Webhook URL: {webhook_url}")
    print_info(f"HMAC Secret: {'*' * len(hmac_secret)}")
    
    # Load payload
    try:
        payload = load_payload()
    except FileNotFoundError as e:
        print_error(str(e))
        sys.exit(1)
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON in payload file: {e}")
        sys.exit(1)
    
    # Run tests
    results = {}
    
    # Test 1: Health check
    results["health"] = await test_health_endpoint(webhook_url)
    
    # Test 2: Valid webhook request
    results["webhook"] = await test_webhook_endpoint(webhook_url, hmac_secret, payload)
    
    # Test 3: Invalid signature (should be rejected)
    results["security"] = await test_invalid_signature(webhook_url, payload)
    
    # Print summary
    print_header("Test Summary")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        color = Colors.GREEN if result else Colors.RED
        print(f"{color}{status:6}{Colors.RESET} - {test_name}")
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.RESET}")
    
    if passed == total:
        print_success("All tests passed! Webhook is working correctly.")
        sys.exit(0)
    else:
        print_error(f"{total - passed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print_warning("\nTest interrupted by user")
        sys.exit(130)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
