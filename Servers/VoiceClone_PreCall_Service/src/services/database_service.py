"""
Database service for Voice Clone Pre-Call Service.

Handles all database operations using async SQLAlchemy.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, update, and_
from sqlalchemy.exc import SQLAlchemyError

from src.models.database_models import (
    Base,
    CallerVoiceMapping,
    VoiceCloneCache,
    CallLog,
    VoiceCloneLog,
    CloneReadyEvent,
    CloneFailedEvent,
    CloneTransferEvent
)
from src.utils.exceptions import DatabaseException
from src.config import get_settings

logger = logging.getLogger(__name__)


class DatabaseService:
    """Manages database connections and operations."""
    
    def __init__(self):
        """Initialize database service."""
        self.engine = None
        self.async_session_maker = None
    
    async def init(self) -> None:
        """Initialize database engine and create tables."""
        try:
            settings = get_settings()
            self.engine = create_async_engine(
                settings.database_url,
                echo=False,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20
            )
            
            # Create session maker
            self.async_session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create tables if they don't exist
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise DatabaseException(f"Database initialization failed: {e}")
    
    async def close(self) -> None:
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")
    
    def get_session(self) -> AsyncSession:
        """Get a new database session."""
        if not self.async_session_maker:
            raise DatabaseException("Database not initialized")
        return self.async_session_maker()
    
    # CallerVoiceMapping operations
    async def get_voice_sample_for_caller(self, caller_id: str) -> Optional[str]:
        """
        Get voice sample path for caller.
        
        Args:
            caller_id: Caller phone number
            
        Returns:
            Voice sample URL/path or None if not found
        """
        try:
            async with self.get_session() as session:
                result = await session.execute(
                    select(CallerVoiceMapping).where(
                        and_(
                            CallerVoiceMapping.caller_id == caller_id,
                            CallerVoiceMapping.deleted_at.is_(None)
                        )
                    )
                )
                mapping = result.scalar_one_or_none()
                return mapping.voice_sample_url if mapping else None
                
        except SQLAlchemyError as e:
            logger.error(f"Database error getting voice sample for {caller_id}: {e}")
            raise DatabaseException(f"Failed to get voice sample: {e}")
    
    async def save_caller_voice_mapping(
        self,
        caller_id: str,
        voice_sample_url: str,
        voice_name: str,
        account_id: Optional[str] = None,
    ) -> CallerVoiceMapping:
        """
        Save or update caller voice mapping.
        
        Args:
            caller_id: Caller phone number
            voice_sample_url: Voice sample URL/path
            voice_name: Voice name
            account_id: Optional account ID for multi-tenancy
            
        Returns:
            CallerVoiceMapping instance
        """
        try:
            async with self.get_session() as session:
                # Check if mapping exists
                result = await session.execute(
                    select(CallerVoiceMapping).where(
                        CallerVoiceMapping.caller_id == caller_id
                    )
                )
                mapping = result.scalar_one_or_none()
                
                if mapping:
                    # Update existing
                    mapping.voice_sample_url = voice_sample_url
                    mapping.voice_name = voice_name
                    mapping.account_id = account_id
                    mapping.updated_at = datetime.utcnow()
                    mapping.deleted_at = None  # Undelete if previously deleted
                else:
                    # Create new
                    mapping = CallerVoiceMapping(
                        caller_id=caller_id,
                        voice_sample_url=voice_sample_url,
                        voice_name=voice_name,
                        account_id=account_id
                    )
                    session.add(mapping)
                
                await session.commit()
                await session.refresh(mapping)
                return mapping
                
        except SQLAlchemyError as e:
            logger.error(f"Database error saving voice mapping for {caller_id}: {e}")
            raise DatabaseException(f"Failed to save voice mapping: {e}")
    
    # VoiceCloneCache operations
    async def get_cached_clone(self, caller_id: str) -> Optional[VoiceCloneCache]:
        """
        Get cached clone if TTL not expired.
        
        Args:
            caller_id: Caller phone number
            
        Returns:
            VoiceCloneCache instance or None
        """
        try:
            async with self.get_session() as session:
                now = datetime.utcnow()
                result = await session.execute(
                    select(VoiceCloneCache).where(
                        and_(
                            VoiceCloneCache.caller_id == caller_id,
                            VoiceCloneCache.ttl_expires_at > now,
                            VoiceCloneCache.deleted_at.is_(None)
                        )
                    ).order_by(VoiceCloneCache.created_at.desc())
                )
                return result.scalar_one_or_none()
                
        except SQLAlchemyError as e:
            logger.error(f"Database error getting cached clone for {caller_id}: {e}")
            raise DatabaseException(f"Failed to get cached clone: {e}")
    
    async def save_clone_cache(
        self,
        caller_id: str,
        cloned_voice_id: str,
        ttl_seconds: int,
    ) -> VoiceCloneCache:
        """
        Save clone to cache table.
        
        Args:
            caller_id: Caller phone number
            cloned_voice_id: ElevenLabs voice ID
            ttl_seconds: TTL in seconds
            
        Returns:
            VoiceCloneCache instance
        """
        try:
            async with self.get_session() as session:
                now = datetime.utcnow()
                expires_at = now + timedelta(seconds=ttl_seconds)
                
                cache_entry = VoiceCloneCache(
                    caller_id=caller_id,
                    cloned_voice_id=cloned_voice_id,
                    ttl_expires_at=expires_at,
                    last_used_at=now
                )
                
                session.add(cache_entry)
                await session.commit()
                await session.refresh(cache_entry)
                return cache_entry
                
        except SQLAlchemyError as e:
            logger.error(f"Database error saving clone cache for {caller_id}: {e}")
            raise DatabaseException(f"Failed to save clone cache: {e}")
    
    async def increment_clone_reuse(self, cloned_voice_id: str) -> None:
        """
        Increment reuse counter for analytics.
        
        Args:
            cloned_voice_id: ElevenLabs voice ID
        """
        try:
            async with self.get_session() as session:
                await session.execute(
                    update(VoiceCloneCache)
                    .where(VoiceCloneCache.cloned_voice_id == cloned_voice_id)
                    .values(
                        reuse_count=VoiceCloneCache.reuse_count + 1,
                        last_used_at=datetime.utcnow()
                    )
                )
                await session.commit()
                
        except SQLAlchemyError as e:
            logger.error(f"Database error incrementing clone reuse for {cloned_voice_id}: {e}")
            # Don't raise exception for analytics operation
    
    # CallLog operations
    async def log_call_initiated(
        self,
        call_id: str,
        threecx_call_id: str,
        caller_id: str,
        cloned_voice_id: str,
    ) -> CallLog:
        """
        Log call initiation.
        
        Args:
            call_id: ElevenLabs call ID
            threecx_call_id: 3CX call ID
            caller_id: Caller phone number
            cloned_voice_id: ElevenLabs voice ID
            
        Returns:
            CallLog instance
        """
        try:
            async with self.get_session() as session:
                call_log = CallLog(
                    call_id=call_id,
                    threecx_call_id=threecx_call_id,
                    caller_id=caller_id,
                    cloned_voice_id=cloned_voice_id,
                    status="initiated"
                )
                
                session.add(call_log)
                await session.commit()
                await session.refresh(call_log)
                return call_log
                
        except SQLAlchemyError as e:
            logger.error(f"Database error logging call initiation: {e}")
            raise DatabaseException(f"Failed to log call initiation: {e}")
    
    async def log_call_completed(
        self,
        call_id: str,
        duration_seconds: int,
        transcript: Optional[str] = None,
        status: str = "completed",
    ) -> CallLog:
        """
        Update call log with completion details.
        
        Args:
            call_id: ElevenLabs call ID
            duration_seconds: Call duration
            transcript: Call transcript
            status: Call status
            
        Returns:
            Updated CallLog instance
        """
        try:
            async with self.get_session() as session:
                result = await session.execute(
                    select(CallLog).where(CallLog.call_id == call_id)
                )
                call_log = result.scalar_one_or_none()
                
                if call_log:
                    call_log.call_ended_at = datetime.utcnow()
                    call_log.duration_seconds = duration_seconds
                    call_log.transcript = transcript
                    call_log.status = status
                    call_log.updated_at = datetime.utcnow()
                    
                    await session.commit()
                    await session.refresh(call_log)
                    return call_log
                else:
                    raise DatabaseException(f"Call log not found for call_id: {call_id}")
                    
        except SQLAlchemyError as e:
            logger.error(f"Database error logging call completion: {e}")
            raise DatabaseException(f"Failed to log call completion: {e}")
    
    # VoiceCloneLog operations
    async def log_clone_creation(
        self,
        caller_id: str,
        cloned_voice_id: str,
        api_response_time_ms: int,
        sample_file_size_bytes: int,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> VoiceCloneLog:
        """
        Log voice clone creation event.
        
        Args:
            caller_id: Caller phone number
            cloned_voice_id: ElevenLabs voice ID
            api_response_time_ms: API response time in milliseconds
            sample_file_size_bytes: Voice sample file size
            status: Creation status
            error_message: Error message if failed
            
        Returns:
            VoiceCloneLog instance
        """
        try:
            async with self.get_session() as session:
                clone_log = VoiceCloneLog(
                    caller_id=caller_id,
                    cloned_voice_id=cloned_voice_id,
                    api_response_time_ms=api_response_time_ms,
                    sample_file_size_bytes=sample_file_size_bytes,
                    status=status,
                    error_message=error_message
                )
                
                session.add(clone_log)
                await session.commit()
                await session.refresh(clone_log)
                return clone_log
                
        except SQLAlchemyError as e:
            logger.error(f"Database error logging clone creation: {e}")
            # Don't raise exception for logging operation
            logger.warning(f"Clone creation logged to console only: {caller_id}")
    
    # CloneReadyEvent operations
    async def log_clone_ready(
        self,
        caller_id: str,
        greeting_call_id: str,
        cloned_voice_id: str,
        clone_duration_ms: int,
    ) -> CloneReadyEvent:
        """Log clone ready event."""
        try:
            async with self.get_session() as session:
                event = CloneReadyEvent(
                    caller_id=caller_id,
                    greeting_call_id=greeting_call_id,
                    cloned_voice_id=cloned_voice_id,
                    clone_duration_ms=clone_duration_ms
                )
                
                session.add(event)
                await session.commit()
                await session.refresh(event)
                return event
                
        except SQLAlchemyError as e:
            logger.error(f"Database error logging clone ready event: {e}")
    
    # CloneFailedEvent operations
    async def log_clone_failed(
        self,
        caller_id: str,
        greeting_call_id: str,
        error_message: str,
    ) -> CloneFailedEvent:
        """Log clone failed event."""
        try:
            async with self.get_session() as session:
                event = CloneFailedEvent(
                    caller_id=caller_id,
                    greeting_call_id=greeting_call_id,
                    error_message=error_message
                )
                
                session.add(event)
                await session.commit()
                await session.refresh(event)
                return event
                
        except SQLAlchemyError as e:
            logger.error(f"Database error logging clone failed event: {e}")
    
    # CloneTransferEvent operations
    async def log_clone_transfer(
        self,
        greeting_call_id: str,
        agent_call_id: str,
        cloned_voice_id: str,
    ) -> CloneTransferEvent:
        """Log clone transfer event."""
        try:
            async with self.get_session() as session:
                event = CloneTransferEvent(
                    greeting_call_id=greeting_call_id,
                    agent_call_id=agent_call_id,
                    cloned_voice_id=cloned_voice_id
                )
                
                session.add(event)
                await session.commit()
                await session.refresh(event)
                return event
                
        except SQLAlchemyError as e:
            logger.error(f"Database error logging clone transfer event: {e}")
    
    async def health_check(self) -> bool:
        """
        Check database connectivity.
        
        Returns:
            True if database is accessible, False otherwise
        """
        try:
            async with self.get_session() as session:
                await session.execute(select(1))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
