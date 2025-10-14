#!/usr/bin/env python3
"""
Simple TopDesk incident retrieval by ticket number
Usage: python3 get_topdesk_incident.py "I2510 017"
"""

import sys
import os
import requests
import json

def get_incident_by_ticket_number(ticket_number):
    """
    Retrieve TopDesk incident by ticket number
    
    Args:
        ticket_number (str): Incident number like "I2510 017"
        
    Returns:
        dict: Incident details or error information
    """
    
        # TopDesk credentials
    base_url = "https://pietervanforeest-test.topdesk.net"
    username = "api_aipilots"
    password = os.getenv('TOPDESK_PASSWORD', '')
    
    try:
        # Step 1: Search for incident by number
        search_url = f"{base_url}/tas/api/incidents"
        search_params = {
            'query': f'number=="{ticket_number}"',
            'fields': 'id,number,briefDescription'
        }
        
        search_response = requests.get(
            search_url,
            params=search_params,
            auth=(username, password),
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if search_response.status_code != 200:
            return {
                "success": False,
                "error": f"Search failed: HTTP {search_response.status_code}",
                "ticket_number": ticket_number
            }
        
        incidents = search_response.json()
        
        if not incidents or len(incidents) == 0:
            return {
                "success": False,
                "error": f"No incident found with number '{ticket_number}'",
                "ticket_number": ticket_number
            }
        
        # Step 2: Get full incident details using UUID
        incident_id = incidents[0]['id']
        detail_url = f"{base_url}/tas/api/incidents/id/{incident_id}"
        
        detail_response = requests.get(
            detail_url,
            auth=(username, password),
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if detail_response.status_code != 200:
            return {
                "success": False,
                "error": f"Detail fetch failed: HTTP {detail_response.status_code}",
                "ticket_number": ticket_number,
                "incident_id": incident_id
            }
        
        full_incident = detail_response.json()
        
        # Return formatted summary
        return {
            "success": True,
            "ticket_number": full_incident.get('number'),
            "incident_id": full_incident.get('id'),
            "description": full_incident.get('briefDescription'),
            "status": full_incident.get('processingStatus', {}).get('name'),
            "caller": {
                "name": full_incident.get('caller', {}).get('dynamicName'),
                "email": full_incident.get('caller', {}).get('email'),
                "phone": full_incident.get('caller', {}).get('phoneNumber')
            },
            "category": full_incident.get('category', {}).get('name'),
            "priority": full_incident.get('priority', {}).get('name'),
            "created": full_incident.get('creationDate'),
            "target_date": full_incident.get('targetDate'),
            "request_details": full_incident.get('request'),
            "operator": full_incident.get('operator', {}).get('name') if full_incident.get('operator') else None,
            "processing_status": full_incident.get('processingStatus', {}).get('name'),
            "branch": full_incident.get('callerBranch', {}).get('name')
        }
        
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timeout - TopDesk API did not respond in time",
            "ticket_number": ticket_number
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "Connection error - Could not connect to TopDesk API",
            "ticket_number": ticket_number
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "ticket_number": ticket_number
        }

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 get_topdesk_incident.py \"I2510 017\"")
        print("       python3 get_topdesk_incident.py I2510017")
        sys.exit(1)
    
    ticket_number = sys.argv[1].strip()
    print(f"🔍 Searching for incident: {ticket_number}")
    print("=" * 50)
    
    result = get_incident_by_ticket_number(ticket_number)
    
    if result["success"]:
        print("✅ INCIDENT FOUND!")
        print(f"   📋 Ticket: {result['ticket_number']}")
        print(f"   📝 Description: {result['description']}")
        print(f"   👤 Caller: {result['caller']['name']}")
        print(f"   📧 Email: {result['caller']['email']}")
        print(f"   📞 Phone: {result['caller']['phone']}")
        print(f"   📂 Category: {result['category']}")
        print(f"   ⚡ Priority: {result['priority']}")
        print(f"   📊 Status: {result['status']}")
        print(f"   🏢 Branch: {result['branch']}")
        print(f"   📅 Created: {result['created']}")
        print(f"   🎯 Target: {result['target_date']}")
        if result['operator']:
            print(f"   👨‍💻 Operator: {result['operator']}")
        print(f"   🆔 UUID: {result['incident_id']}")
        
        if result['request_details']:
            print(f"\n📄 Request Details:")
            print(f"   {result['request_details'][:200]}...")
            
    else:
        print("❌ INCIDENT NOT FOUND OR ERROR:")
        print(f"   {result['error']}")
    
    print("\n" + "=" * 50)
    print("Raw JSON response:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()