"""TopDesk API client with proper parameter mapping."""

import base64
import logging
from typing import Dict, Any, List, Optional
import requests


logger = logging.getLogger(__name__)


class TopDeskAPIClient:
    """Client for TopDesk API integration."""
    
    def __init__(self, base_url: str, username: str, password: str):
        """Initialize TopDesk API client.
        
        Args:
            base_url: Base URL of TopDesk instance (e.g., https://company.topdesk.net/tas/api)
            username: TopDesk API username
            password: TopDesk API password/token
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        
        # Create Basic Auth header
        auth_string = f"{username}:{password}"
        auth_bytes = auth_string.encode('utf-8')
        auth_token = base64.b64encode(auth_bytes).decode('utf-8')
        
        self.headers = {
            'Authorization': f'Basic {auth_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        logger.info(f"TopDesk API client initialized for {base_url}")
    
    def create_incident(
        self,
        caller_id: str,
        brief_description: str,
        request: str,
        category: Optional[str] = None,
        priority: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a TopDesk incident with proper parameter mapping.
        
        Args:
            caller_id: UUID of the caller (person)
            brief_description: Short description of the incident
            request: Detailed description of the issue
            category: Category name (optional)
            priority: Priority name (optional)
            
        Returns:
            Dictionary with incident details or error
        """
        # Transform MCP parameters to TopDesk API format
        payload: Dict[str, Any] = {
            "briefDescription": brief_description,
            "request": request,
            "caller": {"id": caller_id}
        }
        
        # Add optional fields
        if category:
            payload["category"] = {"name": category}
        if priority:
            payload["priority"] = {"name": priority}
        
        try:
            logger.info(f"Creating incident for caller {caller_id}")
            response = requests.post(
                f"{self.base_url}/incidents",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"Incident created: {result.get('number')}")
                return {
                    'success': True,
                    'incident_number': result.get('number'),
                    'incident_id': result.get('id'),
                    'caller_name': result.get('caller', {}).get('dynamicName'),
                    'category': result.get('category', {}).get('name'),
                    'priority': result.get('priority', {}).get('name'),
                    'status': result.get('processingStatus', {}).get('name'),
                    'raw_response': result
                }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Failed to create incident: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
                
        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            logger.exception("Error creating incident")
            return {
                'success': False,
                'error': error_msg
            }
    
    def get_incident(self, incident_id: str) -> Dict[str, Any]:
        """Get a specific incident by ID.
        
        Args:
            incident_id: UUID of the incident
            
        Returns:
            Dictionary with incident details or error
        """
        try:
            logger.info(f"Getting incident {incident_id}")
            response = requests.get(
                f"{self.base_url}/incidents/id/{incident_id}",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'incident': result
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.exception("Error getting incident")
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_incidents(
        self,
        status: Optional[str] = None,
        caller_id: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """List incidents with optional filters.
        
        Args:
            status: Filter by status name
            caller_id: Filter by caller UUID
            limit: Maximum number of incidents to return
            
        Returns:
            Dictionary with list of incidents or error
        """
        try:
            params: Dict[str, Any] = {'page_size': limit}
            
            # Build query parameters
            query_parts = []
            if status:
                query_parts.append(f'processingStatus.name=={status}')
            if caller_id:
                query_parts.append(f'caller.id=={caller_id}')
            
            if query_parts:
                params['query'] = ';'.join(query_parts)
            
            logger.info(f"Listing incidents with filters: {params}")
            response = requests.get(
                f"{self.base_url}/incidents",
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            if response.status_code in [200, 206]:  # 206 = partial content
                incidents = response.json()
                return {
                    'success': True,
                    'incidents': incidents,
                    'count': len(incidents)
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.exception("Error listing incidents")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_incident_by_number(self, ticket_number: int) -> Dict[str, Any]:
        """Get an incident by ticket number (e.g., 2510017).
        
        This method first searches for the incident by number, then retrieves
        full details using the UUID. This resolves the ticket number to UUID
        internally, so users only need to provide the numeric ticket number.
        
        The ticket number is automatically formatted to TopDesk format "Ixxxx xxx".
        For example: 2510017 becomes "I2510 017"
        
        Args:
            ticket_number: The incident number as integer (e.g., 2510017)
            
        Returns:
            Dictionary with incident details or error
        """
        try:
            # Format the ticket number to TopDesk format "Ixxxx xxx"
            # Pad with leading zeros to ensure exactly 7 digits
            ticket_str = f"{ticket_number:07d}"  # Pad to 7 digits with leading zeros
            
            if ticket_number < 0 or ticket_number > 9999999:
                return {
                    'success': False,
                    'error': f"Ticket number must be between 0 and 9999999, got: {ticket_number}"
                }
            
            formatted_ticket = f"I{ticket_str[:4]} {ticket_str[4:]}"
            
            logger.info(f"Searching for incident by number: {ticket_number} (formatted as: {formatted_ticket})")
            
            # Step 1: Search for incident by number
            search_params = {
                'query': f'number=="{formatted_ticket}"',
                'fields': 'id,number,briefDescription'
            }
            
            search_response = requests.get(
                f"{self.base_url}/incidents",
                headers=self.headers,
                params=search_params,
                timeout=30
            )
            
            if search_response.status_code not in [200, 204]:
                return {
                    'success': False,
                    'error': f"Search failed: HTTP {search_response.status_code}: {search_response.text}"
                }
            
            # Handle 204 No Content (no results found)
            if search_response.status_code == 204:
                return {
                    'success': False,
                    'error': f"No incident found with number {ticket_number} (searched as '{formatted_ticket}')"
                }
            
            incidents = search_response.json()
            
            if not incidents or len(incidents) == 0:
                return {
                    'success': False,
                    'error': f"No incident found with number {ticket_number} (searched as '{formatted_ticket}')"
                }
            
            # Step 2: Get full incident details using UUID
            incident_id = incidents[0].get('id')
            if not incident_id:
                return {
                    'success': False,
                    'error': f"Incident found but no ID available for {ticket_number}"
                }
            
            logger.info(f"Found incident {ticket_number}, retrieving full details for UUID: {incident_id}")
            
            detail_response = requests.get(
                f"{self.base_url}/incidents/id/{incident_id}",
                headers=self.headers,
                timeout=30
            )
            
            if detail_response.status_code != 200:
                return {
                    'success': False,
                    'error': f"Detail fetch failed: HTTP {detail_response.status_code}: {detail_response.text}"
                }
            
            full_incident = detail_response.json()
            
            # Return formatted response similar to create_incident
            return {
                'success': True,
                'incident_number': full_incident.get('number'),
                'incident_id': full_incident.get('id'),
                'brief_description': full_incident.get('briefDescription'),
                'status': full_incident.get('processingStatus', {}).get('name'),
                'caller_name': full_incident.get('caller', {}).get('dynamicName'),
                'caller_email': full_incident.get('caller', {}).get('email'),
                'caller_phone': full_incident.get('caller', {}).get('phoneNumber'),
                'category': full_incident.get('category', {}).get('name'),
                'priority': full_incident.get('priority', {}).get('name'),
                'creation_date': full_incident.get('creationDate'),
                'target_date': full_incident.get('targetDate'),
                'request_details': full_incident.get('request'),
                'operator': full_incident.get('operator', {}).get('name') if full_incident.get('operator') else None,
                'branch': full_incident.get('callerBranch', {}).get('name'),
                'raw_response': full_incident
            }
                
        except Exception as e:
            logger.exception(f"Error getting incident by number {ticket_number}")
            return {
                'success': False,
                'error': f"Exception: {str(e)}"
            }
    
    def get_person(self, person_id: str) -> Dict[str, Any]:
        """Get a specific person by ID.
        
        Args:
            person_id: UUID of the person
            
        Returns:
            Dictionary with person details or error
        """
        try:
            logger.info(f"Getting person {person_id}")
            response = requests.get(
                f"{self.base_url}/persons/id/{person_id}",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'person': result
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.exception("Error getting person")
            return {
                'success': False,
                'error': str(e)
            }
    
    def search_persons(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for persons.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            Dictionary with list of persons or error
        """
        try:
            params = {
                'query': query,
                'page_size': limit
            }
            
            logger.info(f"Searching persons: {query}")
            response = requests.get(
                f"{self.base_url}/persons",
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            if response.status_code in [200, 206]:
                persons = response.json()
                return {
                    'success': True,
                    'persons': persons,
                    'count': len(persons)
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.exception("Error searching persons")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_categories(self) -> Dict[str, Any]:
        """Get list of incident categories.
        
        Returns:
            Dictionary with list of categories or error
        """
        try:
            logger.info("Getting incident categories")
            response = requests.get(
                f"{self.base_url}/incidents/categories",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                categories = response.json()
                return {
                    'success': True,
                    'categories': categories
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.exception("Error getting categories")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_priorities(self) -> Dict[str, Any]:
        """Get list of incident priorities.
        
        Returns:
            Dictionary with list of priorities or error
        """
        try:
            logger.info("Getting incident priorities")
            response = requests.get(
                f"{self.base_url}/incidents/priorities",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                priorities = response.json()
                return {
                    'success': True,
                    'priorities': priorities
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.exception("Error getting priorities")
            return {
                'success': False,
                'error': str(e)
            }
