"""
Pydantic models for ElevenLabs API responses.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class VoiceSettings(BaseModel):
    """Voice settings for ElevenLabs voice."""
    stability: Optional[float] = Field(None, description="Voice stability")
    similarity_boost: Optional[float] = Field(None, description="Similarity boost")
    style: Optional[float] = Field(None, description="Style exaggeration")
    use_speaker_boost: Optional[bool] = Field(None, description="Use speaker boost")


class VoiceSampleInfo(BaseModel):
    """Information about a voice sample."""
    sample_id: Optional[str] = Field(None, description="Sample identifier")
    file_name: Optional[str] = Field(None, description="Original filename")
    mime_type: Optional[str] = Field(None, description="MIME type")
    size_bytes: Optional[int] = Field(None, description="File size in bytes")
    hash: Optional[str] = Field(None, description="File hash")


class VoiceCreateResponse(BaseModel):
    """Response from voice creation API."""
    voice_id: str = Field(..., description="Created voice ID")
    name: str = Field(..., description="Voice name")
    samples: Optional[List[VoiceSampleInfo]] = Field(None, description="Voice samples")
    category: Optional[str] = Field(None, description="Voice category")
    fine_tuning: Optional[Dict[str, Any]] = Field(None, description="Fine tuning settings")
    labels: Optional[Dict[str, str]] = Field(None, description="Voice labels")
    description: Optional[str] = Field(None, description="Voice description")
    preview_url: Optional[str] = Field(None, description="Preview URL")
    settings: Optional[VoiceSettings] = Field(None, description="Voice settings")


class VoiceInfo(BaseModel):
    """Information about a voice."""
    voice_id: str = Field(..., description="Voice identifier")
    name: str = Field(..., description="Voice name")
    category: Optional[str] = Field(None, description="Voice category")
    description: Optional[str] = Field(None, description="Voice description")
    labels: Optional[Dict[str, str]] = Field(None, description="Voice labels")
    preview_url: Optional[str] = Field(None, description="Preview URL")
    settings: Optional[VoiceSettings] = Field(None, description="Voice settings")


class AgentVoiceConfig(BaseModel):
    """Voice configuration for agent."""
    voice_id: str = Field(..., description="Voice ID to use")
    stability: Optional[float] = Field(None, description="Voice stability")
    similarity_boost: Optional[float] = Field(None, description="Similarity boost")


class AgentConfig(BaseModel):
    """Agent configuration."""
    first_message: Optional[str] = Field(None, description="First message from agent")
    voice: Optional[AgentVoiceConfig] = Field(None, description="Voice configuration")


class ConversationConfig(BaseModel):
    """Conversation configuration wrapper."""
    agent: Optional[AgentConfig] = Field(None, description="Agent configuration")


class AgentUpdateRequest(BaseModel):
    """Request to update agent configuration."""
    conversation_config: Optional[ConversationConfig] = Field(None, description="Conversation config")


class AgentUpdateResponse(BaseModel):
    """Response from agent update API."""
    agent_id: str = Field(..., description="Agent identifier")
    name: Optional[str] = Field(None, description="Agent name")
    conversation_config: Optional[Dict[str, Any]] = Field(None, description="Updated conversation config")
