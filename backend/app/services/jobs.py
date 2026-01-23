from datetime import datetime
from typing import Optional, Dict, Any
from app.db.mongodb import get_database
from app.models.job import JobStatus, JobType, ProcessingJobInDB, ProcessingJobCreate, ProcessingJobResponse
from bson import ObjectId
import logging

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
            
        await db.processing_jobs.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": update_data}
        )

    async def get_job(self, job_id: str) -> Optional[ProcessingJobResponse]:
        db = await get_database()
        job = await db.processing_jobs.find_one({"_id": ObjectId(job_id)})
        if job:
            return ProcessingJobResponse(**job)
        return None

job_service = JobService()