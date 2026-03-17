#!/usr/bin/env python3
"""
Final System Test Suite with Corrected HMAC + Stability Fixes + Additional Logging
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
    print(f"❌ ERROR: {e}")
    sys.exit(1)

# -----------------------------------------------------
# LOGGER INITIALIZATION
# -----------------------------------------------------
logger = setup_logger("system_test")
logger.setLevel(logging.INFO)
logging.getLogger().setLevel(logging.INFO)
conversation_context.set("SYSTEM_TEST")
logger.info("🚀 System Test Suite Started")

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(msg):
    logger.info(f"===== {msg} =====")
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{msg}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def load_payload() -> dict:
    logger.info("Loading custom_payload.json")
    path = Path(__file__).parent / "custom_payload.json"
    if not path.exists():
        path = Path("custom_payload.json")
    logger.info(f"Payload loaded from: {path}")
    return json.load(open(path, "r", encoding="utf-8"))


# =====================================================
# TEST 1: Storage Direct
# =====================================================
def test_storage_direct():
    print_header("TEST 1: Storage Integration")

    try:
        logger.info("Initializing StorageManager...")
        storage = StorageManager.from_env()

        payload = load_payload()
        logger.info("Payload loaded for storage test")

        conversation_id = f"storage_test_{int(time.time())}"
        logger.info(f"Saving transcript for conversation_id={conversation_id}")

        url = storage.save_transcript(conversation_id, "test_agent", payload.get("data"))
        logger.info(f"Transcript save returned URL: {url}")

        retrieved = storage.get_transcript(conversation_id)
        logger.info(f"Retrieved transcript: {'FOUND' if retrieved else 'NOT FOUND'}")

        return retrieved is not None

    except Exception as e:
        logger.exception(f"Storage Test Failed: {e}")
        return False


# =====================================================
# TEST 2: Logging Direct
# =====================================================
def test_logging_direct():
    print_header("TEST 2: Logging Integration")

    conn_str = os.getenv("AzureWebJobsStorage_elevenlabswebhook")
    container_name = os.getenv("BLOB_CONTAINER_NAME", "webhook-logs")

    logger.info(f"Testing log upload → container={container_name}")

    if not conn_str:
        logger.error("Missing Azure storage connection string — cannot test logging.")
        return False

    test_msg = f"TEST_LOG_{uuid.uuid4()}"
    logger.info(f"Generated test log message: {test_msg}")

    time.sleep(3)

    try:
        blob_service = BlobServiceClient.from_connection_string(conn_str)
        container = blob_service.get_container_client(container_name)

        logger.info("Listing latest blobs...")
        blobs = sorted(container.list_blobs(), key=lambda b: b.creation_time, reverse=True)

        for blob in blobs[:15]:
            logger.debug(f"Checking blob: {blob.name}")
            content = container.get_blob_client(blob).download_blob().readall().decode()
            if test_msg in content:
                logger.info(f"SUCCESS: Found test log in blob: {blob.name}")
                return True

        logger.error("Could not find test log in blob storage.")
        return False

    except Exception as e:
        logger.exception(f"Logging Test Failed: {e}")
        return False


# =====================================================
# TEST 3: Health Check
# =====================================================
async def test_health_endpoint(webhook_url: str):
    print_header("TEST 3: Health Check")

    health_url = webhook_url.replace("/webhook", "/health")
    logger.info(f"Calling health endpoint: {health_url}")

    try:
        async with httpx.AsyncClient(verify=False, timeout=20) as client:
            r = await client.get(health_url)
            logger.info(f"Health Response Code: {r.status_code}")
            logger.info(f"Health Response Body: {r.text}")
            return r.status_code == 200

    except Exception as e:
        logger.exception(f"Health Check Error: {e}")
        return False


# =====================================================
# TEST 4: FIXED SIGNATURE GENERATION
# =====================================================
def generate_signature(payload_bytes: bytes, secret: str):
    ts = int(time.time())
    msg = f"{ts}.".encode() + payload_bytes
    mac = hmac.new(secret.encode(), msg, sha256)
    sig = f"t={ts},v0={mac.hexdigest()}"
    logger.info(f"Generated Signature: {sig}")
    return sig


async def test_webhook_endpoint(webhook_url, hmac_secret):
    print_header("TEST 4: Webhook End-to-End")
    logger.info("Preparing payload for webhook test...")

    try:
        payload = load_payload()
        payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        logger.info(f"Payload size: {len(payload_bytes)} bytes")

        signature = generate_signature(payload_bytes, hmac_secret)

        headers = {
            "Content-Type": "application/json",
            "elevenlabs-signature": signature,
        }

        logger.info(f"Sending webhook request → {webhook_url}")

        async with httpx.AsyncClient(verify=False, timeout=40) as client:
            resp = await client.post(webhook_url, content=payload_bytes, headers=headers)

        logger.info(f"Webhook Response Status: {resp.status_code}")
        logger.info(f"Webhook Response Body: {resp.text}")

        return resp.status_code == 200

    except httpx.ReadTimeout:
        logger.error("❌ TIMEOUT — webhook server did not respond in time")
        return False

    except Exception as e:
        logger.exception(f"Webhook Test Error: {e}")
        return False


# =====================================================
# TEST 5: Invalid Signature
# =====================================================
async def test_invalid_signature(webhook_url):
    print_header("TEST 5: Invalid Signature Test")

    try:
        payload = load_payload()
        payload_bytes = json.dumps(payload).encode()

        headers = {
            "Content-Type": "application/json",
            "elevenlabs-signature": "t=0,v0=INVALIDSIGNATURE",
        }

        logger.info("Sending invalid signature request...")

        async with httpx.AsyncClient(verify=False, timeout=20) as client:
            r = await client.post(webhook_url, content=payload_bytes, headers=headers)

        logger.info(f"Invalid Signature Response Code: {r.status_code}")
        logger.info(f"Invalid Signature Response Body: {r.text}")

        return r.status_code in (400, 401)

    except Exception as e:
        logger.exception("Invalid Signature Test Error")
        return False


# =====================================================
# MAIN
# =====================================================
async def main():
    webhook_url = os.getenv("WEBHOOK_URL")
    secret = os.getenv("HMAC_SECRET")

    logger.info(f"WEBHOOK_URL={webhook_url}")
    logger.info(f"HMAC secret present: {bool(secret)}")

    logger.info("Running system test suite...")

    results = {
        "Storage": test_storage_direct(),
        "Logging": test_logging_direct(),
        "Health": await test_health_endpoint(webhook_url),
        "Webhook": await test_webhook_endpoint(webhook_url, secret),
        "Security": await test_invalid_signature(webhook_url),
    }

    logger.info(f"FINAL TEST RESULTS: {results}")

    print("\n===== FINAL SUMMARY =====")
    for name, result in results.items():
        print(f"{name}: {'PASS' if result else 'FAIL'}")


if __name__ == "__main__":
    asyncio.run(main())
