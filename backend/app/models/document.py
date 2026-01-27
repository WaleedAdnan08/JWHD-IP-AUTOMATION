from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Union, Dict, Any
from datetime import datetime
from app.models.common import MongoBaseModel, PyObjectId
from app.models.extraction import ExtractionResult

class DocumentType(str, Enum):
    COVER_SHEET = "cover_sheet"
    ASSIGNMENT = "assignment"
    DECLARATION = "declaration"
    POWER_OF_ATTORNEY = "power_of_attorney"
    OFFICE_ACTION = "office_action"
    SPECIFICATION = "specification"
    ADS_GENERATED = "ads_generated"

class ProcessedStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class DocumentBase(BaseModel):
    filename: str
    document_type: DocumentType
    file_size: int
    mime_type: str
    storage_key: str
    processed_status: ProcessedStatus = ProcessedStatus.PENDING
    extraction_data: Optional[ExtractionResult] = None

class DocumentCreate(DocumentBase):
    application_id: Optional[PyObjectId] = None
    user_id: PyObjectId

class DocumentInDB(MongoBaseModel, DocumentBase):
    application_id: Optional[PyObjectId] = None
    user_id: PyObjectId
    upload_date: datetime = Field(default_factory=datetime.utcnow)

class DocumentResponse(MongoBaseModel, DocumentBase):
    application_id: Optional[str] = None
    user_id: str
    upload_date: datetime
    # Loosen the type for the response model to handle cases where data is not yet a full ExtractionResult
    extraction_data: Optional[Union[ExtractionResult, Dict[str, Any]]] = None
