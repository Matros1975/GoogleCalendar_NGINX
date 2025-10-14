#!/usr/bin/env python3
"""
Complete examples for using the TopDesk Custom MCP 'get_incident_by_number' tool.

This script demonstrates multiple ways to interact with the new tool that retrieves
TopDesk incidents using human-readable ticket numbers instead of UUIDs.
"""

import asyncio
import httpx
import json
import os
from typing import Dict, Any, Optional

# Configuration
MCP_SERVER_URL = "https://localhost/topdesk/mcp/call"
BEARER_TOKEN = "e3707c16425c14fa417e2384a12748c0c7c51dfdfd1714c58992215983f33257"  # Update with your token

class TopDeskMCPClient:
    """Client for interacting with TopDesk Custom MCP server."""
    
    def __init__(self, server_url: str, bearer_token: str):
        self.server_url = server_url
        self.bearer_token = bearer_token
        
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool."""
        payload = {
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                self.server_url,
                headers=headers,
                json=payload,
                timeout=30.0
            )
            return response.json()
    
    async def get_incident_by_number(self, ticket_number: str) -> Dict[str, Any]:
        """Get incident details by ticket number."""
        return await self.call_tool("topdesk_get_incident_by_number", {
            "ticket_number": ticket_number
        })

def extract_incident_data(mcp_response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract incident data from MCP response."""
    try:
        content = mcp_response.get("result", {}).get("content", [])
        if content and len(content) > 0:
            text_content = content[0].get("text", "")
            return json.loads(text_content)
    except (json.JSONDecodeError, KeyError):
        pass
    return None

async def example_1_basic_usage():
    """Example 1: Basic usage - Get a single incident."""
    print("=== Example 1: Basic Usage ===")
    
    client = TopDeskMCPClient(MCP_SERVER_URL, BEARER_TOKEN)
    
    # Get incident details
    ticket_number = "I2510 017"
    print(f"Retrieving incident: {ticket_number}")
    
    response = await client.get_incident_by_number(ticket_number)
    incident_data = extract_incident_data(response)
    
    if incident_data and incident_data.get("success"):
        print(f"✅ Found incident:")
        print(f"   Number: {incident_data.get('incident_number')}")
        print(f"   Description: {incident_data.get('brief_description')}")
        print(f"   Status: {incident_data.get('status')}")
        print(f"   Caller: {incident_data.get('caller_name')}")
        print(f"   Priority: {incident_data.get('priority')}")
    else:
        error_msg = incident_data.get("error") if incident_data else "Unknown error"
        print(f"❌ Error: {error_msg}")
    
    print()

async def example_2_multiple_incidents():
    """Example 2: Retrieve multiple incidents."""
    print("=== Example 2: Multiple Incidents ===")
    
    client = TopDeskMCPClient(MCP_SERVER_URL, BEARER_TOKEN)
    
    ticket_numbers = ["I2510 017", "I2510 018", "I2510 999"]  # Last one doesn't exist
    
    for ticket_number in ticket_numbers:
        print(f"Checking ticket: {ticket_number}")
        
        response = await client.get_incident_by_number(ticket_number)
        incident_data = extract_incident_data(response)
        
        if incident_data and incident_data.get("success"):
            print(f"  ✅ {incident_data.get('brief_description')} [{incident_data.get('status')}]")
        else:
            error_msg = incident_data.get("error") if incident_data else "Unknown error"
            print(f"  ❌ {error_msg}")
    
    print()

async def example_3_detailed_information():
    """Example 3: Extract detailed information from incident."""
    print("=== Example 3: Detailed Information ===")
    
    client = TopDeskMCPClient(MCP_SERVER_URL, BEARER_TOKEN)
    
    ticket_number = "I2510 017"
    response = await client.get_incident_by_number(ticket_number)
    incident_data = extract_incident_data(response)
    
    if incident_data and incident_data.get("success"):
        print(f"Incident Details for {ticket_number}:")
        print(f"  ID: {incident_data.get('incident_id')}")
        print(f"  Description: {incident_data.get('brief_description')}")
        print(f"  Status: {incident_data.get('status')}")
        print(f"  Category: {incident_data.get('category')}")
        print(f"  Priority: {incident_data.get('priority')}")
        print(f"  Created: {incident_data.get('creation_date')}")
        print(f"  Target: {incident_data.get('target_date')}")
        print(f"  Branch: {incident_data.get('branch')}")
        
        # Caller information
        print(f"  Caller:")
        print(f"    Name: {incident_data.get('caller_name')}")
        print(f"    Email: {incident_data.get('caller_email')}")
        print(f"    Phone: {incident_data.get('caller_phone')}")
        
        # Operator (if assigned)
        operator = incident_data.get('operator')
        print(f"  Operator: {operator if operator else 'Not assigned'}")
        
        # Request details (truncated for display)
        request = incident_data.get('request_details', '')
        if len(request) > 100:
            request = request[:100] + "..."
        print(f"  Request: {request}")
    
    print()

async def example_4_error_handling():
    """Example 4: Proper error handling."""
    print("=== Example 4: Error Handling ===")
    
    client = TopDeskMCPClient(MCP_SERVER_URL, BEARER_TOKEN)
    
    # Test with non-existent ticket
    invalid_tickets = ["I2510 999", "INVALID123", ""]
    
    for ticket in invalid_tickets:
        print(f"Testing invalid ticket: '{ticket}'")
        
        try:
            response = await client.get_incident_by_number(ticket)
            incident_data = extract_incident_data(response)
            
            if incident_data:
                if incident_data.get("success"):
                    print(f"  ✅ Unexpected success for {ticket}")
                else:
                    print(f"  ❌ Expected error: {incident_data.get('error')}")
            else:
                print(f"  ❌ Failed to parse response")
                
        except Exception as e:
            print(f"  ❌ Exception: {str(e)}")
    
    print()

def example_5_curl_equivalent():
    """Example 5: Show curl equivalent commands."""
    print("=== Example 5: Curl Equivalents ===")
    
    ticket_number = "I2510 017"
    
    # Basic curl command
    curl_cmd = f'''curl -k -X POST "{MCP_SERVER_URL}" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer {BEARER_TOKEN}" \\
  -d '{{
    "method": "tools/call",
    "params": {{
      "name": "topdesk_get_incident_by_number",
      "arguments": {{
        "ticket_number": "{ticket_number}"
      }}
    }}
  }}\''''
    
    print("To call this tool with curl:")
    print(curl_cmd)
    print()
    
    # Formatted output with jq
    curl_with_jq = curl_cmd + " | jq '.result.content[0].text | fromjson'"
    print("To get formatted output (requires jq):")
    print(curl_with_jq)
    print()

def example_6_javascript_fetch():
    """Example 6: JavaScript fetch equivalent."""
    print("=== Example 6: JavaScript Fetch ===")
    
    js_code = f'''// JavaScript/Node.js example
const fetch = require('node-fetch');
const https = require('https');

const agent = new https.Agent({{ rejectUnauthorized: false }});

async function getIncidentByNumber(ticketNumber) {{
  const response = await fetch('{MCP_SERVER_URL}', {{
    method: 'POST',
    headers: {{
      'Content-Type': 'application/json',
      'Authorization': 'Bearer {BEARER_TOKEN}'
    }},
    body: JSON.stringify({{
      method: 'tools/call',
      params: {{
        name: 'topdesk_get_incident_by_number',
        arguments: {{ ticket_number: ticketNumber }}
      }}
    }}),
    agent: agent
  }});
  
  const result = await response.json();
  const incidentData = JSON.parse(result.result.content[0].text);
  return incidentData;
}}

// Usage
getIncidentByNumber('I2510 017')
  .then(data => console.log(JSON.stringify(data, null, 2)))
  .catch(console.error);'''
    
    print(js_code)
    print()

async def main():
    """Run all examples."""
    print("TopDesk Custom MCP: Get Incident by Number - Examples")
    print("=" * 60)
    print()
    
    # Check if we can reach the server
    try:
        client = TopDeskMCPClient(MCP_SERVER_URL, BEARER_TOKEN)
        test_response = await client.get_incident_by_number("I2510 017")
        
        if "result" in test_response or "error" in test_response:
            print("✅ MCP Server is reachable")
            print()
            
            # Run async examples
            await example_1_basic_usage()
            await example_2_multiple_incidents()
            await example_3_detailed_information()
            await example_4_error_handling()
            
            # Run sync examples
            example_5_curl_equivalent()
            example_6_javascript_fetch()
            
        else:
            print("❌ MCP Server not responding correctly")
            print("Response:", test_response)
            
    except Exception as e:
        print(f"❌ Could not connect to MCP Server: {str(e)}")
        print(f"URL: {MCP_SERVER_URL}")
        print("Make sure the TopDesk Custom MCP server is running")
        print()
        
        # Still show the non-async examples
        example_5_curl_equivalent()
        example_6_javascript_fetch()

if __name__ == "__main__":
    # Update the bearer token from environment if available
    env_token = os.getenv('MCP_BEARER_TOKEN')
    if env_token:
        BEARER_TOKEN = env_token
    
    asyncio.run(main())