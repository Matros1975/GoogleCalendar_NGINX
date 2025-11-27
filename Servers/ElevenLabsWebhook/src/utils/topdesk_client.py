"""
TopDesk API client for creating incidents from call transcripts.

Implements async TopDesk API integration for the ElevenLabs webhook service.
"""

import os
import base64
import logging
from typing import Dict, Any, Optional

import httpx


logger = logging.getLogger(__name__)

# TopDesk ticket number format constants
TICKET_NUMBER_TOTAL_DIGITS = 7
TICKET_NUMBER_PREFIX_DIGITS = 4


class TopDeskClient:
    """Async client for TopDesk API integration."""
    
    def __init__(self):
        """Initialize TopDesk API client from environment variables."""
        self.base_url = os.getenv("TOPDESK_URL", "").rstrip('/')
        self.username = os.getenv("TOPDESK_USERNAME", "")
        self.password = os.getenv("TOPDESK_PASSWORD", "")
        
        # Create Basic Auth header
        if self.username and self.password:
            auth_string = f"{self.username}:{self.password}"
            auth_bytes = auth_string.encode('utf-8')
            auth_token = base64.b64encode(auth_bytes).decode('utf-8')
            self.auth_header = f"Basic {auth_token}"
        else:
            self.auth_header = ""
        
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": self.auth_header,
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                timeout=30.0
            )
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    def _format_ticket_number(self, number: str) -> str:
        """
        Format ticket number to TopDesk format "Ixxxx xxx".
        
        Args:
            number: Raw ticket number from API
            
        Returns:
            Formatted ticket number (e.g., "I2510 017")
        """
        # If already formatted, return as-is
        if number and number.startswith("I") and " " in number:
            return number
        
        # Extract digits only
        digits = ''.join(filter(str.isdigit, str(number)))
        
        if len(digits) < TICKET_NUMBER_TOTAL_DIGITS:
            digits = digits.zfill(TICKET_NUMBER_TOTAL_DIGITS)
        
        return f"I{digits[:TICKET_NUMBER_PREFIX_DIGITS]} {digits[TICKET_NUMBER_PREFIX_DIGITS:TICKET_NUMBER_TOTAL_DIGITS]}"
    
    async def create_incident(
        self,
        brief_description: str,
        request: str,
        conversation_id: str,
        caller_name: Optional[str] = None,
        caller_email: Optional[str] = None,
        category: Optional[str] = None,
        priority: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create incident in TopDesk.
        
        Args:
            brief_description: Short summary of the issue (max 80 chars)
            request: Detailed description of the customer's request
            conversation_id: ElevenLabs conversation ID for reference
            caller_name: Caller's name if mentioned
            caller_email: Caller's email if mentioned
            category: Issue category (optional)
            priority: Priority level (optional)
            
        Returns:
            dict with 'success', 'ticket_number', 'ticket_id', or 'error'
        """
        if not self.base_url:
            return {
                "success": False,
                "error": "TopDesk URL not configured (TOPDESK_URL)"
            }
        
        if not self.auth_header:
            return {
                "success": False,
                "error": "TopDesk credentials not configured (TOPDESK_USERNAME, TOPDESK_PASSWORD)"
            }
        
        # Build payload
        payload: Dict[str, Any] = {
            "briefDescription": brief_description[:80] if brief_description else "Call transcript",
            "request": f"ElevenLabs Conversation ID: {conversation_id}\n\n{request}"
        }
        
        # Add optional fields
        if category:
            payload["category"] = {"name": category}
        if priority:
            payload["priority"] = {"name": priority}
        if caller_email:
            payload["callerLookup"] = {"email": caller_email}
        
        try:
            client = await self._get_client()
            logger.info(f"Creating TopDesk incident for conversation {conversation_id}")
            
            response = await client.post(
                f"{self.base_url}/tas/api/incidents",
                json=payload
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                ticket_number = result.get("number", "")
                ticket_id = result.get("id", "")
                
                logger.info(f"TopDesk incident created: {ticket_number}")
                
                return {
                    "success": True,
                    "ticket_number": ticket_number,
                    "ticket_id": ticket_id,
                    "raw_response": result
                }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Failed to create TopDesk incident: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
                
        except httpx.TimeoutException:
            error_msg = "TopDesk API request timed out"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"TopDesk API error: {str(e)}"
            logger.exception(error_msg)
            return {"success": False, "error": error_msg}
    
    async def add_invisible_action(
        self,
        ticket_id: str,
        transcript: str
    ) -> bool:
        """
        Add transcript as invisible action to ticket.
        
        Args:
            ticket_id: TopDesk ticket ID (UUID from API response)
            transcript: Formatted transcript text
            
        Returns:
            True if successful, False otherwise
        """
        if not self.base_url or not self.auth_header:
            logger.error("TopDesk not configured, cannot add action")
            return False
        
        if not ticket_id:
            logger.error("No ticket ID provided for action")
            return False
        
        payload = {
            "memoText": f"Call Transcript:\n\n{transcript}",
            "invisibleForCaller": True
        }
        
        try:
            client = await self._get_client()
            logger.info(f"Adding invisible action to ticket {ticket_id}")
            
            response = await client.post(
                f"{self.base_url}/tas/api/incidents/id/{ticket_id}/actions",
                json=payload
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Transcript added to ticket {ticket_id}")
                return True
            else:
                logger.error(
                    f"Failed to add action to ticket {ticket_id}: "
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            logger.exception(f"Error adding action to ticket {ticket_id}: {e}")
            return False
