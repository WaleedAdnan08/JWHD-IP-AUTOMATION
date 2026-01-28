#!/usr/bin/env python3
"""
Test script to verify the Gemini model fix and file upload process.
"""

import asyncio
import sys
import os
import logging

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.llm import llm_service
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_gemini_model():
    """Test basic Gemini model functionality."""
    logger.info("=== TESTING GEMINI MODEL FIX ===")
    
    # Test 1: Check if LLM service is initialized
    logger.info(f"1. Testing LLM Service Initialization...")
    logger.info(f"   Model configured: {settings.GEMINI_MODEL}")
    logger.info(f"   Client initialized: {llm_service.client is not None}")
    
    if not llm_service.client:
        logger.error("❌ LLM service not initialized. Check API key and configuration.")
        return False
    
    # Test 2: Simple text generation
    logger.info("2. Testing basic text generation...")
    try:
        simple_prompt = "Generate a simple JSON response with a 'message' field containing 'Hello World'."
        schema = {"message": "string"}
        
        result = await llm_service.generate_structured_content(
            prompt=simple_prompt,
            schema=schema
        )
        
        if result and result.get("message"):
            logger.info(f"✅ Basic generation successful: {result}")
        else:
            logger.warning(f"⚠️ Unexpected result format: {result}")
            
    except Exception as e:
        logger.error(f"❌ Basic generation failed: {e}")
        return False
    
    # Test 3: File upload test (if test file exists)
    logger.info("3. Testing file upload...")
    test_files = ["tests/standard.pdf", "test_data/dummy.docx"]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            try:
                logger.info(f"   Uploading test file: {test_file}")
                file_obj = await llm_service.upload_file(test_file)
                logger.info(f"✅ File upload successful: {file_obj.name}")
                break
            except Exception as e:
                logger.error(f"❌ File upload failed for {test_file}: {e}")
        else:
            logger.info(f"   Test file not found: {test_file}")
    
    logger.info("=== TEST COMPLETED ===")
    return True

async def test_patent_extraction():
    """Test patent document extraction if test file exists."""
    logger.info("=== TESTING PATENT EXTRACTION ===")
    
    test_file = "tests/standard.pdf"
    if not os.path.exists(test_file):
        logger.info(f"Test file {test_file} not found. Skipping extraction test.")
        return
    
    try:
        logger.info(f"Testing patent extraction with: {test_file}")
        
        # Mock progress callback
        async def progress_callback(percent, message):
            logger.info(f"Progress: {percent}% - {message}")
        
        result = await llm_service.analyze_cover_sheet(
            file_path=test_file,
            progress_callback=progress_callback
        )
        
        logger.info(f"✅ Extraction successful!")
        logger.info(f"   Title: {result.title}")
        logger.info(f"   Application Number: {result.application_number}")
        logger.info(f"   Inventors: {len(result.inventors) if result.inventors else 0}")
        
    except Exception as e:
        logger.error(f"❌ Patent extraction failed: {e}")

if __name__ == "__main__":
    async def main():
        success = await test_gemini_model()
        if success:
            await test_patent_extraction()
        else:
            logger.error("Basic model test failed. Skipping extraction test.")
    
    asyncio.run(main())