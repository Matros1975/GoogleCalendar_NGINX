"""Pytest configuration and fixtures."""

import pytest
from unittest.mock import Mock


@pytest.fixture
def mock_topdesk_client():
    """Mock TopDesk API client."""
    client = Mock()
    
    # Mock successful incident creation
    client.create_incident.return_value = {
        'success': True,
        'incident_number': 'I-2024-001',
        'incident_id': 'test-incident-id',
        'caller_name': 'Test User',
        'category': 'Core applicaties',
        'priority': 'P1 (I&A)'
    }
    
    # Mock successful incident retrieval
    client.get_incident.return_value = {
        'success': True,
        'incident': {
            'id': 'test-incident-id',
            'number': 'I-2024-001',
            'briefDescription': 'Test incident'
        }
    }
    
    # Mock successful incident list
    client.list_incidents.return_value = {
        'success': True,
        'incidents': [
            {'id': 'id1', 'number': 'I-2024-001'},
            {'id': 'id2', 'number': 'I-2024-002'}
        ],
        'count': 2
    }
    
    # Mock successful person retrieval
    client.get_person.return_value = {
        'success': True,
        'person': {
            'id': 'test-person-id',
            'firstName': 'Test',
            'surName': 'User'
        }
    }
    
    # Mock successful person search
    client.search_persons.return_value = {
        'success': True,
        'persons': [
            {'id': 'id1', 'firstName': 'Test', 'surName': 'User1'}
        ],
        'count': 1
    }
    
    # Mock successful categories
    client.get_categories.return_value = {
        'success': True,
        'categories': [
            {'name': 'Core applicaties'},
            {'name': 'Werkplek hardware'}
        ]
    }
    
    # Mock successful priorities
    client.get_priorities.return_value = {
        'success': True,
        'priorities': [
            {'name': 'P1 (I&A)'},
            {'name': 'P2 (I&A)'}
        ]
    }
    
    return client


@pytest.fixture
def sample_caller_id():
    """Sample caller UUID."""
    return "d34b277f-e6a2-534c-a96b-23bf383cb4a1"


@pytest.fixture
def sample_incident_data(sample_caller_id):
    """Sample incident creation data."""
    return {
        "caller_id": sample_caller_id,
        "brief_description": "Cannot login to Windows",
        "request": "User cannot login. Error message shown.",
        "category": "Core applicaties",
        "priority": "P1 (I&A)"
    }
