"""
Custom exceptions for VoiceClone Pre-Call Service.
"""


class VoiceCloneException(Exception):
    """Base exception for voice cloning errors."""
    pass


class VoiceCloneTimeoutException(VoiceCloneException):
    """Voice clone creation timed out."""
    pass


class VoiceCloneAPIException(VoiceCloneException):
    """ElevenLabs API error during voice cloning."""
    pass


class VoiceAgentException(Exception):
    """Base exception for voice agent errors."""
    pass


class VoiceAgentAPIException(VoiceAgentException):
    """ElevenLabs API error during voice agent call."""
    pass


class APIException(Exception):
    """General API communication error."""
    pass


class StorageException(Exception):
    """File storage error (S3 or local)."""
    pass


class DatabaseException(Exception):
    """Database operation error."""
    pass


class ValidationException(Exception):
    """Request validation error."""
    pass


class WebhookValidationException(Exception):
    """Webhook signature validation error."""
    pass


class CallerNotFoundException(Exception):
    """Caller ID not found in database."""
    pass


class VoiceSampleNotFoundException(Exception):
    """Voice sample file not found."""
    pass
