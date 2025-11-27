"""
Storage utilities for conversation data and audio files.
"""

import os
import json
import base64
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class StorageManager:
    """Manages storage of conversation transcripts and audio files."""
    
    def __init__(
        self,
        audio_path: Optional[str] = None,
        transcript_path: Optional[str] = None,
        enable_audio: bool = False,
        enable_transcript: bool = True
    ):
        """
        Initialize storage manager.
        
        Args:
            audio_path: Path for audio file storage
            transcript_path: Path for transcript storage
            enable_audio: Whether to store audio files
            enable_transcript: Whether to store transcripts
        """
        self.audio_path = Path(audio_path) if audio_path else None
        self.transcript_path = Path(transcript_path) if transcript_path else None
        self.enable_audio = enable_audio
        self.enable_transcript = enable_transcript
        
        # Create directories if needed
        if self.enable_audio and self.audio_path:
            self.audio_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Audio storage enabled at: {self.audio_path}")
        
        if self.enable_transcript and self.transcript_path:
            self.transcript_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Transcript storage enabled at: {self.transcript_path}")
    
    @classmethod
    def from_env(cls) -> "StorageManager":
        """Create StorageManager from environment variables."""
        audio_path = os.getenv("AUDIO_STORAGE_PATH")
        transcript_path = os.getenv("TRANSCRIPT_STORAGE_PATH")
        enable_audio = os.getenv("ENABLE_AUDIO_STORAGE", "false").lower() == "true"
        enable_transcript = os.getenv("ENABLE_TRANSCRIPT_STORAGE", "true").lower() == "true"
        
        return cls(
            audio_path=audio_path,
            transcript_path=transcript_path,
            enable_audio=enable_audio,
            enable_transcript=enable_transcript
        )
    
    def save_transcript(
        self,
        conversation_id: str,
        agent_id: str,
        data: Dict[str, Any]
    ) -> Optional[str]:
        """
        Save conversation transcript to storage.
        
        Args:
            conversation_id: Unique conversation identifier
            agent_id: Agent identifier
            data: Transcript data to save
            
        Returns:
            Path to saved file or None if storage disabled
        """
        if not self.enable_transcript or not self.transcript_path:
            logger.debug("Transcript storage disabled, skipping save")
            return None
        
        try:
            # Generate filename with timestamp
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{conversation_id}_{timestamp}.json"
            filepath = self.transcript_path / filename
            
            # Add metadata to the data
            save_data = {
                "conversation_id": conversation_id,
                "agent_id": agent_id,
                "saved_at": datetime.utcnow().isoformat() + "Z",
                "data": data
            }
            
            # Write to file
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(save_data, f, indent=2, default=str)
            
            logger.info(f"Transcript saved: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to save transcript: {e}")
            return None
    
    def save_audio(
        self,
        conversation_id: str,
        agent_id: str,
        audio_base64: str,
        audio_format: str = "mp3"
    ) -> Optional[str]:
        """
        Save audio file to storage.
        
        Args:
            conversation_id: Unique conversation identifier
            agent_id: Agent identifier
            audio_base64: Base64-encoded audio data
            audio_format: Audio format (default: mp3)
            
        Returns:
            Path to saved file or None if storage disabled
        """
        if not self.enable_audio or not self.audio_path:
            logger.debug("Audio storage disabled, skipping save")
            return None
        
        try:
            # Decode base64 audio
            audio_data = base64.b64decode(audio_base64)
            
            # Generate filename with timestamp
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{conversation_id}_{timestamp}.{audio_format}"
            filepath = self.audio_path / filename
            
            # Write to file
            with open(filepath, "wb") as f:
                f.write(audio_data)
            
            logger.info(f"Audio saved: {filepath} ({len(audio_data)} bytes)")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to save audio: {e}")
            return None
    
    def get_transcript(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a transcript by conversation ID.
        
        Args:
            conversation_id: Conversation ID to look up
            
        Returns:
            Transcript data or None if not found
        """
        if not self.transcript_path:
            return None
        
        try:
            # Find matching files
            pattern = f"{conversation_id}_*.json"
            matches = list(self.transcript_path.glob(pattern))
            
            if not matches:
                return None
            
            # Return most recent
            latest = max(matches, key=lambda p: p.stat().st_mtime)
            
            with open(latest, "r", encoding="utf-8") as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Failed to retrieve transcript: {e}")
            return None
