from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
from app.models.patent_application import PatentApplicationMetadata, Inventor, PatentApplicationCreate, PatentApplicationResponse, PatentApplicationInDB
from app.services.llm import llm_service
from app.services.ads_generator import ADSGenerator
from app.services.xfa_mapper import XFAMapper
from app.services.pdf_injector import PDFInjector
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

@router.post("/import-csv", status_code=status.HTTP_201_CREATED)
async def import_csv(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Import a CSV file, create a new application record, and return the application_id.
    """
    # 1. Parse CSV
    # Validate file extension
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported"
        )
    
    try:
        content = await file.read()
        inventors = parse_inventors_csv(content)
    except Exception as e:
        logger.error(f"CSV parsing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse CSV: {str(e)}"
        )

    # 2. Create Application Record
    try:
        # Create a basic application with the imported inventors
        app_in = PatentApplicationCreate(
            title="Imported via CSV", # Placeholder
            inventors=inventors,
            workflow_status="uploaded" # Using string to avoid enum import issues if tricky
        )
        
        app_db = PatentApplicationInDB(
            **app_in.model_dump(),
            created_by=current_user.id
        )
        
        doc = app_db.model_dump(by_alias=True)
        
        # Insert
        new_app = await db.patent_applications.insert_one(doc)
        
        return {
            "application_id": str(new_app.inserted_id),
            "message": f"Successfully imported {len(inventors)} inventors."
        }
        
    except Exception as e:
        logger.error(f"Failed to create application from CSV: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create application record"
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
async def generate_ads(data: PatentApplicationMetadata):
    """
    Generate an ADS PDF from the provided metadata and return it as a downloadable file.
    Uses XFA Injection to fill the official USPTO form.
    """
    mapper = XFAMapper()
    injector = PDFInjector()
    
    # Path to the template
    # We should ideally configure this path or locate it reliably
    # Assuming the same template location structure as ADSGenerator
    # Or strict path as per prompt: "d:/SnapDev/JWHD IP AUTOMATION/Client attachments/Original ADS from USPTO Website.pdf"
    # But that path is outside the codebase/container usually.
    # For now, I'll assume we should use the template inside the project or the one specified.
    # The previous ADSGenerator used "backend/app/templates/pto_sb_14_template.pdf".
    # The prompt for this task specified: "Original ADS from USPTO Website.pdf" at "../Client attachments/..."
    # I should probably use the one in templates if I want it self-contained, or the specific one.
    # I will stick to the one requested: "Original ADS from USPTO Website.pdf"
    # BUT I need to resolve the path relative to backend.
    
    # Resolving path relative to this file? No, relative to CWD.
    # CWD is "d:/SnapDev/JWHD IP AUTOMATION/CodeBase JWHD IP Automation"
    # File is at "../Client attachments/Original ADS from USPTO Website.pdf"
    # Use the XFA-enabled template we copied to the templates directory
    template_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "templates",
        "xfa_ads_template.pdf"
    )
    
    # Fallback to external path if internal template not found
    if not os.path.exists(template_path):
        template_path = os.path.join("..", "Client attachments", "Original ADS from USPTO Website.pdf")
        
    if not os.path.exists(template_path):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="XFA template not found. Please ensure the XFA-enabled ADS template is available."
        )

    try:
        # 1. Map Data to XML
        xml_data = mapper.map_metadata_to_xml(data)
        
        # 2. Inject XML into PDF
        pdf_stream = injector.inject_xml(template_path, xml_data)
        
        # 3. Return Streaming Response
        filename = f"ADS_Filled_{data.application_number.replace('/', '-') if data.application_number else 'Draft'}.pdf"
        
        # We need to yield the data from the BytesIO
        # BytesIO is not an async iterator, so we can wrap it or just pass it to StreamingResponse
        # StreamingResponse accepts a file-like object.
        
        return StreamingResponse(
            pdf_stream,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
        
    except Exception as e:
        logger.error(f"ADS generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate ADS: {str(e)}"
        )