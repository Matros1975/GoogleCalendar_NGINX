"""
Pydantic models for ElevenLabs API requests and responses.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class VoiceCloneAPIRequest(BaseModel):
    """Request to create a voice clone via ElevenLabs API."""
    name: str = Field(..., description="Name for the cloned voice")
    description: Optional[str] = Field(None, description="Description of the voice")
    labels: Optional[Dict[str, str]] = Field(None, description="Custom labels/metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe Voice Clone",
                "description": "Professional voice clone for customer calls",
                "labels": {"caller_id": "+31612345678"}
            }
        }


class VoiceCloneAPIResponse(BaseModel):
    """Response from voice clone creation."""
    voice_id: str = Field(..., description="Created voice ID")
    name: str = Field(..., description="Voice name")
    category: Optional[str] = Field(None, description="Voice category")
    labels: Optional[Dict[str, str]] = Field(None, description="Voice labels")
    
    class Config:
        json_schema_extra = {
            "example": {
                "voice_id": "voice_123abc",
                "name": "John Doe Voice Clone",
                "category": "cloned",
                "labels": {"caller_id": "+31612345678"}
            }
        }


class VoiceAgentCallRequest(BaseModel):
    """Request to trigger a Voice Agent call."""
    agent_id: str = Field(..., description="Voice Agent ID")
    phone_number: str = Field(..., description="Phone number to call (E.164 format)")
    voice_id: str = Field(..., description="Voice ID to use")
    custom_variables: Optional[Dict[str, Any]] = Field(None, description="Context data for agent")
    
    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "agent_abc",
                "phone_number": "+31612345678",
                "voice_id": "voice_123abc",
                "custom_variables": {
                    "caller_id": "+31612345678",
                    "3cx_call_id": "abc123-def456-ghi789"
                }
            }
        }


class VoiceAgentCallResponse(BaseModel):
    """Response from Voice Agent call initiation."""
    call_id: str = Field(..., description="ElevenLabs call ID")
    status: str = Field(..., description="Call status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "call_id": "elevenlabs_call_123",
                "status": "initiated"
            }
        }


class VoiceDetails(BaseModel):
    """Voice details from ElevenLabs."""
    voice_id: str = Field(..., description="Voice ID")
    name: str = Field(..., description="Voice name")
    category: str = Field(..., description="Voice category")
    description: Optional[str] = Field(None, description="Voice description")
    labels: Optional[Dict[str, str]] = Field(None, description="Voice labels")
    samples: Optional[List[Dict[str, Any]]] = Field(None, description="Voice samples")
    
    class Config:
        json_schema_extra = {
            "example": {
                "voice_id": "voice_123abc",
                "name": "John Doe Voice Clone",
                "category": "cloned",
                "description": "Professional voice clone",
                "labels": {"caller_id": "+31612345678"},
                "samples": []
            }
        }


class ElevenLabsErrorResponse(BaseModel):
    """Error response from ElevenLabs API."""
    detail: Dict[str, Any] = Field(..., description="Error details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": {
                    "status": "error",
                    "message": "Voice clone creation failed"
                }
            }
        }


class TranscriptMessage(BaseModel):
    """Individual message in a conversation transcript."""
    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = Field(None, description="Message timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "role": "user",
                "content": "Hello, I need help with my account",
                "timestamp": "2025-12-10T12:00:30Z"
            }
        }


class ConversationTranscript(BaseModel):
    """Full conversation transcript."""
    call_id: str = Field(..., description="Call ID")
    messages: List[TranscriptMessage] = Field(..., description="Conversation messages")
    duration_seconds: int = Field(..., description="Total call duration")
    
    class Config:
        json_schema_extra = {
            "example": {
                "call_id": "elevenlabs_call_123",
                "messages": [
                    {
                        "role": "assistant",
                        "content": "Hello, how can I help you?",
                        "timestamp": "2025-12-10T12:00:00Z"
                    },
                    {
                        "role": "user",
                        "content": "I need help with my account",
                        "timestamp": "2025-12-10T12:00:30Z"
                    }
                ],
                "duration_seconds": 120
            }
        }
