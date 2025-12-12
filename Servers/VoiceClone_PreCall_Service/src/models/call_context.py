"""
Call context data model for protocol-agnostic call information.

Represents the context of a call regardless of protocol (Twilio or SIP).
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class CallContext:
    """
    Protocol-agnostic call context.
    
    Contains all information about a call needed by the business logic,
    abstracted from the specific protocol (Twilio/SIP).
    """
    # Call identification
    call_id: str  # Twilio CallSid or SIP call ID
    session_id: Optional[str] = None  # Session identifier for tracking
    
    # Caller information
    caller_number: str = ""  # Caller phone number (E.164 format)
    recipient_number: str = ""  # Number that was called (E.164 format)
    
    # Call status
    status: str = "initiated"  # initiated, ringing, in-progress, completed, failed
    
    # Protocol information
    protocol: str = "twilio"  # "twilio" or "sip"
    
    # Timestamps
    initiated_at: Optional[datetime] = None
    answered_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate call context."""
        if not self.call_id:
            raise ValueError("Call ID cannot be empty")
        
        valid_protocols = ["twilio", "sip"]
        if self.protocol not in valid_protocols:
            raise ValueError(f"Protocol must be one of {valid_protocols}")
        
        valid_statuses = ["initiated", "ringing", "in-progress", "completed", "failed"]
        if self.status not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        
        # Auto-set initiated_at if not provided
        if self.initiated_at is None:
            self.initiated_at = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for logging/serialization."""
        return {
            "call_id": self.call_id,
            "session_id": self.session_id,
            "caller_number": self.caller_number,
            "recipient_number": self.recipient_number,
            "status": self.status,
            "protocol": self.protocol,
            "initiated_at": self.initiated_at.isoformat() if self.initiated_at else None,
            "answered_at": self.answered_at.isoformat() if self.answered_at else None,
        }
