import sys
import os
import requests
import json

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend'))

from app.models.patent_application import PatentApplicationMetadata, Inventor

def test_api_endpoint():
    """
    Test the full API endpoint for XFA PDF generation
    """
    print("=== Testing API Endpoint ===")
    
    # Create test data
    test_data = {
        "title": "AI-Powered Patent System",
        "application_number": "18/123,456",
        "filing_date": "2024-01-29",
        "entity_status": "Small Entity",
        "inventors": [
            {
                "first_name": "John",
                "middle_name": "A",
                "last_name": "Doe",
                "street_address": "123 Main St",
                "city": "San Francisco",
                "state": "CA",
                "zip_code": "94105",
                "country": "US",
                "citizenship": "US"
            },
            {
                "first_name": "Jane",
                "last_name": "Smith",
                "street_address": "456 Oak Ave",
                "city": "New York",
                "state": "NY",
                "zip_code": "10001",
                "country": "US",
                "citizenship": "US"
            }
        ]
    }
    
    # Test API endpoint
    api_url = "http://localhost:8000/api/v1/applications/generate-ads"
    
    try:
        print(f"Making request to: {api_url}")
        response = requests.post(
            api_url,
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            # Save the PDF
            output_filename = "test_api_output.pdf"
            with open(output_filename, "wb") as f:
                f.write(response.content)
            
            print(f"✅ SUCCESS: PDF saved as {output_filename}")
            print(f"File size: {len(response.content)} bytes")
            
            # Verify it's a PDF
            if response.content.startswith(b'%PDF'):
                print("✅ Valid PDF format detected")
            else:
                print("❌ Invalid PDF format")
                
        else:
            print(f"❌ API Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Error text: {response.text}")
                
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Make sure the backend server is running on localhost:8000")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def test_local_components():
    """
    Test the local components (mapper + injector) directly
    """
    print("\n=== Testing Local Components ===")
    
    try:
        from app.services.xfa_mapper import XFAMapper
        from app.services.pdf_injector import PDFInjector
        
        # Create test metadata
        metadata = PatentApplicationMetadata(
            title="Local Test Application",
            application_number="17/999,888",
            filing_date="2024-01-29",
            entity_status="Small Entity",
            inventors=[
                Inventor(
                    first_name="Alice",
                    last_name="Johnson",
                    street_address="789 Tech Blvd",
                    city="Austin",
                    state="TX",
                    zip_code="73301",
                    country="US"
                )
            ]
        )
        
        # Test mapper
        mapper = XFAMapper()
        xml_data = mapper.map_metadata_to_xml(metadata)
        print("✅ XML mapping successful")
        print(f"XML length: {len(xml_data)} characters")
        
        # Test injector
        injector = PDFInjector()
        template_path = os.path.join("backend", "app", "templates", "xfa_ads_template.pdf")
        
        if not os.path.exists(template_path):
            template_path = os.path.join("..", "Client attachments", "Original ADS from USPTO Website.pdf")
            
        if os.path.exists(template_path):
            pdf_stream = injector.inject_xml(template_path, xml_data)
            
            # Save output
            output_filename = "test_local_output.pdf"
            with open(output_filename, "wb") as f:
                f.write(pdf_stream.getvalue())
                
            print(f"✅ PDF injection successful: {output_filename}")
            print(f"File size: {pdf_stream.getvalue().__len__()} bytes")
        else:
            print(f"❌ Template not found at: {template_path}")
            
    except Exception as e:
        print(f"❌ Local test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("XFA PDF Generation End-to-End Test")
    print("=" * 50)
    
    # Test local components first
    test_local_components()
    
    # Test API endpoint
    test_api_endpoint()
    
    print("\n" + "=" * 50)
    print("Test completed. Check the generated PDF files:")
    print("- test_local_output.pdf (local components)")
    print("- test_api_output.pdf (API endpoint)")