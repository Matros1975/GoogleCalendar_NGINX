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
