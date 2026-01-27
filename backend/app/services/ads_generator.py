from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject
from app.models.patent_application import PatentApplicationMetadata, Inventor
import os
import logging
import io
from reportlab.lib import pagesizes
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

class ADSGenerator:
    def __init__(self):
        self.template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "templates",
            "pto_sb_14_template.pdf"
        )
        self.MAX_INVENTORS_ON_MAIN_FORM = 4

    def _generate_continuation_sheet(self, inventors: list[Inventor], start_index: int) -> io.BytesIO:
        """
        Generates a continuation sheet PDF for extra inventors using ReportLab.
        """
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=pagesizes.letter)
        width, height = pagesizes.letter
        
        y_position = height - 50
        can.setFont("Helvetica-Bold", 14)
        can.drawString(50, y_position, "ADS CONTINUATION SHEET - ADDITIONAL INVENTORS")
        y_position -= 30
        
        can.setFont("Helvetica", 10)
        
        for i, inv in enumerate(inventors):
            # Check for page break
            if y_position < 50:
                can.showPage()
                y_position = height - 50
                can.setFont("Helvetica-Bold", 14)
                can.drawString(50, y_position, "ADS CONTINUATION SHEET (Cont.)")
                y_position -= 30
                can.setFont("Helvetica", 10)

            idx = start_index + i + 1
            
            # Name Block
            can.setFont("Helvetica-Bold", 11)
            name_str = f"{idx}. {inv.first_name or ''} {inv.middle_name or ''} {inv.last_name or ''}".strip()
            if not name_str.strip(f"{idx}. "):
                name_str = f"{idx}. {inv.name or 'Unknown Name'}"
            can.drawString(50, y_position, name_str)
            y_position -= 15
            
            # Details Block
            can.setFont("Helvetica", 10)
            address_line = f"Address: {inv.street_address or ''}, {inv.city or ''}, {inv.state or ''} {inv.zip_code or ''}"
            can.drawString(70, y_position, address_line)
            y_position -= 15
            
            country_line = f"Country: {inv.country or ''} | Citizenship: {inv.citizenship or ''}"
            can.drawString(70, y_position, country_line)
            y_position -= 25 # Gap between inventors

        can.save()
        packet.seek(0)
        return packet

    def generate_ads_pdf(self, data: PatentApplicationMetadata, output_path: str) -> str:
        """
        Generates a filled ADS PDF by populating the official PTO/SB/14 template.
        If inventors > 4, generates and appends a continuation sheet.
        """
        logger.info(f"Generating ADS PDF at: {output_path} using template: {self.template_path}")
        
        if not os.path.exists(self.template_path):
            raise FileNotFoundError(f"ADS Template not found at: {self.template_path}")

        try:
            reader = PdfReader(self.template_path)
            writer = PdfWriter()
            writer.append(reader)
            
            # Map metadata to form fields
            field_data = {
                'Title': data.title or "",
                'ApplicationNumber': data.application_number or "",
                'FilingDate': data.filing_date or "",
                'EntityStatus': data.entity_status or "",
            }
            
            # 1. Fill Main Form (First 4 Inventors)
            main_inventors = data.inventors[:self.MAX_INVENTORS_ON_MAIN_FORM] if data.inventors else []
            
            for idx, inv in enumerate(main_inventors):
                i = idx + 1 # 1-based index
                
                field_data[f'GivenName_{i}'] = inv.first_name or ""
                field_data[f'FamilyName_{i}'] = inv.last_name or ""
                field_data[f'City_{i}'] = inv.city or ""
                field_data[f'State_{i}'] = inv.state or ""
                field_data[f'Country_{i}'] = inv.country or ""
                field_data[f'Address_{i}'] = inv.street_address or ""

            # Update form fields on the main page(s)
            for page in writer.pages:
                writer.update_page_form_field_values(
                    page, field_data, auto_regenerate=False
                )
            
            # 2. Handle Continuation Sheet (Inventors 5+)
            if data.inventors and len(data.inventors) > self.MAX_INVENTORS_ON_MAIN_FORM:
                extra_inventors = data.inventors[self.MAX_INVENTORS_ON_MAIN_FORM:]
                logger.info(f"Generating continuation sheet for {len(extra_inventors)} extra inventors...")
                
                continuation_packet = self._generate_continuation_sheet(
                    extra_inventors,
                    start_index=self.MAX_INVENTORS_ON_MAIN_FORM
                )
                
                # Merge continuation sheet
                continuation_reader = PdfReader(continuation_packet)
                for page in continuation_reader.pages:
                    writer.add_page(page)

            # Write output
            with open(output_path, "wb") as output_stream:
                writer.write(output_stream)
                
            logger.info(f"Successfully filled ADS PDF (Inventors: {len(data.inventors)}).")
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