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
