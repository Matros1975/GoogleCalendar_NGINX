"""
ElevenLabs API client for voice operations.
"""

import logging
from typing import Dict, Any, Optional
import httpx

from src.models.elevenlabs_models import (
    VoiceCreateResponse,
    VoiceInfo,
    AgentUpdateResponse,
    AgentUpdateRequest,
    ConversationConfig,
    AgentConfig,
    AgentVoiceConfig
)

logger = logging.getLogger(__name__)


class ElevenLabsAPIClient:
    """Client for ElevenLabs API interactions."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.elevenlabs.io/v1"):
        """
        Initialize ElevenLabs API client.
        
        Args:
            api_key: ElevenLabs API key
            base_url: Base URL for API (default: https://api.elevenlabs.io/v1)
        """
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "xi-api-key": api_key
        }
    
    async def create_instant_voice(
        self,
        voice_sample: bytes,
        voice_name: str,
        description: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> VoiceCreateResponse:
        """
        Create instant voice clone from audio sample.
        
        Args:
            voice_sample: Audio file bytes (WAV, MP3, OGG)
            voice_name: Name for the cloned voice
            description: Optional description
            labels: Optional metadata labels
            
        Returns:
            Voice creation response with voice_id
            
        Raises:
            httpx.HTTPError: If API request fails
        """
        url = f"{self.base_url}/voices/add"
        
        # Prepare form data
        files = {
            "files": ("voice_sample.mp3", voice_sample, "audio/mpeg")
        }
        
        data = {
            "name": voice_name
        }
        
        if description:
            data["description"] = description
        
        if labels:
            # Labels should be sent as JSON string
            import json
            data["labels"] = json.dumps(labels)
        
        logger.info(f"Creating instant voice: {voice_name}")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    url,
                    headers=self.headers,
                    files=files,
                    data=data
                )
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Voice created successfully: {result.get('voice_id')}")
                
                return VoiceCreateResponse(**result)
                
            except httpx.HTTPError as e:
                logger.error(f"Failed to create voice: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.error(f"Response: {e.response.text}")
                raise
    
    async def update_agent_voice(
        self,
        agent_id: str,
        voice_id: str,
        first_message: Optional[str] = None
    ) -> AgentUpdateResponse:
        """
        Update agent configuration to use new voice.
        
        Args:
            agent_id: ElevenLabs agent ID
            voice_id: Voice ID to activate
            first_message: Optional custom greeting
            
        Returns:
            Agent update response
            
        Raises:
            httpx.HTTPError: If API request fails
        """
        url = f"{self.base_url}/convai/agents/{agent_id}"
        
        # Build update request
        agent_config = AgentConfig(
            voice=AgentVoiceConfig(voice_id=voice_id)
        )
        
        if first_message:
            agent_config.first_message = first_message
        
        update_request = AgentUpdateRequest(
            conversation_config=ConversationConfig(agent=agent_config)
        )
        
        logger.info(f"Updating agent {agent_id} with voice {voice_id}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.patch(
                    url,
                    headers={**self.headers, "Content-Type": "application/json"},
                    json=update_request.model_dump(exclude_none=True)
                )
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Agent updated successfully: {agent_id}")
                
                return AgentUpdateResponse(**result)
                
            except httpx.HTTPError as e:
                logger.error(f"Failed to update agent: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.error(f"Response: {e.response.text}")
                raise
    
    async def get_voice_info(self, voice_id: str) -> VoiceInfo:
        """
        Get voice details by ID.
        
        Args:
            voice_id: Voice ID
            
        Returns:
            Voice information
            
        Raises:
            httpx.HTTPError: If API request fails
        """
        url = f"{self.base_url}/voices/{voice_id}"
        
        logger.debug(f"Fetching voice info: {voice_id}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                
                result = response.json()
                return VoiceInfo(**result)
                
            except httpx.HTTPError as e:
                logger.error(f"Failed to get voice info: {e}")
                raise
    
    async def delete_voice(self, voice_id: str) -> bool:
        """
        Delete a cloned voice (cleanup).
        
        Args:
            voice_id: Voice ID to delete
            
        Returns:
            True if deletion successful
            
        Raises:
            httpx.HTTPError: If API request fails
        """
        url = f"{self.base_url}/voices/{voice_id}"
        
        logger.info(f"Deleting voice: {voice_id}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.delete(url, headers=self.headers)
                response.raise_for_status()
                
                logger.info(f"Voice deleted successfully: {voice_id}")
                return True
                
            except httpx.HTTPError as e:
                logger.error(f"Failed to delete voice: {e}")
                raise
