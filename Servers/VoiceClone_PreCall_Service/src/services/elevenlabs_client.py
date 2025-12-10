"""
ElevenLabs API client for voice cloning and agent calls.
"""

import time
import asyncio
from typing import Optional, Dict, Any, List

import httpx

from src.config import get_settings
from src.utils.logger import get_logger
from src.utils.exceptions import VoiceCloneAPIException, VoiceAgentAPIException, APIException

logger = get_logger(__name__)


class ElevenLabsService:
    """
    Async HTTP client for ElevenLabs API.
    
    Handles voice cloning and voice agent call triggering.
    """
    
    def __init__(self):
        """Initialize ElevenLabs service."""
        self.settings = get_settings()
        self.base_url = self.settings.elevenlabs_api_base
        self.api_key = self.settings.elevenlabs_api_key
        self.agent_id = self.settings.elevenlabs_agent_id
        self.phone_number_id = self.settings.elevenlabs_phone_number_id
        self.timeout = httpx.Timeout(30.0)
        self.max_retries = 3
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests."""
        return {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }
    
    async def _retry_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """
        Execute HTTP request with retry logic.
        
        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request parameters
            
        Returns:
            HTTP response
            
        Raises:
            APIException: If request fails after retries
        """
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(method, url, **kwargs)
                    response.raise_for_status()
                    return response
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < self.max_retries - 1:
                    # Retry on server errors
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # Don't retry on client errors or final attempt
                    logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
                    raise APIException(f"API request failed: {e.response.status_code}")
                    
            except httpx.TimeoutException as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Request timeout (attempt {attempt + 1}/{self.max_retries}), retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Request timeout after {self.max_retries} attempts")
                    raise APIException("API request timed out")
                    
            except Exception as e:
                logger.error(f"Unexpected error in API request: {e}")
                raise APIException(f"API request failed: {str(e)}")
        
        raise APIException("Max retries exceeded")
    
    async def create_voice_clone(
        self,
        voice_sample_data: bytes,
        voice_name: str,
        description: Optional[str] = None,
    ) -> str:
        """
        Create voice clone from sample file.
        
        Args:
            voice_sample_data: Voice sample file bytes
            voice_name: Name for the cloned voice
            description: Optional description
        
        Returns:
            cloned_voice_id: String ID of created clone
        
        Raises:
            VoiceCloneAPIException: If clone creation fails
        """
        try:
            start_time = time.time()
            
            # Prepare multipart form data
            files = {
                "files": ("sample.mp3", voice_sample_data, "audio/mpeg")
            }
            
            data = {
                "name": voice_name,
                "description": description or f"Cloned voice for {voice_name}",
            }
            
            # Create voice clone
            url = f"{self.base_url}/voices/add"
            headers = {"xi-api-key": self.api_key}
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    data=data,
                    files=files
                )
                response.raise_for_status()
            
            result = response.json()
            voice_id = result.get("voice_id")
            
            if not voice_id:
                raise VoiceCloneAPIException("No voice_id in API response")
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.info(f"Voice clone created: {voice_id} ({elapsed_ms}ms)")
            
            return voice_id
            
        except httpx.HTTPStatusError as e:
            logger.error(f"ElevenLabs API error creating voice clone: {e.response.status_code} - {e.response.text}")
            raise VoiceCloneAPIException(f"Failed to create voice clone: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error creating voice clone: {e}")
            raise VoiceCloneAPIException(f"Failed to create voice clone: {str(e)}")
    
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
            call_id: ElevenLabs call ID
        
        Raises:
            VoiceAgentAPIException: If agent call fails
        """
        try:
            # Build payload
            payload = {
                "phone_number_id": self.phone_number_id,
                "to_number": phone_number,
                "voice_settings": {
                    "voice_id": voice_id,
                },
            }
            
            if custom_variables:
                payload["custom_variables"] = custom_variables
            
            # Trigger call
            url = f"{self.base_url}/convai/conversation"
            
            response = await self._retry_request(
                "POST",
                url,
                headers=self._get_headers(),
                json=payload
            )
            
            result = response.json()
            call_id = result.get("conversation_id") or result.get("call_id")
            
            if not call_id:
                raise VoiceAgentAPIException("No call_id in API response")
            
            logger.info(f"Voice agent call triggered: {call_id}")
            return call_id
            
        except APIException:
            raise VoiceAgentAPIException("Failed to trigger voice agent call")
        except Exception as e:
            logger.error(f"Error triggering voice agent call: {e}")
            raise VoiceAgentAPIException(f"Failed to trigger call: {str(e)}")
    
    async def get_voice_details(self, voice_id: str) -> Dict[str, Any]:
        """
        Get details about a specific voice.
        
        Args:
            voice_id: ElevenLabs voice ID
            
        Returns:
            Voice metadata dictionary
        """
        try:
            url = f"{self.base_url}/voices/{voice_id}"
            
            response = await self._retry_request(
                "GET",
                url,
                headers=self._get_headers()
            )
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error getting voice details: {e}")
            raise APIException(f"Failed to get voice details: {str(e)}")
    
    async def list_voices(self) -> List[Dict[str, Any]]:
        """
        List all available voices in account.
        
        Returns:
            List of voice metadata dictionaries
        """
        try:
            url = f"{self.base_url}/voices"
            
            response = await self._retry_request(
                "GET",
                url,
                headers=self._get_headers()
            )
            
            result = response.json()
            return result.get("voices", [])
            
        except Exception as e:
            logger.error(f"Error listing voices: {e}")
            raise APIException(f"Failed to list voices: {str(e)}")
    
    async def health_check(self) -> bool:
        """
        Check ElevenLabs API connectivity.
        
        Returns:
            True if API is reachable, False otherwise
        """
        try:
            url = f"{self.base_url}/voices"
            
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(url, headers=self._get_headers())
                response.raise_for_status()
            
            return True
            
        except Exception as e:
            logger.error(f"ElevenLabs health check failed: {e}")
            return False
