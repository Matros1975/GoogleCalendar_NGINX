"""
SQLAlchemy database models for Voice Clone Pre-Call Service.

All models use async support via AsyncAttrs mixin and include:
- UUID primary keys
- created_at/updated_at timestamps
- Soft delete support with deleted_at
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Integer, DateTime, Text, Boolean, JSON,
    Index, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all database models with async support."""
    pass


class CallerVoiceMapping(Base):
    """
    Maps caller IDs to voice sample files.
    
    Stores the relationship between phone numbers and their associated
    voice samples for cloning.
    """
    __tablename__ = "caller_voice_mapping"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    caller_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    voice_sample_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    voice_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    account_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    __table_args__ = (
        Index('idx_caller_voice_mapping_caller_id', 'caller_id'),
        Index('idx_caller_voice_mapping_account_id', 'account_id'),
        Index('idx_caller_voice_mapping_created_at', 'created_at'),
    )


class VoiceCloneCache(Base):
    """
    Caches created voice clones with TTL.
    
    Stores voice clone IDs with expiration times to avoid
    recreating clones unnecessarily.
    """
    __tablename__ = "voice_clone_cache"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    caller_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cloned_voice_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    clone_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    ttl_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    reuse_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    __table_args__ = (
        Index('idx_voice_clone_cache_caller_id', 'caller_id'),
        Index('idx_voice_clone_cache_cloned_voice_id', 'cloned_voice_id'),
        Index('idx_voice_clone_cache_ttl_expires_at', 'ttl_expires_at'),
    )


class CallLog(Base):
    """
    Logs all voice agent calls.
    
    Records complete call information including transcripts and metadata.
    """
    __tablename__ = "call_log"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    call_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    threecx_call_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    caller_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cloned_voice_id: Mapped[str] = mapped_column(String(255), nullable=False)
    call_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    call_ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    __table_args__ = (
        Index('idx_call_log_call_id', 'call_id', unique=True),
        Index('idx_call_log_caller_id', 'caller_id'),
        Index('idx_call_log_threecx_call_id', 'threecx_call_id'),
        Index('idx_call_log_status', 'status'),
        Index('idx_call_log_created_at', 'created_at'),
    )


class VoiceCloneLog(Base):
    """
    Logs voice clone creation events.
    
    Records performance metrics and success/failure of clone operations.
    """
    __tablename__ = "voice_clone_log"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    caller_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cloned_voice_id: Mapped[str] = mapped_column(String(255), nullable=False)
    clone_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    api_response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    sample_file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    __table_args__ = (
        Index('idx_voice_clone_log_caller_id', 'caller_id'),
        Index('idx_voice_clone_log_cloned_voice_id', 'cloned_voice_id'),
        Index('idx_voice_clone_log_status', 'status'),
    )


class CloneReadyEvent(Base):
    """
    Tracks when voice clones are ready for use.
    
    Records the completion time of async voice cloning operations.
    """
    __tablename__ = "clone_ready_events"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    caller_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    greeting_call_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cloned_voice_id: Mapped[str] = mapped_column(String(255), nullable=False)
    clone_duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    ready_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    __table_args__ = (
        Index('idx_clone_ready_events_caller_id', 'caller_id'),
        Index('idx_clone_ready_events_greeting_call_id', 'greeting_call_id'),
        Index('idx_clone_ready_events_ready_at', 'ready_at'),
    )


class CloneFailedEvent(Base):
    """
    Tracks failed voice clone attempts.
    
    Records errors during async voice cloning operations.
    """
    __tablename__ = "clone_failed_events"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    caller_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    greeting_call_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    failed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    __table_args__ = (
        Index('idx_clone_failed_events_caller_id', 'caller_id'),
        Index('idx_clone_failed_events_greeting_call_id', 'greeting_call_id'),
        Index('idx_clone_failed_events_failed_at', 'failed_at'),
    )


class CloneTransferEvent(Base):
    """
    Tracks automatic transfers from greeting to cloned voice.
    
    Records when and how calls transition to the cloned voice agent.
    """
    __tablename__ = "clone_transfer_events"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    greeting_call_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    agent_call_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cloned_voice_id: Mapped[str] = mapped_column(String(255), nullable=False)
    transferred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    __table_args__ = (
        Index('idx_clone_transfer_events_greeting_call_id', 'greeting_call_id'),
        Index('idx_clone_transfer_events_agent_call_id', 'agent_call_id'),
        Index('idx_clone_transfer_events_transferred_at', 'transferred_at'),
    )
