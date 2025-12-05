#!/usr/bin/env python3
"""
Final System Test Suite
Combines all integration tests into a single robust execution file.

Tests included:
1. Direct Storage Integration (Blob Storage) - Verifies no local persistence
2. Direct Logging Integration - Verifies logs go to Blob
3. Health Check - Verifies service is running
4. Webhook Endpoint - Verifies end-to-end processing with valid signature
5. Security Check - Verifies rejection of invalid signatures

Usage:
    export AzureWebJobsStorage_ticketcategorizer="<connection_string>"
    export WEBHOOK_URL="https://<your-app>/elevenlabs/webhook"
    export HMAC_SECRET="<your_secret>"
    
    python tests/integration/test_final_system.py
"""

import asyncio
import json
import os
import sys
import time
import uuid
import hmac
import base64
import logging
from hashlib import sha256
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

# Add project root to path
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.append(str(project_root))

try:
    import httpx
    from azure.storage.blob import BlobServiceClient
    from src.utils.storage import StorageManager
    from src.utils.logger import setup_logger, conversation_context
except ImportError as e:
    print(f"❌ ERROR: Failed to import required modules: {e}")
    print("Ensure you have installed requirements.txt and are running from the correct directory.")
    sys.exit(1)


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(msg):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{msg}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")


def load_payload() -> dict:
    path = Path(__file__).parent / "custom_payload.json"
    if not path.exists():
        path = Path("custom_payload.json")
    
    if not path.exists():
        raise FileNotFoundError("custom_payload.json not found")
        
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


# ==========================================
# TEST 1: Direct Storage Integration
# ==========================================
def test_storage_direct():
    print_header("TEST 1: Direct Storage Integration")
    
    try:
        storage = StorageManager.from_env()
        if not storage.container_client:
            print(f"{Colors.RED}[FAIL] Storage not initialized (check connection string){Colors.RESET}")
            return False

        print(f"{Colors.GREEN}[PASS] StorageManager initialized{Colors.RESET}")
        
        # Load payload
        payload = load_payload()
        conversation_id = f"test_storage_{int(time.time())}"
        agent_id = "test_agent"
        
        # 1. Test Transcript
        print(f"\n{Colors.BLUE}[INFO] Testing Transcript Upload...{Colors.RESET}")
        url = storage.save_transcript(conversation_id, agent_id, payload.get('data', {}))
        
        if url:
            print(f"{Colors.GREEN}[PASS] Transcript saved: {url}{Colors.RESET}")
            
            # Verify retrieval
            retrieved = storage.get_transcript(conversation_id)
            if retrieved and retrieved.get('conversation_id') == conversation_id:
                print(f"{Colors.GREEN}[PASS] Transcript retrieved and verified{Colors.RESET}")
            else:
                print(f"{Colors.RED}[FAIL] Transcript retrieval failed or mismatch{Colors.RESET}")
                return False
        else:
            print(f"{Colors.YELLOW}[WARN] Transcript not saved (disabled?){Colors.RESET}")

        # 2. Test Audio
        if storage.enable_audio:
            print(f"\n{Colors.BLUE}[INFO] Testing Audio Upload...{Colors.RESET}")
            mock_audio = base64.b64encode(b'mock_mp3_data').decode('utf-8')
            audio_url = storage.save_audio(conversation_id, agent_id, mock_audio)
            
            if audio_url:
                print(f"{Colors.GREEN}[PASS] Audio saved: {audio_url}{Colors.RESET}")
            else:
                print(f"{Colors.RED}[FAIL] Audio save returned None{Colors.RESET}")
                return False
        
        return True

    except Exception as e:
        print(f"{Colors.RED}[FAIL] Storage test failed: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        return False


# ==========================================
# TEST 2: Direct Logging Integration
# ==========================================
def test_logging_direct():
    print_header("TEST 2: Direct Logging Integration")
    
    conn_str = os.getenv("AzureWebJobsStorage_ticketcategorizer") or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container_name = os.getenv("BLOB_CONTAINER_NAME", "webhook-logs")
    
    if not conn_str:
        print(f"{Colors.RED}[FAIL] No connection string found{Colors.RESET}")
        return False

    try:
        # Generate unique test ID
        test_id = str(uuid.uuid4())
        test_msg = f"TEST_LOG_ENTRY_{test_id}"
        
        print(f"{Colors.BLUE}[INFO] Writing log entry: {test_msg}{Colors.RESET}")
        
        # Setup logger and write
        logger = setup_logger(name=f"test_logger_{int(time.time())}", level="INFO")
        conversation_context.set("TEST_CTX")
        logger.info(test_msg)
        
        # Give it a moment to upload
        print("Waiting for log propagation...")
        time.sleep(2)
        
        # Verify in Blob Storage manually
        print(f"{Colors.BLUE}[INFO] Verifying in Blob Storage...{Colors.RESET}")
        blob_service = BlobServiceClient.from_connection_string(conn_str)
        container = blob_service.get_container_client(container_name)
        
        # List recent blobs (logs are in logs/YYYY/MM/DD/HH/...)
        # We'll just look at the last few blobs
        found = False
        blobs = list(container.list_blobs())
        # Sort by creation time descending
        blobs.sort(key=lambda b: b.creation_time, reverse=True)
        
        for blob in blobs[:10]:  # Check last 10 logs
            downloader = container.get_blob_client(blob).download_blob()
            content = downloader.readall().decode('utf-8')
            
            if test_msg in content:
                print(f"{Colors.GREEN}[PASS] Found log entry in blob: {blob.name}{Colors.RESET}")
                found = True
                break
        
        if not found:
            print(f"{Colors.RED}[FAIL] Log entry not found in recent blobs{Colors.RESET}")
            return False
            
        return True

    except Exception as e:
        print(f"{Colors.RED}[FAIL] Logging test failed: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        return False


# ==========================================
# TEST 3: Health Check
# ==========================================
async def test_health_endpoint(webhook_url: str) -> bool:
    print_header("TEST 3: Health Check Endpoint")
    
    # Convert webhook URL to health URL
    health_url = webhook_url.replace("/webhook", "/health")
    print(f"URL: {health_url}")
    
    async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
        try:
            response = await client.get(health_url)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                print(f"{Colors.GREEN}[PASS] Health check passed{Colors.RESET}")
                return True
            else:
                print(f"{Colors.RED}[FAIL] Health check failed{Colors.RESET}")
                return False
        except Exception as e:
            print(f"{Colors.RED}[FAIL] Health check error: {e}{Colors.RESET}")
            return False


# ==========================================
# TEST 4: Webhook Endpoint (End-to-End)
# ==========================================
def generate_signature(payload_bytes: bytes, secret: str) -> str:
    timestamp = int(time.time())
    payload_str = payload_bytes.decode("utf-8")
    full_payload = f"{timestamp}.{payload_str}"
    mac = hmac.new(secret.encode("utf-8"), full_payload.encode("utf-8"), sha256)
    return f"t={timestamp},v0={mac.hexdigest()}"

async def test_webhook_endpoint(webhook_url: str, hmac_secret: str) -> bool:
    print_header("TEST 4: Webhook Endpoint (End-to-End)")
    
    try:
        payload = load_payload()
        # Serialize payload exactly as the server expects
        payload_bytes = json.dumps(payload, separators=(',', ':')).encode("utf-8")
        signature = generate_signature(payload_bytes, hmac_secret)
        
        headers = {
            "Content-Type": "application/json",
            "elevenlabs-signature": signature,
            "User-Agent": "Test-Suite/1.0"
        }
        
        print(f"{Colors.BLUE}[INFO] Sending POST to {webhook_url}{Colors.RESET}")
        
        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            start_time = time.time()
            response = await client.post(webhook_url, content=payload_bytes, headers=headers)
            elapsed = time.time() - start_time
            
            print(f"Response time: {elapsed:.2f}s")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"{Colors.GREEN}[PASS] Webhook accepted payload{Colors.RESET}")
                try:
                    print("Response:", json.dumps(response.json(), indent=2))
                except:
                    print("Response:", response.text)
                return True
            else:
                print(f"{Colors.RED}[FAIL] Request failed: {response.status_code}{Colors.RESET}")
                print(response.text)
                return False

    except Exception as e:
        print(f"{Colors.RED}[FAIL] Webhook test failed: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        return False


# ==========================================
# TEST 5: Security (Invalid Signature)
# ==========================================
async def test_invalid_signature(webhook_url: str) -> bool:
    print_header("TEST 5: Security (Invalid Signature)")
    
    try:
        payload = load_payload()
        payload_bytes = json.dumps(payload, separators=(',', ':')).encode("utf-8")
        
        # Use invalid signature
        invalid_signature = "t=1234567890,v0=invalid_hash_abc123"
        
        headers = {
            "Content-Type": "application/json",
            "elevenlabs-signature": invalid_signature,
            "User-Agent": "Test-Suite/1.0"
        }
        
        print(f"{Colors.BLUE}[INFO] Sending POST with invalid signature...{Colors.RESET}")
        
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            response = await client.post(webhook_url, content=payload_bytes, headers=headers)
            
            print(f"Status Code: {response.status_code}")
            
            # Accept 401 (Unauthorized) or 400 (Bad Request) as valid rejections
            if response.status_code in [401, 400]:
                print(f"{Colors.GREEN}[PASS] Invalid signature correctly rejected (Status: {response.status_code}){Colors.RESET}")
                return True
            else:
                print(f"{Colors.RED}[FAIL] Security check failed. Expected 400/401, got {response.status_code}{Colors.RESET}")
                return False
                
    except Exception as e:
        print(f"{Colors.RED}[FAIL] Security test failed: {e}{Colors.RESET}")
        return False


# ==========================================
# MAIN EXECUTION
# ==========================================
async def main():
    print(f"{Colors.BOLD}Starting Final System Test Suite{Colors.RESET}")
    print(f"Time: {datetime.now().isoformat()}")
    
    # Check Environment
    webhook_url = os.getenv("WEBHOOK_URL")
    hmac_secret = os.getenv("HMAC_SECRET")
    
    if not webhook_url or not hmac_secret:
        print(f"\n{Colors.RED}[FAIL] Error: WEBHOOK_URL or HMAC_SECRET not set{Colors.RESET}")
        sys.exit(1)
        
    # Ensure URL format
    if not webhook_url.endswith("/webhook"):
        if webhook_url.endswith("/"):
            webhook_url += "elevenlabs/webhook"
        else:
            webhook_url += "/elevenlabs/webhook"
    
    results = {}
    
    # Run Tests
    results["Storage"] = test_storage_direct()
    results["Logging"] = test_logging_direct()
    results["Health"] = await test_health_endpoint(webhook_url)
    results["Webhook"] = await test_webhook_endpoint(webhook_url, hmac_secret)
    results["Security"] = await test_invalid_signature(webhook_url)
    
    print_header("TEST SUMMARY")
    all_passed = True
    for name, result in results.items():
        if result is None:
            status = f"{Colors.YELLOW}SKIPPED{Colors.RESET}"
        elif result:
            status = f"{Colors.GREEN}PASS{Colors.RESET}"
        else:
            status = f"{Colors.RED}FAIL{Colors.RESET}"
            all_passed = False
        print(f"{name:<15} : {status}")
    
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
