"""
Redis cache service for Voice Clone Pre-Call Service.

Handles all Redis operations for voice clone caching.
"""

import json
import logging
from typing import Optional, Any
import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.utils.exceptions import CacheException
from src.config import get_settings

logger = logging.getLogger(__name__)


class CacheService:
    """Manages Redis cache operations."""
    
    def __init__(self):
        """Initialize cache service."""
        self.redis_client: Optional[Redis] = None
    
    async def connect(self) -> None:
        """Initialize Redis connection."""
        try:
            settings = get_settings()
            self.redis_client = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Redis connection established successfully")
            
        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise CacheException(f"Redis connection failed: {e}")
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Deserialized value or None if not found
        """
        try:
            if not self.redis_client:
                raise CacheException("Redis not connected")
            
            value = await self.redis_client.get(key)
            if value is None:
                return None
            
            # Try to deserialize JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # Return as string if not JSON
                return value
                
        except RedisError as e:
            logger.error(f"Redis error getting key {key}: {e}")
            raise CacheException(f"Failed to get from cache: {e}")
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache with optional TTL.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized if not string)
            ttl: TTL in seconds (None for no expiration)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                raise CacheException("Redis not connected")
            
            # Serialize to JSON if not string
            if not isinstance(value, str):
                value = json.dumps(value)
            
            if ttl:
                await self.redis_client.setex(key, ttl, value)
            else:
                await self.redis_client.set(key, value)
            
            return True
            
        except RedisError as e:
            logger.error(f"Redis error setting key {key}: {e}")
            raise CacheException(f"Failed to set in cache: {e}")
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted, False if not found
        """
        try:
            if not self.redis_client:
                raise CacheException("Redis not connected")
            
            result = await self.redis_client.delete(key)
            return result > 0
            
        except RedisError as e:
            logger.error(f"Redis error deleting key {key}: {e}")
            raise CacheException(f"Failed to delete from cache: {e}")
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            if not self.redis_client:
                raise CacheException("Redis not connected")
            
            result = await self.redis_client.exists(key)
            return result > 0
            
        except RedisError as e:
            logger.error(f"Redis error checking existence of key {key}: {e}")
            raise CacheException(f"Failed to check key existence: {e}")
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment counter.
        
        Args:
            key: Counter key
            amount: Amount to increment by
            
        Returns:
            New counter value
        """
        try:
            if not self.redis_client:
                raise CacheException("Redis not connected")
            
            return await self.redis_client.incrby(key, amount)
            
        except RedisError as e:
            logger.error(f"Redis error incrementing key {key}: {e}")
            raise CacheException(f"Failed to increment counter: {e}")
    
    async def get_ttl(self, key: str) -> int:
        """
        Get remaining TTL in seconds.
        
        Args:
            key: Cache key
            
        Returns:
            TTL in seconds (-1 if no expiry, -2 if not found)
        """
        try:
            if not self.redis_client:
                raise CacheException("Redis not connected")
            
            return await self.redis_client.ttl(key)
            
        except RedisError as e:
            logger.error(f"Redis error getting TTL for key {key}: {e}")
            raise CacheException(f"Failed to get TTL: {e}")
    
    async def flush_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Key pattern (e.g., "voice_clone:*")
            
        Returns:
            Number of keys deleted
        """
        try:
            if not self.redis_client:
                raise CacheException("Redis not connected")
            
            # Find all matching keys
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)
            
            # Delete keys if any found
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
            
        except RedisError as e:
            logger.error(f"Redis error flushing pattern {pattern}: {e}")
            raise CacheException(f"Failed to flush pattern: {e}")
    
    async def health_check(self) -> bool:
        """
        Check Redis connectivity.
        
        Returns:
            True if Redis is accessible, False otherwise
        """
        try:
            if not self.redis_client:
                return False
            
            await self.redis_client.ping()
            return True
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
