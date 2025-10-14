# Quick Reference: TopDesk Get Incident by Number Tool

## Tool Summary
- **Name**: `topdesk_get_incident_by_number`
- **Purpose**: Retrieve TopDesk incidents using human-readable ticket numbers
- **Benefit**: No need to know UUIDs - just use the ticket number users see

## Quick Usage

### 1. Curl Command
```bash
curl -k -X POST "https://localhost/topdesk/mcp/call" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
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

### 2. Python Example
```python
import asyncio
import httpx

async def get_incident(ticket_number):
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.post(
            "https://localhost/topdesk/mcp/call",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer YOUR_TOKEN"
            },
            json={
                "method": "tools/call",
                "params": {
                    "name": "topdesk_get_incident_by_number",
                    "arguments": {"ticket_number": ticket_number}
                }
            }
        )
        return response.json()

# Usage
result = asyncio.run(get_incident(2510017))
```

## Input/Output

### Input
- `ticket_number` (integer): The incident number (e.g., 2510017)

### Output (Success)
```json
{
  "success": true,
  "incident_number": "I2510 017",
  "incident_id": "6b704cbf-76f5-4802-b65d-2661fcae68d5",
  "brief_description": "Kan niet inloggen op Windows",
  "status": "Nieuw",
  "caller_name": "Aalbregt, Jacob",
  "caller_email": "J.Aalbregt@pietervanforeest.nl",
  "caller_phone": "015 515 5022",
  "category": "Core applicaties",
  "priority": "P1 (I&A)",
  "creation_date": "2025-10-13T14:24:30.000+0000",
  "target_date": "2025-10-14T08:54:00.000+0000",
  "request_details": "...",
  "operator": null,
  "branch": "PvF",
  "raw_response": { /* Full TopDesk API response */ }
}
```

### Output (Error)
```json
{
  "success": false,
  "error": "No incident found with number 2510999 (searched as 'I2510 999')"
}
```

## Environment
- **Bearer Token**: `e3707c16425c14fa417e2384a12748c0c7c51dfdfd1714c58992215983f33257`
- **Server URL**: `https://localhost/topdesk/mcp/call`
- **Container**: `topdesk-custom-mcp`

## Common Use Cases
1. **Voice Agents**: Users say ticket numbers naturally (e.g., "2510017")
2. **Support Scripts**: Lookup tickets with simple integers
3. **Dashboards**: Display incident details by number
4. **Integration**: Bridge between numeric ticket IDs and API calls

## Files with Examples
- `/Servers/TopDeskCustomMCP/examples/usage_examples.py` - Complete Python examples
- `/Servers/TopDeskCustomMCP/examples/get_incident_by_number.md` - Documentation with examples
- `/topdesk_get_incident_tool.py` - Standalone utility script (root directory)

## Testing
```bash
# Test with existing tickets
2510017, 2510018

# Test error handling
2510999 (doesn't exist)
123456 (wrong length)
```