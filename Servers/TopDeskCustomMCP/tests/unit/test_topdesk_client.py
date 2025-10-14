"""Unit tests for TopDesk API client."""

import pytest
from unittest.mock import Mock, patch
import base64
from src.topdesk_client import TopDeskAPIClient


@pytest.fixture
def topdesk_config():
    """TopDesk configuration."""
    return {
        "base_url": "https://test.topdesk.net/tas/api",
        "username": "test_user",
        "password": "test_pass"
    }


def test_client_initialization(topdesk_config):
    """Test TopDesk client initialization."""
    client = TopDeskAPIClient(**topdesk_config)

    assert client.base_url == topdesk_config["base_url"]
    assert client.username == topdesk_config["username"]
    assert client.password == topdesk_config["password"]

    # Verify auth header is created correctly
    expected_auth = base64.b64encode(
        f"{topdesk_config['username']}:{topdesk_config['password']}".encode()
    ).decode()
    assert client.headers['Authorization'] == f'Basic {expected_auth}'


def test_client_strips_trailing_slash(topdesk_config):
    """Test that client strips trailing slash from base URL."""
    topdesk_config['base_url'] = "https://test.topdesk.net/tas/api/"
    client = TopDeskAPIClient(**topdesk_config)

    assert client.base_url == "https://test.topdesk.net/tas/api"


@patch('src.topdesk_client.requests.post')
def test_create_incident_success(mock_post, topdesk_config, sample_incident_data):
    """Test successful incident creation."""
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        'id': 'incident-123',
        'number': 'I-2024-001',
        'caller': {'dynamicName': 'Test User'},
        'category': {'name': 'Core applicaties'},
        'priority': {'name': 'P1 (I&A)'},
        'processingStatus': {'name': 'Open'}
    }
    mock_post.return_value = mock_response

    client = TopDeskAPIClient(**topdesk_config)
    result = client.create_incident(
        caller_id=sample_incident_data['caller_id'],
        brief_description=sample_incident_data['brief_description'],
        request=sample_incident_data['request'],
        category=sample_incident_data['category'],
        priority=sample_incident_data['priority']
    )

    assert result['success'] is True
    assert result['incident_number'] == 'I-2024-001'
    assert result['incident_id'] == 'incident-123'

    # Verify correct API call
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args[0][0] == f"{topdesk_config['base_url']}/incidents"

    # Verify parameter mapping
    payload = call_args[1]['json']
    assert payload['briefDescription'] == sample_incident_data['brief_description']
    assert payload['request'] == sample_incident_data['request']
    assert payload['caller'] == {'id': sample_incident_data['caller_id']}
    assert payload['category'] == {'name': sample_incident_data['category']}
    assert payload['priority'] == {'name': sample_incident_data['priority']}


@patch('src.topdesk_client.requests.post')
def test_create_incident_minimal(mock_post, topdesk_config, sample_caller_id):
    """Test incident creation with minimal parameters."""
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        'id': 'incident-123',
        'number': 'I-2024-001'
    }
    mock_post.return_value = mock_response

    client = TopDeskAPIClient(**topdesk_config)
    result = client.create_incident(
        caller_id=sample_caller_id,
        brief_description="Test",
        request="Test request"
    )

    assert result['success'] is True

    # Verify optional fields are not included when None
    payload = mock_post.call_args[1]['json']
    assert 'category' not in payload
    assert 'priority' not in payload


@patch('src.topdesk_client.requests.post')
def test_create_incident_api_error(mock_post, topdesk_config, sample_incident_data):
    """Test incident creation with API error."""
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request: Invalid caller ID"
    mock_post.return_value = mock_response

    client = TopDeskAPIClient(**topdesk_config)
    result = client.create_incident(
        caller_id=sample_incident_data['caller_id'],
        brief_description=sample_incident_data['brief_description'],
        request=sample_incident_data['request']
    )

    assert result['success'] is False
    assert 'HTTP 400' in result['error']


@patch('src.topdesk_client.requests.get')
def test_get_incident_success(mock_get, topdesk_config):
    """Test successful incident retrieval."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'id': 'incident-123',
        'number': 'I-2024-001',
        'briefDescription': 'Test incident'
    }
    mock_get.return_value = mock_response

    client = TopDeskAPIClient(**topdesk_config)
    result = client.get_incident('incident-123')

    assert result['success'] is True
    assert result['incident']['id'] == 'incident-123'


@patch('src.topdesk_client.requests.get')
def test_list_incidents_with_filters(mock_get, topdesk_config):
    """Test listing incidents with filters."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {'id': 'id1', 'number': 'I-2024-001'},
        {'id': 'id2', 'number': 'I-2024-002'}
    ]
    mock_get.return_value = mock_response

    client = TopDeskAPIClient(**topdesk_config)
    result = client.list_incidents(status="Open", caller_id="caller-123", limit=5)

    assert result['success'] is True
    assert result['count'] == 2

    # Verify query parameters
    call_args = mock_get.call_args
    params = call_args[1]['params']
    assert params['page_size'] == 5
    assert 'processingStatus.name==Open' in params['query']
    assert 'caller.id==caller-123' in params['query']


@patch('src.topdesk_client.requests.get')
def test_search_persons_success(mock_get, topdesk_config):
    """Test successful person search."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {'id': 'person-1', 'firstName': 'John', 'surName': 'Doe'}
    ]
    mock_get.return_value = mock_response

    client = TopDeskAPIClient(**topdesk_config)
    result = client.search_persons("John Doe", limit=5)

    assert result['success'] is True
    assert result['count'] == 1


@patch('src.topdesk_client.requests.get')
def test_get_categories_success(mock_get, topdesk_config):
    """Test successful categories retrieval."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {'name': 'Core applicaties'},
        {'name': 'Werkplek hardware'}
    ]
    mock_get.return_value = mock_response

    client = TopDeskAPIClient(**topdesk_config)
    result = client.get_categories()

    assert result['success'] is True
    assert len(result['categories']) == 2


@patch('src.topdesk_client.requests.get')
def test_get_priorities_success(mock_get, topdesk_config):
    """Test successful priorities retrieval."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {'name': 'P1 (I&A)'},
        {'name': 'P2 (I&A)'}
    ]
    mock_get.return_value = mock_response

    client = TopDeskAPIClient(**topdesk_config)
    result = client.get_priorities()

    assert result['success'] is True
    assert len(result['priorities']) == 2


@patch('src.topdesk_client.requests.get')
def test_get_incident_by_number_success(mock_get, topdesk_config):
    """Test successful incident retrieval by ticket number."""
    # Mock search response
    search_response = Mock()
    search_response.status_code = 200
    search_response.json.return_value = [
        {
            'id': 'incident-uuid-123',
            'number': 'I2510 017',
            'briefDescription': 'Test incident'
        }
    ]

    # Mock detail response
    detail_response = Mock()
    detail_response.status_code = 200
    detail_response.json.return_value = {
        'id': 'incident-uuid-123',
        'number': 'I2510 017',
        'briefDescription': 'Test incident',
        'request': 'Detailed description',
        'processingStatus': {'name': 'Open'},
        'caller': {
            'dynamicName': 'Test User',
            'email': 'test@example.com',
            'phoneNumber': '+1234567890'
        },
        'category': {'name': 'Core applicaties'},
        'priority': {'name': 'P1 (I&A)'},
        'creationDate': '2024-10-14T10:00:00Z',
        'targetDate': '2024-10-15T10:00:00Z',
        'operator': {'name': 'Operator Name'},
        'callerBranch': {'name': 'Main Branch'}
    }

    # Configure mock to return different responses for different calls
    mock_get.side_effect = [search_response, detail_response]

    client = TopDeskAPIClient(**topdesk_config)
    result = client.get_incident_by_number(2510017)

    assert result['success'] is True
    assert result['incident_number'] == 'I2510 017'
    assert result['incident_id'] == 'incident-uuid-123'
    assert result['brief_description'] == 'Test incident'
    assert result['status'] == 'Open'
    assert result['caller_name'] == 'Test User'
    assert result['caller_email'] == 'test@example.com'
    assert result['category'] == 'Core applicaties'
    assert result['priority'] == 'P1 (I&A)'
    assert 'raw_response' in result

    # Verify search call was made with correct formatted number
    search_call = mock_get.call_args_list[0]
    assert search_call[0][0] == f"{topdesk_config['base_url']}/incidents"
    search_params = search_call[1]['params']
    assert search_params['query'] == 'number=="I2510 017"'
    assert search_params['fields'] == 'id,number,briefDescription'

    # Verify detail call was made with correct UUID
    detail_call = mock_get.call_args_list[1]
    assert detail_call[0][0] == f"{topdesk_config['base_url']}/incidents/id/incident-uuid-123"


@patch('src.topdesk_client.requests.get')
def test_get_incident_by_number_with_leading_zeros(mock_get, topdesk_config):
    """Test ticket number formatting with leading zeros."""
    search_response = Mock()
    search_response.status_code = 200
    search_response.json.return_value = [
        {'id': 'incident-123', 'number': 'I0000 042', 'briefDescription': 'Test'}
    ]

    detail_response = Mock()
    detail_response.status_code = 200
    detail_response.json.return_value = {
        'id': 'incident-123',
        'number': 'I0000 042',
        'briefDescription': 'Test'
    }

    mock_get.side_effect = [search_response, detail_response]

    client = TopDeskAPIClient(**topdesk_config)
    result = client.get_incident_by_number(42)

    assert result['success'] is True

    # Verify ticket was formatted with leading zeros: 42 -> "I0000 042"
    search_call = mock_get.call_args_list[0]
    search_params = search_call[1]['params']
    assert search_params['query'] == 'number=="I0000 042"'


@patch('src.topdesk_client.requests.get')
def test_get_incident_by_number_maximum_value(mock_get, topdesk_config):
    """Test ticket number formatting with maximum valid value."""
    search_response = Mock()
    search_response.status_code = 200
    search_response.json.return_value = [
        {'id': 'incident-max', 'number': 'I9999 999', 'briefDescription': 'Max ticket'}
    ]

    detail_response = Mock()
    detail_response.status_code = 200
    detail_response.json.return_value = {
        'id': 'incident-max',
        'number': 'I9999 999',
        'briefDescription': 'Max ticket'
    }

    mock_get.side_effect = [search_response, detail_response]

    client = TopDeskAPIClient(**topdesk_config)
    result = client.get_incident_by_number(9999999)

    assert result['success'] is True

    # Verify maximum ticket number formatting: 9999999 -> "I9999 999"
    search_call = mock_get.call_args_list[0]
    search_params = search_call[1]['params']
    assert search_params['query'] == 'number=="I9999 999"'


@patch('src.topdesk_client.requests.get')
def test_get_incident_by_number_not_found_204(mock_get, topdesk_config):
    """Test handling of 204 No Content response (no incident found)."""
    search_response = Mock()
    search_response.status_code = 204
    mock_get.return_value = search_response

    client = TopDeskAPIClient(**topdesk_config)
    result = client.get_incident_by_number(1234567)

    assert result['success'] is False
    assert "No incident found with number 1234567" in result['error']
    assert "I1234 567" in result['error']


@patch('src.topdesk_client.requests.get')
def test_get_incident_by_number_empty_results(mock_get, topdesk_config):
    """Test handling of empty search results."""
    search_response = Mock()
    search_response.status_code = 200
    search_response.json.return_value = []
    mock_get.return_value = search_response

    client = TopDeskAPIClient(**topdesk_config)
    result = client.get_incident_by_number(7654321)

    assert result['success'] is False
    assert "No incident found with number 7654321" in result['error']
    assert "I7654 321" in result['error']


@patch('src.topdesk_client.requests.get')
def test_get_incident_by_number_search_error(mock_get, topdesk_config):
    """Test handling of search API error."""
    search_response = Mock()
    search_response.status_code = 500
    search_response.text = "Internal Server Error"
    mock_get.return_value = search_response

    client = TopDeskAPIClient(**topdesk_config)
    result = client.get_incident_by_number(1234567)

    assert result['success'] is False
    assert "Search failed" in result['error']
    assert "HTTP 500" in result['error']


@patch('src.topdesk_client.requests.get')
def test_get_incident_by_number_missing_id(mock_get, topdesk_config):
    """Test handling of missing incident ID in search results."""
    search_response = Mock()
    search_response.status_code = 200
    search_response.json.return_value = [
        {'number': 'I1234 567', 'briefDescription': 'Test'}
        # Missing 'id' field
    ]
    mock_get.return_value = search_response

    client = TopDeskAPIClient(**topdesk_config)
    result = client.get_incident_by_number(1234567)

    assert result['success'] is False
    assert "no ID available" in result['error']


@patch('src.topdesk_client.requests.get')
def test_get_incident_by_number_detail_fetch_error(mock_get, topdesk_config):
    """Test handling of detail fetch API error."""
    search_response = Mock()
    search_response.status_code = 200
    search_response.json.return_value = [
        {'id': 'incident-123', 'number': 'I1234 567', 'briefDescription': 'Test'}
    ]

    detail_response = Mock()
    detail_response.status_code = 404
    detail_response.text = "Not Found"

    mock_get.side_effect = [search_response, detail_response]

    client = TopDeskAPIClient(**topdesk_config)
    result = client.get_incident_by_number(1234567)

    assert result['success'] is False
    assert "Detail fetch failed" in result['error']
    assert "HTTP 404" in result['error']


def test_get_incident_by_number_negative_value(topdesk_config):
    """Test validation of negative ticket numbers."""
    client = TopDeskAPIClient(**topdesk_config)
    result = client.get_incident_by_number(-1)

    assert result['success'] is False
    assert "must be between 0 and 9999999" in result['error']


def test_get_incident_by_number_too_large(topdesk_config):
    """Test validation of ticket numbers exceeding maximum."""
    client = TopDeskAPIClient(**topdesk_config)
    result = client.get_incident_by_number(10000000)

    assert result['success'] is False
    assert "must be between 0 and 9999999" in result['error']


@patch('src.topdesk_client.requests.get')
def test_get_incident_by_number_exception_handling(mock_get, topdesk_config):
    """Test exception handling during search."""
    mock_get.side_effect = Exception("Network error")

    client = TopDeskAPIClient(**topdesk_config)
    result = client.get_incident_by_number(1234567)

    assert result['success'] is False
    assert "Exception" in result['error']
    assert "Network error" in result['error']


@patch('src.topdesk_client.requests.get')
def test_get_incident_by_number_minimal_response(mock_get, topdesk_config):
    """Test handling of minimal incident data (optional fields missing)."""
    search_response = Mock()
    search_response.status_code = 200
    search_response.json.return_value = [
        {'id': 'incident-123', 'number': 'I1234 567', 'briefDescription': 'Test'}
    ]

    detail_response = Mock()
    detail_response.status_code = 200
    detail_response.json.return_value = {
        'id': 'incident-123',
        'number': 'I1234 567',
        'briefDescription': 'Test incident'
        # Many optional fields missing
    }

    mock_get.side_effect = [search_response, detail_response]

    client = TopDeskAPIClient(**topdesk_config)
    result = client.get_incident_by_number(1234567)

    assert result['success'] is True
    assert result['incident_number'] == 'I1234 567'
    assert result['incident_id'] == 'incident-123'
    # Optional fields should be None when missing
    assert result.get('status') is None
    assert result.get('caller_name') is None
    assert result.get('operator') is None
