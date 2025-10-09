"""Unit tests for tool handlers."""

import pytest
from src.handlers.incidents import IncidentHandlers
from src.handlers.persons import PersonHandlers
from src.handlers.status import StatusHandlers


@pytest.mark.asyncio
async def test_create_incident_success(mock_topdesk_client, sample_incident_data):
    """Test successful incident creation."""
    handlers = IncidentHandlers(mock_topdesk_client)
    
    result = await handlers.create_incident(sample_incident_data)
    
    assert result['success'] is True
    assert result['incident_number'] == 'I-2024-001'
    assert result['incident_id'] == 'test-incident-id'
    
    # Verify client was called with correct parameters
    mock_topdesk_client.create_incident.assert_called_once()


@pytest.mark.asyncio
async def test_create_incident_missing_caller_id(mock_topdesk_client):
    """Test incident creation with missing caller_id."""
    handlers = IncidentHandlers(mock_topdesk_client)
    
    result = await handlers.create_incident({
        "brief_description": "Test",
        "request": "Test request"
    })
    
    assert "error" in result
    assert "caller_id" in result["error"]


@pytest.mark.asyncio
async def test_create_incident_missing_brief_description(mock_topdesk_client, sample_caller_id):
    """Test incident creation with missing brief_description."""
    handlers = IncidentHandlers(mock_topdesk_client)
    
    result = await handlers.create_incident({
        "caller_id": sample_caller_id,
        "request": "Test request"
    })
    
    assert "error" in result
    assert "brief_description" in result["error"]


@pytest.mark.asyncio
async def test_get_incident_success(mock_topdesk_client):
    """Test successful incident retrieval."""
    handlers = IncidentHandlers(mock_topdesk_client)
    
    result = await handlers.get_incident({"incident_id": "test-incident-id"})
    
    assert result['success'] is True
    assert result['incident']['id'] == 'test-incident-id'
    
    mock_topdesk_client.get_incident.assert_called_once_with("test-incident-id")


@pytest.mark.asyncio
async def test_get_incident_missing_id(mock_topdesk_client):
    """Test incident retrieval with missing incident_id."""
    handlers = IncidentHandlers(mock_topdesk_client)
    
    result = await handlers.get_incident({})
    
    assert "error" in result
    assert "incident_id" in result["error"]


@pytest.mark.asyncio
async def test_list_incidents_success(mock_topdesk_client):
    """Test successful incident listing."""
    handlers = IncidentHandlers(mock_topdesk_client)
    
    result = await handlers.list_incidents({
        "status": "Open",
        "limit": 10
    })
    
    assert result['success'] is True
    assert result['count'] == 2
    assert len(result['incidents']) == 2


@pytest.mark.asyncio
async def test_get_person_success(mock_topdesk_client):
    """Test successful person retrieval."""
    handlers = PersonHandlers(mock_topdesk_client)
    
    result = await handlers.get_person({"person_id": "test-person-id"})
    
    assert result['success'] is True
    assert result['person']['id'] == 'test-person-id'


@pytest.mark.asyncio
async def test_search_persons_success(mock_topdesk_client):
    """Test successful person search."""
    handlers = PersonHandlers(mock_topdesk_client)
    
    result = await handlers.search_persons({
        "query": "Test User",
        "limit": 10
    })
    
    assert result['success'] is True
    assert result['count'] == 1


@pytest.mark.asyncio
async def test_search_persons_missing_query(mock_topdesk_client):
    """Test person search with missing query."""
    handlers = PersonHandlers(mock_topdesk_client)
    
    result = await handlers.search_persons({})
    
    assert "error" in result
    assert "query" in result["error"]


@pytest.mark.asyncio
async def test_get_categories_success(mock_topdesk_client):
    """Test successful categories retrieval."""
    handlers = StatusHandlers(mock_topdesk_client)
    
    result = await handlers.get_categories({})
    
    assert result['success'] is True
    assert len(result['categories']) == 2


@pytest.mark.asyncio
async def test_get_priorities_success(mock_topdesk_client):
    """Test successful priorities retrieval."""
    handlers = StatusHandlers(mock_topdesk_client)
    
    result = await handlers.get_priorities({})
    
    assert result['success'] is True
    assert len(result['priorities']) == 2
