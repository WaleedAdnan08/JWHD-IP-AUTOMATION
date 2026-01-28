from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.common import MongoBaseModel

class PriorArtReference(BaseModel):
    reference_type: str  # e.g., "US Patent", "Foreign Patent", "NPL"
    identifier: str      # e.g., "US 1234567 A"
    title: Optional[str] = None
    date: Optional[str] = None
    relevant_claims: List[str] = []
    citation_details: Optional[str] = None

class Rejection(BaseModel):
    rejection_type: str # e.g., "102", "103", "112"
    statutory_basis: Optional[str] = None # e.g., "35 U.S.C. 103"
    affected_claims: List[str] = []
    examiner_reasoning: str
    cited_prior_art: List[PriorArtReference] = []
    relevant_claim_language: Optional[str] = None
    page_number: Optional[str] = None

class ClaimStatus(BaseModel):
    claim_number: str
    status: str # e.g., "Rejected", "Allowed", "Objected to", "Cancelled", "Withdrawn"
    dependency_type: str # "Independent" or "Dependent"
    parent_claim: Optional[str] = None # If dependent

class Objection(BaseModel):
    objected_item: str # e.g., "Drawings", "Specification", "Claim 1"
    reason: str
    corrective_action: Optional[str] = None
    page_number: Optional[str] = None

class ExaminerStatement(BaseModel):
    statement_type: str # e.g., "Allowable Subject Matter", "Suggestion", "Interview Summary"
    content: str
    page_number: Optional[str] = None

class OfficeActionHeader(BaseModel):
    application_number: Optional[str] = None
    filing_date: Optional[str] = None
    patent_office: str = "USPTO" # Default to USPTO
    office_action_date: Optional[str] = None # Mailing date
    office_action_type: Optional[str] = None # e.g., "Non-Final", "Final"
    examiner_name: Optional[str] = None
    art_unit: Optional[str] = None
    attorney_docket_number: Optional[str] = None
    confirmation_number: Optional[str] = None
    response_deadline: Optional[str] = None

class OfficeActionExtractedData(MongoBaseModel):
    header: OfficeActionHeader
    claims_status: List[ClaimStatus] = Field(default_factory=list)
    rejections: List[Rejection] = Field(default_factory=list)
    objections: List[Objection] = Field(default_factory=list)
    other_statements: List[ExaminerStatement] = Field(default_factory=list)
    prosecution_history_summary: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "header": {
                    "application_number": "12/345,678",
                    "office_action_date": "2023-01-01",
                    "office_action_type": "Non-Final",
                    "response_deadline": "2023-04-01"
                },
                "claims_status": [
                    {"claim_number": "1", "status": "Rejected", "dependency_type": "Independent"}
                ],
                "rejections": [
                    {
                        "rejection_type": "103",
                        "affected_claims": ["1"],
                        "examiner_reasoning": "Claim 1 is obvious over Smith in view of Jones.",
                        "cited_prior_art": []
                    }
                ]
            }
        }