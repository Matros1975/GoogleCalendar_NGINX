"""
Unit tests for HMAC signature validator.
"""

import time
import json
import pytest

from src.auth.hmac_validator import HMACValidator


class TestHMACValidator:
    """Tests for HMACValidator class."""
    
    def test_valid_signature(self, webhook_secret):
        """Test validation of a valid signature."""
        validator = HMACValidator(secret=webhook_secret)
        
        payload = json.dumps({"type": "test", "data": "value"}).encode("utf-8")
        signature = validator.generate_signature(payload)
        
        is_valid, error = validator.validate(signature, payload)
        
        assert is_valid is True
        assert error == ""
    
    def test_invalid_signature(self, webhook_secret):
        """Test rejection of invalid signature."""
        validator = HMACValidator(secret=webhook_secret)
        
        payload = json.dumps({"type": "test"}).encode("utf-8")
        invalid_signature = f"t={int(time.time())},v0=invalid_hash_value"
        
        is_valid, error = validator.validate(invalid_signature, payload)
        
        assert is_valid is False
        assert "Invalid signature" in error
    
    def test_expired_timestamp(self, webhook_secret):
        """Test rejection of expired timestamp."""
        validator = HMACValidator(secret=webhook_secret, tolerance_seconds=1800)
        
        payload = json.dumps({"type": "test"}).encode("utf-8")
        old_timestamp = int(time.time()) - 3600  # 1 hour ago
        signature = validator.generate_signature(payload, timestamp=old_timestamp)
        
        is_valid, error = validator.validate(signature, payload)
        
        assert is_valid is False
        assert "expired" in error.lower()
    
    def test_future_timestamp(self, webhook_secret):
        """Test rejection of timestamp too far in future."""
        validator = HMACValidator(secret=webhook_secret)
        
        payload = json.dumps({"type": "test"}).encode("utf-8")
        future_timestamp = int(time.time()) + 120  # 2 minutes in future
        signature = validator.generate_signature(payload, timestamp=future_timestamp)
        
        is_valid, error = validator.validate(signature, payload)
        
        assert is_valid is False
        assert "future" in error.lower()
    
    def test_missing_signature_header(self, webhook_secret):
        """Test rejection when signature header is missing."""
        validator = HMACValidator(secret=webhook_secret)
        
        payload = json.dumps({"type": "test"}).encode("utf-8")
        
        is_valid, error = validator.validate(None, payload)
        
        assert is_valid is False
        assert "Missing signature header" in error
    
    def test_missing_secret(self):
        """Test rejection when secret is not configured."""
        validator = HMACValidator(secret="")
        
        payload = json.dumps({"type": "test"}).encode("utf-8")
        signature = "t=123,v0=hash"
        
        is_valid, error = validator.validate(signature, payload)
        
        assert is_valid is False
        assert "not configured" in error
    
    def test_malformed_signature_header(self, webhook_secret):
        """Test rejection of malformed signature header."""
        validator = HMACValidator(secret=webhook_secret)
        
        payload = json.dumps({"type": "test"}).encode("utf-8")
        
        # Missing v0= part
        is_valid, error = validator.validate("t=123456", payload)
        assert is_valid is False
        
        # Invalid format
        is_valid, error = validator.validate("invalid_format", payload)
        assert is_valid is False
    
    def test_generate_signature(self, webhook_secret):
        """Test signature generation."""
        validator = HMACValidator(secret=webhook_secret)
        
        payload = json.dumps({"type": "test"}).encode("utf-8")
        timestamp = 1700000000
        
        signature = validator.generate_signature(payload, timestamp=timestamp)
        
        assert signature.startswith("t=1700000000,v0=")
        assert len(signature) > 20
    
    def test_different_secrets_produce_different_hashes(self):
        """Test that different secrets produce different signatures."""
        validator1 = HMACValidator(secret="secret1")
        validator2 = HMACValidator(secret="secret2")
        
        payload = json.dumps({"type": "test"}).encode("utf-8")
        timestamp = int(time.time())
        
        sig1 = validator1.generate_signature(payload, timestamp=timestamp)
        sig2 = validator2.generate_signature(payload, timestamp=timestamp)
        
        assert sig1 != sig2
    
    def test_same_payload_different_timestamp_different_hash(self, webhook_secret):
        """Test that same payload with different timestamps produces different signatures."""
        validator = HMACValidator(secret=webhook_secret)
        
        payload = json.dumps({"type": "test"}).encode("utf-8")
        
        sig1 = validator.generate_signature(payload, timestamp=1700000000)
        sig2 = validator.generate_signature(payload, timestamp=1700000001)
        
        assert sig1 != sig2
    
    def test_timestamp_just_within_tolerance(self, webhook_secret):
        """Test that timestamp just within tolerance is accepted."""
        tolerance = 1800
        validator = HMACValidator(secret=webhook_secret, tolerance_seconds=tolerance)
        
        payload = json.dumps({"type": "test"}).encode("utf-8")
        # Timestamp just within tolerance (1799 seconds ago)
        old_timestamp = int(time.time()) - (tolerance - 1)
        signature = validator.generate_signature(payload, timestamp=old_timestamp)
        
        is_valid, error = validator.validate(signature, payload)
        
        assert is_valid is True
    
    def test_custom_tolerance(self, webhook_secret):
        """Test custom tolerance settings."""
        # Very short tolerance
        validator = HMACValidator(secret=webhook_secret, tolerance_seconds=60)
        
        payload = json.dumps({"type": "test"}).encode("utf-8")
        # Timestamp 120 seconds ago (outside 60s tolerance)
        old_timestamp = int(time.time()) - 120
        signature = validator.generate_signature(payload, timestamp=old_timestamp)
        
        is_valid, error = validator.validate(signature, payload)
        
        assert is_valid is False
        assert "expired" in error.lower()
