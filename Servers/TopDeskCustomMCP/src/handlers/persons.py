"""Person management handlers."""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class PersonHandlers:
    """Handlers for person operations."""
    
    def __init__(self, topdesk_client):
        """Initialize handlers with TopDesk client.
        
        Args:
            topdesk_client: TopDeskAPIClient instance
        """
        self.client = topdesk_client
    
    async def get_person(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get a person by ID.
        
        Args:
            args: Tool arguments with person_id
            
        Returns:
            Person details
        """
        person_id = args.get("person_id")
        
        if not person_id:
            return {"error": "Missing required parameter: person_id"}
        
        logger.info(f"Getting person {person_id}")
        
        result = self.client.get_person(person_id)
        return result
    
    async def search_persons(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search for persons.
        
        Args:
            args: Tool arguments with query and optional limit
            
        Returns:
            List of matching persons
        """
        query = args.get("query")
        limit = args.get("limit", 10)
        
        if not query:
            return {"error": "Missing required parameter: query"}
        
        logger.info(f"Searching persons: {query}")
        
        result = self.client.search_persons(query=query, limit=limit)
        return result
