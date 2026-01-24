# Development Plan: JWHD IP Automation

This document outlines the remaining development tasks for the ADS Automation System, structured by logical layers (Backend/Frontend) and project phases.

## 🟢 Phase 1.1: Infrastructure (Completed)
- [x] Monorepo Structure
- [x] Database Connection (MongoDB)
- [x] Authentication System (JWT)
- [x] Frontend Shell & Login UI

---

## 🟢 Phase 1.2: Core Backend Services (Completed)
*Focus: Building the engines that power the application.*

### Backend Tasks
1.  **Object Storage Service (`app/services/storage.py`)**
    - [x] Implement GCS client using `google-cloud-storage`.
    - [x] Methods: `upload_file`, `generate_presigned_url`, `delete_file`.
    - [x] Logic for cleaning up temporary files (24h retention).

2.  **Job Management System (`app/services/jobs.py`)**
    - [x] Create async job runner using `FastAPI BackgroundTasks`.
    - [x] Implement status tracking (Pending -> Processing -> Completed/Failed).
    - [x] Create endpoints: `GET /jobs/{id}` for frontend polling.

3.  **LLM Service Foundation (`app/services/llm.py`)**
    - [x] Initialize Google Gemini client (`google-generativeai`).
    - [x] Implement retry logic with exponential backoff.
    - [x] Create base "structured output" parser for JSON responses.

4.  **Document API (`app/api/endpoints/documents.py`)**
    - [x] `POST /documents/upload`: Handle file upload -> S3 -> MongoDB record.
    - [x] `GET /documents/{id}/url`: Generate download link.

---

## 🟢 Phase 1.3: ADS Logic & Extraction Engines (Completed)
*Focus: The "Brain" - Parsing logic and PDF generation.*

### Backend Tasks
1.  **Text Extraction Service**
    - [x] Implement `pypdf` or `PyPDF2` to read text from uploaded Cover Sheets.
    - [x] Handle encoding issues and whitespace normalization.

2.  **Cover Sheet Parser (LLM)**
    - [x] Design Prompt Templates for Inventor Extraction.
    - [x] Schema: `[Name, Address, Citizenship, Application Title]`.
    - [x] Implement "Function Calling" or JSON mode for strict output.

3.  **CSV Import Handler**
    - [x] Parse uploaded CSVs as an alternative input method.
    - [x] Map columns to the internal `Inventor` model.

4.  **ADS Form Generator**
    - [x] Use `pypdf` or `reportlab` to fill the official USPTO PDF template.
    - [x] Map extracted data to specific PDF form fields.
    - [x] Handle "Continuation Sheets" logic for >10 inventors.

5.  **Application Endpoints (`app/api/endpoints/applications.py`)**
    - [x] CRUD operations for Patent Applications.
    - [x] `POST /applications/{id}/generate-ads`: Trigger PDF creation.

**Phase Notes:**
- Implemented `ADSGenerator` service using `reportlab` for precise PDF generation.
- Integrated `extract_text_from_pdf` using `pypdf`.
- Created `CSVHandler` for robust CSV parsing with fuzzy header matching.
- Developed `LLMService` with Gemini for intelligent cover sheet analysis.
- Exposed all functionality via FastAPI endpoints (`/analyze`, `/parse-csv`, `/generate-ads`).

---

## 🟢 Phase 1.4: Frontend Workflow Implementation (Completed)
*Focus: The "Face" - User Interface and User Experience.*

### Frontend Tasks
1.  **Dashboard Components**
    - [x] **Upload Area:** Drag-and-drop zone with file validation (PDF/CSV).
    - [x] **Progress Tracker:** Visual step indicator (Upload -> Extracting -> Ready).
    - [x] **Inventor Table:** Editable table to view/correct extracted data.

2.  **Page: New Application (`/dashboard/upload`)**
    - [x] Connect to `POST /documents/upload`.
    - [x] Trigger extraction job upon successful upload.

3.  **Page: Processing (`/dashboard/processing/[jobId]`)**
    - [x] Implement polling hook to check `GET /jobs/{id}` every 5s.
    - [x] Auto-redirect to Preview when status is "Completed".
    - [x] Show error messages if failed.

4.  **Page: Preview & Download (`/dashboard/application/[id]`)**
    - [x] Display extracted metadata (Title, Inventor Count).
    - [x] "Download ADS" button linked to presigned URL.
    - [x] "Start Over" button.

**Phase Notes:**
- Implemented `ApplicationWizard` as the central orchestrator for the application flow.
- Created `FileUpload` component supporting both PDF (Analysis) and CSV (Parsing) modes.
- Developed `InventorTable` for dynamic editing of inventor details.
- Integrated Axios for API communication with backend endpoints (`/analyze`, `/parse-csv`, `/generate-ads`).

---

## 🔵 Phase 1.5: Integration Testing & Refinement
*Focus: Ensuring system robustness and reliability.*

1.  **End-to-End Verification**
    *   **Full Flow Test:** Upload PDF -> Extract -> Edit Inventors -> Generate ADS -> Download.
    *   **CSV Flow Test:** Upload CSV -> Parse -> Edit -> Generate ADS.
    *   **Edge Cases:** Verify behavior with invalid files, large files, and network errors.

2.  **Logging & Monitoring**
    *   Add structured JSON logging to Backend.
    *   Track LLM token usage and costs.

3.  **Refinement**
    *   Refine Frontend error toasts/alerts.
    *   Ensure Backend returns clear error codes.

4.  **Documentation**
    *   API Reference (Swagger/OpenAPI).
    *   Deployment Guide.