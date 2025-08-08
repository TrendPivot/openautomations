#!/usr/bin/env python3
"""
Zendesk Internal Note Adder
Adds internal notes to specific Zendesk tickets
"""

import os
import sys
import json
import requests
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class ZendeskNoteAdder:
    def __init__(self):
        # Zendesk Configuration (same as DMCA analyzer)
        self.zendesk_auth = ("billing@rarible.com/token", os.getenv("ZENDESK_PASSWORD", ""))
        self.zendesk_base_url = "https://rariblecom.zendesk.com/api/v2"
        
        # Validate authentication
        if not self.zendesk_auth[1]:
            logging.error("ZENDESK_PASSWORD environment variable not set")
            sys.exit(1)

    def add_internal_note(self, ticket_id: int, note_text: str) -> bool:
        """Add an internal note to a specific Zendesk ticket"""
        try:
            # Zendesk API endpoint for adding comments
            url = f"{self.zendesk_base_url}/tickets/{ticket_id}.json"
            
            # Payload for internal comment
            payload = {
                "ticket": {
                    "comment": {
                        "body": note_text,
                        "public": False,  # Internal note (not visible to requester)
                        "author_id": None  # Will use the authenticated user
                    }
                }
            }
            
            logging.info(f"Adding internal note to ticket {ticket_id}")
            logging.info(f"Note text: {note_text}")
            
            # Make the API request
            response = requests.put(
                url,
                json=payload,
                auth=self.zendesk_auth,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                timeout=30
            )
            
            # Check response
            if response.status_code == 200:
                logging.info(f"✅ Successfully added internal note to ticket {ticket_id}")
                return True
            else:
                logging.error(f"❌ Failed to add note. Status: {response.status_code}")
                logging.error(f"Response: {response.text}")
                return False
                
        except requests.RequestException as e:
            logging.error(f"❌ Request failed: {e}")
            return False
        except Exception as e:
            logging.error(f"❌ Unexpected error: {e}")
            return False

    def get_ticket_info(self, ticket_id: int) -> dict:
        """Get basic ticket information for verification"""
        try:
            url = f"{self.zendesk_base_url}/tickets/{ticket_id}.json"
            
            response = requests.get(
                url,
                auth=self.zendesk_auth,
                timeout=30
            )
            
            if response.status_code == 200:
                ticket_data = response.json()['ticket']
                return {
                    'id': ticket_data['id'],
                    'subject': ticket_data['subject'],
                    'status': ticket_data['status'],
                    'created_at': ticket_data['created_at'],
                    'url': f"https://rariblecom.zendesk.com/agent/tickets/{ticket_id}"
                }
            else:
                logging.error(f"Failed to get ticket info. Status: {response.status_code}")
                return None
                
        except Exception as e:
            logging.error(f"Error getting ticket info: {e}")
            return None

def main():
    """Main function to add note to specific ticket"""
    # Configuration for this specific task
    TICKET_ID = 107289
    NOTE_TEXT = "🤖OpenAutomations: DMCA request is processed"
    
    print("="*60)
    print("ZENDESK INTERNAL NOTE ADDER")
    print("="*60)
    
    # Initialize the note adder
    note_adder = ZendeskNoteAdder()
    
    # Get ticket info first for verification
    print(f"\n📋 TICKET INFORMATION")
    print("-" * 25)
    ticket_info = note_adder.get_ticket_info(TICKET_ID)
    
    if ticket_info:
        print(f"Ticket ID: {ticket_info['id']}")
        print(f"Subject: {ticket_info['subject']}")
        print(f"Status: {ticket_info['status']}")
        print(f"Created: {ticket_info['created_at']}")
        print(f"Agent URL: {ticket_info['url']}")
        
        # Ask for confirmation
        print(f"\n💬 NOTE TO ADD")
        print("-" * 15)
        print(f'"{NOTE_TEXT}"')
        
        # Add the note
        print(f"\n🔄 ADDING NOTE")
        print("-" * 15)
        success = note_adder.add_internal_note(TICKET_ID, NOTE_TEXT)
        
        if success:
            print(f"\n✅ SUCCESS!")
            print(f"Internal note added to ticket {TICKET_ID}")
            print(f"View at: {ticket_info['url']}")
        else:
            print(f"\n❌ FAILED!")
            print("Check logs for error details")
            
    else:
        print(f"❌ Could not retrieve ticket {TICKET_ID}")
        print("Check ticket ID and permissions")

    print("\n" + "="*60)

if __name__ == "__main__":
    main() 
