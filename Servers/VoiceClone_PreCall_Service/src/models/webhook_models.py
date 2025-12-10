"""
Pydantic models for webhook payloads.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class TwilioWebhookPayload(BaseModel):
    """
    Incoming Call Webhook from Twilio.
    
    Represents the payload received when Twilio sends a webhook notification.
    """
    
    CallSid: str = Field(..., description="Twilio call SID (unique identifier)")
    AccountSid: str = Field(..., description="Twilio account SID")
    From: str = Field(..., alias="From", description="Caller phone number (E.164 format)")
    To: str = Field(..., alias="To", description="Twilio number that was called")
    CallStatus: str = Field(..., description="Call status: ringing, in-progress, completed")
    Direction: str = Field(default="inbound", description="Call direction")
    ApiVersion: str = Field(default="2010-04-01", description="Twilio API version")
    
    class Config:
        populate_by_name = True


class ThreeCXWebhookPayload(BaseModel):
    """
    Incoming Call Webhook from 3CX PBX (DEPRECATED - kept for backwards compatibility).
    
    Represents the payload received when 3CX sends a webhook notification.
    """
    
    event_type: str = Field(..., description="Event type: IncomingCall, CallStateChanged, CallEnded")
    call_id: str = Field(..., description="3CX call UUID")
    caller_id: str = Field(..., description="Caller phone number (E.164 format)")
    called_number: str = Field(..., description="Number that was called")
    timestamp: datetime = Field(..., description="Event timestamp")
    direction: str = Field(..., description="Call direction: In or Out")
    duration: Optional[int] = Field(None, description="Call duration in seconds")
    recording_url: Optional[str] = Field(None, description="Call recording URL if available")


class VoiceCloneRequest(BaseModel):
    """
    Request to create or retrieve a voice clone.
    """
    
    caller_id: str = Field(..., description="Caller phone number")
    voice_sample_path: Optional[str] = Field(None, description="Override voice sample path")
    voice_name: Optional[str] = Field(None, description="Name for the cloned voice")


class VoiceCloneResponse(BaseModel):
    """
    Response from voice clone operation.
    """
    
    cloned_voice_id: str = Field(..., description="ElevenLabs cloned voice ID")
    caller_id: str = Field(..., description="Caller phone number")
    created_at: datetime = Field(..., description="Clone creation timestamp")
    cached: bool = Field(..., description="True if retrieved from cache")


class IncomingCallResponse(BaseModel):
    """
    Response from incoming call webhook handler.
    """
    
    status: str = Field(..., description="Status: success or error")
    call_id: str = Field(..., description="ElevenLabs call ID")
    cloned_voice_id: str = Field(..., description="Cloned voice ID used")
    threecx_call_id: str = Field(..., description="3CX call ID")
    message: Optional[str] = Field(None, description="Optional message")


class PostCallWebhookPayload(BaseModel):
    """
    POST-Call Webhook from ElevenLabs.
    
    Received after a voice agent call completes.
    """
    
    call_id: str = Field(..., description="ElevenLabs call ID")
    agent_id: str = Field(..., description="Voice agent ID")
    transcript: Optional[str] = Field(None, description="Full conversation transcript")
    duration_seconds: Optional[int] = Field(None, description="Call duration")
    status: str = Field(..., description="Call status: completed, failed, missed")
    custom_variables: Optional[Dict[str, Any]] = Field(None, description="Custom metadata")
    timestamp: datetime = Field(..., description="Event timestamp")


class HealthCheckResponse(BaseModel):
    """
    Health check endpoint response.
    """
    
    status: str = Field(..., description="Overall status: ok, degraded, error")
    database: str = Field(..., description="Database status: ok or error")
    elevenlabs: str = Field(..., description="ElevenLabs API status: ok or error")
    timestamp: datetime = Field(..., description="Health check timestamp")


class CacheInvalidationRequest(BaseModel):
    """
    Request to invalidate voice clone cache.
    """
    
    caller_id: str = Field(..., description="Caller ID to invalidate")


class CacheInvalidationResponse(BaseModel):
    """
    Response from cache invalidation.
    """
    
    success: bool = Field(..., description="True if cache was invalidated")
    message: str = Field(..., description="Result message")


class StatisticsResponse(BaseModel):
    """
    Voice clone statistics response.
    """
    
    total_clones: int = Field(..., description="Total clones created")
    cache_hits: int = Field(..., description="Number of cache hits")
    cache_misses: int = Field(..., description="Number of cache misses")
    hit_rate: float = Field(..., description="Cache hit rate (0.0 to 1.0)")
    avg_creation_time_ms: float = Field(..., description="Average clone creation time")
    total_calls: int = Field(..., description="Total calls made")
