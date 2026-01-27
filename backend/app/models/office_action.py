from pydantic import BaseModel
from typing import List
from app.models.common import MongoBaseModel

class PriorArtReference(BaseModel):
    reference_type: str
    identifier: str
    title: str
    date: str
    relevant_claims: List[str]

class Rejection(BaseModel):
    rejection_type: str
    affected_claims: List[str]
    examiner_reasoning: str
    cited_prior_art: List[PriorArtReference]

class OfficeActionHeader(BaseModel):
    examiner_name: str
    art_unit: str
    application_number: str
    filing_date: str
    mailing_date: str
    confirmation_number: str

class OfficeActionExtractedData(MongoBaseModel):
    header: OfficeActionHeader
    rejections: List[Rejection]
    prosecution_stage: str