"""
Storage utilities for conversation data and audio files using Azure Blob Storage.

"""

import os
import json
import base64
from datetime import datetime
from typing import Optional, Dict, Any
from azure.storage.blob import BlobServiceClient, ContentSettings
from src.utils.logger import setup_logger

logger = setup_logger()


class StorageManager:
    """Manages storage of conversation transcripts and audio files in Azure Blob Storage."""
    
    def __init__(
        self,
        connection_string: str,
        container_name: str,
        enable_audio: bool = False,
        enable_transcript: bool = True
    ):
        """
        Initialize storage manager.
        
        Args:
            connection_string: Azure Storage connection string
            container_name: Blob container name
            enable_audio: Whether to store audio files
            enable_transcript: Whether to store transcripts
        """
        self.connection_string = connection_string
        self.container_name = container_name
        self.enable_audio = enable_audio
        self.enable_transcript = enable_transcript
        self.blob_service_client = None
        self.container_client = None
        
        if self.connection_string and self.container_name:
            try:
                self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
                self.container_client = self.blob_service_client.get_container_client(self.container_name)
                if not self.container_client.exists():
                    self.container_client.create_container()
                    logger.info(f"Created blob container: {self.container_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Blob Storage: {e}")
    
    @classmethod
    def from_env(cls) -> "StorageManager":
        """Create StorageManager from environment variables."""
        # Try different common env vars for connection string
        connection_string = os.getenv("AzureWebJobsStorage_elevenlabswebhook") or \
                           os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        
        container_name = os.getenv("BLOB_CONTAINER_NAME", "webhook-data")
        
        enable_audio = os.getenv("ENABLE_AUDIO_STORAGE", "false").lower() == "true"
        enable_transcript = os.getenv("ENABLE_TRANSCRIPT_STORAGE", "true").lower() == "true"
        
        if not connection_string:
            logger.warning("No Azure Storage connection string found (AzureWebJobsStorage_elevenlabswebhook or AZURE_STORAGE_CONNECTION_STRING)")
        
        return cls(
            connection_string=connection_string,
            container_name=container_name,
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
        Save conversation transcript to blob storage.
        
        Args:
            conversation_id: Unique conversation identifier
            agent_id: Agent identifier
            data: Transcript data to save
            
        Returns:
            Blob URL or path if successful, None otherwise
        """
        if not self.enable_transcript or not self.container_client:
            logger.debug("Transcript storage disabled or not initialized, skipping save")
            return None
        
        try:
            # Generate filename with timestamp
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            blob_name = f"transcripts/{conversation_id}_{timestamp}.json"
            
            # Add metadata to the data
            save_data = {
                "conversation_id": conversation_id,
                "agent_id": agent_id,
                "saved_at": datetime.utcnow().isoformat() + "Z",
                "data": data
            }
            
            # Upload to blob
            blob_client = self.container_client.get_blob_client(blob_name)
            json_data = json.dumps(save_data, indent=2, default=str)
            
            blob_client.upload_blob(
                json_data,
                overwrite=True,
                content_settings=ContentSettings(content_type="application/json")
            )
            
            logger.info(f"Transcript saved to blob: {blob_name}")
            return blob_client.url
            
        except Exception as e:
            logger.error(f"Failed to save transcript to blob: {e}")
            return None
    
    def save_audio(
        self,
        conversation_id: str,
        agent_id: str,
        audio_base64: str,
        audio_format: str = "mp3"
    ) -> Optional[str]:
        """
        Save audio file to blob storage.
        
        Args:
            conversation_id: Unique conversation identifier
            agent_id: Agent identifier
            audio_base64: Base64-encoded audio data
            audio_format: Audio format (default: mp3)
            
        Returns:
            Blob URL or path if successful, None otherwise
        """
        if not self.enable_audio or not self.container_client:
            logger.debug("Audio storage disabled or not initialized, skipping save")
            return None
        
        try:
            # Decode base64 audio
            audio_data = base64.b64decode(audio_base64)
            
            # Generate filename with timestamp
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            blob_name = f"audio/{conversation_id}_{timestamp}.{audio_format}"
            
            # Upload to blob
            blob_client = self.container_client.get_blob_client(blob_name)
            
            content_type = f"audio/{audio_format}"
            if audio_format == "mp3":
                content_type = "audio/mpeg"
            
            blob_client.upload_blob(
                audio_data,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type)
            )
            
            logger.info(f"Audio saved to blob: {blob_name} ({len(audio_data)} bytes)")
            return blob_client.url
            
        except Exception as e:
            logger.error(f"Failed to save audio to blob: {e}")
            return None
    
    def get_transcript(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a transcript by conversation ID from blob storage.
        
        Args:
            conversation_id: Conversation ID to look up
            
        Returns:
            Transcript data or None if not found
        """
        if not self.container_client:
            return None
        
        try:
            # List blobs matching the conversation ID prefix in transcripts folder
            prefix = f"transcripts/{conversation_id}_"
            blobs = list(self.container_client.list_blobs(name_starts_with=prefix))
            
            if not blobs:
                return None
            
            # Return most recent (sort by name which includes timestamp)
            latest_blob = max(blobs, key=lambda b: b.name)
            
            blob_client = self.container_client.get_blob_client(latest_blob.name)
            download_stream = blob_client.download_blob()
            json_content = download_stream.readall()
            
            return json.loads(json_content)
                
        except Exception as e:
            logger.error(f"Failed to retrieve transcript from blob: {e}")
            return None
