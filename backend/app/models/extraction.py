from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Provenance(BaseModel):
    source_page: int
    source_section: Optional[str] = None
    source_paragraph: Optional[str] = None
    text_coordinates: Optional[List[float]] = None

class Inventor(BaseModel):
    name: str
    address: str
    citizenship: str
    provenance: Provenance
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM

class Rejection(BaseModel):
    rejection_type: str
    claims: List[str]
    reasoning: str
    prior_art_cited: List[str]
    provenance: Provenance
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM

class PriorArt(BaseModel):
    reference_type: str
    identifier: str
    title: Optional[str] = None
    date: Optional[str] = None
    relevant_claims: List[str]
    provenance: Provenance
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM

class Claim(BaseModel):
    claim_number: int
    text: str
    dependencies: List[int]
    provenance: Provenance
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM

class ExtractionResult(BaseModel):
    application_title: Optional[str] = None
    inventors: List[Inventor] = Field(default_factory=list)
    rejections: List[Rejection] = Field(default_factory=list)
    prior_arts: List[PriorArt] = Field(default_factory=list)
    claims: List[Claim] = Field(default_factory=list)
    raw_text: str
    schema_version: str = "1.0.0"
