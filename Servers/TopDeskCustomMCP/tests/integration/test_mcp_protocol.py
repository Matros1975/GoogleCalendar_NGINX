"""Integration tests for MCP protocol compliance."""

import pytest
import json
from unittest.mock import Mock
from src.mcp_server import MCPProtocolHandler
from src.auth import BearerTokenValidator


@pytest.fixture
def protocol_handler():
    """Create protocol handler with mock bearer validator."""
    validator = BearerTokenValidator(["test-token"])
    handler = MCPProtocolHandler(
        server_name="TestServer",
        server_version="1.0.0",
        bearer_validator=validator
    )
    return handler


def test_initialize_request(protocol_handler):
    """Test MCP initialize request."""
    params = {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {
            "name": "test-client",
            "version": "1.0.0"
        }
    }
    
    result = protocol_handler.handle_initialize(params)
    
    assert result["protocolVersion"] == "2024-11-05"
    assert "capabilities" in result
    assert "serverInfo" in result
    assert result["serverInfo"]["name"] == "TestServer"
    assert result["serverInfo"]["version"] == "1.0.0"


def test_tools_list_empty(protocol_handler):
    """Test tools/list with no registered tools."""
    result = protocol_handler.handle_tools_list({})
    
    assert "tools" in result
    assert isinstance(result["tools"], list)
    assert len(result["tools"]) == 0


def test_tools_list_with_tools(protocol_handler):
    """Test tools/list with registered tools."""
    # Register a test tool
    protocol_handler.register_tool(
        name="test_tool",
        description="A test tool",
        input_schema={"type": "object", "properties": {}},
        handler=lambda args: {"result": "success"}
    )
    
    result = protocol_handler.handle_tools_list({})
    
    assert len(result["tools"]) == 1
    assert result["tools"][0]["name"] == "test_tool"
    assert result["tools"][0]["description"] == "A test tool"


@pytest.mark.asyncio
async def test_tools_call_success(protocol_handler):
    """Test successful tools/call."""
    # Register a test tool
    async def test_handler(args):
        return {"status": "success", "data": args}
    
    protocol_handler.register_tool(
        name="test_tool",
        description="A test tool",
        input_schema={"type": "object"},
        handler=test_handler
    )
    
    params = {
        "name": "test_tool",
        "arguments": {"test_arg": "test_value"}
    }
    
    result = await protocol_handler.handle_tools_call(params)
    
    assert "content" in result
    assert len(result["content"]) > 0
    assert result["content"][0]["type"] == "text"
    
    # Parse the text content
    text_content = result["content"][0]["text"]
    data = json.loads(text_content)
    assert data["status"] == "success"
    assert data["data"]["test_arg"] == "test_value"


@pytest.mark.asyncio
async def test_tools_call_unknown_tool(protocol_handler):
    """Test tools/call with unknown tool."""
    params = {
        "name": "unknown_tool",
        "arguments": {}
    }
    
    with pytest.raises(ValueError, match="Unknown tool"):
        await protocol_handler.handle_tools_call(params)


def test_bearer_token_validation(protocol_handler):
    """Test bearer token validation."""
    # Valid token
    assert protocol_handler.validate_bearer_token("Bearer test-token") is True
    assert protocol_handler.validate_bearer_token("test-token") is True
    
    # Invalid tokens
    assert protocol_handler.validate_bearer_token("Bearer invalid-token") is False
    assert protocol_handler.validate_bearer_token("") is False
    assert protocol_handler.validate_bearer_token(None) is False


@pytest.mark.asyncio
async def test_handle_request_initialize(protocol_handler):
    """Test full request handling for initialize."""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"}
        }
    }
    
    response = await protocol_handler.handle_request(request, None)
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response
    assert response["result"]["protocolVersion"] == "2024-11-05"


@pytest.mark.asyncio
async def test_handle_request_unauthorized(protocol_handler):
    """Test request handling without valid bearer token."""
    request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    
    response = await protocol_handler.handle_request(request, None)
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 2
    assert "error" in response
    assert response["error"]["code"] == -32001
    assert "Unauthorized" in response["error"]["message"]


@pytest.mark.asyncio
async def test_handle_request_tools_list(protocol_handler):
    """Test request handling for tools/list."""
    request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/list",
        "params": {}
    }
    
    response = await protocol_handler.handle_request(request, "Bearer test-token")
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 3
    assert "result" in response
    assert "tools" in response["result"]


@pytest.mark.asyncio
async def test_handle_request_method_not_found(protocol_handler):
    """Test request handling for unknown method."""
    request = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "unknown/method",
        "params": {}
    }
    
    response = await protocol_handler.handle_request(request, "Bearer test-token")
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 4
    assert "error" in response
    assert response["error"]["code"] == -32601
    assert "Method not found" in response["error"]["message"]


def test_create_error_response(protocol_handler):
    """Test error response creation."""
    error = protocol_handler.create_error_response(
        error_code=-32600,
        error_message="Invalid Request",
        request_id=5
    )
    
    assert error["jsonrpc"] == "2.0"
    assert error["id"] == 5
    assert error["error"]["code"] == -32600
    assert error["error"]["message"] == "Invalid Request"
