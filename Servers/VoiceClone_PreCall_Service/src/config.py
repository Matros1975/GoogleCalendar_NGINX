"""
Configuration management for Voice Clone Pre-Call Service.

Uses Pydantic BaseSettings for type-safe configuration loading from environment variables.
"""

import os
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # ElevenLabs API Configuration
    elevenlabs_api_key: str = Field(..., description="ElevenLabs API key")
    elevenlabs_agent_id: str = Field(..., description="ElevenLabs Voice Agent ID")
    elevenlabs_phone_number_id: str = Field(..., description="ElevenLabs registered phone number ID")
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
    greeting_music_enabled: bool = Field(default=True, description="Play background music during wait")
    greeting_music_url: Optional[str] = Field(
        default="https://your-domain.com/hold-music.mp3",
        description="Hold music file URL"
    )
    clone_max_wait_seconds: int = Field(default=35, description="Max wait time before timeout")
    auto_transition_enabled: bool = Field(
        default=True,
        description="Automatically switch to cloned voice when ready"
    )
    
    # Database Configuration
    database_url: str = Field(..., description="PostgreSQL connection string with asyncpg driver")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection string")
    cache_ttl: int = Field(default=86400, description="Cache TTL in seconds (default 24 hours)")
    
    # Voice Clone Configuration
    voice_clone_timeout: int = Field(default=30, description="Voice clone creation timeout in seconds")
    voice_sample_storage: str = Field(default="s3", description="Storage type: 's3' or 'local'")
    s3_bucket_name: Optional[str] = Field(default="voice-samples", description="S3 bucket name")
    s3_region: Optional[str] = Field(default="eu-west-1", description="AWS region")
    aws_access_key_id: Optional[str] = Field(default=None, description="AWS access key ID")
    aws_secret_access_key: Optional[str] = Field(default=None, description="AWS secret access key")
    local_voice_samples_path: str = Field(
        default="/data/voices",
        description="Local voice samples directory path"
    )
    
    # 3CX Configuration
    threecx_webhook_secret: str = Field(..., alias="3CX_WEBHOOK_SECRET", description="3CX webhook secret")
    threecx_trusted_ips: str = Field(
        default="127.0.0.1,10.0.0.0/8",
        alias="3CX_TRUSTED_IPS",
        description="Comma-separated trusted IP addresses"
    )
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=3006, description="Server port")
    log_level: str = Field(default="INFO", description="Logging level")
    environment: str = Field(default="development", description="Environment: development or production")
    
    # Security
    webhook_secret: str = Field(..., description="Webhook signature validation secret")
    cors_origins: str = Field(default='["https://your-3cx.com"]', description="CORS allowed origins as JSON array")
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        populate_by_name = True
    
    @field_validator("voice_sample_storage")
    @classmethod
    def validate_storage_type(cls, v: str) -> str:
        """Validate storage type is either 's3' or 'local'."""
        if v not in ["s3", "local"]:
            raise ValueError("voice_sample_storage must be either 's3' or 'local'")
        return v
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment is either 'development' or 'production'."""
        if v not in ["development", "production"]:
            raise ValueError("environment must be either 'development' or 'production'")
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
    
    def validate_s3_config(self) -> None:
        """Validate S3 configuration if storage type is S3."""
        if self.voice_sample_storage == "s3":
            if not self.aws_access_key_id or not self.aws_secret_access_key:
                raise ValueError(
                    "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are required when using S3 storage"
                )
            if not self.s3_bucket_name:
                raise ValueError("S3_BUCKET_NAME is required when using S3 storage")
    
    def get_cors_origins_list(self) -> List[str]:
        """Parse CORS origins from JSON string to list."""
        import json
        try:
            return json.loads(self.cors_origins)
        except json.JSONDecodeError:
            return ["https://your-3cx.com"]


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get application settings singleton.
    
    Returns:
        Settings instance
        
    Raises:
        ValueError: If required configuration is missing
    """
    global _settings
    
    if _settings is None:
        try:
            _settings = Settings()
            
            # Validate S3 configuration if needed
            _settings.validate_s3_config()
            
            # Log loaded configuration (redact secrets)
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Configuration loaded successfully")
            logger.info(f"Environment: {_settings.environment}")
            logger.info(f"Port: {_settings.port}")
            logger.info(f"Log Level: {_settings.log_level}")
            logger.info(f"Storage Type: {_settings.voice_sample_storage}")
            logger.info(f"ElevenLabs API Base: {_settings.elevenlabs_api_base}")
            
        except Exception as e:
            raise ValueError(f"Configuration error: {str(e)}")
    
    return _settings


def reload_settings() -> Settings:
    """
    Reload settings (useful for testing).
    
    Returns:
        New Settings instance
    """
    global _settings
    _settings = None
    return get_settings()
