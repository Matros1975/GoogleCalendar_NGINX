"""
HMAC signature validator for ElevenLabs webhooks.

Implements signature validation following ElevenLabs specification:
- Header format: elevenlabs-signature: t=timestamp,v0=hash
- Hash validation: sha256(timestamp.request_body)
- Timestamp tolerance: 30 minutes (1800 seconds)
"""

import hmac
import time
from hashlib import sha256
from typing import Tuple
from src.utils.logger import setup_logger

logger = setup_logger()


class HMACValidator:
    """Validates ElevenLabs webhook HMAC signatures."""
    
    def __init__(self, secret: str, tolerance_seconds: int = 1800):
        """
        Initialize HMAC validator.
        
        Args:
            secret: HMAC secret from ElevenLabs webhook configuration
            tolerance_seconds: Maximum age of timestamp (default 30 minutes)
        """
        self.secret = secret
        self.tolerance_seconds = tolerance_seconds
    
    def validate(self, signature_header: str, payload: bytes) -> Tuple[bool, str]:
        """
        Validate HMAC signature from elevenlabs-signature header.
        
        Args:
            signature_header: Header value "t=timestamp,v0=hash"
            payload: Raw request body bytes
            
        Returns:
            Tuple of (is_valid, error_message)
            - (True, "") if signature is valid
            - (False, error_message) if signature is invalid
        """
        if not self.secret:
            logger.error("HMAC secret not configured")
            return False, "HMAC secret not configured"
        
        if not signature_header:
            logger.warning("Missing signature header")
            return False, "Missing signature header"
        
        try:
            # Parse header: "t=timestamp,v0=hash"
            # Use split with maxsplit=1 to prevent comma injection attacks
            parts = signature_header.split(",", 1)
            if len(parts) < 2:
                logger.warning("Invalid signature header format")
                return False, "Invalid signature header format"
            
            # Extract timestamp
            timestamp_part = parts[0]
            if not timestamp_part.startswith("t="):
                logger.warning("Missing timestamp in signature header")
                return False, "Missing timestamp in signature header"
            timestamp = timestamp_part[2:]  # Remove "t=" prefix
            
            # Extract hash (v0=hash)
            received_hash = parts[1]
            if not received_hash.startswith("v0="):
                logger.warning("Missing v0 hash in signature header")
                return False, "Missing v0 hash in signature header"
            
            # Validate timestamp (not too old)
            try:
                timestamp_int = int(timestamp)
            except ValueError:
                logger.warning(f"Invalid timestamp format: {timestamp}")
                return False, "Invalid timestamp format"
            
            current_time = int(time.time())
            age = current_time - timestamp_int
            
            if age > self.tolerance_seconds:
                logger.warning(f"Timestamp expired: {age} seconds old (tolerance: {self.tolerance_seconds})")
                return False, f"Timestamp expired ({age} seconds old)"
            
            if age < -60:  # Allow 1 minute clock skew into the future
                logger.warning(f"Timestamp too far in future: {-age} seconds")
                return False, "Timestamp too far in future"
            
            # Compute expected hash
            payload_str = payload.decode("utf-8")
            full_payload = f"{timestamp}.{payload_str}"
            
            mac = hmac.new(
                key=self.secret.encode("utf-8"),
                msg=full_payload.encode("utf-8"),
                digestmod=sha256
            )
            expected_hash = "v0=" + mac.hexdigest()
            
            # Compare hashes using constant-time comparison
            if not hmac.compare_digest(received_hash, expected_hash):
                logger.warning("HMAC signature mismatch")
                return False, "Invalid signature"
            
            logger.debug(f"HMAC validation successful (timestamp age: {age}s)")
            return True, ""
            
        except UnicodeDecodeError as e:
            logger.error(f"Error decoding payload: {e}")
            return False, "Error decoding payload"
        except Exception as e:
            logger.error(f"Error validating signature: {e}")
            return False, f"Error validating signature: {str(e)}"
    
    def generate_signature(self, payload: bytes, timestamp: int = None) -> str:
        """
        Generate a valid HMAC signature for testing purposes.
        
        Args:
            payload: Request body bytes
            timestamp: Unix timestamp (defaults to current time)
            
        Returns:
            Signature header value "t=timestamp,v0=hash"
        """
        if timestamp is None:
            timestamp = int(time.time())
        
        payload_str = payload.decode("utf-8")
        full_payload = f"{timestamp}.{payload_str}"
        
        mac = hmac.new(
            key=self.secret.encode("utf-8"),
            msg=full_payload.encode("utf-8"),
            digestmod=sha256
        )
        
        return f"t={timestamp},v0={mac.hexdigest()}"
