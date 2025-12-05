# Task: Add Email Lookup Tool to TopDeskMCP Server

## Overview
Add a new MCP tool `topdesk_lookup_person_by_email` to the TopDeskCustomMCP server that resolves email addresses to registered TopDesk user information.

## Context
The ElevenLabs webhook service extracts caller email addresses from conversation transcripts. This email needs to be validated against the TopDesk database to retrieve the associated person record (caller_id) for ticket creation.

## Requirements

### Tool Name
`topdesk_lookup_person_by_email`

### Input Parameters
```json
{
  "email": "string (required) - Email address to lookup in TopDesk database"
}
```

### Output Structure

#### When email is found:
```json
{
  "email_found": true,
  "person": {
    "id": "uuid-string",
    "dynamicName": "Full Name",
    "email": "user@example.com",
    "mobileNumber": "string or null",
    "phoneNumber": "string or null",
    "department": {
      "id": "uuid",
      "name": "Department Name"
    },
    "branch": {
      "id": "uuid", 
      "name": "Branch Name"
    },
    "budgetHolder": {
      "id": "uuid",
      "name": "Budget Holder Name"
    },
    "jobTitle": "string or null",
    "tasLoginName": "string or null",
    "employeeNumber": "string or null",
    "networkLoginName": "string or null"
  }
}
```

#### When email is not found:
```json
{
  "email_found": false,
  "message": "No person registered with email: user@example.com"
}
```

#### When error occurs:
```json
{
  "email_found": false,
  "error": "Error message describing what went wrong"
}
```

## Implementation Details

### 1. TopDesk API Endpoint
**Endpoint:** `GET /tas/api/persons`  
**Query Parameters:**
- `email={email_address}` - Filter by exact email match
- `page_size=1` - Limit to single result (should only be one match per email)

**TopDesk API Documentation Reference:**
- Endpoint: `/persons`
- Supports filtering by email address
- Returns array of person objects matching the criteria

### 2. File Modifications Required

#### 2.1 `src/topdesk_client.py`
Add new method to `TopDeskAPIClient` class:

```python
def lookup_person_by_email(self, email: str) -> Dict[str, Any]:
    """Look up a person by email address.
    
    Args:
        email: Email address to search for
        
    Returns:
        Dictionary with person details if found, or email_found=False
        
    Example Success Response:
        {
            'email_found': True,
            'person': {
                'id': 'uuid',
                'dynamicName': 'John Doe',
                'email': 'john.doe@company.com',
                ...
            }
        }
        
    Example Not Found Response:
        {
            'email_found': False,
            'message': 'No person registered with email: test@example.com'
        }
    """
    try:
        params = {
            'email': email,
            'page_size': 1
        }
        
        logger.info(f"Looking up person by email: {email}")
        response = requests.get(
            f"{self.base_url}/persons",
            headers=self.headers,
            params=params,
            timeout=30
        )
        
        if response.status_code in [200, 206]:
            persons = response.json()
            
            if persons and len(persons) > 0:
                # Email found - return person data
                return {
                    'email_found': True,
                    'person': persons[0]  # First match (should be only match)
                }
            else:
                # Email not found
                return {
                    'email_found': False,
                    'message': f'No person registered with email: {email}'
                }
        else:
            # API error
            return {
                'email_found': False,
                'error': f"HTTP {response.status_code}: {response.text}"
            }
            
    except Exception as e:
        logger.exception("Error looking up person by email")
        return {
            'email_found': False,
            'error': str(e)
        }
```

**Location:** Add after `search_persons` method (around line 390)

#### 2.2 `src/handlers/persons.py`
Add new handler to `PersonHandlers` class:

```python
async def lookup_person_by_email(self, args: Dict[str, Any]) -> Dict[str, Any]:
    """Look up a person by email address.
    
    Args:
        args: Tool arguments with email
        
    Returns:
        Person details if found, or email_found=False
    """
    email = args.get("email")
    
    if not email:
        return {
            "email_found": False,
            "error": "Missing required parameter: email"
        }
    
    # Basic email validation
    if '@' not in email or '.' not in email.split('@')[-1]:
        return {
            "email_found": False,
            "error": f"Invalid email format: {email}"
        }
    
    logger.info(f"Looking up person by email: {email}")
    
    result = self.client.lookup_person_by_email(email)
    return result
```

**Location:** Add after `search_persons` method (around line 62)

#### 2.3 `src/mcp_server.py`
Register the new tool in the MCP server.

**Find the tool registration section** (search for `@server.list_tools()` or where tools are defined)

**Add tool definition:**
```python
{
    "name": "topdesk_lookup_person_by_email",
    "description": "Look up a TopDesk person by email address. Returns person details if email is registered, or email_found=false if not found.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "Email address to lookup in TopDesk database"
            }
        },
        "required": ["email"]
    }
}
```

**Add tool handler routing** (in the tool call handler function):
```python
elif tool_name == "topdesk_lookup_person_by_email":
    result = await person_handlers.lookup_person_by_email(arguments)
```

### 3. Testing Requirements

#### 3.1 Unit Tests
Create `tests/test_lookup_person_by_email.py`:

```python
"""Unit tests for email lookup functionality."""

import pytest
from unittest.mock import Mock, patch
from src.topdesk_client import TopDeskAPIClient
from src.handlers.persons import PersonHandlers


class TestEmailLookup:
    """Test cases for lookup_person_by_email."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock TopDesk client."""
        client = Mock(spec=TopDeskAPIClient)
        return client
    
    @pytest.fixture
    def person_handlers(self, mock_client):
        """Create PersonHandlers with mock client."""
        return PersonHandlers(mock_client)
    
    @pytest.mark.asyncio
    async def test_email_found(self, person_handlers, mock_client):
        """Test successful email lookup."""
        # Arrange
        mock_response = {
            'email_found': True,
            'person': {
                'id': 'test-uuid',
                'dynamicName': 'Test User',
                'email': 'test@example.com'
            }
        }
        mock_client.lookup_person_by_email.return_value = mock_response
        
        # Act
        result = await person_handlers.lookup_person_by_email({
            'email': 'test@example.com'
        })
        
        # Assert
        assert result['email_found'] is True
        assert result['person']['email'] == 'test@example.com'
        mock_client.lookup_person_by_email.assert_called_once_with('test@example.com')
    
    @pytest.mark.asyncio
    async def test_email_not_found(self, person_handlers, mock_client):
        """Test email not registered in TopDesk."""
        # Arrange
        mock_response = {
            'email_found': False,
            'message': 'No person registered with email: unknown@example.com'
        }
        mock_client.lookup_person_by_email.return_value = mock_response
        
        # Act
        result = await person_handlers.lookup_person_by_email({
            'email': 'unknown@example.com'
        })
        
        # Assert
        assert result['email_found'] is False
        assert 'message' in result
    
    @pytest.mark.asyncio
    async def test_missing_email_parameter(self, person_handlers):
        """Test error when email parameter is missing."""
        # Act
        result = await person_handlers.lookup_person_by_email({})
        
        # Assert
        assert result['email_found'] is False
        assert 'error' in result
        assert 'Missing required parameter' in result['error']
    
    @pytest.mark.asyncio
    async def test_invalid_email_format(self, person_handlers):
        """Test error when email format is invalid."""
        # Act
        result = await person_handlers.lookup_person_by_email({
            'email': 'not-an-email'
        })
        
        # Assert
        assert result['email_found'] is False
        assert 'error' in result
        assert 'Invalid email format' in result['error']
    
    @pytest.mark.asyncio
    async def test_api_error(self, person_handlers, mock_client):
        """Test handling of TopDesk API errors."""
        # Arrange
        mock_response = {
            'email_found': False,
            'error': 'HTTP 500: Internal Server Error'
        }
        mock_client.lookup_person_by_email.return_value = mock_response
        
        # Act
        result = await person_handlers.lookup_person_by_email({
            'email': 'test@example.com'
        })
        
        # Assert
        assert result['email_found'] is False
        assert 'error' in result
```

#### 3.2 Integration Tests
Add to existing integration test file or create new test:

```python
@pytest.mark.integration
async def test_lookup_person_by_email_integration():
    """Test email lookup against real TopDesk API."""
    # This requires a real TopDesk instance and registered email
    # Use TEST_EMAIL environment variable for known test email
    
    test_email = os.getenv('TEST_EMAIL', 'test@company.com')
    
    result = await person_handlers.lookup_person_by_email({
        'email': test_email
    })
    
    assert result['email_found'] is True
    assert result['person']['email'] == test_email
    assert 'id' in result['person']
    assert 'dynamicName' in result['person']
```

#### 3.3 End-to-End MCP Test
Add to `test_e2e.py`:

```python
def test_lookup_person_by_email_tool():
    """Test email lookup tool via MCP protocol."""
    # Test with registered email
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "topdesk_lookup_person_by_email",
            "arguments": {
                "email": "known@company.com"
            }
        }
    }
    
    response = send_mcp_request(request)
    
    assert response['result']['content'][0]['text'] is not None
    result = json.loads(response['result']['content'][0]['text'])
    assert result['email_found'] is True
    
    # Test with unregistered email
    request['params']['arguments']['email'] = 'nonexistent@unknown.com'
    response = send_mcp_request(request)
    result = json.loads(response['result']['content'][0]['text'])
    assert result['email_found'] is False
```

### 4. Documentation Updates

#### 4.1 Update `README.md`
Add tool documentation under "Person Management" section:

```markdown
#### `topdesk_lookup_person_by_email`
Look up a person by email address.

**Parameters:**
- `email` (required): Email address to search for in TopDesk

**Returns:**
- `email_found`: Boolean indicating if email was found
- `person`: Full person object if found (includes id, name, department, etc.)
- `message`: Explanation if not found
- `error`: Error message if lookup failed

**Example:**
```json
{
  "email": "john.doe@company.com"
}
```

**Success Response:**
```json
{
  "email_found": true,
  "person": {
    "id": "d34b277f-e6a2-534c-a96b-23bf383cb4a1",
    "dynamicName": "John Doe",
    "email": "john.doe@company.com",
    "department": {
      "name": "IT Department"
    }
  }
}
```

**Not Found Response:**
```json
{
  "email_found": false,
  "message": "No person registered with email: john.doe@company.com"
}
```

**Use Case:** This tool is useful for validating email addresses extracted from conversation transcripts before creating incidents. If email is found, use the returned `person.id` as the `caller_id` when creating incidents.
```

#### 4.2 Add Example Usage
Create `examples/lookup_email.md`:

```markdown
# Email Lookup Example

## Scenario
ElevenLabs webhook extracts email "alice@company.com" from conversation transcript. Before creating a ticket, validate the email and get the caller_id.

## Step 1: Lookup Email
```json
{
  "name": "topdesk_lookup_person_by_email",
  "arguments": {
    "email": "alice@company.com"
  }
}
```

## Step 2: Handle Result

### If email found:
```json
{
  "email_found": true,
  "person": {
    "id": "abc-123-def",
    "dynamicName": "Alice Smith",
    "email": "alice@company.com"
  }
}
```

→ Use `person.id` as `caller_id` for incident creation

### If email not found:
```json
{
  "email_found": false,
  "message": "No person registered with email: alice@company.com"
}
```

→ Either:
1. Create incident with default caller (if configured)
2. Request user to provide registered email
3. Log warning and skip ticket creation

## Step 3: Create Incident (if email found)
```json
{
  "name": "topdesk_create_incident",
  "arguments": {
    "caller_id": "abc-123-def",
    "brief_description": "Cannot access email",
    "request": "User reported unable to login to Outlook..."
  }
}
```
```

### 5. Integration with ElevenLabsWebhook

After implementing this tool, update the ElevenLabs webhook service to use it:

#### Update `Servers/ElevenLabsWebhook/src/handlers/transcription_handler.py`

Add email validation before ticket creation (around line 240):

```python
# If email was extracted, validate it in TopDesk
if ticket_data.caller_email:
    logger.info(f"Validating email {ticket_data.caller_email} in TopDesk")
    
    # Call TopDesk MCP to lookup email
    # (Requires MCP client integration - separate task)
    email_lookup = await self.topdesk_mcp_client.lookup_email(
        ticket_data.caller_email
    )
    
    if email_lookup['email_found']:
        # Use the validated person ID
        caller_id = email_lookup['person']['id']
        logger.info(f"Email found in TopDesk: {email_lookup['person']['dynamicName']}")
    else:
        logger.warning(f"Email not found in TopDesk: {ticket_data.caller_email}")
        # Use default caller or handle as configured
        caller_id = None
else:
    caller_id = None
```

## Acceptance Criteria

- [ ] `lookup_person_by_email` method added to `TopDeskAPIClient` class
- [ ] `lookup_person_by_email` handler added to `PersonHandlers` class  
- [ ] Tool registered in MCP server with correct schema
- [ ] Unit tests written with 90%+ coverage
- [ ] Integration test passes against real TopDesk instance
- [ ] End-to-end MCP test validates JSON-RPC protocol
- [ ] README.md updated with tool documentation
- [ ] Example usage documented
- [ ] Tool returns `email_found: true` when email exists
- [ ] Tool returns `email_found: false` when email doesn't exist
- [ ] Tool handles API errors gracefully
- [ ] Tool validates email format before API call
- [ ] Tool logs all operations for debugging

## Success Metrics

1. **Functionality:** Tool correctly identifies registered vs unregistered emails
2. **Performance:** Response time < 500ms for typical lookups
3. **Reliability:** Handles all error cases without crashing
4. **Code Quality:** Passes linting, type checking, and test coverage requirements
5. **Documentation:** Clear examples and usage instructions

## Priority
**HIGH** - Required for ElevenLabs webhook integration to validate caller emails before ticket creation

## Estimated Effort
- Implementation: 2-3 hours
- Testing: 1-2 hours  
- Documentation: 1 hour
- **Total: 4-6 hours**

## Dependencies
- Existing TopDeskCustomMCP server infrastructure
- TopDesk API credentials with person read permissions
- Python requests library (already installed)
- pytest for testing (already installed)

## Notes
- Email lookup should be case-insensitive (TopDesk API handles this)
- Only return first match (emails should be unique in TopDesk)
- Consider caching results if same email is looked up frequently
- Future enhancement: Support lookup by phone number or employee ID
