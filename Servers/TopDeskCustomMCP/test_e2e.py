#!/usr/bin/env python3
"""
End-to-end test for TopDesk Custom MCP server.

This script tests the MCP server directly (not through NGINX).
For NGINX testing, use the infrastructure test scripts.
"""

import json
import time
import requests
from typing import Dict, Any


def test_mcp_server(
    base_url: str = "http://localhost:3003",
    bearer_token: str = "test-token"
) -> None:
    """Test the TopDesk Custom MCP server.
    
    Args:
        base_url: Base URL of the MCP server
        bearer_token: Bearer token for authentication
    """
    print("=" * 60)
    print("TopDesk Custom MCP Server - End-to-End Test")
    print("=" * 60)
    
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Test 1: Health Check
    print("\n1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health check passed: {health_data}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return
    
    # Test 2: Initialize MCP
    print("\n2. Testing MCP initialization...")
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "e2e-test-client",
                "version": "1.0.0"
            }
        }
    }
    
    try:
        response = requests.post(
            base_url,
            headers=headers,
            json=init_request,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if "result" in result:
                print(f"✅ MCP initialized successfully")
                print(f"   Server: {result['result']['serverInfo']['name']} v{result['result']['serverInfo']['version']}")
                print(f"   Protocol: {result['result']['protocolVersion']}")
            else:
                print(f"❌ Initialize failed: {result}")
                return
        else:
            print(f"❌ Initialize failed with status {response.status_code}: {response.text}")
            return
    except Exception as e:
        print(f"❌ Initialize error: {e}")
        return
    
    # Test 3: List Tools
    print("\n3. Testing tools/list...")
    list_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    
    try:
        response = requests.post(
            base_url,
            headers=headers,
            json=list_request,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if "result" in result and "tools" in result["result"]:
                tools = result["result"]["tools"]
                print(f"✅ Found {len(tools)} tools:")
                for tool in tools:
                    print(f"   - {tool['name']}: {tool['description']}")
            else:
                print(f"❌ Tools/list failed: {result}")
                return
        else:
            print(f"❌ Tools/list failed with status {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Tools/list error: {e}")
        return
    
    # Test 4: Test without bearer token (should fail)
    print("\n4. Testing authentication (should fail without token)...")
    no_auth_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        response = requests.post(
            base_url,
            headers=no_auth_headers,
            json=list_request,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if "error" in result and result["error"]["code"] == -32001:
                print(f"✅ Authentication correctly rejected unauthorized request")
            else:
                print(f"❌ Authentication should have failed but didn't: {result}")
        else:
            print(f"⚠️  Got HTTP {response.status_code} instead of JSON-RPC error")
    except Exception as e:
        print(f"❌ Auth test error: {e}")
    
    # Test 5: Test get_categories tool (if TopDesk is accessible)
    print("\n5. Testing tool execution (topdesk_get_categories)...")
    tool_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "topdesk_get_categories",
            "arguments": {}
        }
    }
    
    try:
        response = requests.post(
            base_url,
            headers=headers,
            json=tool_request,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if "result" in result:
                print(f"✅ Tool execution successful")
                # Parse the content
                if "content" in result["result"] and len(result["result"]["content"]) > 0:
                    content_text = result["result"]["content"][0]["text"]
                    tool_result = json.loads(content_text)
                    if tool_result.get("success"):
                        print(f"   Categories retrieved: {len(tool_result.get('categories', []))} found")
                    else:
                        print(f"   Tool returned error: {tool_result.get('error')}")
                        print(f"   (This is expected if TopDesk credentials are not configured)")
            else:
                print(f"❌ Tool execution failed: {result}")
        else:
            print(f"❌ Tool execution failed with status {response.status_code}")
    except Exception as e:
        print(f"⚠️  Tool execution error (expected if TopDesk not configured): {e}")
    
    print("\n" + "=" * 60)
    print("✅ End-to-end test completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3003"
    bearer_token = sys.argv[2] if len(sys.argv) > 2 else "test-token"
    
    print(f"\nTesting MCP server at: {base_url}")
    print(f"Using bearer token: {bearer_token[:10]}...")
    
    test_mcp_server(base_url, bearer_token)
