"""
Voice cloning service with caching orchestration.
"""

import time
from typing import Optional

from src.services.database_service import DatabaseService
from src.services.elevenlabs_client import ElevenLabsService
from src.services.storage_service import StorageService
from src.config import get_settings
from src.utils.logger import get_logger
from src.utils.exceptions import (
    VoiceCloneException,
    VoiceCloneTimeoutException,
    CallerNotFoundException,
    VoiceSampleNotFoundException,
)

logger = get_logger(__name__)


class VoiceCloneService:
    """
    Orchestrates voice cloning workflow with database caching.
    """
    
    def __init__(
        self,
        db_service: DatabaseService,
        elevenlabs_service: ElevenLabsService,
        storage_service: StorageService,
    ):
        """
        Initialize voice clone service.
        
        Args:
            db_service: Database service
            elevenlabs_service: ElevenLabs API client
            storage_service: Storage service
        """
        self.db = db_service
        self.elevenlabs = elevenlabs_service
        self.storage = storage_service
        self.settings = get_settings()
    
    async def get_or_create_clone(
        self,
        caller_id: str,
        voice_sample_path: Optional[str] = None,
    ) -> str:
        """
        Get cached clone or create new one.
        
        Args:
            caller_id: Caller phone number
            voice_sample_path: Optional override voice sample path
            
        Returns:
            cloned_voice_id: ElevenLabs voice ID
            
        Raises:
            CallerNotFoundException: If no voice sample found for caller
            VoiceCloneException: If clone creation fails
        """
        try:
            # Step 1: Check cache
            cached_clone = await self.db.get_cached_clone(caller_id)
            if cached_clone:
                logger.info(f"Using cached clone for caller {caller_id}: {cached_clone.cloned_voice_id}")
                await self.db.increment_clone_reuse(cached_clone.cloned_voice_id)
                return cached_clone.cloned_voice_id
            
            # Step 2: Get voice sample path
            if not voice_sample_path:
                voice_sample_path = await self.db.get_voice_sample_for_caller(caller_id)
                if not voice_sample_path:
                    logger.error(f"No voice sample found for caller {caller_id}")
                    raise CallerNotFoundException(f"No voice sample for caller {caller_id}")
            
            # Step 3: Download voice sample
            logger.info(f"Downloading voice sample for caller {caller_id}: {voice_sample_path}")
            voice_sample_data = await self.storage.download_voice_sample(voice_sample_path)
            
            if not self.storage.validate_voice_sample(voice_sample_data):
                raise VoiceCloneException("Invalid voice sample file")
            
            file_size = len(voice_sample_data)
            
            # Step 4: Create voice clone
            start_time = time.time()
            logger.info(f"Creating voice clone for caller {caller_id}")
            
            voice_name = f"Clone_{caller_id}"
            cloned_voice_id = await self.elevenlabs.create_voice_clone(
                voice_sample_data=voice_sample_data,
                voice_name=voice_name,
                description=f"Cloned voice for {caller_id}"
            )
            
            api_response_time_ms = int((time.time() - start_time) * 1000)
            logger.info(f"Voice clone created: {cloned_voice_id} ({api_response_time_ms}ms)")
            
            # Step 5: Save to cache
            await self.db.save_clone_cache(
                caller_id=caller_id,
                cloned_voice_id=cloned_voice_id,
                ttl_seconds=self.settings.cache_ttl,
            )
            
            # Step 6: Log clone creation
            await self.db.log_clone_creation(
                caller_id=caller_id,
                cloned_voice_id=cloned_voice_id,
                api_response_time_ms=api_response_time_ms,
                sample_file_size_bytes=file_size,
                status="success",
            )
            
            return cloned_voice_id
            
        except (CallerNotFoundException, VoiceSampleNotFoundException):
            raise
        except Exception as e:
            logger.error(f"Error creating voice clone for {caller_id}: {e}")
            
            # Log failed attempt
            try:
                await self.db.log_clone_creation(
                    caller_id=caller_id,
                    cloned_voice_id="",
                    api_response_time_ms=0,
                    sample_file_size_bytes=0,
                    status="failed",
                    error_message=str(e),
                )
            except:
                pass
            
            raise VoiceCloneException(f"Failed to create voice clone: {str(e)}")
    
    async def get_cached_clone(self, caller_id: str) -> Optional[str]:
        """
        Check if clone exists in cache and is valid.
        
        Args:
            caller_id: Caller phone number
            
        Returns:
            cloned_voice_id or None if not cached
        """
        try:
            cached_clone = await self.db.get_cached_clone(caller_id)
            if cached_clone:
                return cached_clone.cloned_voice_id
            return None
        except Exception as e:
            logger.error(f"Error checking clone cache: {e}")
            return None
    
    async def invalidate_clone_cache(self, caller_id: str) -> bool:
        """
        Remove clone from cache (manual invalidation).
        
        Args:
            caller_id: Caller phone number
            
        Returns:
            True if cache was invalidated
        """
        try:
            return await self.db.invalidate_clone_cache(caller_id)
        except Exception as e:
            logger.error(f"Error invalidating clone cache: {e}")
            return False
    
    async def cleanup_expired_clones(self) -> int:
        """
        Remove expired clones from cache.
        
        Returns:
            Number of clones cleaned up
        """
        try:
            return await self.db.cleanup_expired_clones()
        except Exception as e:
            logger.error(f"Error cleaning up expired clones: {e}")
            return 0
    
    async def get_clone_statistics(self) -> dict:
        """
        Return cache hit/miss statistics.
        
        Returns:
            Statistics dictionary
        """
        try:
            return await self.db.get_clone_statistics()
        except Exception as e:
            logger.error(f"Error getting clone statistics: {e}")
            return {
                "total_clones": 0,
                "cache_hits": 0,
                "cache_misses": 0,
                "hit_rate": 0.0,
                "avg_creation_time_ms": 0.0,
                "total_calls": 0,
            }
