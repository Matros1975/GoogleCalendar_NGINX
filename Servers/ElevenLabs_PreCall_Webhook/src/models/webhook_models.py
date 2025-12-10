"""
Pydantic models for ElevenLabs pre-call webhook payloads.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class VoiceSample(BaseModel):
    """Voice sample data in webhook payload."""
    format: str = Field(..., description="Audio format (base64, file)")
    data: Optional[str] = Field(None, description="Base64-encoded audio data")
    duration_seconds: Optional[float] = Field(None, description="Audio duration")
    sample_rate: Optional[int] = Field(None, description="Sample rate in Hz")


class CallerMetadata(BaseModel):
    """Caller metadata from webhook."""
    name: Optional[str] = Field(None, description="Caller name")
    date_of_birth: Optional[str] = Field(None, alias="date_of_birth", description="Date of birth")
    phone_number: Optional[str] = Field(None, alias="phone_number", description="Phone number")
    
    class Config:
        populate_by_name = True


class PreCallWebhookPayload(BaseModel):
    """Pre-call webhook payload from ElevenLabs."""
    type: str = Field(..., description="Webhook type (should be 'pre_call')")
    event_timestamp: int = Field(..., description="Unix timestamp of event")
    conversation_id: str = Field(..., description="Unique conversation identifier")
    agent_id: str = Field(..., description="ElevenLabs agent identifier")
    caller_metadata: Optional[CallerMetadata] = Field(None, description="Caller information")
    voice_sample: Optional[VoiceSample] = Field(None, description="Voice sample data")


class PreCallWebhookResponse(BaseModel):
    """Response to pre-call webhook."""
    status: str = Field(..., description="Processing status")
    conversation_id: str = Field(..., description="Conversation identifier")
    voice_id: Optional[str] = Field(None, description="Created voice ID")
    voice_name: Optional[str] = Field(None, description="Voice name")
    agent_updated: bool = Field(default=False, description="Whether agent was updated")
    caller_info: Optional[Dict[str, Any]] = Field(None, description="Caller information for agent")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")


class PreCallWebhookError(BaseModel):
    """Error response for pre-call webhook."""
    status: str = Field(default="error", description="Status (always 'error')")
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human-readable error message")
    conversation_id: Optional[str] = Field(None, description="Conversation identifier if available")
