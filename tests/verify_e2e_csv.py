import requests
import io
import csv

BASE_URL = "http://localhost:8000/api/v1/applications"

def test_csv_flow():
    print("=== Starting CSV Flow Verification ===")

    # 1. Create dummy CSV content
    csv_content = """First Name,Last Name,Address,City,State,Zip,Country,Citizenship
Test,Inventor,123 Fake St,Anytown,CA,90210,USA,USA
Another,Person,456 Real Rd,Otherplace,NY,10001,USA,Canada
"""
    print("1. Created dummy CSV content.")

    # 2. Upload CSV to /parse-csv
    print("\n2. Uploading CSV to /parse-csv...")
    files = {
        'file': ('inventors.csv', csv_content, 'text/csv')
    }
    
    try:
        response = requests.post(f"{BASE_URL}/parse-csv", files=files)
        response.raise_for_status()
        inventors = response.json()
        print(f"   Success! Parsed {len(inventors)} inventors.")
        
        # Verify first inventor
        inv1 = inventors[0]
        if (inv1.get('first_name') == 'Test' and 
            inv1.get('last_name') == 'Inventor' and
            inv1.get('city') == 'Anytown'):
            print("   Verification Passed: First inventor data matches.")
        else:
            print(f"   Verification Failed: Data mismatch. Got: {inv1}")
            return

    except Exception as e:
        print(f"   Failed to parse CSV: {e}")
        if 'response' in locals():
            print(f"   Response body: {response.text}")
        return

    # 3. Construct Metadata Object
    print("\n3. Constructing PatentApplicationMetadata...")
    # The API expects the structure defined in PatentApplicationMetadata
    # We'll use the parsed inventors.
    metadata = {
        "title": "Method and System for Automated CSV Verification",
        "inventors": inventors,
        "applicants": [], # Optional, but good to have empty list if allowed
        "correspondence_address": {
            "name": "Test Firm LLP",
            "street_address": "789 Legal Blvd",
            "city": "Lawyer Town",
            "state": "TX",
            "postal_code": "75001",
            "country": "USA"
        }
    }
    print(f"   Metadata prepared with title: {metadata['title']}")

    # 4. Generate ADS
    print("\n4. Requesting ADS Generation (/generate-ads)...")
    try:
        response = requests.post(f"{BASE_URL}/generate-ads", json=metadata)
        response.raise_for_status()
        result = response.json()
        
        file_id = result.get('file_id')
        download_url = result.get('download_url')
        
        if file_id and download_url:
            print("   Success! ADS Generated.")
            print(f"   File ID: {file_id}")
            print(f"   Download URL: {download_url}")
        else:
            print("   Failed: Response missing file_id or download_url")
            print(f"   Response: {result}")
            
    except Exception as e:
        print(f"   Failed to generate ADS: {e}")
        if 'response' in locals():
            print(f"   Response body: {response.text}")

    print("\n=== CSV Flow Verification Complete ===")

if __name__ == "__main__":
    test_csv_flow()