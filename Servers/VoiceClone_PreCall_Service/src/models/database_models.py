"""
Database models for VoiceClone Pre-Call Service.

SQLAlchemy ORM models with async support for PostgreSQL.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, Integer, Text, DateTime, Boolean, JSON,
    Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all database models with async support."""
    pass


class CallerVoiceMapping(Base):
    """
    Maps caller IDs to voice sample files.
    
    Stores the association between phone numbers and their voice samples
    for voice cloning.
    """
    
    __tablename__ = "caller_voice_mapping"
    
    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # Caller information
    caller_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Caller phone number (E.164 format)"
    )
    
    # Voice sample details
    voice_sample_url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
        comment="S3 URL or local file path to voice sample"
    )
    
    voice_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Display name for the cloned voice"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional description"
    )
    
    # Multi-tenancy support
    account_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Account ID for multi-tenant support"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    
    __table_args__ = (
        Index('ix_caller_voice_mapping_caller_id', 'caller_id'),
        Index('ix_caller_voice_mapping_account_id', 'account_id'),
        Index('ix_caller_voice_mapping_created_at', 'created_at'),
    )


class VoiceCloneCache(Base):
    """
    Caches cloned voices to avoid recreating them.
    
    Stores cloned voice IDs with TTL for performance optimization.
    """
    
    __tablename__ = "voice_clone_cache"
    
    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # Cache key
    caller_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Caller phone number"
    )
    
    # Cached value
    cloned_voice_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="ElevenLabs cloned voice ID"
    )
    
    # Cache metadata
    clone_created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="When the clone was created"
    )
    
    ttl_expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
        comment="When the cache entry expires"
    )
    
    # Usage tracking
    reuse_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Number of times this clone was reused"
    )
    
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    
    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    
    __table_args__ = (
        Index('ix_voice_clone_cache_caller_id', 'caller_id'),
        Index('ix_voice_clone_cache_cloned_voice_id', 'cloned_voice_id'),
        Index('ix_voice_clone_cache_ttl_expires_at', 'ttl_expires_at'),
    )


class CallLog(Base):
    """
    Logs all calls made through the voice agent.
    
    Stores call metadata, transcripts, and status for analytics.
    """
    
    __tablename__ = "call_log"
    
    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # Call identifiers
    call_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="ElevenLabs call ID"
    )
    
    threecx_call_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="3CX call ID"
    )
    
    caller_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Caller phone number"
    )
    
    # Voice clone used
    cloned_voice_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="ElevenLabs cloned voice ID"
    )
    
    # Call timing
    call_started_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    
    call_ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    
    duration_seconds: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    
    # Call content
    transcript: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Full call transcript"
    )
    
    # Call status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        default="initiated",
        comment="Call status: initiated, completed, failed"
    )
    
    # Additional metadata
    metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Extra call metadata (JSON)"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    __table_args__ = (
        Index('ix_call_log_call_id', 'call_id', unique=True),
        Index('ix_call_log_threecx_call_id', 'threecx_call_id'),
        Index('ix_call_log_caller_id', 'caller_id'),
        Index('ix_call_log_status', 'status'),
        Index('ix_call_log_created_at', 'created_at'),
        CheckConstraint(
            "status IN ('initiated', 'completed', 'failed')",
            name='call_log_status_check'
        ),
    )


class VoiceCloneLog(Base):
    """
    Audit log for voice clone operations.
    
    Records all voice clone creation attempts for monitoring and analytics.
    """
    
    __tablename__ = "voice_clone_log"
    
    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # Clone details
    caller_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Caller phone number"
    )
    
    cloned_voice_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="ElevenLabs cloned voice ID"
    )
    
    # Clone timing
    clone_created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    
    # Performance metrics
    api_response_time_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Clone creation latency in milliseconds"
    )
    
    sample_file_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Voice sample file size"
    )
    
    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Status: success, failed"
    )
    
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if failed"
    )
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    
    __table_args__ = (
        Index('ix_voice_clone_log_caller_id', 'caller_id'),
        Index('ix_voice_clone_log_cloned_voice_id', 'cloned_voice_id'),
        Index('ix_voice_clone_log_status', 'status'),
        CheckConstraint(
            "status IN ('success', 'failed')",
            name='voice_clone_log_status_check'
        ),
    )


class CloneReadyEvent(Base):
    """
    Tracks when voice clones are ready for use.
    
    Used for async greeting workflow timing analysis.
    """
    
    __tablename__ = "clone_ready_events"
    
    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # Event details
    caller_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    
    greeting_call_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Greeting call ID"
    )
    
    cloned_voice_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    
    # Performance tracking
    clone_duration_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Time taken to create clone"
    )
    
    # Timing
    ready_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    
    __table_args__ = (
        Index('ix_clone_ready_events_caller_id', 'caller_id'),
        Index('ix_clone_ready_events_greeting_call_id', 'greeting_call_id'),
        Index('ix_clone_ready_events_ready_at', 'ready_at'),
    )


class CloneFailedEvent(Base):
    """
    Tracks voice clone failures.
    
    Used for monitoring and alerting on clone failures.
    """
    
    __tablename__ = "clone_failed_events"
    
    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # Event details
    caller_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    
    greeting_call_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Greeting call ID"
    )
    
    # Error details
    error_message: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    
    # Timing
    failed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    
    __table_args__ = (
        Index('ix_clone_failed_events_caller_id', 'caller_id'),
        Index('ix_clone_failed_events_greeting_call_id', 'greeting_call_id'),
        Index('ix_clone_failed_events_failed_at', 'failed_at'),
    )


class CloneTransferEvent(Base):
    """
    Tracks handoff from greeting to voice agent.
    
    Records when calls transition from greeting to cloned voice agent.
    """
    
    __tablename__ = "clone_transfer_events"
    
    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # Transfer details
    greeting_call_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Original greeting call ID"
    )
    
    agent_call_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="New voice agent call ID"
    )
    
    cloned_voice_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    
    # Timing
    transferred_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    
    __table_args__ = (
        Index('ix_clone_transfer_events_greeting_call_id', 'greeting_call_id'),
        Index('ix_clone_transfer_events_agent_call_id', 'agent_call_id'),
        Index('ix_clone_transfer_events_transferred_at', 'transferred_at'),
    )
