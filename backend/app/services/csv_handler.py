import csv
import io
from typing import List, Dict, Optional
from app.models.patent_application import Inventor

def normalize_header(header: str) -> str:
    """
    Normalizes a CSV header for easier matching.
    Removes whitespace and converts to lowercase.
    """
    return header.lower().strip().replace(" ", "_").replace("-", "_")

def parse_inventors_csv(file_content: bytes) -> List[Inventor]:
    """
    Parses a CSV file content (bytes) and extracts a list of Inventor objects.
    
    Args:
        file_content: The raw bytes of the CSV file.
        
    Returns:
        A list of Inventor objects populated with data from the CSV.
        
    Raises:
        ValueError: If parsing fails or required columns are missing (though currently soft matching is preferred).
    """
    try:
        # Decode bytes to string
        content_str = file_content.decode('utf-8-sig') # Handle BOM if present
    except UnicodeDecodeError:
        # Fallback to latin-1 if utf-8 fails, though utf-8 is standard
        content_str = file_content.decode('latin-1')

    file_obj = io.StringIO(content_str)
    reader = csv.DictReader(file_obj)
    
    if not reader.fieldnames:
        raise ValueError("CSV file is empty or missing headers")

    # Map likely CSV headers to Inventor model fields
    # Keys are Inventor model field names
    # Values are lists of possible CSV header names (normalized)
    field_mapping = {
        "first_name": ["first_name", "firstname", "first", "fname"],
        "last_name": ["last_name", "lastname", "last", "lname", "surname"],
        "middle_name": ["middle_name", "middlename", "middle", "mname", "initial", "middle_initial"],
        "street_address": ["address", "street_address", "street", "mailing_address", "address_line_1"],
        "city": ["city", "town", "municipality"],
        "state": ["state", "province", "region", "state_province"],
        "zip_code": ["zip_code", "zip", "postal_code", "postal", "zipcode"],
        "country": ["country", "country_code", "nation"],
        "citizenship": ["citizenship", "citizen", "nationality"],
        "name": ["name", "full_name", "fullname"] # Fallback if separated names aren't found
    }

    # Determine which CSV column maps to which model field
    csv_headers = reader.fieldnames
    header_map: Dict[str, str] = {} # model_field -> csv_header

    normalized_csv_headers = {normalize_header(h): h for h in csv_headers}

    for model_field, potential_headers in field_mapping.items():
        for potential_header in potential_headers:
            if potential_header in normalized_csv_headers:
                header_map[model_field] = normalized_csv_headers[potential_header]
                break
    
    inventors: List[Inventor] = []
    
    for row in reader:
        inventor_data = {}
        
        # Extract data based on map
        for model_field, csv_header in header_map.items():
            value = row.get(csv_header, "").strip()
            if value:
                inventor_data[model_field] = value
        
        # If we have data, create an object
        if inventor_data:
            # Handling 'name' vs separated names could be done here if needed
            # For now, we trust the model validation
            inventor = Inventor(**inventor_data)
            inventors.append(inventor)
            
    if len(inventors) == 0:
        raise ValueError("No valid inventor rows found in CSV")
        
    if len(inventors) > 20:
        raise ValueError(f"Too many inventors found ({len(inventors)}). Maximum limit is 20.")
            
    return inventors

if __name__ == "__main__":
    # Test execution
    sample_csv = """First Name,Last Name,Middle Name,Address,City,State,Zip,Country,Citizenship
John,Doe,A.,123 Main St,Springfield,IL,62704,USA,USA
Jane,Smith,,456 Elm Ave,Metropolis,NY,10001,USA,Canada
"""
    print("Testing with standard CSV...")
    try:
        results = parse_inventors_csv(sample_csv.encode('utf-8'))
        for inv in results:
            print(inv)
        print("Success!")
    except Exception as e:
        print(f"Failed: {e}")

    sample_csv_variations = """fname,lname,street,town,zipcode
Alice,Wonderland,789 Rabbit Hole,London,SW1A
Bob,Builder,101 Construction Ln,Bobsville,99999
"""
    print("\nTesting with header variations...")
    try:
        results = parse_inventors_csv(sample_csv_variations.encode('utf-8'))
        for inv in results:
            print(inv)
        print("Success!")
    except Exception as e:
        print(f"Failed: {e}")