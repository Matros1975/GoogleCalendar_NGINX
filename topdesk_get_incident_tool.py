"""
TopDesk MCP Tool: Get Incident by Number
Add this to your TopDesk Custom MCP server to retrieve incidents by ticket number
"""

import asyncio
import httpx
from typing import Optional, Dict, Any
import os

class TopDeskIncidentRetriever:
    def __init__(self):
        self.base_url = "https://pietervanforeest-test.topdesk.net"
        self.username = "API_AIPilots"
        self.password = os.getenv('TOPDESK_PASSWORD', '')
        
    async def get_incident_by_number(self, ticket_number: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve incident by ticket number (e.g., "I2510 017")
        
        Args:
            ticket_number: The incident number like "I2510 017"
            
        Returns:
            Complete incident details or None if not found
        """
        
        async with httpx.AsyncClient() as client:
            try:
                # Step 1: Search for incident by number
                search_url = f"{self.base_url}/tas/api/incidents"
                
                params = {
                    'query': f'number=="{ticket_number}"',
                    'fields': 'id,number,briefDescription,status'
                }
                
                response = await client.get(
                    search_url,
                    params=params,
                    auth=(self.username, self.password),
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"Search failed with status {response.status_code}",
                        "details": response.text
                    }
                
                incidents = response.json()
                if not incidents or len(incidents) == 0:
                    return {
                        "success": False,
                        "error": f"No incident found with number {ticket_number}"
                    }
                
                # Step 2: Get full details using the UUID
                incident_id = incidents[0].get('id')
                if not incident_id:
                    return {
                        "success": False,
                        "error": "Incident found but no ID available"
                    }
                
                detail_url = f"{self.base_url}/tas/api/incidents/id/{incident_id}"
                
                detail_response = await client.get(
                    detail_url,
                    auth=(self.username, self.password),
                    headers={'Content-Type': 'application/json'}
                )
                
                if detail_response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"Detail fetch failed with status {detail_response.status_code}",
                        "details": detail_response.text
                    }
                
                full_incident = detail_response.json()
                
                # Return formatted response
                return {
                    "success": True,
                    "incident_number": full_incident.get('number'),
                    "incident_id": full_incident.get('id'),
                    "brief_description": full_incident.get('briefDescription'),
                    "status": full_incident.get('processingStatus', {}).get('name'),
                    "caller": {
                        "name": full_incident.get('caller', {}).get('dynamicName'),
                        "email": full_incident.get('caller', {}).get('email'),
                        "phone": full_incident.get('caller', {}).get('phoneNumber')
                    },
                    "category": full_incident.get('category', {}).get('name'),
                    "priority": full_incident.get('priority', {}).get('name'),
                    "creation_date": full_incident.get('creationDate'),
                    "target_date": full_incident.get('targetDate'),
                    "request_details": full_incident.get('request'),
                    "operator": full_incident.get('operator', {}).get('name') if full_incident.get('operator') else None,
                    "raw_response": full_incident
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Exception occurred: {str(e)}"
                }

# MCP Tool Definition (add this to your MCP server tools)
async def topdesk_get_incident(ticket_number: str) -> str:
    """
    Retrieve TopDesk incident details by ticket number.
    
    Args:
        ticket_number: The incident number (e.g., "I2510 017")
    
    Returns:
        JSON string with incident details
    """
    retriever = TopDeskIncidentRetriever()
    result = await retriever.get_incident_by_number(ticket_number)
    
    import json
    return json.dumps(result, indent=2, ensure_ascii=False)

# Tool registration (add this to your MCP server's tool list)
TOOL_DEFINITION = {
    "name": "topdesk_get_incident",
    "description": "Retrieve TopDesk incident details by ticket number (e.g., 'I2510 017')",
    "inputSchema": {
        "type": "object",
        "properties": {
            "ticket_number": {
                "type": "string",
                "description": "The incident number (e.g., 'I2510 017')"
            }
        },
        "required": ["ticket_number"]
    }
}