from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

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
    
    # Add some dummy text to ensure it passes the "sufficient text" check (>200 chars)
    c.drawString(100, height - 400, "Description of the invention goes here. " * 10)
    
    c.save()
    print(f"Created test PDF at {filename}")

if __name__ == "__main__":
    create_test_pdf("tests/standard.pdf")