"""
Data models for ElevenLabs webhook payloads.

Based on ElevenLabs webhook documentation:
https://elevenlabs.io/docs/agents-platform/workflows/post-call-webhooks
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TranscriptEntry:
    """A single entry in the conversation transcript."""
    role: str  # "agent" or "user"
    message: str
    timestamp: Optional[float] = None  # Time offset in seconds
    tool_call: Optional[Dict[str, Any]] = None  # Tool invocation details
    tool_result: Optional[Dict[str, Any]] = None  # Tool result details
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TranscriptEntry":
        """Create TranscriptEntry from dictionary."""
        return cls(
            role=data.get("role", ""),
            message=data.get("message", ""),
            timestamp=data.get("time_in_call_secs"),
            tool_call=data.get("tool_call"),
            tool_result=data.get("tool_result")
        )


@dataclass
class AnalysisResult:
    """Analysis results from the conversation."""
    evaluation: Optional[Dict[str, Any]] = None
    data_collection: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisResult":
        """Create AnalysisResult from dictionary."""
        if not data:
            return cls()
        return cls(
            evaluation=data.get("evaluation"),
            data_collection=data.get("data_collection"),
            summary=data.get("call_summary")
        )


@dataclass
class ConversationData:
    """Full conversation data including metadata and transcript."""
    conversation_id: str
    agent_id: str
    call_duration_secs: Optional[float] = None
    message_count: int = 0
    status: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    transcript: List[TranscriptEntry] = field(default_factory=list)
    analysis: Optional[AnalysisResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Audio availability fields (coming August 2025)
    has_audio: Optional[bool] = None
    has_user_audio: Optional[bool] = None
    has_response_audio: Optional[bool] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationData":
        """Create ConversationData from dictionary."""
        transcript_data = data.get("transcript", [])
        transcript = [TranscriptEntry.from_dict(t) for t in transcript_data]
        
        analysis_data = data.get("analysis")
        analysis = AnalysisResult.from_dict(analysis_data) if analysis_data else None
        
        # Parse timestamps
        start_time = None
        end_time = None
        if data.get("start_time_unix_secs"):
            start_time = datetime.fromtimestamp(data["start_time_unix_secs"])
        if data.get("end_time_unix_secs"):
            end_time = datetime.fromtimestamp(data["end_time_unix_secs"])
        
        return cls(
            conversation_id=data.get("conversation_id", ""),
            agent_id=data.get("agent_id", ""),
            call_duration_secs=data.get("call_duration_secs"),
            message_count=data.get("message_count", 0),
            status=data.get("status", ""),
            start_time=start_time,
            end_time=end_time,
            transcript=transcript,
            analysis=analysis,
            metadata=data.get("metadata", {}),
            has_audio=data.get("has_audio"),
            has_user_audio=data.get("has_user_audio"),
            has_response_audio=data.get("has_response_audio"),
        )


@dataclass
class WebhookPayload:
    """Base webhook payload."""
    type: str
    conversation_id: str
    agent_id: str
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WebhookPayload":
        """Create WebhookPayload from dictionary."""
        return cls(
            type=data.get("type", ""),
            conversation_id=data.get("conversation_id", ""),
            agent_id=data.get("agent_id", ""),
        )


@dataclass
class TranscriptionPayload(WebhookPayload):
    """Payload for post_call_transcription webhook."""
    data: Optional[ConversationData] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TranscriptionPayload":
        """Create TranscriptionPayload from dictionary."""
        conversation_data = data.get("data", {})
        return cls(
            type=data.get("type", "post_call_transcription"),
            conversation_id=data.get("conversation_id", ""),
            agent_id=data.get("agent_id", ""),
            data=ConversationData.from_dict(conversation_data) if conversation_data else None
        )


@dataclass
class AudioPayload(WebhookPayload):
    """Payload for post_call_audio webhook."""
    audio_base64: str = ""
    audio_format: str = "mp3"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudioPayload":
        """Create AudioPayload from dictionary."""
        return cls(
            type=data.get("type", "post_call_audio"),
            conversation_id=data.get("conversation_id", ""),
            agent_id=data.get("agent_id", ""),
            audio_base64=data.get("audio_base64", ""),
            audio_format=data.get("audio_format", "mp3"),
        )


@dataclass
class CallFailurePayload(WebhookPayload):
    """Payload for call_initiation_failure webhook."""
    error_message: str = ""
    error_code: Optional[str] = None
    provider: Optional[str] = None  # "sip" or "twilio"
    provider_details: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CallFailurePayload":
        """Create CallFailurePayload from dictionary."""
        return cls(
            type=data.get("type", "call_initiation_failure"),
            conversation_id=data.get("conversation_id", ""),
            agent_id=data.get("agent_id", ""),
            error_message=data.get("error_message", ""),
            error_code=data.get("error_code"),
            provider=data.get("provider"),
            provider_details=data.get("provider_details", {}),
        )
