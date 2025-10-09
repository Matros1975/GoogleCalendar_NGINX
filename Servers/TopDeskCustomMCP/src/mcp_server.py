"""MCP protocol server implementation (direct, not FastMCP)."""

import json
import logging
from typing import Dict, Any, Optional, Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from .auth.bearer_validator import BearerTokenValidator


logger = logging.getLogger(__name__)


class MCPProtocolHandler:
    """Handler for MCP protocol (JSON-RPC 2.0)."""
    
    # MCP Protocol version
    PROTOCOL_VERSION = "2024-11-05"
    
    def __init__(
        self,
        server_name: str,
        server_version: str,
        bearer_validator: BearerTokenValidator
    ):
        """Initialize MCP protocol handler.
        
        Args:
            server_name: Name of the MCP server
            server_version: Version of the MCP server
            bearer_validator: Bearer token validator instance
        """
        self.server_name = server_name
        self.server_version = server_version
        self.bearer_validator = bearer_validator
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.tool_handlers: Dict[str, Callable] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
    
    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: Callable
    ) -> None:
        """Register a tool with the MCP server.
        
        Args:
            name: Tool name
            description: Tool description
            input_schema: JSON Schema for tool input
            handler: Callable that handles tool execution
        """
        self.tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema
        }
        self.tool_handlers[name] = handler
        logger.info(f"Registered tool: {name}")
    
    def validate_bearer_token(self, authorization_header: Optional[str]) -> bool:
        """Validate bearer token from Authorization header.
        
        Args:
            authorization_header: Authorization header value
            
        Returns:
            True if valid, False otherwise
        """
        if not authorization_header:
            return False
        
        return self.bearer_validator.validate_token(authorization_header)
    
    def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialize method.
        
        Args:
            params: Initialize parameters
            
        Returns:
            Initialize response
        """
        protocol_version = params.get("protocolVersion")
        if protocol_version != self.PROTOCOL_VERSION:
            logger.warning(f"Client protocol version {protocol_version} != {self.PROTOCOL_VERSION}")
        
        return {
            "protocolVersion": self.PROTOCOL_VERSION,
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": self.server_name,
                "version": self.server_version
            }
        }
    
    def handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list method.
        
        Args:
            params: List parameters
            
        Returns:
            List of tools
        """
        return {
            "tools": list(self.tools.values())
        }
    
    async def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call method.
        
        Args:
            params: Tool call parameters
            
        Returns:
            Tool execution result
        """
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in self.tool_handlers:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        handler = self.tool_handlers[tool_name]
        
        # Execute tool handler
        try:
            result = await handler(arguments)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2)
                    }
                ]
            }
        except Exception as e:
            logger.exception(f"Error executing tool {tool_name}")
            raise
    
    def create_error_response(
        self,
        error_code: int,
        error_message: str,
        request_id: Any = None
    ) -> Dict[str, Any]:
        """Create JSON-RPC error response.
        
        Args:
            error_code: JSON-RPC error code
            error_message: Error message
            request_id: Request ID
            
        Returns:
            JSON-RPC error response
        """
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": error_code,
                "message": error_message
            }
        }
    
    async def handle_request(
        self,
        request_data: Dict[str, Any],
        authorization_header: Optional[str]
    ) -> Dict[str, Any]:
        """Handle incoming JSON-RPC request.
        
        Args:
            request_data: JSON-RPC request
            authorization_header: Authorization header value
            
        Returns:
            JSON-RPC response
        """
        request_id = request_data.get("id")
        method = request_data.get("method")
        params = request_data.get("params", {})
        
        # Validate bearer token for all methods except initialize
        if method != "initialize":
            if not self.validate_bearer_token(authorization_header):
                return self.create_error_response(
                    -32001,
                    "Unauthorized: Invalid or missing bearer token",
                    request_id
                )
        
        try:
            # Route to appropriate handler
            if method == "initialize":
                result = self.handle_initialize(params)
            elif method == "tools/list":
                result = self.handle_tools_list(params)
            elif method == "tools/call":
                result = await self.handle_tools_call(params)
            else:
                return self.create_error_response(
                    -32601,
                    f"Method not found: {method}",
                    request_id
                )
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
            
        except ValueError as e:
            return self.create_error_response(-32602, str(e), request_id)
        except Exception as e:
            logger.exception(f"Error handling request: {method}")
            return self.create_error_response(-32603, "Internal error", request_id)


class MCPHTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for MCP server."""
    
    protocol_handler: MCPProtocolHandler = None
    
    def log_message(self, format: str, *args) -> None:
        """Override to use Python logging."""
        logger.info(f"{self.address_string()} - {format % args}")
    
    def do_OPTIONS(self) -> None:
        """Handle OPTIONS request (CORS preflight)."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_GET(self) -> None:
        """Handle GET request."""
        parsed_path = urlparse(self.path)
        
        # Health check endpoint
        if parsed_path.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            health_data = {
                "status": "healthy",
                "server": self.protocol_handler.server_name,
                "version": self.protocol_handler.server_version
            }
            self.wfile.write(json.dumps(health_data).encode())
            return
        
        # Default: method not allowed
        self.send_response(405)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"error": "Method not allowed"}).encode())
    
    def do_POST(self) -> None:
        """Handle POST request."""
        import asyncio
        
        # Get content length
        content_length = int(self.headers.get('Content-Length', 0))
        
        # Read request body
        try:
            body = self.rfile.read(content_length)
            request_data = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
            self.wfile.write(json.dumps(error).encode())
            return
        
        # Get authorization header
        authorization = self.headers.get('Authorization')
        
        # Handle request
        try:
            # Run async handler in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(
                self.protocol_handler.handle_request(request_data, authorization)
            )
            loop.close()
            
            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            logger.exception("Error handling POST request")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": "Internal error"}
            }
            self.wfile.write(json.dumps(error).encode())


class MCPServer:
    """MCP server with HTTP transport."""
    
    def __init__(
        self,
        server_name: str,
        server_version: str,
        bearer_validator: BearerTokenValidator,
        host: str = "0.0.0.0",
        port: int = 3003
    ):
        """Initialize MCP server.
        
        Args:
            server_name: Name of the MCP server
            server_version: Version of the MCP server
            bearer_validator: Bearer token validator
            host: Host to bind to
            port: Port to bind to
        """
        self.protocol_handler = MCPProtocolHandler(
            server_name,
            server_version,
            bearer_validator
        )
        self.host = host
        self.port = port
        
        # Set class variable for request handler
        MCPHTTPRequestHandler.protocol_handler = self.protocol_handler
    
    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: Callable
    ) -> None:
        """Register a tool."""
        self.protocol_handler.register_tool(name, description, input_schema, handler)
    
    def start(self) -> None:
        """Start the MCP server."""
        server = HTTPServer((self.host, self.port), MCPHTTPRequestHandler)
        logger.info(f"TopDesk Custom MCP Server listening on http://{self.host}:{self.port}")
        logger.info(f"Tools registered: {len(self.protocol_handler.tools)}")
        
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        finally:
            server.shutdown()
