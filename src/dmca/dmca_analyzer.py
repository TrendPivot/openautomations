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

# Optional PostgreSQL support
try:
    import psycopg2
    import psycopg2.extras
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    logging.warning("psycopg2 not available - PostgreSQL tracking disabled. Install with: pip install psycopg2-binary")

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
        
        # PostgreSQL connection parameters from environment variables
        self.db_params = {
            "dbname": os.getenv("PG_DATABASE"),
            "user": os.getenv("PG_USER"),
            "password": os.getenv("PG_PASSWORD"),
            "host": os.getenv("PG_HOST"),
            "port": os.getenv("PG_PORT")
        }
        
        # Initialize database connection
        self.db_connection = None
        self._init_database()
        
        # URL extraction regex
        self.url_regex = re.compile(
            r'((?:https?://)?(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*[-a-zA-Z0-9@:%_\+~#?&//=]))',
            re.IGNORECASE
        )

    def _init_database(self):
        """Initialize PostgreSQL connection and create table if it doesn't exist"""
        if not POSTGRES_AVAILABLE:
            logging.warning("PostgreSQL tracking disabled - psycopg2 module not available")
            return
            
        try:
            # Check if all required DB parameters are set
            missing_params = [key for key, value in self.db_params.items() if not value]
            if missing_params:
                logging.warning(f"Missing PostgreSQL parameters: {missing_params}. Database tracking disabled.")
                return
            
            # Establish connection
            self.db_connection = psycopg2.connect(**self.db_params)
            self.db_connection.autocommit = True
            
            # Create schema and table if they don't exist
            with self.db_connection.cursor() as cursor:
                # Create schema
                cursor.execute("CREATE SCHEMA IF NOT EXISTS zendesk;")
                
                # Create table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS zendesk.dmca_automation (
                        id SERIAL PRIMARY KEY,
                        ticket_id BIGINT UNIQUE NOT NULL,
                        ticket_url TEXT,
                        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        urls_found INTEGER DEFAULT 0,
                        urls_converted INTEGER DEFAULT 0,
                        airtable_records INTEGER DEFAULT 0,
                        status VARCHAR(50) DEFAULT 'processed',
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Create index on ticket_id for faster lookups
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_dmca_automation_ticket_id 
                    ON zendesk.dmca_automation (ticket_id);
                """)
                
                # Add ticket_url column if it doesn't exist (migration for existing tables)
                cursor.execute("""
                    DO $$ 
                    BEGIN 
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_schema = 'zendesk' 
                            AND table_name = 'dmca_automation' 
                            AND column_name = 'ticket_url'
                        ) THEN 
                            ALTER TABLE zendesk.dmca_automation ADD COLUMN ticket_url TEXT;
                        END IF; 
                    END $$;
                """)
                
            logging.info("PostgreSQL database initialized successfully")
            
        except psycopg2.Error as e:
            logging.error(f"Failed to initialize PostgreSQL connection: {e}")
            self.db_connection = None
        except Exception as e:
            logging.error(f"Unexpected error initializing database: {e}")
            self.db_connection = None

    def _is_ticket_processed(self, ticket_id: int) -> bool:
        """Check if a ticket has already been processed"""
        if not POSTGRES_AVAILABLE or not self.db_connection:
            return False
        
        try:
            with self.db_connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM zendesk.dmca_automation WHERE ticket_id = %s",
                    (ticket_id,)
                )
                return cursor.fetchone() is not None
        except psycopg2.Error as e:
            logging.error(f"Error checking if ticket {ticket_id} is processed: {e}")
            return False

    def _mark_ticket_processed(self, ticket_id: int, urls_found: int, urls_converted: int, 
                              airtable_records: int, ticket_url: str = None, notes: str = None):
        """Mark a ticket as processed in the database"""
        if not POSTGRES_AVAILABLE or not self.db_connection:
            return
        
        try:
            with self.db_connection.cursor() as cursor:
                # Ensure ticket_id is stored as integer without formatting
                ticket_id_int = int(ticket_id) if ticket_id else None
                
                cursor.execute("""
                    INSERT INTO zendesk.dmca_automation 
                    (ticket_id, ticket_url, urls_found, urls_converted, airtable_records, notes)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (ticket_id) DO UPDATE SET
                        processed_at = CURRENT_TIMESTAMP,
                        ticket_url = EXCLUDED.ticket_url,
                        urls_found = EXCLUDED.urls_found,
                        urls_converted = EXCLUDED.urls_converted,
                        airtable_records = EXCLUDED.airtable_records,
                        notes = EXCLUDED.notes
                """, (ticket_id_int, ticket_url, urls_found, urls_converted, airtable_records, notes))
                
            logging.info(f"Marked ticket {ticket_id_int} as processed in database")
            
        except psycopg2.Error as e:
            logging.error(f"Error marking ticket {ticket_id} as processed: {e}")
        except (ValueError, TypeError) as e:
            logging.error(f"Invalid ticket_id format {ticket_id}: {e}")

    def _get_processed_tickets_summary(self) -> Dict:
        """Get summary of processed tickets from database"""
        if not POSTGRES_AVAILABLE or not self.db_connection:
            return {"total_processed": 0, "database_available": False}
        
        try:
            with self.db_connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_processed,
                        SUM(urls_found) as total_urls_found,
                        SUM(urls_converted) as total_urls_converted,
                        SUM(airtable_records) as total_airtable_records,
                        MAX(processed_at) as last_processed
                    FROM zendesk.dmca_automation
                """)
                result = cursor.fetchone()
                return {
                    "total_processed": result['total_processed'] or 0,
                    "total_urls_found": result['total_urls_found'] or 0,
                    "total_urls_converted": result['total_urls_converted'] or 0,
                    "total_airtable_records": result['total_airtable_records'] or 0,
                    "last_processed": result['last_processed'],
                    "database_available": True
                }
        except psycopg2.Error as e:
            logging.error(f"Error getting processed tickets summary: {e}")
            return {"total_processed": 0, "database_available": False}

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
        
        # Generate agent URL instead of using API URL
        agent_url = f"https://rariblecom.zendesk.com/agent/tickets/{ticket_id}" if ticket_id else ""
        
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
            'zendesk_url': agent_url,
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
                # Convert Zendesk datetime to date-only format for Airtable
                zendesk_date = result['created_at']
                if zendesk_date:
                    try:
                        # Parse ISO datetime and extract date only
                        from datetime import datetime
                        dt = datetime.fromisoformat(zendesk_date.replace('Z', '+00:00'))
                        airtable_date = dt.strftime('%Y-%m-%d')
                    except:
                        # Fallback to original if parsing fails
                        airtable_date = zendesk_date[:10]  # Take first 10 chars (YYYY-MM-DD)
                else:
                    airtable_date = ''
                
                # Create a record for each converted URL matching Airtable columns
                record = {
                    'fields': {
                        'item': converted_url['converted'],
                        'Date Received': airtable_date,
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

    def run_analysis(self) -> Tuple[List[Dict], List[Dict], bool]:
        """Run the complete DMCA analysis pipeline"""
        logging.info("Starting DMCA analysis pipeline...")
        
        # Get database summary before processing
        db_summary = self._get_processed_tickets_summary()
        if db_summary["database_available"]:
            logging.info(f"Database tracking active - {db_summary['total_processed']} tickets previously processed")
        else:
            logging.warning("Database tracking unavailable - duplicate processing may occur")
        
        # Fetch tickets
        tickets = self.fetch_dmca_tickets()
        if not tickets:
            logging.warning("No tickets found to analyze")
            return [], [], False
        
        # Filter out already processed tickets
        new_tickets = []
        skipped_count = 0
        
        for ticket in tickets:
            ticket_id = ticket.get('id')
            if ticket_id and self._is_ticket_processed(ticket_id):
                skipped_count += 1
                logging.info(f"Skipping already processed ticket {ticket_id}")
                continue
            new_tickets.append(ticket)
        
        logging.info(f"Found {len(tickets)} total tickets, {skipped_count} already processed, {len(new_tickets)} new to process")
        
        if not new_tickets:
            logging.info("No new tickets to process")
            return [], [], True
        
        # Analyze each new ticket
        analysis_results = []
        automation_notes_added = 0
        
        for ticket in new_tickets:
            ticket_id = ticket.get('id')
            try:
                result = self.analyze_ticket(ticket)
                analysis_results.append(result)
                logging.info(f"Analyzed ticket {result['ticket_id']}: {result['total_converted']} URLs converted")
                
                # Mark ticket as processed in database
                notes = f"Subject: {result['subject'][:100]}..." if len(result['subject']) > 100 else result['subject']
                
                # Generate agent URL instead of using API URL
                agent_url = f"https://rariblecom.zendesk.com/agent/tickets/{ticket_id}"
                
                self._mark_ticket_processed(
                    ticket_id,
                    result['total_urls_found'],
                    result['total_converted'],
                    result['total_converted'],  # Each converted URL becomes an Airtable record
                    agent_url,  # Use agent URL format
                    notes
                )
                
                # Add internal note to ticket after successful processing
                automation_note = "🤖OpenAutomations: DMCA request is processed"
                note_success = self.add_internal_note(ticket_id, automation_note)
                if note_success:
                    automation_notes_added += 1
                    logging.info(f"Added automation note to ticket {ticket_id}")
                else:
                    logging.warning(f"Failed to add automation note to ticket {ticket_id}")
                
            except Exception as e:
                logging.error(f"Error analyzing ticket {ticket_id}: {e}")
                # Mark as processed with error status
                if ticket_id:
                    # Generate agent URL for error cases too
                    agent_url = f"https://rariblecom.zendesk.com/agent/tickets/{ticket_id}"
                    self._mark_ticket_processed(ticket_id, 0, 0, 0, agent_url, f"Error: {str(e)[:200]}")
                    # Note: Don't add automation note for failed tickets
        
        # Prepare for Airtable
        airtable_records = self.prepare_for_airtable(analysis_results)
        
        # Upload to Airtable (Stage 2)
        upload_success = self.upload_to_airtable(airtable_records)
        
        # Save results to JSON file - REMOVED: Using Postgres-only tracking
        # filename = self.save_analysis_to_file(analysis_results)
        
        # Print summary
        total_tickets = len(analysis_results)
        total_urls = sum(r['total_urls_found'] for r in analysis_results)
        total_converted = sum(r['total_converted'] for r in analysis_results)
        
        logging.info(f"""
        Analysis Complete!
        ================
        New tickets analyzed: {total_tickets}
        Tickets skipped (already processed): {skipped_count}
        URLs found: {total_urls}
        URLs converted: {total_converted}
        Airtable records ready: {len(airtable_records)}
        Automation notes added: {automation_notes_added}
        Database tracking: {'Active' if db_summary['database_available'] else 'Disabled'}
        """)
        
        return analysis_results, airtable_records, upload_success

    def close_database_connection(self):
        """Close the database connection"""
        if POSTGRES_AVAILABLE and self.db_connection:
            try:
                self.db_connection.close()
                logging.info("Database connection closed")
            except Exception as e:
                logging.error(f"Error closing database connection: {e}")

    def add_internal_note(self, ticket_id: int, note_text: str) -> bool:
        """Add an internal note to a specific Zendesk ticket"""
        try:
            # Zendesk API endpoint for adding comments
            url = f"https://rariblecom.zendesk.com/api/v2/tickets/{ticket_id}.json"
            
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
            
            logging.info(f"Adding internal note to ticket {ticket_id}: {note_text}")
            
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
                logging.error(f"❌ Failed to add note to ticket {ticket_id}. Status: {response.status_code}")
                logging.error(f"Response: {response.text}")
                return False
                
        except requests.RequestException as e:
            logging.error(f"❌ Request failed when adding note to ticket {ticket_id}: {e}")
            return False
        except Exception as e:
            logging.error(f"❌ Unexpected error adding note to ticket {ticket_id}: {e}")
            return False

def main():
    """Main function to run the DMCA analyzer"""
    analyzer = DMCAAnalyzer()
    
    # Check for required environment variables
    if not analyzer.zendesk_auth[1]:
        logging.error("ZENDESK_PASSWORD environment variable not set")
        return
    
    try:
        # Get initial database summary
        db_summary = analyzer._get_processed_tickets_summary()
        
        analysis_results, airtable_records, upload_success = analyzer.run_analysis()
        
        print("\n" + "="*50)
        print("DMCA ANALYSIS SUMMARY")
        print("="*50)
        
        # Database tracking summary
        if db_summary["database_available"]:
            updated_summary = analyzer._get_processed_tickets_summary()
            print(f"\n📊 DATABASE TRACKING")
            print("="*20)
            print(f"Total tickets ever processed: {updated_summary['total_processed']}")
            print(f"Total URLs found: {updated_summary['total_urls_found']}")
            print(f"Total URLs converted: {updated_summary['total_urls_converted']}")
            print(f"Total Airtable records: {updated_summary['total_airtable_records']}")
            if updated_summary['last_processed']:
                print(f"Last processed: {updated_summary['last_processed']}")
        else:
            print(f"\n⚠️  DATABASE TRACKING")
            print("="*20)
            if not POSTGRES_AVAILABLE:
                print("PostgreSQL tracking disabled - psycopg2 module not available")
                print("Install with: pip install psycopg2-binary")
                print("⚠️  WARNING: All tickets will be processed every run (no duplicate prevention)")
            else:
                print("PostgreSQL tracking disabled - missing environment variables:")
                missing = [k for k, v in analyzer.db_params.items() if not v]
                for param in missing:
                    print(f"  • {param.upper()}")
                print("Set these variables to enable duplicate prevention.")
                print("⚠️  WARNING: All tickets will be processed every run (no duplicate prevention)")
        
        if analysis_results:
            print(f"\n🎯 THIS RUN RESULTS")
            print("="*20)
            
            # Get automation notes count from the analysis
            total_notes_attempted = len(analysis_results)
            
            for result in analysis_results:
                print(f"\nTicket #{result['ticket_id']}")
                print(f"Subject: {result['subject']}")
                print(f"URLs found: {result['total_urls_found']}")
                print(f"URLs converted: {result['total_converted']}")
                
                if result['converted_urls']:
                    print("Converted URLs:")
                    for url_data in result['converted_urls']:
                        print(f"  • {url_data['converted']} (from {url_data['original_url'][:60]}...)")
            
            print(f"\n🤖 AUTOMATION NOTES")
            print("="*20)
            print(f"Notes attempted: {total_notes_attempted}")
            print(f'Note text: "🤖OpenAutomations: DMCA request is processed"')
            print("Check individual ticket logs for note success/failure details")
            
            # Airtable integration summary
            print(f"\n🔗 AIRTABLE INTEGRATION")
            print("="*25)
            if analyzer.airtable_api_key:
                if upload_success:
                    print(f"✅ Records uploaded to Airtable: {len(airtable_records)}")
                    print(f"🌐 View results: {analyzer.airtable_web_url}")
                else:
                    print(f"❌ Upload failed - check API key and permissions")
                    print(f"📊 Records prepared but not uploaded: {len(airtable_records)}")
                    print("🔧 Run 'python3 test_airtable.py' to diagnose the issue")
            else:
                print("⚠️  AIRTABLE_API_KEY not set - records prepared but not uploaded")
                print(f"📊 Records ready for upload: {len(airtable_records)}")
                print("💡 Set AIRTABLE_API_KEY to enable automatic upload")
        else:
            print("\n✅ No new DMCA tickets found to analyze")
            print("All current open tickets have already been processed.")
        
    except Exception as e:
        logging.error(f"Analysis failed: {e}")
    finally:
        # Ensure database connection is properly closed
        analyzer.close_database_connection()

if __name__ == "__main__":
    main() 
