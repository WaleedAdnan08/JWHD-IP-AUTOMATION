from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject
from app.models.patent_application import PatentApplicationMetadata
import os
import logging
import io

logger = logging.getLogger(__name__)

class ADSGenerator:
    def __init__(self):
        self.template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "templates", 
            "pto_sb_14_template.pdf"
        )

    def generate_ads_pdf(self, data: PatentApplicationMetadata, output_path: str) -> str:
        """
        Generates a filled ADS PDF by populating the official PTO/SB/14 template.
        
        Args:
            data: The PatentApplicationMetadata object containing the data.
            output_path: The file path where the PDF should be saved.
            
        Returns:
            The path to the generated PDF.
        """
        logger.info(f"Generating ADS PDF at: {output_path} using template: {self.template_path}")
        
        if not os.path.exists(self.template_path):
            raise FileNotFoundError(f"ADS Template not found at: {self.template_path}")

        try:
            reader = PdfReader(self.template_path)
            writer = PdfWriter()
            writer.append(reader)
            
            # Map metadata to form fields
            # Field names must match those in the PDF template
            field_data = {
                'Title': data.title or "",
                'ApplicationNumber': data.application_number or "",
                'FilingDate': data.filing_date or "",
                'EntityStatus': data.entity_status or "",
            }
            
            # Map inventors (Limit to what fits in template for now, typically 2-4 on first page)
            # In a full implementation, we would duplicate pages for more inventors.
            if data.inventors:
                for idx, inv in enumerate(data.inventors):
                    # 1-based index for field names
                    i = idx + 1
                    
                    # Basic mapping
                    field_data[f'GivenName_{i}'] = inv.first_name or ""
                    field_data[f'FamilyName_{i}'] = inv.last_name or ""
                    field_data[f'City_{i}'] = inv.city or ""
                    field_data[f'State_{i}'] = inv.state or ""
                    field_data[f'Country_{i}'] = inv.country or ""
                    
                    # Address logic
                    full_address = inv.street_address or ""
                    if not full_address and inv.name:
                         # Fallback if we only have raw name/address strings
                         pass
                    field_data[f'Address_{i}'] = full_address

            # Update form fields
            # Depending on pypdf version, we might need to update fields on specific pages
            # or globally if supported. Standard way is per page.
            for page in writer.pages:
                writer.update_page_form_field_values(
                    page, field_data, auto_regenerate=False
                )
            
            # Write output
            with open(output_path, "wb") as output_stream:
                writer.write(output_stream)
                
            logger.info(f"Successfully filled ADS PDF.")
            return output_path

        except Exception as e:
            logger.error(f"Failed to fill ADS PDF: {e}")
            raise e

if __name__ == "__main__":
    # Setup path to run standalone
    import sys
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    sys.path.append(backend_dir)
    
    # Now we can import from app
    from app.models.patent_application import PatentApplicationMetadata, Inventor
    
    generator = ADSGenerator()
    
    dummy_data = PatentApplicationMetadata(
        title="System and Method for Automated Patent Processing",
        filing_date="2024-01-24",
        entity_status="Small Entity",
        application_number="18/123,456",
        inventors=[
            Inventor(
                first_name="Jane",
                middle_name="A.",
                last_name="Doe",
                street_address="123 Innovation Dr",
                city="Tech City",
                state="CA",
                zip_code="90210",
                country="US",
                citizenship="US"
            ),
            Inventor(
                first_name="John",
                last_name="Smith",
                city="New York",
                state="NY",
                country="US",
                street_address="456 Elm St"
            )
        ]
    )
    
    output = "filled_ads.pdf"
    print(f"Generating filled PDF at {output}...")
    try:
        generator.generate_ads_pdf(dummy_data, output)
        print("Successfully generated PDF.")
        print(f"File exists: {os.path.exists(output)}")
    except Exception as e:
        print(f"Error generating PDF: {e}")