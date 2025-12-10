"""
Configuration management for VoiceClone Pre-Call Service.

Uses Pydantic BaseSettings for type-safe configuration with environment variable validation.
"""

import os
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # ElevenLabs Configuration
    elevenlabs_api_key: str = Field(..., description="ElevenLabs API key")
    elevenlabs_agent_id: str = Field(..., description="ElevenLabs Voice Agent ID")
    elevenlabs_api_base: str = Field(
        default="https://api.elevenlabs.io/v1",
        description="ElevenLabs API base URL"
    )
    
    # Greeting Configuration (Async Voice Cloning)
    greeting_voice_id: str = Field(
        default="default_greeting_voice",
        description="ElevenLabs voice ID for prerecorded greeting"
    )
    greeting_message: str = Field(
        default="Hello thanks for calling. Please hold while we prepare your personalized experience.",
        description="Greeting message text"
    )
    greeting_music_enabled: bool = Field(
        default=True,
        description="Play background music during wait"
    )
    greeting_music_url: Optional[str] = Field(
        default=None,
        description="Hold music file URL"
    )
    clone_max_wait_seconds: int = Field(
        default=35,
        ge=10,
        le=60,
        description="Max wait time before timeout"
    )
    auto_transition_enabled: bool = Field(
        default=True,
        description="Automatically switch to cloned voice when ready"
    )
    
    # Database Configuration
    database_url: str = Field(
        ...,
        description="PostgreSQL connection URL (async)"
    )
    cache_ttl: int = Field(
        default=86400,
        ge=3600,
        description="Voice clone cache TTL in seconds (default: 24 hours)"
    )
    
    # Voice Clone Configuration
    voice_clone_timeout: int = Field(
        default=30,
        ge=10,
        le=60,
        description="Voice clone creation timeout in seconds"
    )
    voice_sample_storage: str = Field(
        default="local",
        description="Storage backend: 's3' or 'local'"
    )
    
    # S3 Configuration (if using S3)
    s3_bucket_name: Optional[str] = Field(
        default=None,
        description="S3 bucket name for voice samples"
    )
    s3_region: Optional[str] = Field(
        default="eu-west-1",
        description="AWS region"
    )
    aws_access_key_id: Optional[str] = Field(
        default=None,
        description="AWS access key ID"
    )
    aws_secret_access_key: Optional[str] = Field(
        default=None,
        description="AWS secret access key"
    )
    
    # Local Storage Configuration
    local_voice_samples_path: str = Field(
        default="/data/voices",
        description="Local path for voice samples"
    )
    
    # Twilio Configuration
    twilio_account_sid: str = Field(
        default="",
        description="Twilio Account SID"
    )
    twilio_auth_token: str = Field(
        default="",
        description="Twilio Auth Token for webhook signature validation"
    )
    twilio_phone_number: str = Field(
        default="",
        description="Twilio phone number (E.164 format)"
    )
    twilio_webhook_url: str = Field(
        default="",
        description="Twilio webhook URL for inbound calls"
    )
    
    # Testing Mode
    skip_webhook_signature_validation: bool = Field(
        default=False,
        description="Skip Twilio signature validation for local testing"
    )
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")
    log_level: str = Field(default="INFO", description="Logging level")
    environment: str = Field(default="development", description="Environment: development or production")
    
    # Security
    webhook_secret: str = Field(..., description="Webhook signature verification secret")
    cors_origins: str = Field(
        default='["*"]',
        description="CORS allowed origins (JSON array as string)"
    )
    
    @field_validator("voice_sample_storage")
    @classmethod
    def validate_storage_backend(cls, v: str) -> str:
        """Validate storage backend is either 's3' or 'local'."""
        if v not in ["s3", "local"]:
            raise ValueError("voice_sample_storage must be 's3' or 'local'")
        return v
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v_upper
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment."""
        valid_envs = ["development", "production"]
        v_lower = v.lower()
        if v_lower not in valid_envs:
            raise ValueError(f"environment must be one of {valid_envs}")
        return v_lower
    
    def get_cors_origins_list(self) -> List[str]:
        """Parse CORS origins from JSON string."""
        import json
        try:
            return json.loads(self.cors_origins)
        except json.JSONDecodeError:
            return []
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get application settings singleton.
    
    Returns:
        Settings instance loaded from environment
        
    Raises:
        ValueError: If required environment variables are missing
    """
    global _settings
    
    if _settings is None:
        try:
            _settings = Settings()
        except Exception as e:
            raise ValueError(f"Failed to load configuration: {str(e)}")
    
    return _settings


def reload_settings() -> Settings:
    """Force reload settings from environment (mainly for testing)."""
    global _settings
    _settings = None
    return get_settings()
