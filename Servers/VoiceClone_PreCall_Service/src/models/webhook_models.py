"""
Pydantic models for webhook payloads.

Defines request/response schemas for 3CX and other webhook integrations.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ThreeCXWebhookPayload(BaseModel):
    """
    Incoming call webhook payload from 3CX PBX.
    
    Represents the data sent by 3CX when an incoming call event occurs.
    """
    event_type: str = Field(..., description="Event type: IncomingCall, CallStateChanged, CallEnded")
    call_id: str = Field(..., description="3CX call UUID")
    caller_id: str = Field(..., description="Caller phone number")
    called_number: str = Field(..., description="Number that was called")
    timestamp: datetime = Field(..., description="Event timestamp")
    direction: str = Field(default="In", description="Call direction: In or Out")
    duration: Optional[int] = Field(None, description="Call duration in seconds (if ended)")
    recording_url: Optional[str] = Field(None, description="Call recording URL (if available)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "IncomingCall",
                "call_id": "abc123-def456-ghi789",
                "caller_id": "+31612345678",
                "called_number": "+31201234567",
                "timestamp": "2025-12-10T12:00:00Z",
                "direction": "In",
                "duration": None,
                "recording_url": None
            }
        }


class VoiceCloneRequest(BaseModel):
    """Request to create a voice clone."""
    caller_id: str = Field(..., description="Caller phone number")
    voice_sample_path: Optional[str] = Field(None, description="Override voice sample path")
    voice_name: Optional[str] = Field(None, description="Override voice name")
    
    class Config:
        json_schema_extra = {
            "example": {
                "caller_id": "+31612345678",
                "voice_sample_path": None,
                "voice_name": None
            }
        }


class VoiceCloneResponse(BaseModel):
    """Response from voice clone creation."""
    cloned_voice_id: str = Field(..., description="ElevenLabs cloned voice ID")
    caller_id: str = Field(..., description="Caller phone number")
    created_at: datetime = Field(..., description="Clone creation timestamp")
    cached: bool = Field(..., description="True if clone was retrieved from cache")
    
    class Config:
        json_schema_extra = {
            "example": {
                "cloned_voice_id": "voice_123abc",
                "caller_id": "+31612345678",
                "created_at": "2025-12-10T12:00:00Z",
                "cached": False
            }
        }


class IncomingCallResponse(BaseModel):
    """Response for incoming call webhook."""
    status: str = Field(..., description="Processing status: success or error")
    call_id: str = Field(..., description="ElevenLabs call ID")
    cloned_voice_id: str = Field(..., description="Cloned voice ID used")
    threecx_call_id: str = Field(..., alias="3cx_call_id", description="3CX call ID")
    message: Optional[str] = Field(None, description="Additional message or error details")
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "status": "success",
                "call_id": "elevenlabs_call_123",
                "cloned_voice_id": "voice_123abc",
                "3cx_call_id": "abc123-def456-ghi789",
                "message": "Call initiated successfully"
            }
        }


class PostCallWebhookPayload(BaseModel):
    """
    POST-call webhook payload from ElevenLabs.
    
    Sent by ElevenLabs when a voice agent call completes.
    """
    call_id: str = Field(..., description="ElevenLabs call ID")
    agent_id: str = Field(..., description="Voice agent ID")
    transcript: Optional[str] = Field(None, description="Call transcript")
    duration_seconds: Optional[int] = Field(None, description="Call duration in seconds")
    status: str = Field(..., description="Call status: completed, failed, missed")
    custom_variables: Optional[Dict[str, Any]] = Field(None, description="Custom variables")
    timestamp: datetime = Field(..., description="Event timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "call_id": "elevenlabs_call_123",
                "agent_id": "agent_abc",
                "transcript": "Hello, how can I help you today?",
                "duration_seconds": 120,
                "status": "completed",
                "custom_variables": {"caller_id": "+31612345678"},
                "timestamp": "2025-12-10T12:02:00Z"
            }
        }


class HealthCheckResponse(BaseModel):
    """Health check endpoint response."""
    status: str = Field(..., description="Overall status: ok, degraded, or error")
    database: str = Field(..., description="Database status: ok or error")
    redis: str = Field(..., description="Redis status: ok or error")
    elevenlabs: str = Field(..., description="ElevenLabs API status: ok or error")
    timestamp: datetime = Field(..., description="Health check timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "database": "ok",
                "redis": "ok",
                "elevenlabs": "ok",
                "timestamp": "2025-12-10T12:00:00Z"
            }
        }


class GreetingCallRequest(BaseModel):
    """Request to initiate a greeting call."""
    caller_id: str = Field(..., description="Caller phone number")
    threecx_call_id: str = Field(..., description="3CX call ID")
    greeting_voice_id: str = Field(..., description="Voice ID for greeting")
    greeting_message: str = Field(..., description="Greeting message text")
    
    class Config:
        json_schema_extra = {
            "example": {
                "caller_id": "+31612345678",
                "threecx_call_id": "abc123-def456-ghi789",
                "greeting_voice_id": "default_greeting_voice",
                "greeting_message": "Hello, please hold while we prepare your experience."
            }
        }


class GreetingCallResponse(BaseModel):
    """Response from greeting call initiation."""
    greeting_call_id: str = Field(..., description="ElevenLabs greeting call ID")
    status: str = Field(..., description="Initiation status: success or error")
    message: Optional[str] = Field(None, description="Additional message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "greeting_call_id": "greeting_call_123",
                "status": "success",
                "message": "Greeting call initiated"
            }
        }


class CloneStatusResponse(BaseModel):
    """Response for clone status check."""
    caller_id: str = Field(..., description="Caller phone number")
    status: str = Field(..., description="Clone status: ready, pending, failed")
    cloned_voice_id: Optional[str] = Field(None, description="Cloned voice ID if ready")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    duration_ms: Optional[int] = Field(None, description="Clone creation duration in ms")
    
    class Config:
        json_schema_extra = {
            "example": {
                "caller_id": "+31612345678",
                "status": "ready",
                "cloned_voice_id": "voice_123abc",
                "error_message": None,
                "duration_ms": 15000
            }
        }
