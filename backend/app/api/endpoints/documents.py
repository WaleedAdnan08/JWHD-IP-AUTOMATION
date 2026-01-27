from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status
from app.db.mongodb import get_database
from app.models.user import UserResponse
from app.api.deps import get_current_user
from app.services.storage import storage_service
from app.services.audit import audit_service
from app.models.document import DocumentCreate, DocumentInDB, DocumentType, DocumentResponse
from app.models.job import JobType
from app.services.jobs import job_service
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import uuid
import logging

router = APIRouter()

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    if file.content_type not in ["application/pdf", "text/csv", "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF, CSV, and DOCX are allowed.")
    
    if file.size > 50 * 1024 * 1024: # 50MB
        raise HTTPException(status_code=413, detail="File too large. Limit is 50MB.")

    try:
        # Generate unique storage key
        file_ext = file.filename.split('.')[-1]
        storage_key = f"{current_user.id}/{uuid.uuid4()}.{file_ext}"
        
        # Read content
        content = await file.read()
        
        # Upload to GCS
        storage_service.upload_file(content, storage_key, content_type=file.content_type)
        
        # Create DB record
        doc_in = DocumentCreate(
            filename=file.filename,
            document_type=document_type,
            file_size=len(content),
            mime_type=file.content_type,
            storage_key=storage_key,
            user_id=current_user.id
        )
        
        doc_db = DocumentInDB(**doc_in.model_dump())
        new_doc = await db.documents.insert_one(doc_db.model_dump(by_alias=True))
        created_doc = await db.documents.find_one({"_id": new_doc.inserted_id})
        
        await audit_service.log_event(
            user_id=current_user.id,
            event_type="document_upload",
            details={
                "document_id": str(new_doc.inserted_id),
                "filename": file.filename,
                "file_size": len(content),
                "storage_key": storage_key
            }
        )
        
        return DocumentResponse(**created_doc)

    except Exception as e:
        logging.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail="File upload failed")

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    try:
        doc = await db.documents.find_one({"_id": ObjectId(document_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if str(doc["user_id"]) != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this document")
            
        return DocumentResponse(**doc)
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Failed to fetch document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch document")

@router.get("/{document_id}/url")
async def get_download_url(
    document_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    try:
        doc = await db.documents.find_one({"_id": ObjectId(document_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Permission check: Ensure current user owns the document
        # Note: In a real app, you might also allow admins or specific roles
        if str(doc["user_id"]) != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this document")
            
        url = storage_service.generate_presigned_url(doc["storage_key"])
        return {"url": url}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Failed to generate download URL: {e}")
        raise HTTPException(status_code=500, detail="Could not generate download URL")

@router.post("/{document_id}/parse", status_code=status.HTTP_202_ACCEPTED)
async def parse_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Initiate asynchronous parsing of a document.
    Returns a Job ID to track progress.
    """
    try:
        # 1. Verify document exists and belongs to user
        doc = await db.documents.find_one({"_id": ObjectId(document_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
            
        if str(doc["user_id"]) != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this document")
            
        # 2. Create Job Record
        job_id = await job_service.create_job(
            user_id=current_user.id,
            job_type=JobType.ADS_EXTRACTION,
            input_refs=[document_id]
        )
        
        # 3. Schedule Background Task
        # We need to import the task function here or inside the service
        # To avoid circular imports, we'll implement the task orchestration in job_service
        from app.worker import process_document_extraction_task
        process_document_extraction_task.delay(
            job_id=job_id,
            document_id=document_id,
            storage_key=doc["storage_key"]
        )
        
        await audit_service.log_event(
            user_id=current_user.id,
            event_type="job_started",
            details={
                "job_id": job_id,
                "document_id": document_id,
                "job_type": "ads_extraction"
            }
        )
        
        return {"job_id": job_id, "status": "accepted"}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Failed to initiate parsing for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate parsing job")