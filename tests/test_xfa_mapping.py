import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend'))

from app.services.xfa_mapper import XFAMapper
from app.models.patent_application import PatentApplicationMetadata, Inventor

def test_xfa_mapping():
    mapper = XFAMapper()

    # Create dummy data
    metadata = PatentApplicationMetadata(
        title="AI-Powered Patent Automation System",
        application_number="18/999,888",
        filing_date="2024-02-15",
        entity_status="Small Entity",
        inventors=[
            Inventor(
                first_name="Alice",
                middle_name="M.",
                last_name="Engineer",
                street_address="123 Innovation Way",
                city="San Francisco",
                state="CA",
                zip_code="94105",
                country="US"
            ),
            Inventor(
                first_name="Bob",
                last_name="Builder",
                street_address="456 Construct Ave",
                city="Austin",
                state="TX",
                zip_code="73301",
                country="US"
            ),
             Inventor(
                first_name="Charlie",
                last_name="Coder",
                street_address="789 Binary Blvd",
                city="Toronto",
                state="ON",
                country="CA"
            )
        ]
    )

    print("Mapping metadata to XFA XML...")
    xml_output = mapper.map_metadata_to_xml(metadata)
    
    # Basic Validation
    print("\n--- XML OUTPUT START ---")
    print(xml_output)
    print("--- XML OUTPUT END ---\n")

    # Assertions
    if "<chkSmallEntity>1</chkSmallEntity>" in xml_output:
        print("PASS: Small Entity Checked")
    else:
        print("FAIL: Small Entity NOT Checked")

    if "<invention-title>AI-Powered Patent Automation System</invention-title>" in xml_output:
        print("PASS: Title Mapped")
    else:
        print("FAIL: Title NOT Mapped")

    # Check for inventors
    # Count occurrences of <sfApplicantInformation>
    count = xml_output.count("<sfApplicantInformation>")
    print(f"Inventor Count in XML: {count}")
    
    if count == 3:
        print("PASS: 3 Inventors Mapped")
    else:
        print(f"FAIL: Expected 3 inventors, found {count}")

    if "Alice" in xml_output and "Bob" in xml_output and "Charlie" in xml_output:
        print("PASS: All names present")
    else:
        print("FAIL: Missing names")

if __name__ == "__main__":
    test_xfa_mapping()