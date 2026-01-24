import requests
import json
import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
TEST_PDF_PATH = "tests/test_patent.pdf"

def create_test_pdf(filename):
    """Creates a dummy patent application PDF for testing."""
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, height - 100, "Title of Invention: Automated IP Management System")
    
    # Application Number & Filing Date
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 130, "Application Number: 12/345,678")
    c.drawString(100, height - 150, "Filing Date: 2023-10-15")
    c.drawString(100, height - 170, "Entity Status: Small Entity")
    
    # Inventors
    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, height - 210, "Inventors:")
    
    c.setFont("Helvetica", 12)
    # Inventor 1
    c.drawString(120, height - 230, "Inventor: John Doe")
    c.drawString(120, height - 245, "Address: 123 Innovation Way, San Francisco, CA, US")
    c.drawString(120, height - 260, "Citizenship: US")
    
    # Inventor 2
    c.drawString(120, height - 290, "Inventor: Jane Smith")
    c.drawString(120, height - 305, "Address: 456 Tech Blvd, Austin, TX, US")
    c.drawString(120, height - 320, "Citizenship: US")
    
    c.save()
    print(f"Created test PDF at {filename}")

def test_analyze_endpoint():
    print("\n--- Testing /applications/analyze ---")
    
    if not os.path.exists(TEST_PDF_PATH):
        create_test_pdf(TEST_PDF_PATH)
        
    try:
        with open(TEST_PDF_PATH, 'rb') as f:
            files = {'file': ('test_patent.pdf', f, 'application/pdf')}
            response = requests.post(f"{BASE_URL}/applications/analyze", files=files)
            
        if response.status_code == 200:
            print("SUCCESS: Extraction request successful.")
            data = response.json()
            print(f"Extracted Metadata:\n{json.dumps(data, indent=2)}")
            
            # Simple assertions
            # Note: LLM extraction might vary slightly, so we check for containment or non-empty
            if "Automated IP Management System" in data.get("title", ""):
                print("Assertion PASSED: Title matches.")
            else:
                print(f"Assertion WARNING: Title mismatch. Expected 'Automated IP Management System', got '{data.get('title')}'")
                
            inventors = data.get("inventors", [])
            if len(inventors) >= 2:
                print(f"Assertion PASSED: Found {len(inventors)} inventors (Expected >= 2).")
            else:
                print(f"Assertion FAILED: Found {len(inventors)} inventors (Expected >= 2).")
                
            return data
        else:
            print(f"FAILURE: Status Code {response.status_code}")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"ERROR: {e}")
        return None

def test_generate_ads_endpoint(metadata):
    print("\n--- Testing /applications/generate-ads ---")
    
    if not metadata:
        print("Skipping ADS generation due to missing metadata.")
        return

    try:
        response = requests.post(f"{BASE_URL}/applications/generate-ads", json=metadata)
        
        if response.status_code == 200:
            print("SUCCESS: ADS Generation request successful.")
            result = response.json()
            print(f"Response:\n{json.dumps(result, indent=2)}")
            
            if "download_url" in result and result["download_url"]:
                print("Assertion PASSED: Download URL returned.")
            else:
                print("Assertion FAILED: No download URL in response.")
        else:
            print(f"FAILURE: Status Code {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    # Ensure backend is running before running this test
    print("Starting E2E Verification...")
    
    # 1. Create PDF
    create_test_pdf(TEST_PDF_PATH)
    
    # 2. Extract
    extracted_data = test_analyze_endpoint()
    
    # 3. Generate ADS
    if extracted_data:
        test_generate_ads_endpoint(extracted_data)
        
    print("\nE2E Verification Finished.")