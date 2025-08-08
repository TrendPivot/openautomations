#!/usr/bin/env python3
"""
Airtable Integration Tester
Diagnoses issues with Airtable API integration for DMCA automation
"""

import os
import json
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv('config.env')

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class AirtableTestSuite:
    def __init__(self):
        # Configuration
        self.airtable_api_key = os.getenv("AIRTABLE_API_KEY", "")
        self.airtable_app_id = "appjPNekcQqLmNfu6"
        self.airtable_table_id = "tblo8hUjb3o9ppRBt"
        self.airtable_view_id = "viwyVw493gKptuXmE"
        self.airtable_base_url = f"https://api.airtable.com/v0/{self.airtable_app_id}/{self.airtable_table_id}"
        self.airtable_web_url = f"https://airtable.com/{self.airtable_app_id}/{self.airtable_table_id}/{self.airtable_view_id}?blocks=hide"
        
        # Headers for API requests
        self.headers = {
            'Authorization': f'Bearer {self.airtable_api_key}',
            'Content-Type': 'application/json'
        }
        
        print("="*60)
        print("🧪 AIRTABLE INTEGRATION TEST SUITE")
        print("="*60)
        print(f"App ID: {self.airtable_app_id}")
        print(f"Table ID: {self.airtable_table_id}")
        print(f"View ID: {self.airtable_view_id}")
        print(f"API URL: {self.airtable_base_url}")
        print(f"Web URL: {self.airtable_web_url}")
        print(f"API Key: {'***' + self.airtable_api_key[-4:] if self.airtable_api_key else 'NOT SET'}")
        print("="*60)

    def test_1_api_key_validation(self):
        """Test 1: Validate API key"""
        print("\n🔑 TEST 1: API Key Validation")
        print("-" * 40)
        
        if not self.airtable_api_key:
            print("❌ FAIL: AIRTABLE_API_KEY not set")
            return False
        
        if not self.airtable_api_key.startswith(('pat', 'key')):
            print("⚠️  WARNING: API key doesn't start with 'pat' or 'key' - might be invalid format")
            print(f"   Key starts with: {self.airtable_api_key[:10]}...")
        
        print(f"✅ API key present: {len(self.airtable_api_key)} characters")
        return True

    def test_2_table_access(self):
        """Test 2: Test table access (GET request)"""
        print("\n📋 TEST 2: Table Access")
        print("-" * 40)
        
        try:
            # Try to fetch records from the table
            response = requests.get(
                self.airtable_base_url,
                headers=self.headers,
                params={"maxRecords": 3},  # Just get a few records
                timeout=30
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                records = data.get('records', [])
                print(f"✅ SUCCESS: Retrieved {len(records)} records")
                
                # Show table structure
                if records:
                    print("\n📊 Table Structure (first record fields):")
                    first_record = records[0]
                    fields = first_record.get('fields', {})
                    for field_name, field_value in fields.items():
                        print(f"   • {field_name}: {type(field_value).__name__}")
                
                return True
            else:
                print(f"❌ FAIL: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except requests.RequestException as e:
            print(f"❌ FAIL: Network error - {e}")
            return False

    def test_3_create_test_record(self):
        """Test 3: Create a test record"""
        print("\n📝 TEST 3: Create Test Record")
        print("-" * 40)
        
        # Create a test record similar to DMCA format
        test_record = {
            'records': [{
                'fields': {
                    'item': 'TEST-0x1234567890abcdef:999',
                    'Date Received': datetime.now().strftime('%Y-%m-%d'),  # Date only format
                    'Zendesk': f'https://rariblecom.zendesk.com/agent/tickets/TEST-{datetime.now().strftime("%H%M%S")}',
                    'Status': 'Done',
                    'Notes': f'Test record created by Airtable test suite at {datetime.now()}'
                }
            }]
        }
        
        try:
            response = requests.post(
                self.airtable_base_url,
                headers=self.headers,
                json=test_record,
                timeout=30
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Request Payload: {json.dumps(test_record, indent=2)}")
            
            if response.status_code == 200:
                data = response.json()
                created_records = data.get('records', [])
                if created_records:
                    record_id = created_records[0].get('id')
                    print(f"✅ SUCCESS: Created test record with ID: {record_id}")
                    return record_id
                else:
                    print("❌ FAIL: No records returned in response")
                    return None
            else:
                print(f"❌ FAIL: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except requests.RequestException as e:
            print(f"❌ FAIL: Network error - {e}")
            return None

    def test_4_verify_record_exists(self, record_id):
        """Test 4: Verify the test record exists"""
        print("\n🔍 TEST 4: Verify Record Exists")
        print("-" * 40)
        
        if not record_id:
            print("❌ SKIP: No record ID to verify")
            return False
        
        try:
            # Get the specific record
            response = requests.get(
                f"{self.airtable_base_url}/{record_id}",
                headers=self.headers,
                timeout=30
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                fields = data.get('fields', {})
                print(f"✅ SUCCESS: Record exists")
                print(f"Record fields: {json.dumps(fields, indent=2)}")
                return True
            else:
                print(f"❌ FAIL: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except requests.RequestException as e:
            print(f"❌ FAIL: Network error - {e}")
            return False

    def test_5_check_field_names(self):
        """Test 5: Check if expected field names exist"""
        print("\n🏷️  TEST 5: Field Name Validation")
        print("-" * 40)
        
        expected_fields = ['item', 'Date Received', 'Zendesk', 'Status', 'Notes']
        
        try:
            # Get table schema/records to check field names
            response = requests.get(
                self.airtable_base_url,
                headers=self.headers,
                params={"maxRecords": 1},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                records = data.get('records', [])
                
                if records:
                    available_fields = list(records[0].get('fields', {}).keys())
                    print(f"Available fields in table: {available_fields}")
                    
                    missing_fields = []
                    for field in expected_fields:
                        if field in available_fields:
                            print(f"   ✅ {field}")
                        else:
                            print(f"   ❌ {field} (MISSING)")
                            missing_fields.append(field)
                    
                    if missing_fields:
                        print(f"\n⚠️  WARNING: Missing expected fields: {missing_fields}")
                        print("This could cause upload issues!")
                        return False
                    else:
                        print("✅ All expected fields are present")
                        return True
                else:
                    print("⚠️  Table is empty, cannot verify field names")
                    return True  # Not a failure, just unknown
            else:
                print(f"❌ FAIL: Could not retrieve table structure: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            print(f"❌ FAIL: Network error - {e}")
            return False

    def test_6_cleanup_test_record(self, record_id):
        """Test 6: Clean up test record"""
        print("\n🧹 TEST 6: Cleanup Test Record")
        print("-" * 40)
        
        if not record_id:
            print("❌ SKIP: No record ID to clean up")
            return True
        
        try:
            response = requests.delete(
                f"{self.airtable_base_url}/{record_id}",
                headers=self.headers,
                timeout=30
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✅ SUCCESS: Test record deleted")
                return True
            else:
                print(f"⚠️  WARNING: Could not delete test record: {response.status_code}")
                print(f"You may need to manually delete record {record_id}")
                return False
                
        except requests.RequestException as e:
            print(f"⚠️  WARNING: Error deleting test record - {e}")
            return False

    def run_full_test_suite(self):
        """Run all tests"""
        print("\n🚀 Starting Full Test Suite...\n")
        
        results = {}
        
        # Test 1: API Key
        results['api_key'] = self.test_1_api_key_validation()
        if not results['api_key']:
            print("\n❌ CRITICAL: Cannot proceed without valid API key")
            return self.print_summary(results)
        
        # Test 2: Table Access
        results['table_access'] = self.test_2_table_access()
        if not results['table_access']:
            print("\n❌ CRITICAL: Cannot access table")
            return self.print_summary(results)
        
        # Test 3: Create Record
        test_record_id = self.test_3_create_test_record()
        results['create_record'] = bool(test_record_id)
        
        # Test 4: Verify Record
        if test_record_id:
            results['verify_record'] = self.test_4_verify_record_exists(test_record_id)
        else:
            results['verify_record'] = False
        
        # Test 5: Field Names
        results['field_names'] = self.test_5_check_field_names()
        
        # Test 6: Cleanup
        results['cleanup'] = self.test_6_cleanup_test_record(test_record_id)
        
        return self.print_summary(results)

    def print_summary(self, results):
        """Print test summary"""
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        total_tests = len(results)
        passed_tests = sum(1 for result in results.values() if result)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
        
        print(f"\nResult: {passed_tests}/{total_tests} tests passed")
        
        # Provide diagnostics
        print("\n🔍 DIAGNOSIS:")
        if not results.get('api_key'):
            print("• Set valid AIRTABLE_API_KEY environment variable")
        elif not results.get('table_access'):
            print("• Check API key permissions and app/table IDs")
            print("• Verify table exists and is accessible")
        elif not results.get('create_record'):
            print("• API key may be read-only (needs write permissions)")
            print("• Table structure might not match expected format")
        elif not results.get('field_names'):
            print("• Table field names don't match expected DMCA format")
            print("• Records may be going to wrong fields")
        else:
            print("• All tests passed! Airtable integration should work")
            print("• If DMCA script still fails, check the record creation logic")
        
        print(f"\n🌐 Manual Check: {self.airtable_web_url}")
        print("="*60)
        
        return passed_tests == total_tests

def main():
    """Main function"""
    tester = AirtableTestSuite()
    success = tester.run_full_test_suite()
    
    if success:
        print("\n🎉 All tests passed! Airtable integration is working.")
    else:
        print("\n🚨 Some tests failed. Check the diagnosis above.")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main()) 
