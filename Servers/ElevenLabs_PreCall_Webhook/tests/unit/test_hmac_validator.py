"""
Unit tests for HMAC validator.
"""

import pytest
import time
import json
from src.auth.hmac_validator import HMACValidator


class TestHMACValidator:
    """Test suite for HMACValidator."""
    
    @pytest.fixture
    def validator(self):
        """Create validator with test secret."""
        return HMACValidator(secret="test_secret_key_12345")
    
    @pytest.fixture
    def sample_payload(self):
        """Sample webhook payload."""
        return json.dumps({
            "type": "pre_call",
            "conversation_id": "test_123",
            "agent_id": "agent_456"
        }).encode("utf-8")
    
    def test_validate_valid_signature(self, validator, sample_payload):
        """Test validation of valid signature."""
        # Generate valid signature
        signature = validator.generate_signature(sample_payload)
        
        # Validate
        is_valid, error = validator.validate(signature, sample_payload)
        
        assert is_valid is True
        assert error == ""
    
    def test_validate_invalid_signature(self, validator, sample_payload):
        """Test validation of invalid signature."""
        # Create invalid signature with current timestamp to avoid expiry
        import time
        current_timestamp = int(time.time())
        signature = f"t={current_timestamp},v0=invalid_hash_12345"
        
        # Validate
        is_valid, error = validator.validate(signature, sample_payload)
        
        assert is_valid is False
        assert "Invalid signature" in error
    
    def test_validate_missing_signature(self, validator, sample_payload):
        """Test validation with missing signature."""
        is_valid, error = validator.validate(None, sample_payload)
        
        assert is_valid is False
        assert "Missing signature header" in error
    
    def test_validate_malformed_signature(self, validator, sample_payload):
        """Test validation with malformed signature."""
        # Missing v0 part
        signature = "t=123456789"
        
        is_valid, error = validator.validate(signature, sample_payload)
        
        assert is_valid is False
        assert "Invalid signature header format" in error
    
    def test_validate_expired_timestamp(self, validator, sample_payload):
        """Test validation with expired timestamp."""
        # Create signature with old timestamp (2 hours ago)
        old_timestamp = int(time.time()) - 7200
        signature = validator.generate_signature(sample_payload, timestamp=old_timestamp)
        
        is_valid, error = validator.validate(signature, sample_payload)
        
        assert is_valid is False
        assert "expired" in error.lower()
    
    def test_validate_future_timestamp(self, validator, sample_payload):
        """Test validation with future timestamp (beyond clock skew)."""
        # Create signature with future timestamp (2 minutes ahead)
        future_timestamp = int(time.time()) + 120
        signature = validator.generate_signature(sample_payload, timestamp=future_timestamp)
        
        is_valid, error = validator.validate(signature, sample_payload)
        
        assert is_valid is False
        assert "future" in error.lower()
    
    def test_validate_within_tolerance(self, validator, sample_payload):
        """Test validation within tolerance window."""
        # Create signature 10 minutes ago (within 30 min tolerance)
        recent_timestamp = int(time.time()) - 600
        signature = validator.generate_signature(sample_payload, timestamp=recent_timestamp)
        
        is_valid, error = validator.validate(signature, sample_payload)
        
        assert is_valid is True
        assert error == ""
    
    def test_validate_wrong_secret(self, sample_payload):
        """Test validation with wrong secret."""
        # Create signature with one secret
        validator1 = HMACValidator(secret="secret1")
        signature = validator1.generate_signature(sample_payload)
        
        # Validate with different secret
        validator2 = HMACValidator(secret="secret2")
        is_valid, error = validator2.validate(signature, sample_payload)
        
        assert is_valid is False
        assert "Invalid signature" in error
    
    def test_validate_no_secret_configured(self, sample_payload):
        """Test validation when no secret is configured."""
        validator = HMACValidator(secret="")
        signature = "t=123456789,v0=somehash"
        
        is_valid, error = validator.validate(signature, sample_payload)
        
        assert is_valid is False
        assert "not configured" in error.lower()
    
    def test_validate_invalid_timestamp_format(self, validator, sample_payload):
        """Test validation with invalid timestamp format."""
        signature = "t=not_a_number,v0=somehash"
        
        is_valid, error = validator.validate(signature, sample_payload)
        
        assert is_valid is False
        assert "Invalid timestamp format" in error
    
    def test_generate_signature_with_custom_timestamp(self, validator, sample_payload):
        """Test signature generation with custom timestamp."""
        timestamp = 1234567890
        signature = validator.generate_signature(sample_payload, timestamp=timestamp)
        
        assert signature.startswith(f"t={timestamp},v0=")
        assert len(signature) > 30  # t= + timestamp + ,v0= + hash
    
    def test_generate_signature_with_current_time(self, validator, sample_payload):
        """Test signature generation with current time."""
        before = int(time.time())
        signature = validator.generate_signature(sample_payload)
        after = int(time.time())
        
        # Extract timestamp from signature
        timestamp_str = signature.split(",")[0].replace("t=", "")
        timestamp = int(timestamp_str)
        
        assert before <= timestamp <= after
    
    def test_custom_tolerance(self, sample_payload):
        """Test custom tolerance setting."""
        # Create validator with 1 hour tolerance
        validator = HMACValidator(secret="test_secret", tolerance_seconds=3600)
        
        # Create signature 45 minutes ago
        old_timestamp = int(time.time()) - 2700
        signature = validator.generate_signature(sample_payload, timestamp=old_timestamp)
        
        is_valid, error = validator.validate(signature, sample_payload)
        
        # Should be valid with 1 hour tolerance
        assert is_valid is True
    
    def test_validate_modified_payload(self, validator):
        """Test that modified payload fails validation."""
        original_payload = b'{"type": "pre_call", "id": "123"}'
        signature = validator.generate_signature(original_payload)
        
        # Modify payload
        modified_payload = b'{"type": "pre_call", "id": "456"}'
        
        is_valid, error = validator.validate(signature, modified_payload)
        
        assert is_valid is False
        assert "Invalid signature" in error
