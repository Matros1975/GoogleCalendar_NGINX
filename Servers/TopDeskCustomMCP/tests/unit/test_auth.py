"""Unit tests for bearer token authentication."""

import pytest
from src.auth.bearer_validator import BearerTokenValidator


def test_bearer_validator_initialization():
    """Test BearerTokenValidator initialization."""
    tokens = ["token1", "token2", "token3"]
    validator = BearerTokenValidator(tokens)
    
    assert validator.valid_tokens == set(tokens)


def test_validate_token_success():
    """Test successful token validation."""
    validator = BearerTokenValidator(["valid-token"])
    
    assert validator.validate_token("valid-token") is True


def test_validate_token_with_bearer_prefix():
    """Test token validation with Bearer prefix."""
    validator = BearerTokenValidator(["valid-token"])
    
    assert validator.validate_token("Bearer valid-token") is True
    assert validator.validate_token("bearer valid-token") is True
    assert validator.validate_token("BEARER valid-token") is True


def test_validate_token_failure():
    """Test failed token validation."""
    validator = BearerTokenValidator(["valid-token"])
    
    assert validator.validate_token("invalid-token") is False
    assert validator.validate_token("") is False
    assert validator.validate_token(None) is False


def test_add_token():
    """Test adding a token at runtime."""
    validator = BearerTokenValidator(["token1"])
    
    assert validator.validate_token("token2") is False
    
    validator.add_token("token2")
    assert validator.validate_token("token2") is True


def test_remove_token():
    """Test removing a token at runtime."""
    validator = BearerTokenValidator(["token1", "token2"])
    
    assert validator.validate_token("token1") is True
    
    validator.remove_token("token1")
    assert validator.validate_token("token1") is False
    assert validator.validate_token("token2") is True


def test_multiple_tokens():
    """Test validator with multiple tokens."""
    tokens = ["token-a", "token-b", "token-c"]
    validator = BearerTokenValidator(tokens)
    
    for token in tokens:
        assert validator.validate_token(token) is True
        assert validator.validate_token(f"Bearer {token}") is True
