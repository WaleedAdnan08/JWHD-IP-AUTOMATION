# PRODUCT REQUIREMENTS DOCUMENT

**EXECUTIVE SUMMARY**

*   **Product Vision:** To create an intelligent automation platform that eliminates manual data entry for patent paralegals, starting with the core document ingestion and processing capabilities.
*   **Core Purpose:** This phase aims to transform unstructured legal documents (such as Cover Sheets, Declarations, Office Actions, and CSV files) into structured, machine-readable data. This will serve as the foundation for future automation workflows, such as ADS generation and Office Action responses.
*   **Target Users:** Patent paralegals at JWHD, who currently spend a significant amount of time manually extracting information from patent application materials.
*   **Key Features:**
    *   Document Upload and Management
    *   AI-Powered Data Extraction from various document types
    *   Centralized Dashboard for monitoring document processing status
    *   Manual Review and Correction interface for quality assurance
*   **Complexity Assessment:** Moderate
    *   **State Management:** Local
    *   **External Integrations:** 2 (LLM API, GCP Cloud Storage)
    *   **Business Logic:** Moderate
    *   **Data Synchronization:** None
*   **MVP Success Metrics:**
    *   Users can successfully upload documents and see them processed.
    *   The system can extract key data points from supported document types with a high degree of accuracy.
    *   The core workflow, from document upload to data review, is functional and intuitive.

**1. USERS & PERSONAS**

*   **Primary Persona:**
    *   **Name:** Pat the Paralegal
    *   **Context:** Works at a busy patent law firm, juggling multiple patent applications at once. Spends a significant portion of the day on tedious, manual data entry tasks.
    *   **Goals:** To reduce the time spent on manual data entry, minimize the risk of human error, and focus on higher-value paralegal work.
    *   **Needs:** A reliable system that can automatically and accurately extract information from various patent-related documents.

**2. FUNCTIONAL REQUIREMENTS**

*   **2.1 User-Requested Features (All are Priority 0)**

    *   **FR-001: Document Upload and Management**
        *   **Description:** Users can upload various types of patent-related documents (PDF, DOCX, CSV) into the system. The system will validate the files and store them securely.
        *   **Entity Type:** User-Generated Content
        *   **User Benefit:** A centralized and secure location for all patent application documents, with an easy-to-use upload interface.
        *   **Primary User:** Pat the Paralegal
        *   **Lifecycle Operations:**
            *   **Create:** Upload new documents.
            *   **View:** View uploaded documents and their processing status.
            *   **Delete:** Delete uploaded documents.
            *   **List/Search:** Find and browse uploaded documents.
        *   **Acceptance Criteria:**
            *   - [ ] Given a user is authenticated, they can upload PDF, DOCX, and CSV files up to 50MB.
            *   - [ ] The system validates file types and sizes, providing clear error messages for invalid files.
            *   - [ ] Uploaded files are stored securely in GCP Cloud Storage.
            *   - [ ] The user can see a list of their uploaded documents with their current processing status.

    *   **FR-002: AI-Powered Data Extraction**
        *   **Description:** The system uses an LLM to automatically extract structured data from uploaded documents, including Cover Sheets, Declarations, Office Actions, and CSV files.
        *   **Entity Type:** System-Generated Data
        *   **User Benefit:** Eliminates the need for manual data entry, saving significant time and reducing the risk of errors.
        *   **Primary User:** Pat the Paralegal
        *   **Lifecycle Operations:**
            *   **Create:** The system automatically initiates the extraction process upon document upload.
            *   **View:** Users can view the extracted data in a structured format.
        *   **Acceptance Criteria:**
            *   - [ ] The system correctly identifies the document type and applies the appropriate extraction logic.
            *   - [ ] Key data points are extracted with a high degree of accuracy (over 90%).
            *   - [ ] The system can handle digital documents.

    *   **FR-003: Document Processing Status Dashboard**
        *   **Description:** A centralized dashboard that provides real-time status updates for all document processing jobs.
        *   **Entity Type:** System Data
        *   **User Benefit:** Provides transparency into the document processing pipeline, allowing users to track the progress of their uploads.
        *   **Primary User:** Pat the Paralegal
        *   **Lifecycle Operations:**
            *   **View:** Users can view the status of all active and completed jobs.
            *   **List/Search:** Users can filter and search for specific jobs.
        *   **Acceptance Criteria:**
            *   - [ ] The dashboard displays the document name, type, and status (queued, processing, complete, failed).
            *   - [ ] The dashboard provides a preview of the extracted data for completed jobs.
            *   - [ ] Low-confidence extractions are flagged for manual review.

    *   **FR-005: Rejection Analysis Service**
        *   **Description:** The service must identify and extract all instances of §101, §102, §103, and §112 rejections from Office Action documents, including the affected claims, the examiner's reasoning, and any cited prior art for each specific rejection.
        *   **Entity Type:** System-Generated Data
        *   **User Benefit:** Provides a structured, immediate, and precise overview of all legal grounds for rejection, enabling paralegals to quickly triage and prepare for the necessary response without manually searching through the document.
        *   **Primary User:** Pat the Paralegal
        *   **Lifecycle Operations:**
            *   **Create:** The system automatically runs this analysis on documents identified as Office Actions.
            *   **View:** Users can view the structured rejection analysis as part of the extracted data for an Office Action.
        *   **Acceptance Criteria:**
            *   - [ ] Given an Office Action document, the system correctly identifies and lists all §101 rejections with their corresponding claims and reasoning.
            *   - [ ] Given an Office Action document, the system correctly identifies and lists all §102 rejections with their corresponding claims, reasoning, and cited prior art.
            *   - [ ] Given an Office Action document, the system correctly identifies and lists all §103 rejections with their corresponding claims, reasoning, and cited prior art.
            *   - [ ] Given an Office Action document, the system correctly identifies and lists all §112 rejections with their corresponding claims and reasoning.

    *   **FR-006: Cross-Document Name Validation Service**
        *   **Description:** The service validates inventor and applicant names by comparing them across all uploaded documents within a single application package (e.g., Cover Sheet, Declaration). This service is a core MVP feature, vital for preventing common USPTO rejections related to name discrepancies on the ADS.
        *   **Entity Type:** System-Generated Data
        *   **User Benefit:** Proactively catches and flags inconsistencies in names, preventing costly and time-consuming office actions from the USPTO.
        *   **Primary User:** Pat the Paralegal
        *   **Lifecycle Operations:**
            *   **Create:** The system automatically performs validation once all initial documents for an application are processed.
            *   **View:** Users are alerted to any detected name discrepancies on the dashboard.
        *   **Acceptance Criteria:**
            *   - [ ] Given a set of documents for an application, the system identifies and flags any variations in inventor or applicant names.
            *   - [ ] The system presents the inconsistencies to the user in a clear and understandable format.

*   **2.2 Essential Market Features**
 
    *   **FR-007: User Authentication**
        *   **Description:** Secure user login and session management to protect user data.
        *   **Entity Type:** Configuration/System
        *   **User Benefit:** Ensures that only authorized users can access the system and their documents.
        *   **Primary User:** All personas
        *   **Lifecycle Operations:**
            *   **Create:** Register a new account.
            *   **View:** View profile information.
            *   **Edit:** Update profile and preferences.
            *   **Delete:** Delete their account.
        *   **Acceptance Criteria:**
            *   - [ ] Users can securely log in with a username and password.
            *   - [ ] The system provides a password reset functionality.
            *   - [ ] User sessions are managed securely.

**3. USER WORKFLOWS**

*   **3.1 Primary Workflow: Document Ingestion and Review**
    *   **Trigger:** A paralegal needs to process a new set of patent application documents.
    *   **Outcome:** The paralegal has uploaded the documents, the system has extracted the relevant data, and the paralegal can review the extracted data for accuracy.
    *   **Steps:**
        1.  User logs into the system.
        2.  User navigates to the Document Upload Interface.
        3.  User selects and uploads the relevant documents (Cover Sheet, Declaration, etc.).
        4.  The system validates the files and begins the asynchronous extraction process.
        5.  User navigates to the Document Processing Status Dashboard to monitor the progress.
        6.  Once processing is complete, the user can view the extracted data.
        7.  If any extractions are flagged as low-confidence, the user navigates to the Manual Correction & Re-extraction Interface to review and correct the data.

**4. BUSINESS RULES**

*   **Access Control:**
    *   Only authenticated users can upload and view documents.
*   **Data Rules:**
    *   All uploaded documents are considered sensitive and must be stored securely.
    *   The original uploaded files are immutable and cannot be edited.

**5. DATA REQUIREMENTS**

*   **Core Entities:**
    *   **User:**
        *   **Type:** System/Configuration
        *   **Attributes:** user_id, email, name, password_hash
    *   **Document:**
        *   **Type:** User-Generated Content
        *   **Attributes:** document_id, file_name, file_type, upload_timestamp, processing_status, user_id
    *   **ExtractedData:**
        *   **Type:** System-Generated Data
        *   **Attributes:** data_id, document_id, extracted_fields (JSON blob), confidence_scores

**6. INTEGRATION REQUIREMENTS**

*   **External Systems:**
    *   **OpenAI API or Anthropic Claude API:** For LLM-based document parsing.
    *   **GCP Cloud Storage:** For secure document storage.

**7. FUNCTIONAL VIEWS/AREAS**

*   **Primary Views:**
    *   **Document Upload Interface:** For uploading new documents.
    *   **Document Processing Status Dashboard:** For monitoring the status of document processing jobs.
    *   **Extraction Review & Correction Interface:** For reviewing and correcting low-confidence extractions.

**8. MVP SCOPE & DEFERRED FEATURES**

*   **8.1 MVP Success Definition**
    *   The core workflow of uploading a document, having the system extract the data, and being able to review the extracted data is fully functional.
*   **8.2 In Scope for MVP**
    *   FR-001: Document Upload and Management
    *   FR-002: AI-Powered Data Extraction
    *   FR-003: Document Processing Status Dashboard
    *   FR-004: Rejection Analysis Service
    *   FR-005: Cross-Document Name Validation Service
    *   FR-006: User Authentication
*   **8.3 Deferred Features (Post-MVP Roadmap)**
    *   **DF-001: ADS Generation**
        *   **Description:** Automatically generates Application Data Sheets (ADS) from the extracted data.
        *   **Reason for Deferral:** This is a downstream workflow that depends on the core extraction functionality. It is a logical next step after the MVP is validated.
    *   **DF-002: Office Action Response Automation**
        *   **Description:** Automatically generates response templates for Office Actions.
        *   **Reason for Deferral:** Similar to ADS generation, this is a downstream workflow that builds upon the core extraction capabilities.

**9. ASSUMPTIONS & DECISIONS**

*   **Key Assumptions Made:**
    *   The primary pain point for the target users is the manual extraction of data from documents.
    *   An LLM-based approach will be more flexible and robust than a traditional rule-based extraction system.
*   **Questions Asked & Answers:** None. The provided PRD was clear and unambiguous.