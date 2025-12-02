"""Unit tests for email lookup functionality."""

import pytest
from unittest.mock import Mock, patch

from src.topdesk_client import TopDeskAPIClient
from src.handlers.persons import PersonHandlers


@pytest.fixture
def topdesk_config():
    """TopDesk configuration."""
    return {
        "base_url": "https://test.topdesk.net/tas/api",
        "username": "test_user",
        "password": "test_pass"
    }


class TestEmailLookupHandler:
    """Test cases for PersonHandlers.lookup_person_by_email."""
    
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
    async def test_invalid_email_format_no_at(self, person_handlers):
        """Test error when email format is invalid (no @)."""
        # Act
        result = await person_handlers.lookup_person_by_email({
            'email': 'not-an-email'
        })
        
        # Assert
        assert result['email_found'] is False
        assert 'error' in result
        assert 'Invalid email format' in result['error']
    
    @pytest.mark.asyncio
    async def test_invalid_email_format_no_domain_dot(self, person_handlers):
        """Test error when email format is invalid (no dot in domain)."""
        # Act
        result = await person_handlers.lookup_person_by_email({
            'email': 'test@example'
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


class TestEmailLookupClient:
    """Test cases for TopDeskAPIClient.lookup_person_by_email."""
    
    @patch('src.topdesk_client.requests.get')
    def test_lookup_person_found(self, mock_get, topdesk_config):
        """Test successful person lookup by email."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'id': 'person-uuid-123',
                'dynamicName': 'John Doe',
                'email': 'john.doe@company.com',
                'mobileNumber': '+31612345678',
                'department': {'id': 'dept-1', 'name': 'IT'},
                'branch': {'id': 'branch-1', 'name': 'Headquarters'}
            }
        ]
        mock_get.return_value = mock_response
        
        # Act
        client = TopDeskAPIClient(**topdesk_config)
        result = client.lookup_person_by_email('john.doe@company.com')
        
        # Assert
        assert result['email_found'] is True
        assert result['person']['id'] == 'person-uuid-123'
        assert result['person']['dynamicName'] == 'John Doe'
        assert result['person']['email'] == 'john.doe@company.com'
        
        # Verify API was called with correct parameters
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]['params']['email'] == 'john.doe@company.com'
        assert call_args[1]['params']['page_size'] == 1
    
    @patch('src.topdesk_client.requests.get')
    def test_lookup_person_not_found_empty_list(self, mock_get, topdesk_config):
        """Test person not found (empty result list)."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        # Act
        client = TopDeskAPIClient(**topdesk_config)
        result = client.lookup_person_by_email('unknown@example.com')
        
        # Assert
        assert result['email_found'] is False
        assert 'message' in result
        assert 'No person registered with email' in result['message']
    
    @patch('src.topdesk_client.requests.get')
    def test_lookup_person_not_found_204(self, mock_get, topdesk_config):
        """Test person not found (204 No Content response)."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 204
        mock_get.return_value = mock_response
        
        # Act
        client = TopDeskAPIClient(**topdesk_config)
        result = client.lookup_person_by_email('unknown@example.com')
        
        # Assert
        assert result['email_found'] is False
        assert 'message' in result
        assert 'No person registered with email' in result['message']
    
    @patch('src.topdesk_client.requests.get')
    def test_lookup_person_api_error(self, mock_get, topdesk_config):
        """Test API error handling."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response
        
        # Act
        client = TopDeskAPIClient(**topdesk_config)
        result = client.lookup_person_by_email('test@example.com')
        
        # Assert
        assert result['email_found'] is False
        assert 'error' in result
        assert 'HTTP 500' in result['error']
    
    @patch('src.topdesk_client.requests.get')
    def test_lookup_person_exception(self, mock_get, topdesk_config):
        """Test exception handling."""
        # Arrange
        mock_get.side_effect = Exception("Network error")
        
        # Act
        client = TopDeskAPIClient(**topdesk_config)
        result = client.lookup_person_by_email('test@example.com')
        
        # Assert
        assert result['email_found'] is False
        assert 'error' in result
        assert 'Network error' in result['error']
    
    @patch('src.topdesk_client.requests.get')
    def test_lookup_person_206_partial_content(self, mock_get, topdesk_config):
        """Test handling of 206 Partial Content response."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 206
        mock_response.json.return_value = [
            {
                'id': 'person-uuid-123',
                'dynamicName': 'Jane Doe',
                'email': 'jane.doe@company.com'
            }
        ]
        mock_get.return_value = mock_response
        
        # Act
        client = TopDeskAPIClient(**topdesk_config)
        result = client.lookup_person_by_email('jane.doe@company.com')
        
        # Assert
        assert result['email_found'] is True
        assert result['person']['email'] == 'jane.doe@company.com'

