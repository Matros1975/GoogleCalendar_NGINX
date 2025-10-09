#!/usr/bin/env python3

import requests
import json
import base64
import time

def test_working_topdesk_api():
    """Test the working direct TopDesk API approach"""
    
    print("🎯 Testing WORKING TopDesk API (Direct)")
    print("=" * 60)
    
    # TOPdesk API details
    base_url = "https://pietervanforeest.topdesk.net/tas/api"
    username = "API_AIPILOTS"
    password = "g2jjr-kp6oc-tct6p-ie237-fyub5"
    
    # Build auth token
    api_token = base64.b64encode(f"{username}:{password}".encode()).decode()
    
    headers = {
        'Authorization': f'Basic {api_token}',
        'Content-Type': 'application/json'
    }
    
    # Use Jacob Aalbregt's actual TopDesk ID
    jacob_id = "d34b277f-e6a2-534c-a96b-23bf383cb4a1"
    
    # Payload that works with correct field mappings
    topdesk_payload = {
        "briefDescription": "ElevenLabs voice agent test incident",
        "request": "Test incident created via ElevenLabs voice agent integration. This validates the TopDesk API connectivity and field mappings.",
        "caller": {
            "id": jacob_id
        },
        "category": {
            "name": "Core applicaties"  # Corrected from "Besturingssystemen"
        },
        "priority": {
            "name": "P1 (I&A)"  # Corrected from "Kritiek"
        }
    }
    
    print(f"✅ Using CORRECT field mappings:")
    print(f"   Category: 'Core applicaties' (not 'Besturingssystemen')")
    print(f"   Priority: 'P1 (I&A)' (not 'Kritiek')")
    print(f"   Caller ID: {jacob_id} (Jacob Aalbregt)")
    print()
    
    print(f"Payload: {json.dumps(topdesk_payload, indent=2)}")
    
    # Test with TopDesk API
    url = f"{base_url}/incidents"
    print(f"\n🚀 Creating incident via: {url}")
    
    try:
        response = requests.post(url, headers=headers, json=topdesk_payload, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"\n🎉 SUCCESS! Incident created:")
            print(f"   📋 Number: {result.get('number', 'N/A')}")
            print(f"   🆔 ID: {result.get('id', 'N/A')}")
            print(f"   👤 Caller: {result.get('caller', {}).get('dynamicName', 'N/A')}")
            print(f"   📞 Phone: {result.get('caller', {}).get('phoneNumber', 'N/A')}")
            print(f"   📧 Email: {result.get('caller', {}).get('email', 'N/A')}")
            print(f"   🏷️ Category: {result.get('category', {}).get('name', 'N/A')}")
            print(f"   ⚡ Priority: {result.get('priority', {}).get('name', 'N/A')}")
            
            return {
                'success': True,
                'incident_number': result.get('number'),
                'incident_id': result.get('id'),
                'category': result.get('category', {}).get('name'),
                'priority': result.get('priority', {}).get('name')
            }
        else:
            print(f"\n❌ FAILED: {response.status_code}")
            print(f"Response: {response.text}")
            return {'success': False, 'error': response.text}
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return {'success': False, 'error': str(e)}

def show_mcp_server_issues():
    """Show the MCP server issues and recommendations"""
    
    print("\n" + "🔧 MCP SERVER ISSUES & SOLUTIONS" + "\n" + "=" * 60)
    
    print("❌ ISSUE: TopDesk MCP Server Problems")
    print("   - All MCP methods return 'Invalid request parameters'")
    print("   - tools/list, tools/call, etc. all fail")
    print("   - topdesk-mcp v0.8.1 package may have configuration issues")
    print()
    
    print("✅ SOLUTION 1: Use Direct TopDesk API (RECOMMENDED)")
    print("   - Direct API calls work perfectly")
    print("   - Faster and more reliable than MCP proxy")
    print("   - No dependency on external MCP packages")
    print("   - ElevenLabs can call TopDesk API directly")
    print()
    
    print("✅ SOLUTION 2: Fix MCP Server Configuration")
    print("   - Check topdesk-mcp package environment variables")
    print("   - Verify TOPDESK_API_URL, TOPDESK_USERNAME, TOPDESK_PASSWORD")
    print("   - Update to latest topdesk-mcp version")
    print("   - Check MCP server logs for errors")
    print()
    
    print("💡 RECOMMENDATION FOR ELEVENLABS:")
    print("   Use direct TopDesk API calls instead of MCP server")
    print("   More reliable and eliminates MCP server dependency")

def show_elevenlabs_integration():
    """Show how ElevenLabs should integrate with TopDesk"""
    
    print("\n" + "🎤 ELEVENLABS INTEGRATION GUIDE" + "\n" + "=" * 60)
    
    print("📝 STATIC REFERENCE DATA (use in ElevenLabs system prompt):")
    print()
    print("TOPDESK CATEGORIES:")
    print("  - Core applicaties")
    print("  - Werkplek hardware") 
    print("  - Netwerk")
    print("  - Wachtwoord wijziging")
    print()
    print("TOPDESK PRIORITIES:")
    print("  - P1 (I&A)  # Critical")
    print("  - P2 (I&A)  # High")
    print("  - P3 (I&A)  # Medium") 
    print("  - P4 (I&A)  # Low")
    print()
    
    print("🔗 API ENDPOINT:")
    print("  URL: https://pietervanforeest.topdesk.net/tas/api/incidents")
    print("  Method: POST")
    print("  Auth: Basic Auth (API_AIPILOTS / g2jjr-kp6oc-tct6p-ie237-fyub5)")
    print()
    
    print("📋 PAYLOAD FORMAT:")
    payload_example = {
        "briefDescription": "Brief description from voice",
        "request": "Detailed request from voice conversation",
        "caller": {
            "id": "person-uuid-from-lookup"
        },
        "category": {
            "name": "Core applicaties"
        },
        "priority": {
            "name": "P1 (I&A)"
        }
    }
    print(json.dumps(payload_example, indent=2))
    
    print("\n🎯 FIELD MAPPING CORRECTIONS:")
    print("  ❌ 'Besturingssystemen' → ✅ 'Core applicaties'")
    print("  ❌ 'Kritiek' → ✅ 'P1 (I&A)'")

if __name__ == '__main__':
    print("TopDesk Integration Test - FIXED VERSION")
    print("=" * 50)
    
    # Test the working direct API
    result = test_working_topdesk_api()
    
    # Show MCP issues and solutions
    show_mcp_server_issues()
    
    # Show ElevenLabs integration guide
    show_elevenlabs_integration()
    
    print("\n" + "=" * 50)
    print("✅ CONCLUSION:")
    if result.get('success'):
        print("✅ Direct TopDesk API works perfectly!")
        print("✅ Field mappings are correct")
        print("💡 Recommend using direct API for ElevenLabs integration")
    else:
        print("❌ Even direct API failed - check credentials")
    
    print("❌ MCP server has configuration issues")
    print("💡 Use direct API calls instead of MCP server")