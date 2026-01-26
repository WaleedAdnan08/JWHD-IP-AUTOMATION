from datetime import datetime
from typing import Optional, Dict, Any
from app.db.mongodb import get_database
from app.models.job import JobStatus, JobType, ProcessingJobInDB, ProcessingJobCreate, ProcessingJobResponse
from app.models.document import ProcessedStatus
from bson import ObjectId
import logging
import os
import uuid

logger = logging.getLogger(__name__)

class JobService:
    async def create_job(self, user_id: str, job_type: JobType, input_refs: list[str]) -> str:
        db = await get_database()
        job_in = ProcessingJobCreate(
            user_id=user_id,
            job_type=job_type,
            input_references=input_refs,
            status=JobStatus.PENDING
        )
        job_db = ProcessingJobInDB(**job_in.model_dump())
        result = await db.processing_jobs.insert_one(job_db.model_dump(by_alias=True))
        logger.info(f"Created job {result.inserted_id} for user {user_id} with type {job_type}")
        return str(result.inserted_id)

    async def update_job_status(self, job_id: str, status: JobStatus, progress: int = 0, error: Optional[str] = None):
        db = await get_database()
        update_data = {
            "status": status,
            "progress_percentage": progress,
            "updated_at": datetime.utcnow()
        }
        if status == JobStatus.COMPLETED:
            update_data["completed_at"] = datetime.utcnow()
        if error:
            update_data["error_details"] = error
            logger.error(f"Job {job_id} failed: {error}")
            
        await db.processing_jobs.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": update_data}
        )
        logger.info(f"Updated job {job_id} status to {status} (Progress: {progress}%)")

    async def get_job(self, job_id: str) -> Optional[ProcessingJobResponse]:
        db = await get_database()
        job = await db.processing_jobs.find_one({"_id": ObjectId(job_id)})
        if job:
            return ProcessingJobResponse(**job)
        return None

    async def process_document_extraction(self, job_id: str, document_id: str, storage_key: str):
        """
        Background task to process document extraction.
        """
        # Delayed imports to avoid circular dependencies
        from app.services.storage import storage_service
        from app.services.llm import llm_service
        from app.services.audit import audit_service
        
        logger.info(f"Starting extraction for Job {job_id} (Doc: {document_id})")
        db = await get_database()
        
        # Get user_id for logging (could be passed in, or fetched from job)
        job = await db.processing_jobs.find_one({"_id": ObjectId(job_id)})
        user_id = str(job["user_id"]) if job else "system"
        
        temp_file_path = f"temp_{uuid.uuid4()}.pdf"
        
        try:
            # 1. Update Job Status to PROCESSING
            await self.update_job_status(job_id, JobStatus.PROCESSING, progress=10)
            await db.documents.update_one(
                {"_id": ObjectId(document_id)},
                {"$set": {"processed_status": ProcessedStatus.PROCESSING}}
            )
            
            # 2. Download file from Storage
            logger.info(f"Downloading file {storage_key} to {temp_file_path}")
            storage_service.download_to_filename(storage_key, temp_file_path)
            await self.update_job_status(job_id, JobStatus.PROCESSING, progress=30)
            
            # 3. Perform Extraction
            logger.info("Calling LLM Service...")
            start_time = datetime.utcnow()
            metadata = await llm_service.analyze_cover_sheet(temp_file_path)
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            # Log LLM Usage
            await audit_service.log_event(
                user_id=user_id,
                event_type="llm_extraction",
                details={
                    "job_id": job_id,
                    "document_id": document_id,
                    "duration_ms": duration_ms,
                    "model": "gemini-2.0-flash-exp" # Or fetch from settings
                }
            )

            await self.update_job_status(job_id, JobStatus.PROCESSING, progress=90)
            
            # 4. Save Results
            # Store full extraction data in the document
            logger.info("Saving extraction results...")
            await db.documents.update_one(
                {"_id": ObjectId(document_id)},
                {
                    "$set": {
                        "processed_status": ProcessedStatus.COMPLETED,
                        "extraction_data": metadata.model_dump(by_alias=True)
                    }
                }
            )
            
            # 5. Complete Job
            await self.update_job_status(job_id, JobStatus.COMPLETED, progress=100)
            logger.info(f"Job {job_id} completed successfully.")
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            await self.update_job_status(job_id, JobStatus.FAILED, error=str(e))
            await db.documents.update_one(
                {"_id": ObjectId(document_id)},
                {"$set": {"processed_status": ProcessedStatus.FAILED}}
            )
        finally:
            # Cleanup
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

job_service = JobService()