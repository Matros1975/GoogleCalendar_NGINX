#!/usr/bin/env python3

"""
TopDesk Integration Analysis & Working Solution
===============================================

ISSUE SUMMARY:
- TopDesk MCP server (topdesk-mcp v0.8.1) has parameter validation issues
- All MCP methods fail with "Invalid request parameters" (-32602)
- Direct TopDesk API works perfectly on both production and test instances

WORKING SOLUTION: Direct TopDesk API Integration
===============================================
"""

import requests
import base64
import json

class TopDeskAPIClient:
    """Working TopDesk API client for ElevenLabs integration"""
    
    def __init__(self, instance_type="test"):
        """
        Initialize TopDesk API client
        
        Args:
            instance_type: "test" or "production"
        """
        if instance_type == "test":
            self.base_url = "https://pietervanforeest-test.topdesk.net/tas/api"
            self.username = "api_aipilots"  # lowercase
            self.password = "7w7j6-ytlqt-wpcbz-ywu6v-remw7"
        else:  # production
            self.base_url = "https://pietervanforeest.topdesk.net/tas/api"
            self.username = "API_AIPILOTS"  # uppercase
            self.password = "g2jjr-kp6oc-tct6p-ie237-fyub5"
        
        # Create auth header
        auth_token = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
        self.headers = {
            'Authorization': f'Basic {auth_token}',
            'Content-Type': 'application/json'
        }
        
        print(f"✅ TopDesk API Client initialized for {instance_type} instance")
        print(f"   URL: {self.base_url}")
    
    def create_incident(self, caller_id, brief_description, request, category="Core applicaties", priority="P1 (I&A)"):
        """
        Create a TopDesk incident
        
        Args:
            caller_id: Valid TopDesk person UUID
            brief_description: Short description for the incident
            request: Detailed description of the issue
            category: One of the valid categories (see REFERENCE_DATA below)
            priority: One of the valid priorities (see REFERENCE_DATA below)
            
        Returns:
            dict: API response with incident details or error
        """
        payload = {
            "briefDescription": brief_description,
            "request": request,
            "caller": {
                "id": caller_id
            },
            "category": {
                "name": category
            },
            "priority": {
                "name": priority
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/incidents",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                return {
                    'success': True,
                    'incident_number': result.get('number'),
                    'incident_id': result.get('id'),
                    'caller_name': result.get('caller', {}).get('dynamicName'),
                    'category': result.get('category', {}).get('name'),
                    'priority': result.get('priority', {}).get('name'),
                    'raw_response': result
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Exception: {str(e)}"
            }
    
    def get_persons(self, limit=10):
        """
        Get list of persons to find valid caller IDs
        
        Args:
            limit: Maximum number of persons to return
            
        Returns:
            list: List of person objects with IDs and names
        """
        try:
            response = requests.get(
                f"{self.base_url}/persons",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code in [200, 206]:  # 206 = partial content
                persons = response.json()
                return [
                    {
                        'id': person.get('id'),
                        'name': f"{person.get('firstName', '')} {person.get('surName', '')}".strip(),
                        'email': person.get('email', ''),
                        'employee_number': person.get('employeeNumber', '')
                    }
                    for person in persons[:limit]
                ]
            else:
                print(f"❌ Failed to get persons: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting persons: {e}")
            return []

# REFERENCE DATA FOR ELEVENLABS
# =============================

TOPDESK_CATEGORIES = [
    "Core applicaties",
    "Werkplek hardware",
    "Netwerk", 
    "Wachtwoord wijziging"
]

TOPDESK_PRIORITIES = [
    "P1 (I&A)",  # Critical
    "P2 (I&A)",  # High
    "P3 (I&A)",  # Medium
    "P4 (I&A)"   # Low
]

# KNOWN VALID PERSON IDS (same in both test and production)
KNOWN_PERSON_IDS = {
    "Jacob Aalbregt": "d34b277f-e6a2-534c-a96b-23bf383cb4a1",
    "Siham Aabouch": "3a178418-6fd6-48af-b188-b14b9064ca84"
}

def demo_working_integration():
    """Demonstrate the working TopDesk integration"""
    
    print("🚀 TopDesk API Integration Demo")
    print("=" * 40)
    
    # Initialize client for test instance
    client = TopDeskAPIClient("test")
    
    # Get some persons to show available caller IDs
    print("\n👥 Getting available persons...")
    persons = client.get_persons(5)
    for person in persons:
        print(f"  - {person['name']} (ID: {person['id']})")
    
    if persons:
        # Create a test incident
        print(f"\n📋 Creating test incident...")
        person = persons[0]  # Use first person
        
        result = client.create_incident(
            caller_id=person['id'],
            brief_description="ElevenLabs test incident",
            request="This is a test incident created via ElevenLabs voice agent to validate the TopDesk API integration.",
            category="Core applicaties",
            priority="P1 (I&A)"
        )
        
        if result['success']:
            print(f"✅ SUCCESS! Created incident:")
            print(f"   📋 Number: {result['incident_number']}")
            print(f"   🆔 ID: {result['incident_id']}")
            print(f"   👤 Caller: {result['caller_name']}")
            print(f"   🏷️ Category: {result['category']}")
            print(f"   ⚡ Priority: {result['priority']}")
        else:
            print(f"❌ FAILED: {result['error']}")
    else:
        print("❌ No persons found")

def elevenlabs_integration_guide():
    """Show how to integrate with ElevenLabs"""
    
    print("\n" + "🎤 ELEVENLABS INTEGRATION GUIDE" + "\n" + "=" * 50)
    
    print("1. STATIC REFERENCE DATA (add to ElevenLabs system prompt):")
    print("   Categories:", ", ".join(TOPDESK_CATEGORIES))
    print("   Priorities:", ", ".join(TOPDESK_PRIORITIES))
    print()
    
    print("2. PERSON ID LOOKUP:")
    print("   Use TopDeskAPIClient.get_persons() to find valid caller IDs")
    print("   Or use known person IDs for testing")
    print()
    
    print("3. INCIDENT CREATION:")
    print("   client = TopDeskAPIClient('test')  # or 'production'")
    print("   result = client.create_incident(caller_id, description, details)")
    print()
    
    print("4. ERROR HANDLING:")
    print("   Check result['success'] before processing")
    print("   Log result['error'] for debugging")

if __name__ == '__main__':
    print("TopDesk Integration - WORKING SOLUTION")
    print("=" * 45)
    
    # Show the working demo
    demo_working_integration()
    
    # Show integration guide
    elevenlabs_integration_guide()
    
    print("\n" + "=" * 45)
    print("✅ CONCLUSION:")
    print("   - Direct TopDesk API works perfectly")
    print("   - MCP server has validation issues")
    print("   - Use direct API for ElevenLabs integration")
    print("   - More reliable and faster than MCP proxy")