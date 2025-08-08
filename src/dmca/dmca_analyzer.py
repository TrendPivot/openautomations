#!/usr/bin/env python3
"""
Smart DMCA Request Analyzer
Fetches DMCA tickets from Zendesk, extracts and converts URLs, prepares for Airtable automation
"""

import os
import re
import json
import requests
import logging
from urllib.parse import unquote
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class DMCAAnalyzer:
    def __init__(self):
        # Zendesk Configuration
        self.zendesk_auth = ("billing@rarible.com/token", os.getenv("ZENDESK_PASSWORD", ""))
        self.zendesk_search_url = "https://rariblecom.zendesk.com/api/v2/search.json"
        
        # Airtable Configuration (hardcoded for DMCA automation)
        self.airtable_api_key = os.getenv("AIRTABLE_API_KEY", "")
        self.airtable_app_id = "appjPNekcQqLmNfu6"
        self.airtable_table_id = "tblo8hUjb3o9ppRBt"
        self.airtable_view_id = "viwyVw493gKptuXmE"
        self.airtable_base_url = f"https://api.airtable.com/v0/{self.airtable_app_id}/{self.airtable_table_id}"
        self.airtable_web_url = f"https://airtable.com/{self.airtable_app_id}/{self.airtable_table_id}/{self.airtable_view_id}?blocks=hide"
        
        # URL extraction regex
        self.url_regex = re.compile(
            r'((?:https?://)?(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*[-a-zA-Z0-9@:%_\+~#?&//=]))',
            re.IGNORECASE
        )

    def fetch_dmca_tickets(self) -> List[Dict]:
        """Fetch DMCA tickets from Zendesk using search API"""
        try:
            # Query for tickets with specific form ID and open status
            query = "type:ticket form:360003074771 status:open"
            params = {"query": query}
            
            logging.info(f"Fetching DMCA tickets with query: {query}")
            response = requests.get(
                self.zendesk_search_url,
                params=params,
                auth=self.zendesk_auth,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            tickets = data.get('results', [])
            
            logging.info(f"Retrieved {len(tickets)} DMCA tickets")
            return tickets
            
        except requests.RequestException as e:
            logging.error(f"Error fetching tickets from Zendesk: {e}")
            return []

    def extract_urls_from_description(self, description: str) -> List[str]:
        """Extract URLs from ticket description"""
        if not description:
            return []
        
        # Find all URLs in the description
        urls = self.url_regex.findall(description)
        
        # Clean and normalize URLs
        cleaned_urls = []
        for url in urls:
            # Add https if not present
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Decode URL-encoded characters
            url = unquote(url.replace('%3A', ':'))
            cleaned_urls.append(url.strip())
        
        return list(set(cleaned_urls))  # Remove duplicates

    def convert_opensea_url(self, url: str) -> str:
        """Convert OpenSea URLs to standardized format"""
        # OpenSea asset URL pattern
        opensea_asset_pattern = r'https://opensea\.io/assets/(matic|ethereum|arbitrum|optimism|polygon|base)/([a-zA-Z0-9]+)/([0-9]+)'
        match = re.search(opensea_asset_pattern, url, re.IGNORECASE)
        
        if match:
            chain, contract, token_id = match.groups()
            
            # Chain mapping
            chain_mapping = {
                'matic': 'POLYGON',
                'ethereum': 'ETHEREUM',
                'arbitrum': 'ARBITRUM',
                'optimism': 'OPTIMISM',
                'polygon': 'POLYGON',
                'base': 'BASE'
            }
            
            mapped_chain = chain_mapping.get(chain.lower(), chain.upper())
            return f"{mapped_chain}-{contract.lower()}:{token_id}"
        
        # OpenSea collection URL pattern
        opensea_collection_pattern = r'https://opensea\.io/collection/(.*?)(?:/|$|\?)'
        match = re.search(opensea_collection_pattern, url, re.IGNORECASE)
        
        if match:
            return match.group(1)
        
        return ""

    def convert_rarible_url(self, url: str) -> str:
        """Convert Rarible URLs to standardized format"""
        # Rarible user with chain pattern
        rarible_user_chain_pattern = r'https://((?:beta\.|testnet\.)?rarible\.com)/user/(ethereum|polygon|mantle|immutablex|flow|arbitrum|chiliz|lightlink|celo|zksync|base|rari|astarzkevm|kroma|xai|sei|oasys|saakuru|palm|lisk|etherlink|moonbeam|fivire|match|alephzero|aptos|shape|eclipse|telos|solana|abstract|berachain|apechain|arenaz|basecamptestnet|crossfi|goat|hederaevm|hyperevm|megaethtestnet|settlus|somniatestnet|viction|zkcandy)/([a-zA-Z0-9-]+)/?(?:owned|items)?/?$'
        match = re.search(rarible_user_chain_pattern, url, re.IGNORECASE)
        
        if match:
            chain, address = match.group(2), match.group(3)
            return f"{chain.upper()}-{address.lower()}"
        
        # Main Rarible pattern (token/collection)
        rarible_main_pattern = r'https://((?:beta\.|testnet\.)?rarible\.com)/(user|token|collection)/(?:(ethereum|polygon|mantle|immutablex|flow|arbitrum|chiliz|lightlink|celo|zksync|base|rari|astarzkevm|kroma|xai|sei|oasys|saakuru|palm|lisk|etherlink|moonbeam|fivire|match|alephzero|aptos|shape|eclipse|telos|solana|abstract|berachain|apechain|arenaz|basecamptestnet|crossfi|goat|hederaevm|hyperevm|megaethtestnet|settlus|somniatestnet|viction|zkcandy)/)?([a-zA-Z0-9-]+)(?::([a-zA-Z0-9]+))?/?(?:owned|items)?/?$'
        match = re.search(rarible_main_pattern, url, re.IGNORECASE)
        
        if match:
            resource_type = match.group(2)
            chain = match.group(3) or "ethereum"
            contract = match.group(4).lower()
            token_id = match.group(5) or ""
            
            if resource_type == 'user':
                return f"ETHEREUM-{contract}"
            
            # Handle special cases for chains without token IDs
            if chain.lower() in ['eclipse', 'solana']:
                return f"{chain.upper()}-{contract}"
            
            return f"{chain.upper()}-{contract}{':' + token_id if token_id else ''}"
        
        # Simplified Rarible collection pattern
        rarible_simple_pattern = r'rarible\.com/collection/(ethereum|polygon|mantle|immutablex|flow|arbitrum|chiliz|lightlink|celo|zksync|base|rari|astarzkevm|kroma|xai|sei|oasys|saakuru|palm|lisk|etherlink|moonbeam|fivire|match|alephzero|aptos|shape|eclipse|telos|solana|abstract|berachain|apechain|arenaz|basecamptestnet|crossfi|goat|hederaevm|hyperevm|megaethtestnet|settlus|somniatestnet|viction|zkcandy)/([a-zA-Z0-9]+)/?(?:items)?$'
        match = re.search(rarible_simple_pattern, url, re.IGNORECASE)
        
        if match:
            chain, contract = match.groups()
            if chain.lower() in ['eclipse', 'solana']:
                return f"{chain.upper()}-{contract.lower()}"
            return f"{chain.upper()}-{contract.lower()}"
        
        return ""

    def convert_rarible_fun_url(self, url: str) -> str:
        """Convert Rarible.fun URLs to standardized format"""
        rarible_fun_pattern = r'https://rarible\.fun/collections/([a-zA-Z0-9-]+)/([a-zA-Z0-9x]+)(?:/.*)?'
        match = re.search(rarible_fun_pattern, url, re.IGNORECASE)
        
        if match:
            chain, contract = match.groups()
            return f"{chain.upper()}-{contract.lower()}"
        
        return ""

    def convert_url(self, url: str) -> str:
        """Convert any supported marketplace URL to standardized format"""
        if not url:
            return ""
        
        # Decode URL-encoded characters
        url = url.replace('%3A', ':')
        
        # Try OpenSea conversion
        if 'opensea.io' in url:
            result = self.convert_opensea_url(url)
            if result:
                return result
        
        # Try Rarible conversion
        if 'rarible.com' in url:
            result = self.convert_rarible_url(url)
            if result:
                return result
        
        # Try Rarible.fun conversion
        if 'rarible.fun' in url:
            result = self.convert_rarible_fun_url(url)
            if result:
                return result
        
        return ""

    def analyze_ticket(self, ticket: Dict) -> Dict:
        """Analyze a single DMCA ticket"""
        ticket_id = ticket.get('id')
        subject = ticket.get('subject', '')
        description = ticket.get('description', '')
        created_at = ticket.get('created_at', '')
        url = ticket.get('url', '')
        
        # Extract URLs from description
        urls = self.extract_urls_from_description(description)
        
        # Convert URLs to standardized format
        converted_urls = []
        for url_item in urls:
            converted = self.convert_url(url_item)
            if converted:
                converted_urls.append({
                    'original_url': url_item,
                    'converted': converted
                })
        
        analysis_result = {
            'ticket_id': ticket_id,
            'subject': subject,
            'description': description[:500] + '...' if len(description) > 500 else description,
            'created_at': created_at,
            'zendesk_url': url,
            'extracted_urls': urls,
            'converted_urls': converted_urls,
            'total_urls_found': len(urls),
            'total_converted': len(converted_urls),
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        return analysis_result

    def prepare_for_airtable(self, analysis_results: List[Dict]) -> List[Dict]:
        """Prepare analyzed data for Airtable upload with correct column mapping"""
        airtable_records = []
        
        for result in analysis_results:
            for converted_url in result['converted_urls']:
                # Create a record for each converted URL matching Airtable columns
                record = {
                    'fields': {
                        'item': converted_url['converted'],
                        'Date Received': result['created_at'],
                        'Zendesk': result['zendesk_url'],
                        'Status': 'Done',
                        'Notes': f"Ticket #{result['ticket_id']}: {result['subject']}\nOriginal URL: {converted_url['original_url']}"
                    }
                }
                airtable_records.append(record)
        
        return airtable_records

    def upload_to_airtable(self, airtable_records: List[Dict]) -> bool:
        """Upload records to Airtable (Stage 2)"""
        if not self.airtable_api_key:
            logging.warning("AIRTABLE_API_KEY not set - skipping upload")
            return False
        
        if not airtable_records:
            logging.info("No records to upload to Airtable")
            return True
        
        headers = {
            'Authorization': f'Bearer {self.airtable_api_key}',
            'Content-Type': 'application/json'
        }
        
        # Upload in batches of 10 (Airtable limit)
        batch_size = 10
        total_uploaded = 0
        
        for i in range(0, len(airtable_records), batch_size):
            batch = airtable_records[i:i + batch_size]
            
            try:
                payload = {'records': batch}
                response = requests.post(
                    self.airtable_base_url,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                
                batch_uploaded = len(batch)
                total_uploaded += batch_uploaded
                logging.info(f"Uploaded batch {i//batch_size + 1}: {batch_uploaded} records")
                
                # Rate limiting - wait between batches
                if i + batch_size < len(airtable_records):
                    time.sleep(0.2)  # 200ms delay between batches
                    
            except requests.RequestException as e:
                logging.error(f"Failed to upload batch {i//batch_size + 1}: {e}")
                return False
        
        logging.info(f"Successfully uploaded {total_uploaded} records to Airtable")
        logging.info(f"View results at: {self.airtable_web_url}")
        return True

    def save_analysis_to_file(self, analysis_results: List[Dict], filename: str = None):
        """Save analysis results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dmca_analysis_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(analysis_results, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Analysis results saved to {filename}")
        return filename

    def run_analysis(self) -> Tuple[List[Dict], List[Dict]]:
        """Run the complete DMCA analysis pipeline"""
        logging.info("Starting DMCA analysis pipeline...")
        
        # Fetch tickets
        tickets = self.fetch_dmca_tickets()
        if not tickets:
            logging.warning("No tickets found to analyze")
            return [], []
        
        # Analyze each ticket
        analysis_results = []
        for ticket in tickets:
            try:
                result = self.analyze_ticket(ticket)
                analysis_results.append(result)
                logging.info(f"Analyzed ticket {result['ticket_id']}: {result['total_converted']} URLs converted")
            except Exception as e:
                logging.error(f"Error analyzing ticket {ticket.get('id', 'unknown')}: {e}")
        
        # Prepare for Airtable
        airtable_records = self.prepare_for_airtable(analysis_results)
        
        # Upload to Airtable (Stage 2)
        self.upload_to_airtable(airtable_records)
        
        # Save results
        filename = self.save_analysis_to_file(analysis_results)
        
        # Print summary
        total_tickets = len(analysis_results)
        total_urls = sum(r['total_urls_found'] for r in analysis_results)
        total_converted = sum(r['total_converted'] for r in analysis_results)
        
        logging.info(f"""
        Analysis Complete!
        ================
        Tickets analyzed: {total_tickets}
        URLs found: {total_urls}
        URLs converted: {total_converted}
        Airtable records ready: {len(airtable_records)}
        Results saved to: {filename}
        """)
        
        return analysis_results, airtable_records

def main():
    """Main function to run the DMCA analyzer"""
    analyzer = DMCAAnalyzer()
    
    # Check for required environment variables
    if not analyzer.zendesk_auth[1]:
        logging.error("ZENDESK_PASSWORD environment variable not set")
        return
    
    try:
        analysis_results, airtable_records = analyzer.run_analysis()
        
        print("\n" + "="*50)
        print("DMCA ANALYSIS SUMMARY")
        print("="*50)
        
        if analysis_results:
            for result in analysis_results:
                print(f"\nTicket #{result['ticket_id']}")
                print(f"Subject: {result['subject']}")
                print(f"URLs found: {result['total_urls_found']}")
                print(f"URLs converted: {result['total_converted']}")
                
                if result['converted_urls']:
                    print("Converted URLs:")
                    for url_data in result['converted_urls']:
                        print(f"  • {url_data['converted']} (from {url_data['original_url'][:60]}...)")
            
            # Airtable integration summary
            print(f"\n🔗 AIRTABLE INTEGRATION")
            print("="*25)
            if analyzer.airtable_api_key:
                print(f"✅ Records uploaded to Airtable: {len(airtable_records)}")
                print(f"🌐 View results: {analyzer.airtable_web_url}")
            else:
                print("⚠️  AIRTABLE_API_KEY not set - records prepared but not uploaded")
                print(f"📊 Records ready for upload: {len(airtable_records)}")
                print("💡 Set AIRTABLE_API_KEY to enable automatic upload")
        else:
            print("No DMCA tickets found to analyze")
        
    except Exception as e:
        logging.error(f"Analysis failed: {e}")

if __name__ == "__main__":
    main() 