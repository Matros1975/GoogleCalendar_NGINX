"""
Voice sample file handling utilities.
"""

import base64
import os
import logging
from typing import Tuple, Optional
import io

logger = logging.getLogger(__name__)


class FileHandler:
    """Handles voice sample file operations."""
    
    def __init__(self, storage_path: Optional[str] = None, enable_storage: bool = False):
        """
        Initialize file handler.
        
        Args:
            storage_path: Path to store voice samples
            enable_storage: Whether to persist voice samples to disk
        """
        self.storage_path = storage_path
        self.enable_storage = enable_storage
        
        if self.enable_storage and self.storage_path:
            os.makedirs(self.storage_path, exist_ok=True)
    
    def decode_base64_audio(self, base64_data: str) -> bytes:
        """
        Decode base64-encoded audio data.
        
        Args:
            base64_data: Base64-encoded audio string
            
        Returns:
            Decoded audio bytes
            
        Raises:
            ValueError: If base64 decoding fails
        """
        try:
            # Remove data URL prefix if present (e.g., "data:audio/mp3;base64,")
            if "," in base64_data:
                base64_data = base64_data.split(",", 1)[1]
            
            audio_bytes = base64.b64decode(base64_data)
            logger.debug(f"Decoded base64 audio: {len(audio_bytes)} bytes")
            return audio_bytes
        except Exception as e:
            logger.error(f"Failed to decode base64 audio: {e}")
            raise ValueError(f"Invalid base64 audio data: {str(e)}")
    
    def validate_audio_size(self, audio_bytes: bytes, max_size_mb: float = 10.0) -> Tuple[bool, Optional[str]]:
        """
        Validate audio file size.
        
        Args:
            audio_bytes: Audio data
            max_size_mb: Maximum allowed size in megabytes
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        size_mb = len(audio_bytes) / (1024 * 1024)
        
        if size_mb > max_size_mb:
            error_msg = f"Audio file too large: {size_mb:.2f}MB (max {max_size_mb}MB)"
            logger.warning(error_msg)
            return False, error_msg
        
        logger.debug(f"Audio size validated: {size_mb:.2f}MB")
        return True, None
    
    def get_audio_format(self, audio_bytes: bytes) -> str:
        """
        Detect audio format from file header.
        
        Args:
            audio_bytes: Audio data
            
        Returns:
            Audio format string ("wav", "mp3", "ogg", or "unknown")
        """
        if len(audio_bytes) < 12:
            return "unknown"
        
        # Check for WAV (RIFF header)
        if audio_bytes[:4] == b'RIFF' and audio_bytes[8:12] == b'WAVE':
            return "wav"
        
        # Check for MP3 (ID3 tag or MPEG frame sync)
        if audio_bytes[:3] == b'ID3' or (audio_bytes[0] == 0xFF and (audio_bytes[1] & 0xE0) == 0xE0):
            return "mp3"
        
        # Check for OGG (OggS header)
        if audio_bytes[:4] == b'OggS':
            return "ogg"
        
        return "unknown"
    
    def save_voice_sample(self, audio_bytes: bytes, filename: str) -> Optional[str]:
        """
        Save voice sample to disk if storage is enabled.
        
        Args:
            audio_bytes: Audio data
            filename: Filename to use
            
        Returns:
            Full path to saved file, or None if storage disabled
        """
        if not self.enable_storage or not self.storage_path:
            return None
        
        try:
            filepath = os.path.join(self.storage_path, filename)
            with open(filepath, "wb") as f:
                f.write(audio_bytes)
            logger.info(f"Saved voice sample to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save voice sample: {e}")
            return None
    
    def create_file_from_bytes(self, audio_bytes: bytes, filename: str) -> io.BytesIO:
        """
        Create a file-like object from audio bytes for upload.
        
        Args:
            audio_bytes: Audio data
            filename: Filename for the file object
            
        Returns:
            BytesIO object with audio data
        """
        file_obj = io.BytesIO(audio_bytes)
        file_obj.name = filename
        return file_obj
