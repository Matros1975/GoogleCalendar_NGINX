"""Main entry point for TopDesk Custom MCP server."""

import os
import sys
import json
import logging
from typing import List

from .auth import BearerTokenValidator
from .topdesk_client import TopDeskAPIClient
from .mcp_server import MCPServer
from .handlers import IncidentHandlers, PersonHandlers, StatusHandlers


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def get_env_var(name: str, required: bool = True, default: str = None) -> str:
    """Get environment variable with validation.
    
    Args:
        name: Variable name
        required: Whether variable is required
        default: Default value if not required
        
    Returns:
        Variable value
        
    Raises:
        ValueError: If required variable is missing
    """
    value = os.environ.get(name, default)
    if required and not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def parse_bearer_tokens(tokens_str: str) -> List[str]:
    """Parse bearer tokens from JSON string or comma-separated list.
    
    Args:
        tokens_str: JSON array string or comma-separated tokens
        
    Returns:
        List of token strings
    """
    # Try parsing as JSON array first
    try:
        tokens = json.loads(tokens_str)
        if isinstance(tokens, list):
            return [str(t) for t in tokens]
    except (json.JSONDecodeError, ValueError):
        pass
    
    # Fall back to comma-separated
    return [t.strip() for t in tokens_str.split(',') if t.strip()]


def main():
    """Main entry point."""
    logger.info("Starting TopDesk Custom MCP Server...")
    
    try:
        # Load configuration from environment
        topdesk_base_url = get_env_var("TOPDESK_BASE_URL")
        topdesk_username = get_env_var("TOPDESK_USERNAME")
        topdesk_password = get_env_var("TOPDESK_PASSWORD")
        
        bearer_tokens_str = get_env_var("BEARER_TOKENS")
        bearer_tokens = parse_bearer_tokens(bearer_tokens_str)
        
        mcp_host = get_env_var("MCP_HOST", required=False, default="0.0.0.0")
        mcp_port = int(get_env_var("MCP_PORT", required=False, default="3002"))
        
        logger.info(f"Configuration loaded:")
        logger.info(f"  TopDesk URL: {topdesk_base_url}")
        logger.info(f"  TopDesk Username: {topdesk_username}")
        logger.info(f"  Bearer Tokens: {len(bearer_tokens)} configured")
        logger.info(f"  MCP Host: {mcp_host}")
        logger.info(f"  MCP Port: {mcp_port}")
        
        # Initialize components
        bearer_validator = BearerTokenValidator(bearer_tokens)
        topdesk_client = TopDeskAPIClient(topdesk_base_url, topdesk_username, topdesk_password)
        
        # Initialize handlers
        incident_handlers = IncidentHandlers(topdesk_client)
        person_handlers = PersonHandlers(topdesk_client)
        status_handlers = StatusHandlers(topdesk_client)
        
        # Create MCP server
        server = MCPServer(
            server_name="TopDeskCustomMCP",
            server_version="1.0.0",
            bearer_validator=bearer_validator,
            host=mcp_host,
            port=mcp_port
        )
        
        # Register incident tools
        server.register_tool(
            name="topdesk_create_incident",
            description="Create a new TopDesk incident",
            input_schema={
                "type": "object",
                "properties": {
                    "caller_id": {
                        "type": "string",
                        "description": "UUID of the caller (person)"
                    },
                    "brief_description": {
                        "type": "string",
                        "description": "Short description of the incident"
                    },
                    "request": {
                        "type": "string",
                        "description": "Detailed description of the issue"
                    },
                    "category": {
                        "type": "string",
                        "description": "Incident category name (optional)"
                    },
                    "priority": {
                        "type": "string",
                        "description": "Incident priority name (optional)"
                    }
                },
                "required": ["caller_id", "brief_description", "request"]
            },
            handler=incident_handlers.create_incident
        )
        
        server.register_tool(
            name="topdesk_get_incident",
            description="Get a specific incident by ID",
            input_schema={
                "type": "object",
                "properties": {
                    "incident_id": {
                        "type": "string",
                        "description": "UUID of the incident"
                    }
                },
                "required": ["incident_id"]
            },
            handler=incident_handlers.get_incident
        )
        
        server.register_tool(
            name="topdesk_list_incidents",
            description="List incidents with optional filters",
            input_schema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by status name (optional)"
                    },
                    "caller_id": {
                        "type": "string",
                        "description": "Filter by caller UUID (optional)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of incidents to return (default: 10)"
                    }
                }
            },
            handler=incident_handlers.list_incidents
        )
        
        # Register person tools
        server.register_tool(
            name="topdesk_get_person",
            description="Get a specific person by ID",
            input_schema={
                "type": "object",
                "properties": {
                    "person_id": {
                        "type": "string",
                        "description": "UUID of the person"
                    }
                },
                "required": ["person_id"]
            },
            handler=person_handlers.get_person
        )
        
        server.register_tool(
            name="topdesk_search_persons",
            description="Search for persons by query",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)"
                    }
                },
                "required": ["query"]
            },
            handler=person_handlers.search_persons
        )
        
        # Register status tools
        server.register_tool(
            name="topdesk_get_categories",
            description="Get list of incident categories",
            input_schema={
                "type": "object",
                "properties": {}
            },
            handler=status_handlers.get_categories
        )
        
        server.register_tool(
            name="topdesk_get_priorities",
            description="Get list of incident priorities",
            input_schema={
                "type": "object",
                "properties": {}
            },
            handler=status_handlers.get_priorities
        )
        
        # Start server
        logger.info("All tools registered, starting server...")
        server.start()
        
    except Exception as e:
        logger.exception("Failed to start server")
        sys.exit(1)


if __name__ == "__main__":
    main()
