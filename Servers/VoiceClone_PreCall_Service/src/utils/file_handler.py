"""
File handler utilities for voice sample processing.
"""

import os
import hashlib
import aiofiles
from typing import Optional
from pathlib import Path

from src.utils.logger import get_logger
from src.utils.exceptions import VoiceSampleNotFoundException, StorageException

logger = get_logger(__name__)


async def read_voice_sample(file_path: str) -> bytes:
    """
    Read voice sample file from local storage.
    
    Args:
        file_path: Path to voice sample file
        
    Returns:
        File contents as bytes
        
    Raises:
        VoiceSampleNotFoundException: If file not found
        StorageException: If file read fails
    """
    try:
        path = Path(file_path)
        
        if not path.exists():
            logger.error(f"Voice sample file not found: {file_path}")
            raise VoiceSampleNotFoundException(f"Voice sample not found: {file_path}")
        
        if not path.is_file():
            logger.error(f"Path is not a file: {file_path}")
            raise StorageException(f"Path is not a file: {file_path}")
        
        async with aiofiles.open(file_path, 'rb') as f:
            content = await f.read()
        
        logger.info(f"Successfully read voice sample: {file_path} ({len(content)} bytes)")
        return content
        
    except VoiceSampleNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error reading voice sample {file_path}: {e}")
        raise StorageException(f"Failed to read voice sample: {str(e)}")


async def save_voice_sample(file_path: str, content: bytes) -> str:
    """
    Save voice sample file to local storage.
    
    Args:
        file_path: Path to save file
        content: File contents as bytes
        
    Returns:
        Absolute path to saved file
        
    Raises:
        StorageException: If file save fails
    """
    try:
        path = Path(file_path)
        
        # Create parent directories if they don't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        logger.info(f"Successfully saved voice sample: {file_path} ({len(content)} bytes)")
        return str(path.absolute())
        
    except Exception as e:
        logger.error(f"Error saving voice sample {file_path}: {e}")
        raise StorageException(f"Failed to save voice sample: {str(e)}")


def get_file_size(file_path: str) -> int:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in bytes
        
    Raises:
        VoiceSampleNotFoundException: If file not found
    """
    try:
        path = Path(file_path)
        
        if not path.exists():
            raise VoiceSampleNotFoundException(f"File not found: {file_path}")
        
        return path.stat().st_size
        
    except VoiceSampleNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error getting file size for {file_path}: {e}")
        raise StorageException(f"Failed to get file size: {str(e)}")


def compute_file_hash(content: bytes, algorithm: str = "sha256") -> str:
    """
    Compute hash of file content.
    
    Args:
        content: File content as bytes
        algorithm: Hash algorithm (default: sha256)
        
    Returns:
        Hexadecimal hash string
    """
    try:
        hasher = hashlib.new(algorithm)
        hasher.update(content)
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Error computing file hash: {e}")
        raise StorageException(f"Failed to compute file hash: {str(e)}")


def validate_audio_file(file_path: str) -> bool:
    """
    Validate that file is a supported audio format.
    
    Args:
        file_path: Path to audio file
        
    Returns:
        True if valid audio file
    """
    # Supported audio formats for ElevenLabs
    supported_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.opus'}
    
    path = Path(file_path)
    return path.suffix.lower() in supported_extensions


async def get_file_metadata(file_path: str) -> dict:
    """
    Get file metadata (size, type, etc.).
    
    Args:
        file_path: Path to file
        
    Returns:
        Dictionary with file metadata
        
    Raises:
        VoiceSampleNotFoundException: If file not found
    """
    try:
        path = Path(file_path)
        
        if not path.exists():
            raise VoiceSampleNotFoundException(f"File not found: {file_path}")
        
        stat = path.stat()
        
        return {
            "path": str(path.absolute()),
            "name": path.name,
            "size_bytes": stat.st_size,
            "extension": path.suffix,
            "is_valid_audio": validate_audio_file(file_path),
        }
        
    except VoiceSampleNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error getting file metadata for {file_path}: {e}")
        raise StorageException(f"Failed to get file metadata: {str(e)}")
