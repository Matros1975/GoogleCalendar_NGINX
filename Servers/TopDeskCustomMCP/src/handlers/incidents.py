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
    
    async def get_incident_by_number(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get an incident by ticket number.
        
        This method resolves the ticket number (e.g., 2510017 or 12345) to the UUID
        internally and returns full incident details. Users only need to provide
        the numeric ticket number, which is automatically formatted to TopDesk
        format "Ixxxx xxx" with proper zero-padding.
        
        Examples:
        - 2510017 becomes "I2510 017"
        - 12345 becomes "I0012 345" 
        - 999 becomes "I0000 999"
        
        Args:
            args: Tool arguments with ticket_number (integer)
            
        Returns:
            Incident details
        """
        ticket_number = args.get("ticket_number")
        
        if not ticket_number:
            return {"error": "Missing required parameter: ticket_number"}
        
        # Validate that ticket_number is an integer
        if not isinstance(ticket_number, int):
            return {"error": "ticket_number must be an integer (e.g., 2510017, 12345)"}
        
        # Validate ticket number range (0 to 9999999)
        if ticket_number < 0 or ticket_number > 9999999:
            return {"error": "ticket_number must be between 0 and 9999999"}
        
        logger.info(f"Getting incident by number: {ticket_number}")
        
        result = self.client.get_incident_by_number(ticket_number)
        return result
