export interface PriorArtReference {
  reference_type: string;
  identifier: string;
  title?: string;
  date?: string;
  relevant_claims: string[];
  citation_details?: string;
}

export interface Rejection {
  rejection_type: string;
  statutory_basis?: string;
  affected_claims: string[];
  examiner_reasoning: string;
  cited_prior_art: PriorArtReference[];
  relevant_claim_language?: string;
  page_number?: string;
}

export interface ClaimStatus {
  claim_number: string;
  status: string;
  dependency_type: string;
  parent_claim?: string;
}

export interface Objection {
  objected_item: string;
  reason: string;
  corrective_action?: string;
  page_number?: string;
}

export interface ExaminerStatement {
  statement_type: string;
  content: string;
  page_number?: string;
}

export interface OfficeActionHeader {
  application_number?: string;
  filing_date?: string;
  patent_office: string;
  office_action_date?: string;
  office_action_type?: string;
  examiner_name?: string;
  art_unit?: string;
  attorney_docket_number?: string;
  confirmation_number?: string;
  response_deadline?: string;
  // New enhanced fields
  first_named_inventor?: string;
  applicant_name?: string;
  title_of_invention?: string;
  customer_number?: string;
  examiner_phone?: string;
  examiner_email?: string;
  examiner_type?: string;
}

export interface OfficeActionData {
  header: OfficeActionHeader;
  claims_status: ClaimStatus[];
  rejections: Rejection[];
  objections: Objection[];
  other_statements: ExaminerStatement[];
  prosecution_history_summary?: string;
}

export interface JobStatus {
  status: string;
  progress_percentage: number;
  error_details?: string;
}