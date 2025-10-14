# TopDesk Custom MCP: Get Incident by Number Tool

The `topdesk_get_incident_by_number` tool allows you to retrieve TopDesk incidents using human-readable ticket numbers instead of UUIDs.

## Tool Details

- **Tool Name**: `topdesk_get_incident_by_number`
- **Description**: Retrieve TopDesk incident details by ticket number (e.g., 'I2510 017')
- **Input**: `ticket_number` (string) - The incident number like "I2510 017"

## Usage Examples

### 1. Using curl (Direct API Call)

```bash
curl -k -X POST "https://localhost/topdesk/mcp/call" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_BEARER_TOKEN" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "topdesk_get_incident_by_number",
      "arguments": {
        "ticket_number": 2510017
      }
    }
  }'
```

### 2. Using Python with httpx

```python
import asyncio
import httpx
import json

async def get_incident_by_number(ticket_number: int):
    url = "https://localhost/topdesk/mcp/call"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer YOUR_BEARER_TOKEN"
    }
    
    payload = {
        "method": "tools/call",
        "params": {
            "name": "topdesk_get_incident_by_number",
            "arguments": {
                "ticket_number": ticket_number
            }
        }
    }
    
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.post(url, headers=headers, json=payload)
        return response.json()

# Example usage
result = asyncio.run(get_incident_by_number(2510017))
print(json.dumps(result, indent=2))
```

### 3. Using JavaScript/Node.js

```javascript
const fetch = require('node-fetch');
const https = require('https');

// Ignore SSL certificate issues for localhost
const agent = new https.Agent({
  rejectUnauthorized: false
});

async function getIncidentByNumber(ticketNumber) {
  const url = 'https://localhost/topdesk/mcp/call';
  const payload = {
    method: 'tools/call',
    params: {
      name: 'topdesk_get_incident_by_number',
      arguments: {
        ticket_number: ticketNumber  // Integer, e.g., 2510017
      }
    }
  };

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer YOUR_BEARER_TOKEN'
    },
    body: JSON.stringify(payload),
    agent: agent
  });

  return await response.json();
}

// Example usage
getIncidentByNumber(2510017)
  .then(result => console.log(JSON.stringify(result, null, 2)))
  .catch(console.error);
```

## Response Format

### Successful Response

```json
{
  "jsonrpc": "2.0",
  "id": null,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\n  \"success\": true,\n  \"incident_number\": \"I2510 017\",\n  \"incident_id\": \"6b704cbf-76f5-4802-b65d-2661fcae68d5\",\n  \"brief_description\": \"Kan niet inloggen op Windows\",\n  \"status\": \"Nieuw\",\n  \"caller_name\": \"Aalbregt, Jacob\",\n  \"caller_email\": \"J.Aalbregt@pietervanforeest.nl\",\n  \"caller_phone\": \"015 515 5022\",\n  \"category\": \"Core applicaties\",\n  \"priority\": \"P1 (I&A)\",\n  \"creation_date\": \"2025-10-13T14:24:30.000+0000\",\n  \"target_date\": \"2025-10-14T08:54:00.000+0000\",\n  \"request_details\": \"13-10-2025 16:24 API_AIPilots,: \\nMedewerker Jacob kan niet inloggen op Windows...\",\n  \"operator\": null,\n  \"branch\": \"PvF\",\n  \"raw_response\": { /* Full TopDesk API response */ }\n}"
      }
    ]
  }
}
```

### Error Response (Ticket Not Found)

```json
{
  "jsonrpc": "2.0",
  "id": null,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\n  \"success\": false,\n  \"error\": \"No incident found with number I2510 999\"\n}"
      }
    ]
  }
}
```

## ElevenLabs Voice Agent Integration

For voice agents, you can use this tool to allow users to simply say the ticket number:

**User**: "Get me details for ticket 2510017"

**Voice Agent**: Can retrieve the incident details using the integer ticket number directly, without needing to know the UUID or worry about string formatting.

## Environment Setup

Make sure your environment has the correct bearer token:

```bash
# Get the current bearer token from container
docker exec topdesk-custom-mcp env | grep BEARER
```

Replace `YOUR_BEARER_TOKEN` in the examples above with the actual token from your environment.

## Supported Ticket Number Formats

- Input: `2510017` (integer, 7 digits)
- Automatically formatted to: `I2510 017` (TopDesk format)
- Also handles: `2510018`, `2510999`, etc.

The tool uses TopDesk's search API with exact matching to find the incident by the formatted number.