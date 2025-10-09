#!/usr/bin/env python3

import requests
import json
import base64
import time

def test_mcp_server_with_llabs_payload():
    """Test NEW TopDesk Custom MCP server with exactif __name__ == '__main__':
    print("NEW TopDesk Custom MCP Server Test (Direct Implementation)")
    print("=" * 60)
    print("🔧 Testing the new custom MCP that avoids FastMCP parameter validation bugs")
    print("=" * 60)
    
    # Test NEW Custom MCP server
    test_mcp_server_with_llabs_payload()
    
    # Test direct TopDesk API for comparison
    test_direct_topdesk_api()
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("If both work, the new custom MCP has successfully replaced the buggy FastMCP implementation.")
    print("=" * 60)ad format"""
    
    # NEW: TopDesk Custom MCP details (avoiding FastMCP bugs)
    mcp_url = 'https://matrosmcp.duckdns.org/topdesk/mcp'
    token = 'e3707c16425c14fa417e2384a12748c0c7c51dfdfd1714c58992215983f33257'
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream'
    }
    
    print("🧪 Testing NEW TopDesk Custom MCP server (avoiding FastMCP bugs)")
    print("=" * 60)
    
    # Initialize MCP server
    print("🔧 Initializing MCP server...")
    init_data = {
        'jsonrpc': '2.0',
        'id': int(time.time() * 1000),
        'method': 'initialize',
        'params': {
            'protocolVersion': '2024-11-05',
            'capabilities': {},
            'clientInfo': {
                'name': 'test-client',
                'version': '1.0.0'
            }
        }
    }
    
    response = requests.post(mcp_url, headers=headers, json=init_data, timeout=30)
    print(f"Init Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ Init failed: {response.text}")
        return
    
    # NEW: TopDesk Custom MCP doesn't use session IDs - it's stateless with bearer tokens
    print("✅ Custom MCP initialized successfully (stateless authentication)")
    time.sleep(1)
    
    # Test with simplified MCP payload using known person ID
    print("\n🎯 Testing with MCP payload using real person ID...")
    
    # Using Jacob Aalbregt's actual TopDesk ID
    jacob_id = "d34b277f-e6a2-534c-a96b-23bf383cb4a1"
    
    mcp_payload = {
        "caller_id": jacob_id,
        "brief_description": "Kan niet inloggen op Windows",
        "request": "Medewerker Jacob kan niet inloggen op Windows. Foutmelding: 'geen gebruiker onder deze naam'. Meerdere collega's hebben hetzelfde probleem. Locatie: Den Haag, gebouw A, afdeling 3. Staat volledig stil.",
        "category": "Core applicaties",
        "priority": "P1 (I&A)"
    }
    
    print(f"Payload: {json.dumps(mcp_payload, indent=2)}")
    
    # Call the tool
    tool_call_data = {
        'jsonrpc': '2.0',
        'id': int(time.time() * 1000),
        'method': 'tools/call',
        'params': {
            'name': 'topdesk_create_incident',
            'arguments': mcp_payload
        }
    }
    
    print(f"\nTool call: {json.dumps(tool_call_data, indent=2)}")
    
    tool_response = requests.post(mcp_url, headers=headers, json=tool_call_data, timeout=30)
    print(f"\nTool Status: {tool_response.status_code}")
    print(f"Tool Response: {tool_response.text}")
    
    # Parse SSE response
    if tool_response.status_code == 200:
        response_text = tool_response.text
        if 'data: ' in response_text:
            json_part = response_text.split('data: ')[1].strip()
            try:
                result = json.loads(json_part)
                print(f"\nParsed result: {json.dumps(result, indent=2)}")
                
                if 'result' in result:
                    print(f"\n✅ SUCCESS! Tool call worked:")
                    print(f"Result: {result['result']}")
                elif 'error' in result:
                    print(f"\n❌ Tool call error: {result['error']}")
                else:
                    print(f"\nUnexpected response: {result}")
            except json.JSONDecodeError as e:
                print(f"\n❌ JSON parse error: {e}")
                print(f"Raw JSON: {json_part}")
        else:
            print(f"\n❌ No data field in response: {response_text}")
    else:
        print(f"\n❌ HTTP error: {tool_response.status_code}")
        print(f"Response: {tool_response.text}")

def test_direct_topdesk_api():
    """Test direct TOPdesk API for comparison"""
    
    print("\n" + "=" * 60)
    print("🔍 Testing direct TOPdesk API for comparison")
    print("=" * 60)
    
    # TOPdesk API details (TEST instance - matches MCP container)
    base_url = "https://pietervanforeest-test.topdesk.net/tas/api"
    username = "api_aipilots"  # lowercase, matches container
    password = "7w7j6-ytlqt-wpcbz-ywu6v-remw7"  # matches container
    
    # Build auth token
    api_token = base64.b64encode(f"{username}:{password}".encode()).decode()
    
    headers = {
        'Authorization': f'Basic {api_token}',
        'Content-Type': 'application/json'
    }
    
    # Convert to TOPdesk format with real person ID (same Jacob from test instance)
    jacob_id = "d34b277f-e6a2-534c-a96b-23bf383cb4a1"
    
    topdesk_payload = {
        "briefDescription": "Kan niet inloggen op Windows",
        "request": "Medewerker Jacob kan niet inloggen op Windows. Foutmelding: 'geen gebruiker onder deze naam'. Meerdere collega's hebben hetzelfde probleem. Locatie: Den Haag, gebouw A, afdeling 3. Staat volledig stil.",
        "caller": {
            "id": jacob_id
        },
        "category": {
            "name": "Core applicaties"
        },
        "priority": {
            "name": "P1 (I&A)"
        }
    }
    
    print(f"TOPdesk payload: {json.dumps(topdesk_payload, indent=2)}")
    
    # Test with TOPdesk API
    url = f"{base_url}/incidents"
    print(f"\nTesting with TOPdesk API: {url}")
    
    try:
        response = requests.post(url, headers=headers, json=topdesk_payload, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"\n✅ SUCCESS! Incident created:")
            print(f"   Number: {result.get('number', 'N/A')}")
            print(f"   ID: {result.get('id', 'N/A')}")
        else:
            print(f"\n❌ FAILED: {response.status_code}")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

if __name__ == '__main__':
    print("MCP Server Test with 11Labs Payload Format")
    print("=" * 50)
    
    # Test MCP server
    test_mcp_server_with_llabs_payload()
    
    # Test direct TOPdesk API for comparison
    test_direct_topdesk_api()
    
    print("\n" + "=" * 50)
    print("Test completed!")
    print("If MCP fails but direct API works, the issue is in MCP server configuration.")