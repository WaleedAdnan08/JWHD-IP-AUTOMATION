import sys
import os
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

# Mock environment variables BEFORE importing app modules
os.environ["MONGODB_URL"] = "mongodb://localhost:27017/test_db"
os.environ["SECRET_KEY"] = "super_secret_test_key"
os.environ["GOOGLE_API_KEY"] = "dummy_key_for_testing"

from backend.app.services.llm import llm_service
from backend.app.models.patent_application import PatentApplicationMetadata, Inventor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_verification():
    logger.info("=== VERIFYING UNIFIED EXTRACTION PIPELINE ===")
    
    # Mock dependencies
    llm_service.upload_file = AsyncMock(return_value="mock_file_obj")
    llm_service.generate_structured_content = AsyncMock()
    
    # TEST 1: Text-First Strategy (Small file, good text)
    logger.info("\n--- TEST 1: Text-First Strategy ---")
    with patch("backend.app.services.llm.PdfReader") as MockPdfReader:
        # Setup mock PDF
        mock_reader = MagicMock()
        mock_reader.pages = [MagicMock(), MagicMock()] # 2 pages
        # Return sufficient text
        # Make text > 200 chars to trigger Text-First
        long_text = "Title of Invention: Test Patent\n" + ("Lorem ipsum dolor sit amet " * 20)
        mock_reader.pages[0].extract_text.return_value = long_text
        mock_reader.pages[1].extract_text.return_value = "Inventor Information:\nJohn Doe, New York, NY"
        mock_reader.get_form_text_fields.return_value = {} # No form fields
        mock_reader.trailer = {"/Root": {}} # No XFA
        MockPdfReader.return_value = mock_reader
        
        # Mock LLM response for text analysis
        llm_service.generate_structured_content.return_value = {
            "title": "Test Patent",
            "application_number": "12/345,678",
            "inventors": [{"name": "John Doe", "city": "New York", "state": "NY"}]
        }

        # Pass dummy content to avoid file I/O
        result = await llm_service.analyze_cover_sheet("dummy.pdf", file_content=b"dummy_pdf_bytes")
        
        if result.title == "Test Patent" and len(result.inventors) == 1:
            logger.info("✅ Text-First Strategy: PASSED")
        else:
            logger.error(f"❌ Text-First Strategy: FAILED (Result: {result})")

    # TEST 2: Chunking Strategy (Large file, scanned/no text)
    logger.info("\n--- TEST 2: Chunking Strategy (Large File) ---")
    with patch("backend.app.services.llm.PdfReader") as MockPdfReader:
        # Setup mock PDF (Large)
        mock_reader = MagicMock()
        mock_reader.pages = [MagicMock()] * 60 # 60 pages (> 50 threshold)
        # Return empty text (simulate scan) - Force insufficient text
        for page in mock_reader.pages:
            page.extract_text.return_value = ""
        
        # Ensure form fields are also empty so we don't accidentally find text there
        mock_reader.get_form_text_fields.return_value = {}
        mock_reader.trailer = {"/Root": {}}
        MockPdfReader.return_value = mock_reader
        
        # Mock internal chunking logic since we can't easily mock the file read/write inside it
        # We'll mock _analyze_document_chunked_structured directly to verify it gets CALLED
        original_chunk_method = llm_service._analyze_document_chunked_structured
        llm_service._analyze_document_chunked_structured = AsyncMock(return_value=PatentApplicationMetadata(
            title="Chunked Patent",
            inventors=[{"name": "Chunked Inventor"}]
        ))
        
        # Pass dummy content to avoid file I/O error
        result = await llm_service.analyze_cover_sheet("dummy_large.pdf", file_content=b"large_pdf_bytes")
        
        if result.title == "Chunked Patent":
            logger.info("✅ Chunking Strategy: PASSED (Correctly routed to _analyze_document_chunked_structured)")
        else:
            logger.error("❌ Chunking Strategy: FAILED (Did not route correctly)")
            
        # Restore method
        llm_service._analyze_document_chunked_structured = original_chunk_method

    # TEST 3: XFA Strategy
    logger.info("\n--- TEST 3: XFA Strategy ---")
    with patch("backend.app.services.llm.PdfReader") as MockPdfReader:
        mock_reader = MagicMock()
        mock_reader.pages = [MagicMock()]
        mock_reader.pages[0].extract_text.return_value = ""
        # Setup XFA structure
        mock_reader.trailer = {
            "/Root": {
                "/AcroForm": {
                    "/XFA": ["datasets", MagicMock()] 
                }
            }
        }
        # Mock the XFA data extraction to return something valid
        mock_obj = mock_reader.trailer["/Root"]["/AcroForm"]["/XFA"][1]
        mock_obj.get_object().get_data.return_value = b"<xml>Dummy XFA Data</xml>"
        
        MockPdfReader.return_value = mock_reader
        
        # Mock LLM response for XFA
        llm_service.generate_structured_content.return_value = {
            "title": "XFA Patent",
            "inventors": [{"name": "XFA Inventor"}]
        }
        
        # Pass dummy content
        result = await llm_service.analyze_cover_sheet("dummy_xfa.pdf", file_content=b"xfa_pdf_bytes")
        
        if result.title == "XFA Patent":
            logger.info("✅ XFA Strategy: PASSED")
        else:
            logger.error("❌ XFA Strategy: FAILED")

if __name__ == "__main__":
    asyncio.run(run_verification())