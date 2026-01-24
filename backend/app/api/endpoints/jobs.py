from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_current_user
from app.models.user import UserResponse
from app.services.jobs import job_service
from app.models.job import ProcessingJobResponse
import logging

router = APIRouter()

@router.get("/{job_id}", response_model=ProcessingJobResponse)
async def get_job_status(
    job_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get the status of a specific job.
    """
    try:
        job = await job_service.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Permission check
        if job.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this job")
            
        return job
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error fetching job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch job status")