#!/usr/bin/env python3
"""
Example: Retrieve TopDesk incident by ticket number (e.g., "I2510 017")
"""

import requests
import json
import os
from urllib.parse import quote

def get_incident_by_number(ticket_number):
    """
    Retrieve incident details using ticket number (e.g., "I2510 017")
    
    Args:
        ticket_number (str): The incident number like "I2510 017"
    
    Returns:
        dict: Incident details or None if not found
    """
    
    # TopDesk API configuration
    base_url = "https://pietervanforeest-test.topdesk.net"
    username = "api_aipilots"
    password = os.getenv('TOPDESK_PASSWORD', '')
    
    # Method 1: Search incidents by number field
    search_url = f"{base_url}/tas/api/incidents"
    
    # Use query parameter to search by number
    params = {
        'query': f'number=="{ticket_number}"',
        'fields': 'id,number,briefDescription,status,caller,priority,category,creationDate'
    }
    
    try:
        response = requests.get(
            search_url,
            params=params,
            auth=(username, password),
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Search URL: {response.url}")
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            incidents = response.json()
            if incidents and len(incidents) > 0:
                incident = incidents[0]  # Should be only one match
                print(f"✅ Found incident: {incident.get('number')} - {incident.get('briefDescription')}")
                return incident
            else:
                print(f"❌ No incident found with number: {ticket_number}")
                return None
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return None

def get_incident_by_number_alternative(ticket_number):
    """
    Alternative method: Use query string search
    """
    base_url = "https://pietervanforeest-test.topdesk.net"
    username = "api_aipilots"
    password = os.getenv('TOPDESK_PASSWORD', '')
    
    # Method 2: Use the search endpoint with different syntax
    search_url = f"{base_url}/tas/api/incidents"
    
    # Alternative query format
    params = {
        '$filter': f"number eq '{ticket_number}'",
        '$select': 'id,number,briefDescription,status,caller,priority,category'
    }
    
    try:
        response = requests.get(
            search_url,
            params=params,
            auth=(username, password),
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Alternative Search URL: {response.url}")
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            incidents = response.json()
            if incidents and len(incidents) > 0:
                return incidents[0]
            else:
                print(f"❌ No incident found with alternative method")
                return None
        else:
            print(f"❌ Alternative API Error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Alternative Exception: {str(e)}")
        return None

def get_full_incident_details(incident_id):
    """
    Once you have the UUID, get full incident details
    """
    base_url = "https://pietervanforeest-test.topdesk.net"
    username = "api_aipilots"
    password = os.getenv('TOPDESK_PASSWORD', '')
    
    detail_url = f"{base_url}/tas/api/incidents/id/{incident_id}"
    
    try:
        response = requests.get(
            detail_url,
            auth=(username, password),
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Error getting details: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Exception getting details: {str(e)}")
        return None

if __name__ == "__main__":
    # Example usage
    ticket_numbers = ["I2510 017", "I2510 018"]  # Recently created tickets
    
    for ticket_number in ticket_numbers:
        print(f"\n🔍 Searching for incident: {ticket_number}")
        print("=" * 50)
        
        # Try primary method
        incident = get_incident_by_number(ticket_number)
        
        if incident:
            # Get full details using the UUID
            incident_id = incident.get('id')
            if incident_id:
                print(f"\n📋 Getting full details for ID: {incident_id}")
                full_details = get_full_incident_details(incident_id)
                if full_details:
                    print(f"✅ Full incident details retrieved")
                    print(f"   Number: {full_details.get('number')}")
                    print(f"   Description: {full_details.get('briefDescription')}")
                    print(f"   Status: {full_details.get('processingStatus', {}).get('name')}")
                    print(f"   Caller: {full_details.get('caller', {}).get('dynamicName')}")
                    print(f"   Created: {full_details.get('creationDate')}")
        else:
            # Try alternative method
            print(f"\n🔄 Trying alternative search method...")
            incident = get_incident_by_number_alternative(ticket_number)
            if incident:
                print(f"✅ Found with alternative method: {incident.get('number')}")