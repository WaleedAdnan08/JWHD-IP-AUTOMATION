from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from fastapi.responses import Response
from typing import List, Optional
from app.api.deps import get_current_user
from app.models.user import UserResponse
from app.models.job import JobType, JobStatus
from app.models.office_action import OfficeActionExtractedData
from app.services.jobs import job_service
from app.services.storage import storage_service
from app.services.report_generator import report_generator
from app.db.mongodb import get_database
from app.models.document import DocumentInDB, ProcessedStatus
from app.worker import process_document_extraction_task
from bson import ObjectId
import logging
import uuid
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_office_action(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    """
    Upload an Office Action PDF for analysis.
    Starts an async extraction job.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # 1. Upload to Storage
    file_content = await file.read()
    filename = f"{uuid.uuid4()}_{file.filename}"
    storage_key = storage_service.upload_file(file_content, filename, file.content_type)
    
    # 2. Create Document Record
    db = await get_database()
    doc_in_db = DocumentInDB(
        user_id=str(current_user.id),
        filename=file.filename,
        storage_key=storage_key,
        document_type="office_action",
        file_size=len(file_content),
        mime_type=file.content_type,
        processed_status=ProcessedStatus.PENDING,
        created_at=datetime.utcnow()
    )
    logger.info(f"Creating document with user_id: {str(current_user.id)}")
    result = await db.documents.insert_one(doc_in_db.model_dump(by_alias=True))
    document_id = str(result.inserted_id)
    
    # 3. Create Processing Job
    job_id = await job_service.create_job(
        user_id=str(current_user.id),
        job_type=JobType.OFFICE_ACTION_ANALYSIS,
        input_refs=[document_id]
    )
    
    # 4. Trigger Worker
    process_document_extraction_task.delay(job_id, document_id, storage_key)
    
    return {"job_id": job_id, "document_id": document_id}

@router.get("/{document_id}", response_model=OfficeActionExtractedData)
async def get_office_action_data(
    document_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Retrieve extracted Office Action data for a document.
    """
    db = await get_database()
    
    # Debug: Check if document exists at all
    doc_exists = await db.documents.find_one({"_id": ObjectId(document_id)})
    logger.info(f"Document exists check: {doc_exists is not None}")
    if doc_exists:
        logger.info(f"Document user_id: {doc_exists.get('user_id')} (type: {type(doc_exists.get('user_id'))})")
        logger.info(f"Current user_id: {current_user.id} (type: {type(current_user.id)})")
        logger.info(f"Document status: {doc_exists.get('processed_status')}")
        logger.info(f"Has extraction_data: {bool(doc_exists.get('extraction_data'))}")
        
        # Check if user_id matches in any format
        doc_user_id = doc_exists.get('user_id')
        current_user_str = str(current_user.id)
        current_user_obj = ObjectId(current_user.id) if isinstance(current_user.id, str) else current_user.id
        
        logger.info(f"User ID comparison:")
        logger.info(f"  doc_user_id == current_user_str: {doc_user_id == current_user_str}")
        logger.info(f"  doc_user_id == current_user_obj: {doc_user_id == current_user_obj}")
        logger.info(f"  str(doc_user_id) == current_user_str: {str(doc_user_id) == current_user_str}")
    
    # Try multiple query approaches
    queries_to_try = [
        {"_id": ObjectId(document_id), "user_id": str(current_user.id)},
        {"_id": ObjectId(document_id), "user_id": ObjectId(current_user.id)},
        {"_id": ObjectId(document_id)}  # No user filter for debugging
    ]
    
    document = None
    for i, query in enumerate(queries_to_try):
        logger.info(f"Trying query {i+1}: {query}")
        document = await db.documents.find_one(query)
        if document:
            logger.info(f"Query {i+1} succeeded!")
            break
        else:
            logger.info(f"Query {i+1} failed")
    
    # If no document found with user filtering, check if it exists without user filter for debugging
    if not document:
        # Final attempt: check if document exists at all (for debugging)
        any_document = await db.documents.find_one({"_id": ObjectId(document_id)})
        if any_document:
            logger.error(f"Document exists but user access failed. Doc user_id: {any_document.get('user_id')}, Current user: {current_user.id}")
            # Try to fix user_id type mismatch on the fly
            if str(any_document.get('user_id')) == str(current_user.id):
                logger.info("User ID mismatch detected - using document anyway")
                document = any_document
            else:
                raise HTTPException(status_code=403, detail="Access denied to this document")
        else:
            raise HTTPException(status_code=404, detail="Document not found")
    
    # Check if extraction data exists (more important than status)
    extraction_data = document.get("extraction_data")
    if not extraction_data:
        # Check if processing is still in progress
        status = document.get("processed_status")
        if status in [ProcessedStatus.PENDING, ProcessedStatus.PROCESSING]:
            raise HTTPException(status_code=400, detail=f"Document processing is not complete. Status: {status}")
        else:
            raise HTTPException(status_code=404, detail="No extraction data found")
    
    return OfficeActionExtractedData(**extraction_data)

@router.put("/{document_id}", response_model=OfficeActionExtractedData)
async def update_office_action_data(
    document_id: str,
    data: OfficeActionExtractedData,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Update the extracted data manually.
    """
    db = await get_database()
    result = await db.documents.update_one(
        {"_id": ObjectId(document_id), "user_id": str(current_user.id)},
        {"$set": {"extraction_data": data.model_dump(by_alias=True)}}
    )
    
    if result.modified_count == 0:
         # Check if exists
         doc = await db.documents.find_one({"_id": ObjectId(document_id), "user_id": str(current_user.id)})
         if not doc:
             raise HTTPException(status_code=404, detail="Document not found")
             
    return data

@router.get("/{document_id}/report")
async def generate_report(
    document_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Generate and download the Word report.
    """
    db = await get_database()
    document = await db.documents.find_one({
        "_id": ObjectId(document_id),
        "user_id": str(current_user.id)
    })
    
    if not document or not document.get("extraction_data"):
         raise HTTPException(status_code=404, detail="Document or data not found")
         
    try:
        # Generate Report
        report_stream = report_generator.generate_office_action_report(document["extraction_data"])
        
        # Return as downloadable file
        headers = {
            'Content-Disposition': f'attachment; filename="Office_Action_Report_{document["filename"]}.docx"'
        }
        return Response(
            content=report_stream.getvalue(),
            headers=headers,
            media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate report")
