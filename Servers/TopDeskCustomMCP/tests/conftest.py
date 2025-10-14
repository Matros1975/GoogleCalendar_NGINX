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

    # Mock successful incident retrieval by ticket number
    client.get_incident_by_number.return_value = {
        'success': True,
        'incident_number': 'I2510 017',
        'incident_id': 'test-incident-id',
        'brief_description': 'Test incident',
        'status': 'Open',
        'caller_name': 'Test User',
        'caller_email': 'test@example.com',
        'caller_phone': '+1234567890',
        'category': 'Core applicaties',
        'priority': 'P1 (I&A)',
        'creation_date': '2024-10-14T10:00:00Z',
        'target_date': '2024-10-15T10:00:00Z',
        'request_details': 'Detailed description of the incident',
        'operator': 'Operator Name',
        'branch': 'Main Branch',
        'raw_response': {}
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
