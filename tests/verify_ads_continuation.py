import sys
import os
import logging
from datetime import datetime

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from app.services.ads_generator import ADSGenerator
from app.models.patent_application import PatentApplicationMetadata, Inventor

# Configure logging
logging.basicConfig(level=logging.INFO)

def verify_continuation_sheet():
    print("--- Verifying ADS Continuation Sheet Generation ---")
    
    # 1. Create Mock Data with 15 Inventors
    inventors = []
    for i in range(1, 16):
        inventors.append(Inventor(
            first_name=f"Inventor{i}",
            last_name=f"FamilyName{i}",
            street_address=f"{i}00 Innovation Way",
            city=f"City{i}",
            state="CA",
            country="US",
            citizenship="US",
            zip_code=f"9000{i}"
        ))
        
    metadata = PatentApplicationMetadata(
        title="High Volume Inventor System",
        application_number="18/999,999",
        filing_date="2024-02-01",
        entity_status="Small Entity",
        inventors=inventors
    )
    
    print(f"Created metadata with {len(inventors)} inventors.")
    
    # 2. Generate PDF
    generator = ADSGenerator()
    output_filename = "test_ads_continuation.pdf"
    
    try:
        pdf_path = generator.generate_ads_pdf(metadata, output_filename)
        print(f"✅ PDF generated successfully at: {pdf_path}")
        
        # 3. Validation
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        num_pages = len(reader.pages)
        print(f"Generated PDF has {num_pages} pages.")
        
        # Expectation: 
        # Page 1: Main form (4 inventors)
        # Page 2+: Continuation sheet (11 remaining inventors)
        # Assuming ~10 inventors fit on a continuation page, we expect roughly 2-3 pages total.
        
        if num_pages > 1:
            print("✅ SUCCESS: Continuation pages generated.")
        else:
            print("❌ FAILURE: Only 1 page generated (continuation missing).")
            
        # Check for content on page 2
        if num_pages >= 2:
            page2_text = reader.pages[1].extract_text()
            if "ADS CONTINUATION SHEET" in page2_text:
                print("✅ SUCCESS: Continuation Sheet Header found on Page 2.")
            else:
                print(f"❌ FAILURE: 'ADS CONTINUATION SHEET' header not found on Page 2. Content: {page2_text[:100]}...")
            
            # Check for Inventor 5 (first on continuation)
            if "5. Inventor5" in page2_text:
                 print("✅ SUCCESS: Inventor 5 found on continuation sheet.")
            else:
                 print("❌ FAILURE: Inventor 5 not found on continuation sheet.")

    except Exception as e:
        print(f"❌ ERROR: Generation failed: {e}")

if __name__ == "__main__":
    verify_continuation_sheet()