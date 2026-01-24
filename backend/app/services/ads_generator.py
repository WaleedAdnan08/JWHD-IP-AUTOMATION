from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from app.models.patent_application import PatentApplicationMetadata, Inventor
import os
import sys
import logging

logger = logging.getLogger(__name__)

class ADSGenerator:
    def generate_ads_pdf(self, data: PatentApplicationMetadata, output_path: str) -> str:
        """
        Generates a PDF summary of the patent application data.
        
        Args:
            data: The PatentApplicationMetadata object containing the data.
            output_path: The file path where the PDF should be saved.
            
        Returns:
            The path to the generated PDF.
        """
        logger.info(f"Generating ADS PDF at: {output_path}")
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = styles['Heading1']
        elements.append(Paragraph("Application Data Sheet (Summary)", title_style))
        elements.append(Spacer(1, 12))
        
        # Metadata Table
        meta_data = [
            ["Field", "Value"],
            ["Title", data.title or "N/A"],
            ["Application Number", data.application_number or "N/A"],
            ["Filing Date", data.filing_date or "N/A"],
            ["Entity Status", data.entity_status or "N/A"],
        ]
        
        # Add basic styling to metadata table
        t = Table(meta_data, colWidths=[150, 350])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 24))
        
        # Inventors Section
        elements.append(Paragraph("Inventors", styles['Heading2']))
        elements.append(Spacer(1, 12))
        
        if data.inventors:
            for idx, inv in enumerate(data.inventors, 1):
                # Construct full name
                full_name_parts = [p for p in [inv.first_name, inv.middle_name, inv.last_name] if p]
                full_name = " ".join(full_name_parts)
                if not full_name and inv.name:
                    full_name = inv.name
                if not full_name:
                    full_name = "N/A"

                inv_data = [
                    [f"Inventor {idx}", ""],
                    ["Name", full_name],
                    ["Address", inv.street_address or "N/A"],
                    ["City", inv.city or "N/A"],
                    ["State", inv.state or "N/A"],
                    ["Zip Code", inv.zip_code or "N/A"],
                    ["Country", inv.country or "N/A"],
                    ["Citizenship", inv.citizenship or "N/A"]
                ]
                
                inv_table = Table(inv_data, colWidths=[150, 350])
                inv_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (1, 0), colors.lightgrey),
                    ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                elements.append(inv_table)
                elements.append(Spacer(1, 12))
        else:
            elements.append(Paragraph("No inventors listed.", styles['Normal']))

        doc.build(elements)
        return output_path

if __name__ == "__main__":
    # Setup path to run standalone
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
                country="US"
            )
        ]
    )
    
    output = "dummy_ads.pdf"
    print(f"Generating dummy PDF at {output}...")
    try:
        generator.generate_ads_pdf(dummy_data, output)
        print("Successfully generated PDF.")
        print(f"File exists: {os.path.exists(output)}")
    except Exception as e:
        print(f"Error generating PDF: {e}")