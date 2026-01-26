from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from app.models.patent_application import PatentApplicationMetadata, Inventor, PatentApplicationCreate, PatentApplicationResponse, PatentApplicationInDB
from app.services.llm import llm_service
from app.services.ads_generator import ADSGenerator
from app.services.csv_handler import parse_inventors_csv
from app.services.storage import storage_service
from app.models.user import UserResponse
from app.api.deps import get_current_user
from app.db.mongodb import get_database
from motor.motor_asyncio import AsyncIOMotorDatabase
import os
import shutil
import uuid
import logging
import bson
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
        logger.info(f"Received file for analysis: {file.filename} (Type: {file.content_type})")

        # Save uploaded file temporarily
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Analyze PDF directly with LLM (Native Vision/Multimodal Support)
        try:
            # We pass the file path directly. The LLM service handles uploading to Gemini.
            metadata = await llm_service.analyze_cover_sheet(temp_file_path)
            
            # Log the result before returning
            logger.info(f"Analysis complete for {file.filename}")
            if metadata.inventors:
                logger.info(f"Found {len(metadata.inventors)} inventors: {[inv.name for inv in metadata.inventors]}")
            else:
                logger.warning("No inventors found in the analysis result.")
                
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

@router.post("/", response_model=PatentApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    application_in: PatentApplicationCreate,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create a new patent application record.
    Validates that the record size does not exceed MongoDB 16MB limit.
    """
    # Create DB model
    app_db = PatentApplicationInDB(
        **application_in.model_dump(),
        created_by=current_user.id
    )
    
    # Calculate BSON size
    doc = app_db.model_dump(by_alias=True)
    try:
        bson_size = len(bson.BSON.encode(doc))
        if bson_size > 16 * 1024 * 1024: # 16MB
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Application record size ({bson_size} bytes) exceeds the 16MB limit."
            )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"BSON encoding failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to validate application record size"
        )

    try:
        new_app = await db.patent_applications.insert_one(doc)
        created_app = await db.patent_applications.find_one({"_id": new_app.inserted_id})
        return PatentApplicationResponse(**created_app)
    except Exception as e:
        logger.error(f"Failed to create application: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create application"
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