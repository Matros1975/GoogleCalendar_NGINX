# TopDesk API: Retrieving Incidents by Ticket Number

## Problem
TopDesk API requires the long UUID (e.g., `6b704cbf-76f5-4802-b65d-2661fcae68d5`) to retrieve incident details directly, but users typically only have the ticket number (e.g., `I2510 017`).

## Solution: Search Then Retrieve

Since TopDesk doesn't provide a direct endpoint to get incidents by ticket number, you need to use a two-step process:

1. **Search** for the incident using the ticket number
2. **Retrieve** full details using the UUID from search results

## Method 1: Query Parameter Search ✅ RECOMMENDED

```python
import requests

def get_incident_by_number(ticket_number):
    base_url = "https://pietervanforeest-test.topdesk.net"
    username = "api_aipilots"
    password = "your_password"
    
    # Step 1: Search by ticket number
    search_url = f"{base_url}/tas/api/incidents"
    params = {
        'query': f'number=="{ticket_number}"',
        'fields': 'id,number,briefDescription,status'
    }
    
    response = requests.get(
        search_url,
        params=params,
        auth=(username, password),
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code == 200:
        incidents = response.json()
        if incidents and len(incidents) > 0:
            incident_id = incidents[0]['id']
            
            # Step 2: Get full details using UUID
            detail_url = f"{base_url}/tas/api/incidents/id/{incident_id}"
            detail_response = requests.get(
                detail_url,
                auth=(username, password),
                headers={'Content-Type': 'application/json'}
            )
            
            if detail_response.status_code == 200:
                return detail_response.json()
    
    return None
```

## Method 2: OData Filter (Alternative)

```python
def get_incident_by_number_odata(ticket_number):
    params = {
        '$filter': f"number eq '{ticket_number}'",
        '$select': 'id,number,briefDescription,status'
    }
    # ... same process as above
```

## API Endpoints Used

### Search Incidents
```
GET /tas/api/incidents?query=number=="I2510 017"&fields=id,number,briefDescription
```

**Response:**
```json
[
  {
    "id": "6b704cbf-76f5-4802-b65d-2661fcae68d5",
    "number": "I2510 017",
    "briefDescription": "Kan niet inloggen op Windows"
  }
]
```

### Get Full Incident Details
```
GET /tas/api/incidents/id/6b704cbf-76f5-4802-b65d-2661fcae68d5
```

**Response:**
```json
{
  "id": "6b704cbf-76f5-4802-b65d-2661fcae68d5",
  "number": "I2510 017",
  "briefDescription": "Kan niet inloggen op Windows",
  "status": "firstLine",
  "caller": {
    "id": "d34b277f-e6a2-534c-a96b-23bf383cb4a1",
    "dynamicName": "Aalbregt, Jacob",
    "email": "J.Aalbregt@pietervanforeest.nl"
  },
  "category": {
    "name": "Core applicaties"
  },
  "priority": {
    "name": "P1 (I&A)"
  },
  "processingStatus": {
    "name": "Nieuw"
  },
  "creationDate": "2025-10-13T14:24:30.000+0000",
  "request": "Full incident description here..."
}
```

## Query Syntax Options

TopDesk API supports several query formats:

### Exact Match (Recommended)
```
query=number=="I2510 017"
```

### Contains Search
```
query=number~"I2510"
```

### Multiple Conditions
```
query=number=="I2510 017";status=="firstLine"
```

### Field Selection
```
fields=id,number,briefDescription,caller,status,priority
```

## Error Handling

Common issues and solutions:

### 401 Unauthorized
- Check username/password credentials
- Verify API user has incident read permissions

### 404 Not Found
- Verify the incident number exists
- Check spelling/formatting of ticket number

### Empty Results
- Incident might not exist
- User might not have permission to see the incident
- Ticket number format might be incorrect

## Integration with MCP

For MCP integration, add this tool to your TopDesk Custom MCP server:

```python
async def topdesk_get_incident(ticket_number: str) -> str:
    """Retrieve incident by ticket number (e.g., 'I2510 017')"""
    # Implementation from topdesk_get_incident_tool.py
    retriever = TopDeskIncidentRetriever()
    result = await retriever.get_incident_by_number(ticket_number)
    return json.dumps(result, indent=2)
```

## Example Usage

```python
# Get incident by ticket number
incident = get_incident_by_number("I2510 017")

if incident:
    print(f"Incident: {incident['number']}")
    print(f"Description: {incident['briefDescription']}")
    print(f"Status: {incident['processingStatus']['name']}")
    print(f"Caller: {incident['caller']['dynamicName']}")
else:
    print("Incident not found")
```

## Performance Notes

- Search operations are slower than direct UUID access
- Consider caching ticket_number → UUID mappings for frequently accessed incidents
- Use field selection to reduce response size
- The search endpoint supports pagination for large result sets

## Security Considerations

- Store credentials securely (environment variables, secrets manager)
- Use HTTPS for all API calls
- Implement proper error handling to avoid credential exposure
- Consider using API tokens instead of username/password for automation