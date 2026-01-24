from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.models.patent_application import PatentApplicationMetadata, Inventor
from app.services.llm import llm_service
from app.services.ads_generator import ADSGenerator
from app.services.csv_handler import parse_inventors_csv
from app.services.storage import storage_service
import os
import shutil
import uuid
import logging
from typing import Dict, Any, List

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/analyze", response_model=PatentApplicationMetadata)
async def analyze_application(file: UploadFile = File(...)):
    """
    Analyze an uploaded PDF file to extract patent application metadata.
    """
    # Validate file type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported"
        )

    temp_file_path = f"temp_{uuid.uuid4()}.pdf"
    
    try:
        # Save uploaded file temporarily
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Analyze PDF directly with LLM (Native Vision/Multimodal Support)
        try:
            # We pass the file path directly. The LLM service handles uploading to Gemini.
            metadata = await llm_service.analyze_cover_sheet(temp_file_path)
            return metadata
        except HTTPException as he:
            # Re-raise HTTP exceptions (like 503 from LLM service) directly
            raise he
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to analyze PDF content: {str(e)}"
            )
            
    finally:
        # Cleanup temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@router.post("/parse-csv", response_model=List[Inventor])
async def parse_csv(file: UploadFile = File(...)):
    """
    Parse an uploaded CSV file to extract inventor data.
    """
    # Validate file extension
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported"
        )
    
    try:
        content = await file.read()
        inventors = parse_inventors_csv(content)
        return inventors
    except Exception as e:
        logger.error(f"CSV parsing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse CSV: {str(e)}"
        )

@router.post("/generate-ads")
async def generate_ads(data: PatentApplicationMetadata) -> Dict[str, str]:
    """
    Generate an ADS PDF from the provided metadata and return a download URL.
    """
    generator = ADSGenerator()
    output_filename = f"ads_{uuid.uuid4()}.pdf"
    
    try:
        # Generate PDF locally
        pdf_path = generator.generate_ads_pdf(data, output_filename)
        
        # Read the generated PDF
        with open(pdf_path, "rb") as f:
            pdf_content = f.read()
            
        # Upload to Storage
        destination_blob_name = f"generated/{output_filename}"
        storage_service.upload_file(
            file_content=pdf_content,
            destination_blob_name=destination_blob_name,
            content_type="application/pdf"
        )
        
        # Generate download URL
        download_url = storage_service.generate_presigned_url(destination_blob_name)
        
        return {
            "file_id": destination_blob_name,
            "download_url": download_url
        }
        
    except Exception as e:
        logger.error(f"ADS generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate ADS: {str(e)}"
        )
    finally:
        # Cleanup local generated file
        if os.path.exists(output_filename):
            os.remove(output_filename)