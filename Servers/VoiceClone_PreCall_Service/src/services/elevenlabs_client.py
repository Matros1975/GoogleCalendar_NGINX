"""
ElevenLabs API client for voice cloning and voice agent operations.

Handles all interactions with the ElevenLabs API including:
- Voice clone creation
- Voice agent call initiation
- Voice management
"""

import logging
import time
from typing import Optional, Dict, Any, List
import httpx
from httpx import AsyncClient, Response

from src.models.elevenlabs_models import (
    VoiceCloneAPIResponse,
    VoiceAgentCallResponse,
    VoiceDetails
)
from src.utils.exceptions import VoiceCloneException, VoiceAgentException, APIException
from src.config import get_settings

logger = logging.getLogger(__name__)


class ElevenLabsClient:
    """Client for ElevenLabs API operations."""
    
    def __init__(self):
        """Initialize ElevenLabs client."""
        self.settings = get_settings()
        self.base_url = self.settings.elevenlabs_api_base
        self.api_key = self.settings.elevenlabs_api_key
        self.agent_id = self.settings.elevenlabs_agent_id
        self.phone_number_id = self.settings.elevenlabs_phone_number_id
        self.timeout = self.settings.voice_clone_timeout
        
        # HTTP client with retry logic
        self.client: Optional[AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    async def connect(self) -> None:
        """Initialize HTTP client."""
        if not self.client:
            self.client = AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json"
                }
            )
            logger.info("ElevenLabs client initialized")
    
    async def disconnect(self) -> None:
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.info("ElevenLabs client closed")
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Response:
        """
        Make HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            **kwargs: Additional request parameters
            
        Returns:
            HTTP response
            
        Raises:
            APIException: If request fails after retries
        """
        if not self.client:
            await self.connect()
        
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                response = await self.client.request(method, endpoint, **kwargs)
                
                # Check for errors
                if response.status_code >= 400:
                    error_data = response.json() if response.content else {}
                    error_msg = error_data.get("detail", {}).get("message", response.text)
                    
                    # Don't retry on client errors (4xx)
                    if 400 <= response.status_code < 500:
                        raise APIException(
                            f"API error: {error_msg}",
                            status_code=response.status_code,
                            response_data=error_data
                        )
                    
                    # Retry on server errors (5xx)
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"API request failed (attempt {attempt + 1}/{max_retries}): "
                            f"{response.status_code} - {error_msg}"
                        )
                        await time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                        continue
                    else:
                        raise APIException(
                            f"API error after {max_retries} retries: {error_msg}",
                            status_code=response.status_code,
                            response_data=error_data
                        )
                
                return response
                
            except httpx.TimeoutException as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Request timeout (attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    await time.sleep(retry_delay * (2 ** attempt))
                    continue
                else:
                    raise APIException(f"Request timeout after {max_retries} retries: {e}")
            
            except httpx.RequestError as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Request error (attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    await time.sleep(retry_delay * (2 ** attempt))
                    continue
                else:
                    raise APIException(f"Request error after {max_retries} retries: {e}")
        
        raise APIException("Request failed after all retries")
    
    async def create_voice_clone(
        self,
        voice_sample_content: bytes,
        voice_name: str,
        description: Optional[str] = None,
    ) -> str:
        """
        Create voice clone from sample file.
        
        Args:
            voice_sample_content: Voice sample file bytes
            voice_name: Name for the cloned voice
            description: Optional description
            
        Returns:
            Cloned voice ID
            
        Raises:
            VoiceCloneException: If clone creation fails
        """
        try:
            logger.info(f"Creating voice clone: {voice_name}")
            start_time = time.time()
            
            # Prepare multipart form data
            files = {
                "files": ("voice_sample.mp3", voice_sample_content, "audio/mpeg")
            }
            
            data = {
                "name": voice_name,
                "description": description or f"Voice clone for {voice_name}",
                "labels": '{"source": "voiceclone_precall_service"}'
            }
            
            # Make request
            response = await self._make_request(
                "POST",
                "/voice-generation/generate-voice",
                files=files,
                data=data
            )
            
            # Parse response
            response_data = response.json()
            voice_id = response_data.get("voice_id")
            
            if not voice_id:
                raise VoiceCloneException("No voice_id in API response")
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.info(
                f"Voice clone created successfully: {voice_id} "
                f"(took {elapsed_ms}ms)"
            )
            
            return voice_id
            
        except APIException:
            raise
        except Exception as e:
            logger.error(f"Failed to create voice clone: {e}")
            raise VoiceCloneException(f"Voice clone creation failed: {e}")
    
    async def trigger_voice_agent_call(
        self,
        phone_number: str,
        voice_id: str,
        custom_variables: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Trigger ElevenLabs Voice Agent to make a call.
        
        Args:
            phone_number: Caller phone number (E.164 format)
            voice_id: ID of voice to use (cloned or preset)
            custom_variables: Context data for agent
            
        Returns:
            Call ID
            
        Raises:
            VoiceAgentException: If agent call fails
        """
        try:
            logger.info(f"Triggering voice agent call to {phone_number} with voice {voice_id}")
            
            # Build payload
            payload = {
                "agent_id": self.agent_id,
                "phone_number_id": self.phone_number_id,
                "to_number": phone_number,
                "voice_settings": {
                    "voice_id": voice_id
                }
            }
            
            if custom_variables:
                payload["custom_variables"] = custom_variables
            
            # Make request
            response = await self._make_request(
                "POST",
                f"/convai/agents/{self.agent_id}/calls",
                json=payload
            )
            
            # Parse response
            response_data = response.json()
            call_id = response_data.get("call_id")
            
            if not call_id:
                raise VoiceAgentException("No call_id in API response")
            
            logger.info(f"Voice agent call initiated: {call_id}")
            return call_id
            
        except APIException:
            raise
        except Exception as e:
            logger.error(f"Failed to trigger voice agent call: {e}")
            raise VoiceAgentException(f"Voice agent call failed: {e}")
    
    async def get_voice_details(self, voice_id: str) -> VoiceDetails:
        """
        Get details about a specific voice.
        
        Args:
            voice_id: Voice ID
            
        Returns:
            VoiceDetails model
        """
        try:
            response = await self._make_request(
                "GET",
                f"/voices/{voice_id}"
            )
            
            data = response.json()
            return VoiceDetails(**data)
            
        except Exception as e:
            logger.error(f"Failed to get voice details for {voice_id}: {e}")
            raise APIException(f"Failed to get voice details: {e}")
    
    async def list_voices(self) -> List[Dict[str, Any]]:
        """
        List all available voices in account.
        
        Returns:
            List of voice metadata dictionaries
        """
        try:
            response = await self._make_request(
                "GET",
                "/voices"
            )
            
            data = response.json()
            return data.get("voices", [])
            
        except Exception as e:
            logger.error(f"Failed to list voices: {e}")
            raise APIException(f"Failed to list voices: {e}")
    
    async def health_check(self) -> bool:
        """
        Check ElevenLabs API connectivity.
        
        Returns:
            True if API is reachable, False otherwise
        """
        try:
            # Try to list voices as a simple connectivity check
            await self.list_voices()
            return True
            
        except Exception as e:
            logger.error(f"ElevenLabs API health check failed: {e}")
            return False
