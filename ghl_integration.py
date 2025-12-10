"""
GoHighLevel API Integration Module
Handles fetching contact details from GoHighLevel CRM
"""

import requests
import pandas as pd
from typing import List, Dict, Optional, Tuple
import time


class GoHighLevelClient:
    BASE_URL = "https://services.leadconnectorhq.com"

    def __init__(self, api_key: str, location_id: str):
        self.location_id = location_id
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Version": "2021-07-28",
            "Content-Type": "application/json",
        }
        self._custom_field_map = None
    
    def get_custom_fields_map(self) -> Dict[str, str]:
        """
        Fetch custom field definitions and create ID -> Name mapping
        Returns: Dict mapping field IDs to field names
        """
        if self._custom_field_map is not None:
            return self._custom_field_map
        
        url = f"{self.BASE_URL}/locations/{self.location_id}/customFields"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            field_map = {}
            custom_fields = data.get("customFields", [])
            
            for field in custom_fields:
                field_id = field.get("id")
                field_name = field.get("name")
                if field_id and field_name:
                    field_map[field_id] = field_name
            
            self._custom_field_map = field_map
            return field_map
            
        except requests.exceptions.RequestException as e:
            return {}
    
    def search_contact_by_email(self, email: str) -> Optional[Dict]:
        """
        Search contact by email
        """
        url = f"{self.BASE_URL}/contacts/search"

        payload = {
            "locationId": self.location_id,
            "query": email,
            "pageLimit": 10
        }

        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            contacts = data.get("contacts", [])
            
            for contact in contacts:
                if contact.get("email", "").lower() == email.lower():
                    return contact
            
            return None

        except requests.exceptions.RequestException:
            return None
    
    def get_contact_by_id(self, contact_id: str) -> Optional[Dict]:
        """
        Get contact details by contact ID
        """
        url = f"{self.BASE_URL}/contacts/{contact_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json().get("contact")
            
        except requests.exceptions.RequestException:
            return None


def parse_custom_fields(custom_fields_raw, field_map: Dict[str, str]) -> Dict[str, str]:
    """
    Parse GHL custom fields using the field map
    """
    result = {}
    
    if isinstance(custom_fields_raw, list):
        for field in custom_fields_raw:
            if isinstance(field, dict):
                field_id = field.get("id")
                field_value = field.get("value")
                
                # Convert list values to string
                if isinstance(field_value, list):
                    field_value = ", ".join(str(v) for v in field_value)
                
                if field_id and field_id in field_map:
                    field_name = field_map[field_id]
                    result[field_name] = str(field_value) if field_value else ""
    
    return result


def fetch_participants_from_ghl(
    api_key: str,
    location_id: str,
    emails: List[str],
    progress_callback=None
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Fetch participant details from GoHighLevel by email
    
    Returns:
        Tuple of (DataFrame, list of status messages)
    """
    client = GoHighLevelClient(api_key, location_id)
    messages = []
    
    # Get custom field definitions
    messages.append("📋 Loading custom field definitions...")
    field_map = client.get_custom_fields_map()
    
    if not field_map:
        messages.append("⚠️ Warning: Could not load custom field definitions")
    else:
        messages.append(f"✅ Loaded {len(field_map)} custom fields")
    
    participants = []
    
    for idx, email in enumerate(emails):
        messages.append(f"\n🔍 Searching for: {email}")
        
        if progress_callback:
            progress_callback((idx + 1) / len(emails))
        
        contact = client.search_contact_by_email(email)
        
        if contact:
            contact_id = contact.get("id")
            
            # Get full contact details
            full_contact = client.get_contact_by_id(contact_id)
            
            if full_contact:
                contact = full_contact
            
            # Parse custom fields
            custom_fields_raw = contact.get("customFields", [])
            custom_fields = parse_custom_fields(custom_fields_raw, field_map)
            
            participant = {
                "First name": contact.get("firstName", ""),
                "Last name": contact.get("lastName", ""),
                "Email": contact.get("email", ""),
                "Phone": contact.get("phone", ""),
                "Company Name": contact.get("companyName", ""),
                "Industry": custom_fields.get("Industry", ""),
                "Role": custom_fields.get("Role", ""),
                "What their company solves.": custom_fields.get("Solution", ""),
                "What is the biggest challenge you are currently facing in your business?": custom_fields.get("Biggest Challenge", ""),
                "What is your superpower—the one thing you do exceptionally well that could help others?": custom_fields.get("Superpower", ""),
            }
            participants.append(participant)
            
            name = f"{participant['First name']} {participant['Last name']}"
            messages.append(f"   ✅ Found: {name} - {participant['Company Name']}")
            
        else:
            messages.append(f"   ❌ Not found: {email}")
        
        time.sleep(0.2)
    
    messages.append(f"\n{'='*50}")
    messages.append(f"✅ Total participants fetched: {len(participants)}")
    
    return pd.DataFrame(participants), messages


def test_ghl_connection(api_key: str, location_id: str) -> bool:
    """
    Test GoHighLevel API connection
    """
    client = GoHighLevelClient(api_key, location_id)
    url = f"{client.BASE_URL}/contacts/search"

    payload = {
        "locationId": location_id,
        "pageLimit": 1
    }

    try:
        response = requests.post(url, json=payload, headers=client.headers)
        response.raise_for_status()
        return True
    except:
        return False
