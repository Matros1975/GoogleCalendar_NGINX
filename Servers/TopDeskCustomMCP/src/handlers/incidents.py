"""Incident management handlers."""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class IncidentHandlers:
    """Handlers for incident operations."""
    
    def __init__(self, topdesk_client):
        """Initialize handlers with TopDesk client.
        
        Args:
            topdesk_client: TopDeskAPIClient instance
        """
        self.client = topdesk_client
    
    async def create_incident(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a TopDesk incident.
        
        Args:
            args: Tool arguments with caller_id, brief_description, request, etc.
            
        Returns:
            Incident creation result
        """
        caller_id = args.get("caller_id")
        brief_description = args.get("brief_description")
        request = args.get("request")
        category = args.get("category")
        priority = args.get("priority")
        
        # Validate required parameters
        if not caller_id:
            return {"error": "Missing required parameter: caller_id"}
        if not brief_description:
            return {"error": "Missing required parameter: brief_description"}
        if not request:
            return {"error": "Missing required parameter: request"}
        
        logger.info(f"Creating incident for caller {caller_id}")
        
        result = self.client.create_incident(
            caller_id=caller_id,
            brief_description=brief_description,
            request=request,
            category=category,
            priority=priority
        )
        
        return result
    
    async def get_incident(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get an incident by ID.
        
        Args:
            args: Tool arguments with incident_id
            
        Returns:
            Incident details
        """
        incident_id = args.get("incident_id")
        
        if not incident_id:
            return {"error": "Missing required parameter: incident_id"}
        
        logger.info(f"Getting incident {incident_id}")
        
        result = self.client.get_incident(incident_id)
        return result
    
    async def list_incidents(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List incidents with optional filters.
        
        Args:
            args: Tool arguments with optional status, caller_id, limit
            
        Returns:
            List of incidents
        """
        status = args.get("status")
        caller_id = args.get("caller_id")
        limit = args.get("limit", 10)
        
        logger.info(f"Listing incidents (status={status}, caller_id={caller_id}, limit={limit})")
        
        result = self.client.list_incidents(
            status=status,
            caller_id=caller_id,
            limit=limit
        )
        
        return result
