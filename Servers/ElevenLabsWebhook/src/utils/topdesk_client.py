"""
TopDesk API client for creating incidents from call transcripts.

Implements async TopDesk API integration for the ElevenLabs webhook service.
"""

import os
import base64
from typing import Dict, Any, Optional

import httpx
from src.utils.logger import setup_logger
import urllib.parse

logger = setup_logger()

# TopDesk ticket number format constants
TICKET_NUMBER_TOTAL_DIGITS = 7
TICKET_NUMBER_PREFIX_DIGITS = 4

# Valid TopDesk categories (from your instance)
VALID_CATEGORIES = [
    "Core applicaties",
    "Werkplek hardware",
    "Netwerk",
    "Wachtwoord wijziging"
]

# Valid TopDesk priorities (from your instance)
VALID_PRIORITIES = [
    "P1 (I&A)",
    "P2 (I&A)",
    "P3 (I&A)",
    "P4 (I&A)"
]


class TopDeskClient:
    """Async client for TopDesk API integration."""
    
    def __init__(self):
        """Initialize TopDesk API client from environment variables."""
        self.base_url = os.getenv("TOPDESK_URL", "").rstrip('/')
        self.username = os.getenv("TOPDESK_USERNAME", "")
        self.password = os.getenv("TOPDESK_PASSWORD", "")
        
        # Log configuration for debugging
        logger.info(f"TopDeskClient initialized with base_url: {self.base_url}")
        logger.info(f"TopDeskClient username: {self.username}")
        
        # Create Basic Auth header
        if self.username and self.password:
            auth_string = f"{self.username}:{self.password}"
            auth_bytes = auth_string.encode('utf-8')
            auth_token = base64.b64encode(auth_bytes).decode('utf-8')
            self.auth_header = f"Basic {auth_token}"
        else:
            self.auth_header = ""
        
        self._client: Optional[httpx.AsyncClient] = None
        self._categories_cache: Optional[list] = None
        self._priorities_cache: Optional[list] = None
    
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
    
    async def get_categories(self) -> list[str]:
        """
        Fetch available incident categories from TopDesk.
        
        Results are cached to avoid repeated API calls.
        
        Returns:
            List of category names (e.g., ["Core applicaties", "Werkplek hardware"])
            Empty list if API call fails or not configured.
        """
        if self._categories_cache is not None:
            return self._categories_cache
        
        if not self.base_url or not self.auth_header:
            logger.warning("TopDesk not configured, cannot fetch categories")
            return []
        
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/incidents/categories")
            
            if response.status_code == 200:
                categories = response.json()
                # Extract category names
                self._categories_cache = [cat.get("name", "") for cat in categories if cat.get("name")]
                logger.info(f"Fetched {len(self._categories_cache)} categories from TopDesk")
                return self._categories_cache
            else:
                logger.error(f"Failed to fetch categories: HTTP {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error fetching categories from TopDesk: {e}")
            return []
    
    async def get_priorities(self) -> list[str]:
        """
        Fetch available incident priorities from TopDesk.
        
        Results are cached to avoid repeated API calls.
        
        Returns:
            List of priority names (e.g., ["P1 (I&A)", "P2 (I&A)"])
            Empty list if API call fails or not configured.
        """
        if self._priorities_cache is not None:
            return self._priorities_cache
        
        if not self.base_url or not self.auth_header:
            logger.warning("TopDesk not configured, cannot fetch priorities")
            return []
        
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/incidents/priorities")
            
            if response.status_code == 200:
                priorities = response.json()
                # Extract priority names
                self._priorities_cache = [pri.get("name", "") for pri in priorities if pri.get("name")]
                logger.info(f"Fetched {len(self._priorities_cache)} priorities from TopDesk")
                return self._priorities_cache
            else:
                logger.error(f"Failed to fetch priorities: HTTP {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error fetching priorities from TopDesk: {e}")
            return []
    
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

    async def validate_employee_number(self, employee_number: str) -> dict | None:
        """
        Validate if employee number exists in TopDesk.
        
        Args:
            employee_number: Employee number to validate
            
        Returns:
            Person object if found, None otherwise
        """
        if not employee_number or not self.base_url or not self.auth_header:
            return None
        
        try:
            query = f"employeeNumber=={employee_number}"
            encoded_query = urllib.parse.quote(query, safe="=")
            
            client = await self._get_client()
            response = await client.get(
                f"{self.base_url}/persons",
                params={
                    "query": encoded_query,
                    "start": 0,
                    "page_size": 50
                }
            )
            
            if response.status_code == 200:
                persons = response.json()
                for person in persons:
                    # Defensive check for exact match
                    if str(person.get("employeeNumber", "")).strip() == str(employee_number):
                        return person
            
            return None
            
        except Exception as e:
            logger.error(f"Error validating employee number {employee_number}: {e}")
            return None
    
    async def create_incident(
        self,
        brief_description: str,
        request: str,
        conversation_id: str,
        employee_number: Optional[str] = None,  
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
            employee_number: Employee number (REQUIRED for ticket creation)
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
        
        # Employee number is REQUIRED - should have been validated before calling this
        if not employee_number:
            return {
                "success": False,
                "error": "Employee number is required for ticket creation"
            }
        
        # Build payload with employee number lookup
        payload: Dict[str, Any] = {
            "briefDescription": brief_description[:80] if brief_description else "Call transcript",
            "request": f"ElevenLabs Conversation ID: {conversation_id}\n\n{request}",
            "callerLookup": {
                "employeeNumber": str(employee_number)
            }
        }
        
        # Add optional fields only if they match valid TopDesk values
        if category and category in VALID_CATEGORIES:
            payload["category"] = {"name": category}
            logger.debug(f"Using category: {category}")
        else:
            if category:
                logger.warning(f"Invalid category '{category}', omitting from payload")
            # Use default category
            payload["category"] = {"name": "Core applicaties"}
            logger.debug("Using default category: Core applicaties")
            
        if priority and priority in VALID_PRIORITIES:
            payload["priority"] = {"name": priority}
            logger.debug(f"Using priority: {priority}")
        else:
            if priority:
                logger.warning(f"Invalid priority '{priority}', omitting from payload")
            # Use default priority
            payload["priority"] = {"name": "P3 (I&A)"}
            logger.debug("Using default priority: P3 (I&A)")
            
        # Note: callerLookup by employeeNumber will find the correct person
        logger.info(f"Creating TopDesk incident for conversation {conversation_id} with employee {employee_number}")
        try:
            client = await self._get_client()
            url = f"{self.base_url}/incidents"
            logger.info(f"Creating TopDesk incident for conversation {conversation_id} with employee {employee_number}")
            logger.info(f"POST URL: {url}")
            logger.debug(f"Payload: {payload}")
            
            response = await client.post(
                url,
                json=payload
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                ticket_number = result.get("number", "")
                ticket_id = result.get("id", "")
                
                logger.info(f"TopDesk incident created: {ticket_number} for employee {employee_number}")
                
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
        
        # TopDesk requires PATCH to incidents endpoint with action field
        payload = {
            "action": f"Call Transcript:\n\n{transcript}",
            "actionInvisibleForCaller": True
        }
        
        try:
            client = await self._get_client()
            logger.info(f"Adding invisible action to ticket {ticket_id}")
            
            url = f"{self.base_url}/incidents/id/{ticket_id}"
            logger.debug(f"PATCH {url}")
            logger.debug(f"Payload: {payload}")
            
            response = await client.patch(
                url,
                json=payload
            )
            
            if response.status_code in [200, 201, 204]:
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