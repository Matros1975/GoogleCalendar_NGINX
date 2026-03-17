"""
Pydantic models for ElevenLabs API responses.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class VoiceCloneCreateRequest(BaseModel):
    """
    Request to create a voice clone via ElevenLabs API.
    """
    
    name: str = Field(..., description="Name for the cloned voice")
    description: Optional[str] = Field(None, description="Optional description")
    files: List[bytes] = Field(..., description="Voice sample audio files")


class VoiceCloneCreateResponse(BaseModel):
    """
    Response from ElevenLabs voice clone creation.
    """
    
    voice_id: str = Field(..., description="Created voice ID")
    name: str = Field(..., description="Voice name")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")


class VoiceDetails(BaseModel):
    """
    Details about a voice from ElevenLabs API.
    """
    
    voice_id: str = Field(..., description="Voice ID")
    name: str = Field(..., description="Voice name")
    category: Optional[str] = Field(None, description="Voice category")
    description: Optional[str] = Field(None, description="Voice description")
    labels: Optional[Dict[str, str]] = Field(None, description="Voice labels/metadata")
    samples: Optional[List[Dict[str, Any]]] = Field(None, description="Voice samples")


class VoiceAgentCallRequest(BaseModel):
    """
    Request to trigger a voice agent call.
    """
    
    phone_number: str = Field(..., description="Recipient phone number (E.164 format)")
    voice_id: str = Field(..., description="Voice ID to use for the call")
    custom_variables: Optional[Dict[str, Any]] = Field(None, description="Custom context data")


class VoiceAgentCallResponse(BaseModel):
    """
    Response from triggering a voice agent call.
    """
    
    call_id: str = Field(..., description="ElevenLabs call ID")
    status: str = Field(..., description="Initial call status")
    phone_number: str = Field(..., description="Recipient phone number")


class ElevenLabsErrorResponse(BaseModel):
    """
    Error response from ElevenLabs API.
    """
    
    error: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class VoiceListResponse(BaseModel):
    """
    Response from listing voices.
    """
    
    voices: List[VoiceDetails] = Field(..., description="List of available voices")
