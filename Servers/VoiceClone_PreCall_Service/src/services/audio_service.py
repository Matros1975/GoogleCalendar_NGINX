"""
Audio service for downloading and caching audio files.

Handles audio file retrieval for greetings and hold music.
"""

import hashlib
import aiofiles
from pathlib import Path
from typing import Optional
import httpx

from src.utils.logger import get_logger
from src.utils.exceptions import ValidationException

logger = get_logger(__name__)


class AudioService:
    """
    Service for downloading and caching audio files.
    
    Downloads audio files from URLs and caches them locally
    to avoid repeated downloads.
    """
    
    def __init__(self, cache_dir: str = "/tmp/audio_cache"):
        """
        Initialize audio service.
        
        Args:
            cache_dir: Directory for caching audio files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.http_client = None
    
    async def _ensure_http_client(self):
        """Ensure HTTP client is initialized."""
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close HTTP client."""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
    
    def _get_cache_path(self, url: str) -> Path:
        """
        Get cache file path for URL.
        
        Args:
            url: Audio file URL
            
        Returns:
            Path to cached file
        """
        # Use URL hash as filename to avoid filesystem issues
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        
        # Try to preserve extension from URL
        extension = ""
        if "." in url:
            extension = Path(url).suffix[:10]  # Limit extension length
        
        return self.cache_dir / f"{url_hash}{extension}"
    
    async def get_audio_file(self, url: str) -> Path:
        """
        Download and cache audio file.
        
        If file is already cached, return cached path.
        Otherwise, download from URL and cache.
        
        Args:
            url: Audio file URL
            
        Returns:
            Path to cached audio file
            
        Raises:
            ValidationException: If URL is invalid or download fails
        """
        if not url:
            raise ValidationException("Audio URL cannot be empty")
        
        # Check if already cached
        cache_path = self._get_cache_path(url)
        if cache_path.exists():
            logger.debug(f"Audio file cache hit: {url}")
            return cache_path
        
        logger.info(f"Downloading audio file: {url}")
        
        try:
            await self._ensure_http_client()
            
            # Download file
            response = await self.http_client.get(url)
            response.raise_for_status()
            
            # Save to cache
            async with aiofiles.open(cache_path, "wb") as f:
                await f.write(response.content)
            
            logger.info(f"Audio file cached: {cache_path}")
            return cache_path
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to download audio file from {url}: {e}")
            raise ValidationException(f"Failed to download audio file: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error downloading audio file: {e}")
            raise ValidationException(f"Audio file download error: {str(e)}")
    
    async def clear_cache(self) -> int:
        """
        Clear all cached audio files.
        
        Returns:
            Number of files removed
        """
        count = 0
        for file_path in self.cache_dir.glob("*"):
            if file_path.is_file():
                file_path.unlink()
                count += 1
        
        logger.info(f"Cleared {count} cached audio files")
        return count
    
    async def get_cache_size(self) -> int:
        """
        Get total size of cached files in bytes.
        
        Returns:
            Total cache size in bytes
        """
        total_size = 0
        for file_path in self.cache_dir.glob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        
        return total_size
