"""
Call instructions data models for protocol-agnostic call control.

These models represent the business logic output that can be converted
to protocol-specific responses (TwiML for Twilio, SIP commands for PJSUA2).
"""

from enum import Enum
from typing import Optional
from dataclasses import dataclass


class CallAction(Enum):
    """Actions that can be taken during a call."""
    PLAY_AUDIO = "play_audio"
    SPEAK = "speak"
    POLL_STATUS = "poll_status"
    CONNECT_WEBSOCKET = "connect_websocket"
    HANGUP = "hangup"


@dataclass
class AudioInstruction:
    """Instruction to play audio file."""
    url: str
    loop: int = 1
    
    def __post_init__(self):
        """Validate audio instruction."""
        if not self.url:
            raise ValueError("Audio URL cannot be empty")
        if self.loop < 1:
            raise ValueError("Loop count must be at least 1")


@dataclass
class SpeechInstruction:
    """Instruction to speak text."""
    text: str
    voice: str = "alice"
    language: str = "en-US"
    
    def __post_init__(self):
        """Validate speech instruction."""
        if not self.text:
            raise ValueError("Speech text cannot be empty")


@dataclass
class StatusPollInstruction:
    """Instruction to poll for clone status."""
    poll_url: str
    interval_seconds: int = 10
    
    def __post_init__(self):
        """Validate status poll instruction."""
        if not self.poll_url:
            raise ValueError("Poll URL cannot be empty")
        if self.interval_seconds < 1:
            raise ValueError("Poll interval must be at least 1 second")


@dataclass
class WebSocketInstruction:
    """Instruction to connect to WebSocket for voice streaming."""
    url: str
    voice_id: str
    api_key: str
    track: str = "inbound_track"
    
    def __post_init__(self):
        """Validate WebSocket instruction."""
        if not self.url:
            raise ValueError("WebSocket URL cannot be empty")
        if not self.voice_id:
            raise ValueError("Voice ID cannot be empty")
        if not self.api_key:
            raise ValueError("API key cannot be empty")


@dataclass
class CallInstructions:
    """
    Protocol-agnostic call instructions.
    
    This is the output of CallController business logic, which handlers
    convert to protocol-specific responses (TwiML, SIP commands, etc.).
    """
    # Call identification
    call_id: str
    
    # Clone status
    clone_status: str  # "processing", "completed", "failed"
    
    # Instructions
    greeting_audio: Optional[SpeechInstruction] = None
    hold_audio: Optional[AudioInstruction] = None
    status_poll: Optional[StatusPollInstruction] = None
    websocket: Optional[WebSocketInstruction] = None
    
    # Error handling
    error_message: Optional[str] = None
    should_hangup: bool = False
    
    def __post_init__(self):
        """Validate call instructions."""
        if not self.call_id:
            raise ValueError("Call ID cannot be empty")
        
        valid_statuses = ["processing", "completed", "failed"]
        if self.clone_status not in valid_statuses:
            raise ValueError(f"Clone status must be one of {valid_statuses}")
        
        # If failed, should have error message or hangup
        if self.clone_status == "failed" and not self.error_message and not self.should_hangup:
            raise ValueError("Failed status must have error message or hangup flag")
        
        # If completed, should have WebSocket instruction
        if self.clone_status == "completed" and not self.websocket:
            raise ValueError("Completed status must have WebSocket instruction")
