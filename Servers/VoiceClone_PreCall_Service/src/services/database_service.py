"""
Database service for VoiceClone Pre-Call Service.

Provides async CRUD operations for all database models.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from src.config import get_settings
from src.models.database_models import (
    Base,
    CallerVoiceMapping,
    VoiceCloneCache,
    CallLog,
    VoiceCloneLog,
    CloneReadyEvent,
    CloneFailedEvent,
    CloneTransferEvent,
)
from src.utils.logger import get_logger
from src.utils.exceptions import DatabaseException

logger = get_logger(__name__)


class DatabaseService:
    """
    Async database service for PostgreSQL operations.
    
    Manages all database interactions using async SQLAlchemy.
    """
    
    def __init__(self):
        """Initialize database service."""
        self.settings = get_settings()
        self.engine = None
        self.async_session_maker = None
    
    async def init(self) -> None:
        """Initialize database engine and create tables."""
        try:
            self.engine = create_async_engine(
                self.settings.database_url,
                echo=self.settings.log_level == "DEBUG",
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
            )
            
            self.async_session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create all tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise DatabaseException(f"Database initialization failed: {str(e)}")
    
    async def close(self) -> None:
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")
    
    async def get_session(self) -> AsyncSession:
        """Get async database session."""
        if not self.async_session_maker:
            await self.init()
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
            async with await self.get_session() as session:
                stmt = select(CallerVoiceMapping).where(
                    CallerVoiceMapping.caller_id == caller_id,
                    CallerVoiceMapping.deleted_at.is_(None)
                )
                result = await session.execute(stmt)
                mapping = result.scalar_one_or_none()
                
                if mapping:
                    logger.info(f"Found voice sample for caller {caller_id}: {mapping.voice_sample_url}")
                    return mapping.voice_sample_url
                
                logger.warning(f"No voice sample found for caller {caller_id}")
                return None
                
        except SQLAlchemyError as e:
            logger.error(f"Database error getting voice sample: {e}")
            raise DatabaseException(f"Failed to get voice sample: {str(e)}")
    
    async def save_caller_voice_mapping(
        self,
        caller_id: str,
        voice_sample_url: str,
        voice_name: str,
        account_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> CallerVoiceMapping:
        """
        Save or update caller → voice mapping.
        
        Args:
            caller_id: Caller phone number
            voice_sample_url: Path to voice sample
            voice_name: Display name for voice
            account_id: Optional account ID
            description: Optional description
            
        Returns:
            Created/updated CallerVoiceMapping
        """
        try:
            async with await self.get_session() as session:
                # Check if mapping exists
                stmt = select(CallerVoiceMapping).where(
                    CallerVoiceMapping.caller_id == caller_id,
                    CallerVoiceMapping.deleted_at.is_(None)
                )
                result = await session.execute(stmt)
                mapping = result.scalar_one_or_none()
                
                if mapping:
                    # Update existing
                    mapping.voice_sample_url = voice_sample_url
                    mapping.voice_name = voice_name
                    mapping.account_id = account_id
                    mapping.description = description
                    mapping.updated_at = datetime.utcnow()
                    logger.info(f"Updated voice mapping for caller {caller_id}")
                else:
                    # Create new
                    mapping = CallerVoiceMapping(
                        caller_id=caller_id,
                        voice_sample_url=voice_sample_url,
                        voice_name=voice_name,
                        account_id=account_id,
                        description=description,
                    )
                    session.add(mapping)
                    logger.info(f"Created voice mapping for caller {caller_id}")
                
                await session.commit()
                await session.refresh(mapping)
                return mapping
                
        except SQLAlchemyError as e:
            logger.error(f"Database error saving voice mapping: {e}")
            raise DatabaseException(f"Failed to save voice mapping: {str(e)}")
    
    # VoiceCloneCache operations
    
    async def get_cached_clone(self, caller_id: str) -> Optional[VoiceCloneCache]:
        """
        Get cached clone if TTL not expired.
        
        Args:
            caller_id: Caller phone number
            
        Returns:
            VoiceCloneCache or None if not found/expired
        """
        try:
            async with await self.get_session() as session:
                now = datetime.utcnow()
                stmt = select(VoiceCloneCache).where(
                    VoiceCloneCache.caller_id == caller_id,
                    VoiceCloneCache.ttl_expires_at > now,
                    VoiceCloneCache.deleted_at.is_(None)
                )
                result = await session.execute(stmt)
                cache_entry = result.scalar_one_or_none()
                
                if cache_entry:
                    logger.info(f"Cache hit for caller {caller_id}: {cache_entry.cloned_voice_id}")
                    return cache_entry
                
                logger.info(f"Cache miss for caller {caller_id}")
                return None
                
        except SQLAlchemyError as e:
            logger.error(f"Database error getting cached clone: {e}")
            raise DatabaseException(f"Failed to get cached clone: {str(e)}")
    
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
            ttl_seconds: Cache TTL in seconds
            
        Returns:
            Created VoiceCloneCache
        """
        try:
            async with await self.get_session() as session:
                now = datetime.utcnow()
                expires_at = now + timedelta(seconds=ttl_seconds)
                
                cache_entry = VoiceCloneCache(
                    caller_id=caller_id,
                    cloned_voice_id=cloned_voice_id,
                    ttl_expires_at=expires_at,
                    last_used_at=now,
                )
                session.add(cache_entry)
                await session.commit()
                await session.refresh(cache_entry)
                
                logger.info(f"Cached clone for caller {caller_id}, expires at {expires_at}")
                return cache_entry
                
        except SQLAlchemyError as e:
            logger.error(f"Database error saving clone cache: {e}")
            raise DatabaseException(f"Failed to save clone cache: {str(e)}")
    
    async def increment_clone_reuse(self, cloned_voice_id: str) -> None:
        """
        Increment reuse counter for analytics.
        
        Args:
            cloned_voice_id: ElevenLabs voice ID
        """
        try:
            async with await self.get_session() as session:
                stmt = (
                    update(VoiceCloneCache)
                    .where(VoiceCloneCache.cloned_voice_id == cloned_voice_id)
                    .values(
                        reuse_count=VoiceCloneCache.reuse_count + 1,
                        last_used_at=datetime.utcnow()
                    )
                )
                await session.execute(stmt)
                await session.commit()
                logger.debug(f"Incremented reuse count for voice {cloned_voice_id}")
                
        except SQLAlchemyError as e:
            logger.error(f"Database error incrementing reuse: {e}")
            # Don't raise - this is non-critical
    
    async def invalidate_clone_cache(self, caller_id: str) -> bool:
        """
        Remove clone from cache (manual invalidation).
        
        Args:
            caller_id: Caller phone number
            
        Returns:
            True if cache was invalidated
        """
        try:
            async with await self.get_session() as session:
                stmt = (
                    update(VoiceCloneCache)
                    .where(
                        VoiceCloneCache.caller_id == caller_id,
                        VoiceCloneCache.deleted_at.is_(None)
                    )
                    .values(deleted_at=datetime.utcnow())
                )
                result = await session.execute(stmt)
                await session.commit()
                
                invalidated = result.rowcount > 0
                if invalidated:
                    logger.info(f"Invalidated cache for caller {caller_id}")
                return invalidated
                
        except SQLAlchemyError as e:
            logger.error(f"Database error invalidating cache: {e}")
            raise DatabaseException(f"Failed to invalidate cache: {str(e)}")
    
    async def cleanup_expired_clones(self) -> int:
        """
        Remove expired clones from cache.
        
        Returns:
            Number of clones cleaned up
        """
        try:
            async with await self.get_session() as session:
                now = datetime.utcnow()
                stmt = (
                    update(VoiceCloneCache)
                    .where(
                        VoiceCloneCache.ttl_expires_at <= now,
                        VoiceCloneCache.deleted_at.is_(None)
                    )
                    .values(deleted_at=now)
                )
                result = await session.execute(stmt)
                await session.commit()
                
                count = result.rowcount
                if count > 0:
                    logger.info(f"Cleaned up {count} expired cache entries")
                return count
                
        except SQLAlchemyError as e:
            logger.error(f"Database error cleaning up cache: {e}")
            raise DatabaseException(f"Failed to cleanup cache: {str(e)}")
    
    # CallLog operations
    
    async def log_call_initiated(
        self,
        call_id: str,
        call_sid: str,
        caller_id: str,
        cloned_voice_id: str,
    ) -> CallLog:
        """
        Log call initiation.
        
        Args:
            call_id: ElevenLabs call ID or Twilio call SID
            call_sid: Twilio call SID
            caller_id: Caller phone number
            cloned_voice_id: Voice ID used
            
        Returns:
            Created CallLog
        """
        try:
            async with await self.get_session() as session:
                call_log = CallLog(
                    call_id=call_id,
                    call_sid=call_sid,
                    caller_id=caller_id,
                    cloned_voice_id=cloned_voice_id,
                    status="initiated",
                )
                session.add(call_log)
                await session.commit()
                await session.refresh(call_log)
                
                logger.info(f"Logged call initiation: {call_id}")
                return call_log
                
        except SQLAlchemyError as e:
            logger.error(f"Database error logging call: {e}")
            raise DatabaseException(f"Failed to log call: {str(e)}")
    
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
            transcript: Optional transcript
            status: Call status
            
        Returns:
            Updated CallLog
        """
        try:
            async with await self.get_session() as session:
                stmt = select(CallLog).where(CallLog.call_id == call_id)
                result = await session.execute(stmt)
                call_log = result.scalar_one_or_none()
                
                if call_log:
                    call_log.call_ended_at = datetime.utcnow()
                    call_log.duration_seconds = duration_seconds
                    call_log.transcript = transcript
                    call_log.status = status
                    call_log.updated_at = datetime.utcnow()
                    
                    await session.commit()
                    await session.refresh(call_log)
                    logger.info(f"Updated call log: {call_id} ({status})")
                    return call_log
                else:
                    logger.warning(f"Call log not found: {call_id}")
                    raise DatabaseException(f"Call log not found: {call_id}")
                
        except SQLAlchemyError as e:
            logger.error(f"Database error updating call log: {e}")
            raise DatabaseException(f"Failed to update call log: {str(e)}")
    
    async def get_call_by_id(self, call_id: str) -> Optional[CallLog]:
        """Retrieve call record."""
        try:
            async with await self.get_session() as session:
                stmt = select(CallLog).where(CallLog.call_id == call_id)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
                
        except SQLAlchemyError as e:
            logger.error(f"Database error getting call: {e}")
            raise DatabaseException(f"Failed to get call: {str(e)}")
    
    async def get_calls_for_caller(
        self,
        caller_id: str,
        limit: int = 10,
        offset: int = 0,
    ) -> List[CallLog]:
        """Get recent calls for caller."""
        try:
            async with await self.get_session() as session:
                stmt = (
                    select(CallLog)
                    .where(CallLog.caller_id == caller_id)
                    .order_by(CallLog.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
                result = await session.execute(stmt)
                return list(result.scalars().all())
                
        except SQLAlchemyError as e:
            logger.error(f"Database error getting calls: {e}")
            raise DatabaseException(f"Failed to get calls: {str(e)}")
    
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
        """Log voice clone creation event."""
        try:
            async with await self.get_session() as session:
                clone_log = VoiceCloneLog(
                    caller_id=caller_id,
                    cloned_voice_id=cloned_voice_id,
                    api_response_time_ms=api_response_time_ms,
                    sample_file_size_bytes=sample_file_size_bytes,
                    status=status,
                    error_message=error_message,
                )
                session.add(clone_log)
                await session.commit()
                await session.refresh(clone_log)
                
                logger.info(f"Logged clone creation: {cloned_voice_id} ({status})")
                return clone_log
                
        except SQLAlchemyError as e:
            logger.error(f"Database error logging clone: {e}")
            raise DatabaseException(f"Failed to log clone: {str(e)}")
    
    # Event logging
    
    async def log_clone_ready_event(
        self,
        caller_id: str,
        greeting_call_id: str,
        cloned_voice_id: str,
        clone_duration_ms: int,
    ) -> CloneReadyEvent:
        """Log clone ready event."""
        try:
            async with await self.get_session() as session:
                event = CloneReadyEvent(
                    caller_id=caller_id,
                    greeting_call_id=greeting_call_id,
                    cloned_voice_id=cloned_voice_id,
                    clone_duration_ms=clone_duration_ms,
                )
                session.add(event)
                await session.commit()
                await session.refresh(event)
                return event
                
        except SQLAlchemyError as e:
            logger.error(f"Database error logging ready event: {e}")
            raise DatabaseException(f"Failed to log ready event: {str(e)}")
    
    async def log_clone_failed_event(
        self,
        caller_id: str,
        greeting_call_id: str,
        error_message: str,
    ) -> CloneFailedEvent:
        """Log clone failed event."""
        try:
            async with await self.get_session() as session:
                event = CloneFailedEvent(
                    caller_id=caller_id,
                    greeting_call_id=greeting_call_id,
                    error_message=error_message,
                )
                session.add(event)
                await session.commit()
                await session.refresh(event)
                return event
                
        except SQLAlchemyError as e:
            logger.error(f"Database error logging failed event: {e}")
            raise DatabaseException(f"Failed to log failed event: {str(e)}")
    
    async def log_clone_transfer_event(
        self,
        greeting_call_id: str,
        agent_call_id: str,
        cloned_voice_id: str,
    ) -> CloneTransferEvent:
        """Log clone transfer event."""
        try:
            async with await self.get_session() as session:
                event = CloneTransferEvent(
                    greeting_call_id=greeting_call_id,
                    agent_call_id=agent_call_id,
                    cloned_voice_id=cloned_voice_id,
                )
                session.add(event)
                await session.commit()
                await session.refresh(event)
                return event
                
        except SQLAlchemyError as e:
            logger.error(f"Database error logging transfer event: {e}")
            raise DatabaseException(f"Failed to log transfer event: {str(e)}")
    
    # Statistics
    
    async def get_clone_statistics(self) -> Dict[str, Any]:
        """Get aggregated statistics."""
        try:
            async with await self.get_session() as session:
                # Total clones created
                total_stmt = select(func.count()).select_from(VoiceCloneLog)
                total_result = await session.execute(total_stmt)
                total_clones = total_result.scalar() or 0
                
                # Cache hits (reuse_count > 1)
                cache_stmt = select(func.sum(VoiceCloneCache.reuse_count - 1)).where(
                    VoiceCloneCache.deleted_at.is_(None)
                )
                cache_result = await session.execute(cache_stmt)
                cache_hits = cache_result.scalar() or 0
                
                # Cache misses (total clones created)
                cache_misses = total_clones
                
                # Hit rate
                total_requests = cache_hits + cache_misses
                hit_rate = cache_hits / total_requests if total_requests > 0 else 0.0
                
                # Average creation time
                avg_stmt = select(func.avg(VoiceCloneLog.api_response_time_ms))
                avg_result = await session.execute(avg_stmt)
                avg_time = avg_result.scalar() or 0.0
                
                # Total calls
                calls_stmt = select(func.count()).select_from(CallLog)
                calls_result = await session.execute(calls_stmt)
                total_calls = calls_result.scalar() or 0
                
                return {
                    "total_clones": total_clones,
                    "cache_hits": cache_hits,
                    "cache_misses": cache_misses,
                    "hit_rate": float(hit_rate),
                    "avg_creation_time_ms": float(avg_time),
                    "total_calls": total_calls,
                }
                
        except SQLAlchemyError as e:
            logger.error(f"Database error getting statistics: {e}")
            raise DatabaseException(f"Failed to get statistics: {str(e)}")
    
    async def health_check(self) -> bool:
        """Test database connectivity."""
        try:
            async with await self.get_session() as session:
                await session.execute(select(1))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    # Twilio-specific methods
    
    async def save_call_record(
        self,
        call_sid: str,
        caller_number: str,
        twilio_number: str,
        status: str = "processing",
    ) -> None:
        """
        Save initial call record for Twilio call.
        
        Args:
            call_sid: Twilio call SID
            caller_number: Caller phone number
            twilio_number: Twilio number called
            status: Initial status (processing, completed, failed)
        """
        try:
            async with await self.get_session() as session:
                call_log = CallLog(
                    call_id=call_sid,
                    call_sid=call_sid,
                    caller_id=caller_number,
                    cloned_voice_id="pending",
                    status=status,
                    call_started_at=datetime.utcnow(),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                
                session.add(call_log)
                await session.commit()
                
                logger.info(f"Saved call record for {call_sid}")
                
        except SQLAlchemyError as e:
            logger.error(f"Database error saving call record: {e}")
            raise DatabaseException(f"Failed to save call record: {str(e)}")
    
    async def update_clone_status(
        self,
        call_sid: str,
        status: str,
        voice_clone_id: Optional[str] = None,
        clone_duration_ms: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Update clone status for a call.
        
        Args:
            call_sid: Twilio call SID
            status: New status (processing, completed, failed)
            voice_clone_id: Cloned voice ID (if completed)
            clone_duration_ms: Clone duration in milliseconds
            error: Error message (if failed)
        """
        try:
            async with await self.get_session() as session:
                stmt = (
                    update(CallLog)
                    .where(CallLog.call_id == call_sid)
                    .values(
                        status=status,
                        updated_at=datetime.utcnow(),
                    )
                )
                
                # Add optional fields if provided
                if voice_clone_id:
                    stmt = stmt.values(cloned_voice_id=voice_clone_id)
                
                if error:
                    stmt = stmt.values(
                        extra_data=func.jsonb_set(
                            CallLog.extra_data,
                            '{error}',
                            f'"{error}"',
                            True
                        )
                    )
                
                await session.execute(stmt)
                await session.commit()
                
                logger.info(f"Updated clone status for {call_sid}: {status}")
                
        except SQLAlchemyError as e:
            logger.error(f"Database error updating clone status: {e}")
            raise DatabaseException(f"Failed to update clone status: {str(e)}")
    
    async def get_clone_status(self, call_sid: str) -> Optional[Dict[str, Any]]:
        """
        Get clone status for a call.
        
        Args:
            call_sid: Twilio call SID
            
        Returns:
            Dictionary with status, voice_clone_id, error
        """
        try:
            async with await self.get_session() as session:
                stmt = select(CallLog).where(CallLog.call_id == call_sid)
                result = await session.execute(stmt)
                call_log = result.scalar_one_or_none()
                
                if not call_log:
                    return None
                
                return {
                    "status": call_log.status,
                    "voice_clone_id": call_log.cloned_voice_id,
                    "error": call_log.extra_data.get("error") if call_log.extra_data else None,
                }
                
        except SQLAlchemyError as e:
            logger.error(f"Database error getting clone status: {e}")
            return None
