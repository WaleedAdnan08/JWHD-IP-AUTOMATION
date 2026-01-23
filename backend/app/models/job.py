from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime
from app.models.common import MongoBaseModel, PyObjectId

class JobType(str, Enum):
    ADS_EXTRACTION = "ads_extraction"
    OFFICE_ACTION_PARSING = "office_action_parsing"
    VALIDATION = "validation"

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ProcessingJobBase(BaseModel):
    job_type: JobType
    status: JobStatus = JobStatus.PENDING
    progress_percentage: int = 0
    error_details: Optional[str] = None
    input_references: List[PyObjectId] = []
    output_references: List[PyObjectId] = []

class ProcessingJobCreate(ProcessingJobBase):
    user_id: PyObjectId

class ProcessingJobInDB(MongoBaseModel, ProcessingJobBase):
    user_id: PyObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

class ProcessingJobResponse(MongoBaseModel, ProcessingJobBase):
    user_id: str
    input_references: List[str] = []
    output_references: List[str] = []
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None