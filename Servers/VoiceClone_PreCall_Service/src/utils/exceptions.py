"""
Custom exception classes for Voice Clone Pre-Call Service.
"""


class VoiceCloneServiceException(Exception):
    """Base exception for all voice clone service errors."""
    pass


class VoiceCloneException(VoiceCloneServiceException):
    """Exception raised when voice clone creation fails."""
    pass


class VoiceAgentException(VoiceCloneServiceException):
    """Exception raised when voice agent call initiation fails."""
    pass


class APIException(VoiceCloneServiceException):
    """Exception raised for ElevenLabs API errors."""
    
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        """
        Initialize API exception.
        
        Args:
            message: Error message
            status_code: HTTP status code from API
            response_data: API response data
        """
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class CacheException(VoiceCloneServiceException):
    """Exception raised for Redis cache errors."""
    pass


class DatabaseException(VoiceCloneServiceException):
    """Exception raised for database errors."""
    pass


class StorageException(VoiceCloneServiceException):
    """Exception raised for storage (S3/local) errors."""
    pass


class ValidationException(VoiceCloneServiceException):
    """Exception raised for validation errors."""
    pass


class ConfigurationException(VoiceCloneServiceException):
    """Exception raised for configuration errors."""
    pass


class WebhookValidationException(VoiceCloneServiceException):
    """Exception raised for webhook signature validation failures."""
    pass


class VoiceSampleNotFoundException(VoiceCloneServiceException):
    """Exception raised when voice sample is not found for caller."""
    pass


class CloneTimeoutException(VoiceCloneServiceException):
    """Exception raised when voice clone creation times out."""
    pass


class GreetingCallException(VoiceCloneServiceException):
    """Exception raised when greeting call initiation fails."""
    pass
