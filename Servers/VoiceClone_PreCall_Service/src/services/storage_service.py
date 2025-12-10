"""
Storage service for voice sample files.

Wraps FileHandler for service-level operations.
"""

import logging
from typing import Optional

from src.utils.file_handler import FileHandler
from src.utils.exceptions import StorageException
from src.config import get_settings

logger = logging.getLogger(__name__)


class StorageService:
    """Manages voice sample file storage operations."""
    
    def __init__(self):
        """Initialize storage service."""
        settings = get_settings()
        self.file_handler = FileHandler(
            storage_type=settings.voice_sample_storage,
            local_path=settings.local_voice_samples_path
        )
    
    async def get_voice_sample(self, file_path: str) -> bytes:
        """
        Retrieve voice sample file.
        
        Args:
            file_path: Path to voice sample (S3 URL or local path)
            
        Returns:
            File contents as bytes
            
        Raises:
            StorageException: If file cannot be retrieved
        """
        try:
            logger.debug(f"Retrieving voice sample: {file_path}")
            content = await self.file_handler.read_file(file_path)
            logger.info(f"Retrieved voice sample ({len(content)} bytes): {file_path}")
            return content
            
        except Exception as e:
            logger.error(f"Failed to retrieve voice sample {file_path}: {e}")
            raise StorageException(f"Failed to retrieve voice sample: {e}")
    
    async def save_voice_sample(
        self,
        file_path: str,
        content: bytes,
        caller_id: Optional[str] = None
    ) -> str:
        """
        Save voice sample file.
        
        Args:
            file_path: Destination path (relative for local, key for S3)
            content: File contents
            caller_id: Optional caller ID for logging
            
        Returns:
            Full path/URL to saved file
            
        Raises:
            StorageException: If file cannot be saved
        """
        try:
            logger.debug(f"Saving voice sample for {caller_id or 'unknown'}: {file_path}")
            full_path = await self.file_handler.write_file(file_path, content)
            logger.info(f"Saved voice sample ({len(content)} bytes): {full_path}")
            return full_path
            
        except Exception as e:
            logger.error(f"Failed to save voice sample {file_path}: {e}")
            raise StorageException(f"Failed to save voice sample: {e}")
    
    async def health_check(self) -> bool:
        """
        Check storage accessibility.
        
        Returns:
            True if storage is accessible, False otherwise
        """
        try:
            settings = get_settings()
            
            # For local storage, check directory exists and is writable
            if settings.voice_sample_storage == "local":
                import os
                path = settings.local_voice_samples_path
                return os.path.exists(path) and os.access(path, os.W_OK)
            
            # For S3, try to list bucket (basic connectivity check)
            elif settings.voice_sample_storage == "s3":
                try:
                    import boto3
                    from botocore.exceptions import ClientError
                    
                    s3_client = boto3.client('s3')
                    s3_client.head_bucket(Bucket=settings.s3_bucket_name)
                    return True
                except ClientError:
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Storage health check failed: {e}")
            return False
