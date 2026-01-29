import sys
import os
import io

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend'))

from app.services.xfa_mapper import XFAMapper
from app.services.pdf_injector import PDFInjector
from app.models.patent_application import PatentApplicationMetadata, Inventor

def verify_injection():
    print("--- Verifying XFA Injection ---")
    
    # 1. Setup Data
    metadata = PatentApplicationMetadata(
        title="Automated XFA Injection System",
        application_number="12/345,678",
        filing_date="2024-01-29",
        entity_status="Small Entity",
        inventors=[
            Inventor(
                first_name="Test",
                last_name="User",
                street_address="100 Main St",
                city="San Jose",
                state="CA",
                zip_code="95112",
                country="US"
            ),
            Inventor(
                first_name="Second",
                last_name="Inventor",
                city="London",
                country="UK"
            )
        ]
    )
    
    # 2. Map to XML
    mapper = XFAMapper()
    xml_data = mapper.map_metadata_to_xml(metadata)
    print("XML Generated.")
    
    # 3. Inject into PDF
    injector = PDFInjector()
    
    # Path logic similar to endpoint
    template_path = os.path.join("..", "Client attachments", "Original ADS from USPTO Website.pdf")
    if not os.path.exists(template_path):
        print(f"Warning: Primary template not found at {template_path}")
        # Try local template if available or fail
        template_path = "backend/app/templates/pto_sb_14_template.pdf"
        
    if not os.path.exists(template_path):
        print(f"Error: No template found at {template_path}")
        return

    print(f"Using template: {template_path}")
    
    try:
        pdf_stream = injector.inject_xml(template_path, xml_data)
        print("PDF Injection Successful.")
        
        # 4. Save to Disk for Verification
        output_filename = "test_output_ads_v3.pdf"
        with open(output_filename, "wb") as f:
            f.write(pdf_stream.getvalue())
            
        print(f"Output saved to: {output_filename}")
        print("Please open this file in Adobe Reader to verify content.")
        
    except Exception as e:
        print(f"Injection Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_injection()