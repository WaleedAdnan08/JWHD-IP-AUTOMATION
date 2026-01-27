import asyncio
import os
import sys
from unittest.mock import MagicMock, patch
from typing import List

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../backend'))

# Set environment variables BEFORE importing app modules
os.environ["MONGODB_URL"] = "mongodb://localhost:27017/test_db"
os.environ["SECRET_KEY"] = "test_secret_key"
os.environ["GOOGLE_API_KEY"] = "test_google_key"

from app.services.llm import LLMService, PatentApplicationMetadata
from app.models.patent_application import Inventor

async def test_standard_pdf():
    print("\n=== TEST 1: Standard Text-Based PDF (Text-First) ===")
    try:
        service = LLMService()
        
        # Create a dummy result to return from the LLM call
        mock_metadata = {
            "title": "Mocked Text Title",
            "application_number": "12/345,678",
            "inventors": [{"name": "John Doe"}],
            "_debug_reasoning": "Text-first path used successfully"
        }

        # Patch the internal text analysis method to verify it gets called
        with patch.object(service, '_analyze_text_only', wraps=service._analyze_text_only) as spy_text_only:
            # Patch the actual LLM generation to avoid API calls and ensure success
            with patch.object(service, 'generate_structured_content', return_value=mock_metadata):
                # We use the real standard.pdf we created
                result = await service.analyze_cover_sheet("tests/standard.pdf")
                
                if spy_text_only.called:
                    print("✅ SUCCESS: _analyze_text_only was called.")
                    # Pydantic maps alias '_debug_reasoning' to 'debug_reasoning' attribute
                    print(f"   Reasoning: {result.debug_reasoning}")
                else:
                    print("❌ FAILURE: _analyze_text_only was NOT called.")
    except Exception as e:
        print(f"❌ ERROR: {e}")

async def test_scanned_pdf():
    print("\n=== TEST 2: Simulated 'Scanned' PDF (Native PDF Fallback) ===")
    try:
        service = LLMService()
        
        # Mock text extraction to return empty string (simulating scan/image-only)
        with patch.object(service, '_extract_text_locally', return_value=""):
            # Mock page count to be small (< 50)
            with patch('app.services.llm.PdfReader') as MockPdfReader:
                mock_reader = MagicMock()
                mock_reader.pages = [1, 2, 3] # Length 3
                MockPdfReader.return_value = mock_reader
                
                # Mock the direct fallback method to verify it gets called
                mock_return = PatentApplicationMetadata(title="Native PDF Title")
                with patch.object(service, '_analyze_pdf_direct_fallback', return_value=mock_return) as spy_direct:
                    # Mock upload to avoid network calls
                    with patch.object(service, 'upload_file', return_value=MagicMock()):
                        # Mock XFA check to avoid issues
                        with patch.object(service, '_extract_xfa_data', return_value=None):
                            
                            await service.analyze_cover_sheet("tests/standard.pdf")
                            
                            if spy_direct.called:
                                print("✅ SUCCESS: _analyze_pdf_direct_fallback was called (Standard Fallback).")
                            else:
                                print("❌ FAILURE: _analyze_pdf_direct_fallback was NOT called.")

    except Exception as e:
         print(f"❌ ERROR: {e}")

async def test_large_pdf():
    print("\n=== TEST 3: Large PDF (Chunking Logic) ===")
    try:
        service = LLMService()
        
        # Mock text extraction to return empty (force vision fallback)
        with patch.object(service, '_extract_text_locally', return_value=""):
            # Mock page count to be large (> 50)
            with patch('app.services.llm.PdfReader') as MockPdfReader:
                mock_reader = MagicMock()
                # Create a list of 60 mock pages
                mock_reader.pages = [MagicMock()] * 60 
                MockPdfReader.return_value = mock_reader
                
                # Mock the chunked analysis method
                mock_return = PatentApplicationMetadata(title="Chunked Title")
                with patch.object(service, '_analyze_document_chunked_structured', return_value=mock_return) as spy_chunked:
                     # Mock upload
                    with patch.object(service, 'upload_file', return_value=MagicMock()):
                         # Mock XFA
                        with patch.object(service, '_extract_xfa_data', return_value=None):
                            
                            # Provide raw bytes to avoid file opening logic issues in mocks
                            await service.analyze_cover_sheet("tests/standard.pdf", file_content=b"fake_large_pdf_bytes")
                            
                            if spy_chunked.called:
                                print("✅ SUCCESS: _analyze_document_chunked_structured was called (Large PDF Strategy).")
                            else:
                                print("❌ FAILURE: _analyze_document_chunked_structured was NOT called.")
    except Exception as e:
        print(f"❌ ERROR: {e}")

async def main():
    if not os.path.exists("tests/standard.pdf"):
        print("Error: tests/standard.pdf not found. Please run create_dummy_pdf.py first.")
        return

    await test_standard_pdf()
    await test_scanned_pdf()
    await test_large_pdf()

if __name__ == "__main__":
    asyncio.run(main())