import logging
import os
from pypdf import PdfReader

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_text_from_pdf(file_path: str) -> str:
    """
    Extracts text from a PDF file located at the given file path.

    Args:
        file_path (str): The local path to the PDF file.

    Returns:
        str: The extracted text content from the PDF.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not a valid PDF or cannot be read.
        Exception: For other unforeseen errors during extraction.
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found at path: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        logger.info(f"Starting text extraction for file: {file_path}")
        reader = PdfReader(file_path)
        extracted_text = []

        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                extracted_text.append(text)
            else:
                logger.warning(f"No text extracted from page {i+1} of {file_path}")

        full_text = "\n".join(extracted_text)
        logger.info(f"Successfully extracted {len(full_text)} characters from {file_path}")
        return full_text

    except Exception as e:
        logger.error(f"Failed to extract text from {file_path}: {str(e)}")
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")

if __name__ == "__main__":
    # Test the function with a dummy file if run directly
    import sys
    
    # Check if a file path is provided as an argument
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        try:
            print(f"--- Testing extraction on {test_file} ---")
            text = extract_text_from_pdf(test_file)
            print("--- Extracted Text Start ---")
            print(text[:500] + "..." if len(text) > 500 else text)
            print("--- Extracted Text End ---")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Usage: python extraction.py <path_to_pdf>")
        print("No file provided for testing.")