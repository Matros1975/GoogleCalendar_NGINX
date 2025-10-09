"""Status and reference data handlers."""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class StatusHandlers:
    """Handlers for status and reference data operations."""
    
    def __init__(self, topdesk_client):
        """Initialize handlers with TopDesk client.
        
        Args:
            topdesk_client: TopDeskAPIClient instance
        """
        self.client = topdesk_client
    
    async def get_categories(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get list of incident categories.
        
        Args:
            args: Tool arguments (none required)
            
        Returns:
            List of categories
        """
        logger.info("Getting incident categories")
        result = self.client.get_categories()
        return result
    
    async def get_priorities(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get list of incident priorities.
        
        Args:
            args: Tool arguments (none required)
            
        Returns:
            List of priorities
        """
        logger.info("Getting incident priorities")
        result = self.client.get_priorities()
        return result
