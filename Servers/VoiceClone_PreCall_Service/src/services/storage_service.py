"""
Storage service for voice sample file handling (S3 and local).
"""

import os
from pathlib import Path
from typing import Optional

import aiofiles
import boto3
from botocore.exceptions import ClientError

from src.config import get_settings
from src.utils.logger import get_logger
from src.utils.exceptions import StorageException, VoiceSampleNotFoundException

logger = get_logger(__name__)


class StorageService:
    """
    Handles voice sample file storage (S3 or local filesystem).
    """
    
    def __init__(self):
        """Initialize storage service."""
        self.settings = get_settings()
        self.storage_backend = self.settings.voice_sample_storage
        
        if self.storage_backend == "s3":
            self.s3_client = boto3.client(
                's3',
                region_name=self.settings.s3_region,
                aws_access_key_id=self.settings.aws_access_key_id,
                aws_secret_access_key=self.settings.aws_secret_access_key,
            )
            self.bucket_name = self.settings.s3_bucket_name
        else:
            self.local_path = Path(self.settings.local_voice_samples_path)
            self.local_path.mkdir(parents=True, exist_ok=True)
    
    async def download_voice_sample(self, sample_url: str) -> bytes:
        """
        Download voice sample from storage.
        
        Args:
            sample_url: S3 URL or local file path
            
        Returns:
            File contents as bytes
            
        Raises:
            VoiceSampleNotFoundException: If file not found
            StorageException: If download fails
        """
        try:
            if self.storage_backend == "s3":
                return await self._download_from_s3(sample_url)
            else:
                return await self._download_from_local(sample_url)
                
        except VoiceSampleNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error downloading voice sample: {e}")
            raise StorageException(f"Failed to download voice sample: {str(e)}")
    
    async def _download_from_s3(self, s3_url: str) -> bytes:
        """Download file from S3."""
        try:
            # Parse S3 URL: s3://bucket/key or https://bucket.s3.region.amazonaws.com/key
            if s3_url.startswith("s3://"):
                key = s3_url.replace(f"s3://{self.bucket_name}/", "")
            else:
                # Extract key from HTTPS URL
                parts = s3_url.split(f"{self.bucket_name}/")
                if len(parts) < 2:
                    raise StorageException(f"Invalid S3 URL: {s3_url}")
                key = parts[1]
            
            # Download from S3
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            content = response['Body'].read()
            
            logger.info(f"Downloaded voice sample from S3: {key} ({len(content)} bytes)")
            return content
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise VoiceSampleNotFoundException(f"S3 object not found: {s3_url}")
            else:
                raise StorageException(f"S3 error: {str(e)}")
    
    async def _download_from_local(self, file_path: str) -> bytes:
        """Download file from local filesystem."""
        try:
            path = Path(file_path)
            
            # If relative path, resolve against local_path
            if not path.is_absolute():
                path = self.local_path / path
            
            if not path.exists():
                raise VoiceSampleNotFoundException(f"File not found: {path}")
            
            async with aiofiles.open(path, 'rb') as f:
                content = await f.read()
            
            logger.info(f"Downloaded voice sample from local: {path} ({len(content)} bytes)")
            return content
            
        except VoiceSampleNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Local file error: {str(e)}")
    
    async def upload_voice_sample(
        self,
        caller_id: str,
        content: bytes,
        filename: Optional[str] = None,
    ) -> str:
        """
        Upload voice sample to storage.
        
        Args:
            caller_id: Caller phone number (used for organizing files)
            content: File content bytes
            filename: Optional filename (defaults to caller_id.mp3)
            
        Returns:
            Storage URL/path of uploaded file
            
        Raises:
            StorageException: If upload fails
        """
        try:
            if not filename:
                filename = f"{caller_id}.mp3"
            
            if self.storage_backend == "s3":
                return await self._upload_to_s3(filename, content)
            else:
                return await self._upload_to_local(filename, content)
                
        except Exception as e:
            logger.error(f"Error uploading voice sample: {e}")
            raise StorageException(f"Failed to upload voice sample: {str(e)}")
    
    async def _upload_to_s3(self, filename: str, content: bytes) -> str:
        """Upload file to S3."""
        try:
            key = f"voice-samples/{filename}"
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content,
                ContentType="audio/mpeg"
            )
            
            s3_url = f"s3://{self.bucket_name}/{key}"
            logger.info(f"Uploaded voice sample to S3: {s3_url}")
            return s3_url
            
        except ClientError as e:
            raise StorageException(f"S3 upload error: {str(e)}")
    
    async def _upload_to_local(self, filename: str, content: bytes) -> str:
        """Upload file to local filesystem."""
        try:
            file_path = self.local_path / filename
            
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            
            logger.info(f"Uploaded voice sample to local: {file_path}")
            return str(file_path.absolute())
            
        except Exception as e:
            raise StorageException(f"Local file upload error: {str(e)}")
    
    def validate_voice_sample(self, content: bytes) -> bool:
        """
        Validate voice sample file.
        
        Args:
            content: File content bytes
            
        Returns:
            True if valid
        """
        # Basic validation: check minimum size (e.g., 1KB)
        if len(content) < 1024:
            logger.warning("Voice sample too small (< 1KB)")
            return False
        
        # Could add more validation (file format, duration, etc.)
        return True
