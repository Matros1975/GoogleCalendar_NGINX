"""
Voice sample file handling utilities.

Handles reading voice samples from S3 or local filesystem.
"""

import os
import logging
from typing import BinaryIO, Optional
import aiofiles
from src.utils.exceptions import StorageException

logger = logging.getLogger(__name__)


class FileHandler:
    """Handles voice sample file operations."""
    
    def __init__(self, storage_type: str = "local", local_path: str = "/data/voices"):
        """
        Initialize file handler.
        
        Args:
            storage_type: Storage type ('s3' or 'local')
            local_path: Local storage directory path
        """
        self.storage_type = storage_type
        self.local_path = local_path
        
        # Create local directory if needed
        if storage_type == "local" and not os.path.exists(local_path):
            try:
                os.makedirs(local_path, exist_ok=True)
                logger.info(f"Created local voice samples directory: {local_path}")
            except OSError as e:
                logger.error(f"Failed to create local directory {local_path}: {e}")
                raise StorageException(f"Failed to create local directory: {e}")
    
    async def read_file(self, file_path: str) -> bytes:
        """
        Read voice sample file.
        
        Args:
            file_path: Path to file (S3 URL or local path)
            
        Returns:
            File contents as bytes
            
        Raises:
            StorageException: If file cannot be read
        """
        if self.storage_type == "s3":
            return await self._read_from_s3(file_path)
        else:
            return await self._read_from_local(file_path)
    
    async def _read_from_local(self, file_path: str) -> bytes:
        """
        Read file from local filesystem.
        
        Args:
            file_path: Local file path
            
        Returns:
            File contents as bytes
            
        Raises:
            StorageException: If file cannot be read
        """
        try:
            # If path is relative, make it absolute with local_path
            if not os.path.isabs(file_path):
                file_path = os.path.join(self.local_path, file_path)
            
            if not os.path.exists(file_path):
                raise StorageException(f"Voice sample file not found: {file_path}")
            
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read()
            
            logger.debug(f"Read {len(content)} bytes from local file: {file_path}")
            return content
            
        except Exception as e:
            logger.error(f"Failed to read local file {file_path}: {e}")
            raise StorageException(f"Failed to read local file: {e}")
    
    async def _read_from_s3(self, s3_url: str) -> bytes:
        """
        Read file from S3.
        
        Args:
            s3_url: S3 URL (s3://bucket/key or https://...)
            
        Returns:
            File contents as bytes
            
        Raises:
            StorageException: If file cannot be read
        """
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            # Parse S3 URL
            if s3_url.startswith("s3://"):
                # Format: s3://bucket/key
                parts = s3_url[5:].split("/", 1)
                bucket = parts[0]
                key = parts[1] if len(parts) > 1 else ""
            elif s3_url.startswith("https://"):
                # Format: https://bucket.s3.region.amazonaws.com/key
                # or https://s3.region.amazonaws.com/bucket/key
                if ".s3." in s3_url or ".s3-" in s3_url:
                    # Extract bucket and key
                    path_parts = s3_url.split("amazonaws.com/", 1)
                    if len(path_parts) > 1:
                        key = path_parts[1]
                        # Extract bucket from domain
                        domain = path_parts[0]
                        if domain.startswith("https://"):
                            domain = domain[8:]
                        bucket = domain.split(".s3")[0]
                    else:
                        raise StorageException(f"Invalid S3 URL format: {s3_url}")
                else:
                    raise StorageException(f"Invalid S3 URL format: {s3_url}")
            else:
                raise StorageException(f"Invalid S3 URL format: {s3_url}")
            
            # Initialize S3 client (uses AWS credentials from environment)
            s3_client = boto3.client('s3')
            
            # Download file
            response = s3_client.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read()
            
            logger.debug(f"Read {len(content)} bytes from S3: {s3_url}")
            return content
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(f"S3 error reading {s3_url}: {error_code} - {e}")
            raise StorageException(f"Failed to read from S3: {error_code}")
        except Exception as e:
            logger.error(f"Failed to read S3 file {s3_url}: {e}")
            raise StorageException(f"Failed to read from S3: {e}")
    
    async def write_file(self, file_path: str, content: bytes) -> str:
        """
        Write voice sample file.
        
        Args:
            file_path: Path to file (relative for local, full for S3)
            content: File contents
            
        Returns:
            Full path/URL to written file
            
        Raises:
            StorageException: If file cannot be written
        """
        if self.storage_type == "s3":
            return await self._write_to_s3(file_path, content)
        else:
            return await self._write_to_local(file_path, content)
    
    async def _write_to_local(self, file_path: str, content: bytes) -> str:
        """Write file to local filesystem."""
        try:
            # Make path absolute
            if not os.path.isabs(file_path):
                file_path = os.path.join(self.local_path, file_path)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            
            logger.debug(f"Wrote {len(content)} bytes to local file: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to write local file {file_path}: {e}")
            raise StorageException(f"Failed to write local file: {e}")
    
    async def _write_to_s3(self, key: str, content: bytes) -> str:
        """Write file to S3."""
        try:
            import boto3
            from botocore.exceptions import ClientError
            from src.config import get_settings
            
            settings = get_settings()
            bucket = settings.s3_bucket_name
            
            # Initialize S3 client
            s3_client = boto3.client('s3')
            
            # Upload file
            s3_client.put_object(Bucket=bucket, Key=key, Body=content)
            
            # Return S3 URL
            s3_url = f"s3://{bucket}/{key}"
            logger.debug(f"Wrote {len(content)} bytes to S3: {s3_url}")
            return s3_url
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(f"S3 error writing {key}: {error_code} - {e}")
            raise StorageException(f"Failed to write to S3: {error_code}")
        except Exception as e:
            logger.error(f"Failed to write S3 file {key}: {e}")
            raise StorageException(f"Failed to write to S3: {e}")
