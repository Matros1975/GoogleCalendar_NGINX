"""
Voice clone orchestration service.

Coordinates voice cloning workflow including caching and database operations.
"""

import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime

from src.services.database_service import DatabaseService
from src.services.cache_service import CacheService
from src.services.storage_service import StorageService
from src.services.elevenlabs_client import ElevenLabsClient
from src.utils.exceptions import (
    VoiceCloneException,
    VoiceSampleNotFoundException,
    CloneTimeoutException
)
from src.config import get_settings

logger = logging.getLogger(__name__)


class VoiceCloneService:
    """Orchestrates voice cloning operations."""
    
    def __init__(
        self,
        database_service: DatabaseService,
        cache_service: CacheService,
        storage_service: StorageService,
        elevenlabs_client: ElevenLabsClient
    ):
        """
        Initialize voice clone service.
        
        Args:
            database_service: Database service instance
            cache_service: Cache service instance
            storage_service: Storage service instance
            elevenlabs_client: ElevenLabs API client
        """
        self.db = database_service
        self.cache = cache_service
        self.storage = storage_service
        self.elevenlabs = elevenlabs_client
        self.settings = get_settings()
    
    async def get_or_create_clone(
        self,
        caller_id: str,
        voice_sample_path: Optional[str] = None,
    ) -> str:
        """
        Get cached clone or create new one.
        
        This method implements the following workflow:
        1. Check Redis cache for existing clone
        2. If cached and valid, return cloned_voice_id
        3. If not cached:
           a. Query database for voice_sample_path (if not provided)
           b. Retrieve voice sample file
           c. Call ElevenLabs API to create clone
           d. Store in Redis cache with TTL
           e. Log in voice_clone_log table
        4. Return cloned_voice_id
        
        Args:
            caller_id: Caller phone number
            voice_sample_path: Optional override for voice sample path
            
        Returns:
            Cloned voice ID
            
        Raises:
            VoiceSampleNotFoundException: If no voice sample found for caller
            VoiceCloneException: If clone creation fails
            CloneTimeoutException: If clone creation times out
        """
        try:
            logger.info(f"Processing voice clone request for caller: {caller_id}")
            
            # Step 1: Check Redis cache
            cache_key = f"voice_clone:{caller_id}"
            cached_clone = await self.cache.get(cache_key)
            
            if cached_clone:
                cloned_voice_id = cached_clone.get("voice_id") if isinstance(cached_clone, dict) else cached_clone
                logger.info(f"Using cached voice clone for {caller_id}: {cloned_voice_id}")
                
                # Increment reuse counter in database
                await self.db.increment_clone_reuse(cloned_voice_id)
                
                return cloned_voice_id
            
            # Step 2: Get voice sample path if not provided
            if not voice_sample_path:
                voice_sample_path = await self.db.get_voice_sample_for_caller(caller_id)
                
                if not voice_sample_path:
                    logger.error(f"No voice sample found for caller: {caller_id}")
                    raise VoiceSampleNotFoundException(
                        f"No voice sample configured for caller: {caller_id}"
                    )
            
            logger.info(f"Using voice sample: {voice_sample_path}")
            
            # Step 3: Retrieve voice sample file
            voice_sample_content = await self.storage.get_voice_sample(voice_sample_path)
            sample_size = len(voice_sample_content)
            logger.info(f"Retrieved voice sample: {sample_size} bytes")
            
            # Step 4: Create voice clone via ElevenLabs API
            start_time = time.time()
            voice_name = f"Clone_{caller_id}_{int(start_time)}"
            
            try:
                cloned_voice_id = await self.elevenlabs.create_voice_clone(
                    voice_sample_content=voice_sample_content,
                    voice_name=voice_name,
                    description=f"Voice clone for {caller_id}"
                )
            except Exception as e:
                elapsed_ms = int((time.time() - start_time) * 1000)
                
                # Log failed clone creation
                await self.db.log_clone_creation(
                    caller_id=caller_id,
                    cloned_voice_id="FAILED",
                    api_response_time_ms=elapsed_ms,
                    sample_file_size_bytes=sample_size,
                    status="failed",
                    error_message=str(e)
                )
                
                if elapsed_ms > (self.settings.voice_clone_timeout * 1000):
                    raise CloneTimeoutException(
                        f"Voice clone creation timed out after {elapsed_ms}ms"
                    )
                else:
                    raise VoiceCloneException(f"Voice clone creation failed: {e}")
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.info(
                f"Voice clone created: {cloned_voice_id} "
                f"for {caller_id} (took {elapsed_ms}ms)"
            )
            
            # Step 5: Store in Redis cache with TTL
            cache_data = {
                "voice_id": cloned_voice_id,
                "created_at": datetime.utcnow().isoformat(),
                "caller_id": caller_id
            }
            
            await self.cache.set(
                cache_key,
                cache_data,
                ttl=self.settings.cache_ttl
            )
            
            # Also store in database cache table
            await self.db.save_clone_cache(
                caller_id=caller_id,
                cloned_voice_id=cloned_voice_id,
                ttl_seconds=self.settings.cache_ttl
            )
            
            # Step 6: Log successful clone creation
            await self.db.log_clone_creation(
                caller_id=caller_id,
                cloned_voice_id=cloned_voice_id,
                api_response_time_ms=elapsed_ms,
                sample_file_size_bytes=sample_size,
                status="success"
            )
            
            return cloned_voice_id
            
        except (VoiceSampleNotFoundException, VoiceCloneException, CloneTimeoutException):
            # Re-raise known exceptions
            raise
        except Exception as e:
            logger.exception(f"Unexpected error in get_or_create_clone for {caller_id}: {e}")
            raise VoiceCloneException(f"Unexpected error: {e}")
    
    async def get_cached_clone(self, caller_id: str) -> Optional[str]:
        """
        Check if clone exists in cache and is valid.
        
        Args:
            caller_id: Caller phone number
            
        Returns:
            Cloned voice ID or None
        """
        try:
            cache_key = f"voice_clone:{caller_id}"
            cached_clone = await self.cache.get(cache_key)
            
            if cached_clone:
                return cached_clone.get("voice_id") if isinstance(cached_clone, dict) else cached_clone
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking cached clone for {caller_id}: {e}")
            return None
    
    async def invalidate_clone_cache(self, caller_id: str) -> bool:
        """
        Remove clone from cache (manual invalidation).
        
        Args:
            caller_id: Caller phone number
            
        Returns:
            True if cache was invalidated, False otherwise
        """
        try:
            cache_key = f"voice_clone:{caller_id}"
            result = await self.cache.delete(cache_key)
            
            if result:
                logger.info(f"Invalidated clone cache for {caller_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error invalidating clone cache for {caller_id}: {e}")
            return False
    
    async def cleanup_expired_clones(self) -> int:
        """
        Remove expired clones from cache.
        
        This can be run as a background task (e.g., hourly).
        
        Returns:
            Number of clones cleaned up
        """
        try:
            # Find all voice clone keys
            pattern = "voice_clone:*"
            
            # Redis will automatically expire keys based on TTL
            # This is mainly for logging/monitoring
            logger.info("Cache cleanup is handled automatically by Redis TTL")
            return 0
            
        except Exception as e:
            logger.error(f"Error during clone cache cleanup: {e}")
            return 0
    
    async def get_clone_statistics(self) -> Dict[str, Any]:
        """
        Return cache hit/miss statistics.
        
        Returns:
            Dictionary with statistics
        """
        try:
            # This would require tracking hits/misses in Redis counters
            # For now, return basic info
            stats = {
                "total_clones": 0,
                "cache_hits": 0,
                "cache_misses": 0,
                "hit_rate": 0.0,
                "avg_creation_time_ms": 0
            }
            
            # TODO: Implement proper statistics tracking
            logger.info("Statistics: placeholder implementation")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting clone statistics: {e}")
            return {
                "error": str(e)
            }
