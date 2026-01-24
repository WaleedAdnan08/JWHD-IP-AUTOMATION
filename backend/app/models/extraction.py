from dataclasses import dataclass
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel

class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class DocumentQuality(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"

class ExtractionMetadata(BaseModel):
    page_count: int = 0
    overall_confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    document_quality: DocumentQuality = DocumentQuality.GOOD
    has_handwriting: bool = False
    extraction_notes: Optional[str] = None
    file_size_bytes: int = 0
    mime_type: str = "application/pdf"
    is_chunked: bool = False
    chunk_count: Optional[int] = None
    successful_chunks: Optional[int] = None
    failed_chunks: Optional[int] = None
    uncertain_count: int = 0
    illegible_count: int = 0

class ExtractionResult(BaseModel):
    extracted_text: str
    metadata: ExtractionMetadata