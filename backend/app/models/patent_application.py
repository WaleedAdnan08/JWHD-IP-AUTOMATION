from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from app.models.common import MongoBaseModel, PyObjectId

class WorkflowStatus(str, Enum):
    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    GENERATED = "generated"
    DOWNLOADED = "downloaded"

class Inventor(BaseModel):
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    suffix: Optional[str] = None
    name: Optional[str] = None  # Full name for backward compatibility or display
    street_address: Optional[str] = None # mailing_address
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    citizenship: Optional[str] = None
    extraction_confidence: Optional[float] = None

class Applicant(BaseModel):
    name: Optional[str] = None
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None

class PatentApplicationMetadata(BaseModel):
    title: Optional[str] = None
    application_number: Optional[str] = None
    filing_date: Optional[str] = None  # Keep as string for extraction, convert later
    entity_status: Optional[str] = None
    inventors: List[Inventor] = []
    applicant: Optional[Applicant] = None
    total_drawing_sheets: Optional[int] = None
    extraction_confidence: Optional[float] = None
    debug_reasoning: Optional[str] = Field(None, alias="_debug_reasoning")

class PatentApplicationBase(BaseModel):
    application_number: Optional[str] = None
    title: Optional[str] = None
    entity_status: Optional[str] = None
    filing_date: Optional[datetime] = None
    inventors: List[Inventor] = []
    applicant: Optional[Applicant] = None
    total_drawing_sheets: Optional[int] = None
    workflow_status: WorkflowStatus = WorkflowStatus.UPLOADED

class PatentApplicationCreate(PatentApplicationBase):
    source_document_ids: List[PyObjectId] = []

class PatentApplicationInDB(MongoBaseModel, PatentApplicationBase):
    source_document_ids: List[PyObjectId] = []
    generated_document_ids: List[PyObjectId] = []
    created_by: PyObjectId
    updated_by: Optional[PyObjectId] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class PatentApplicationResponse(MongoBaseModel, PatentApplicationBase):
    source_document_ids: List[str] = []
    generated_document_ids: List[str] = []
    created_by: str
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime