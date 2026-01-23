# Development Plan: JWHD IP Automation

This document outlines the remaining development tasks for the ADS Automation System, structured by logical layers (Backend/Frontend) and project phases.

## 🟢 Phase 1.1: Infrastructure (Completed)
- [x] Monorepo Structure
- [x] Database Connection (MongoDB)
- [x] Authentication System (JWT)
- [x] Frontend Shell & Login UI

---

## 🟡 Phase 1.2: Core Backend Services
*Focus: Building the engines that power the application.*

### Backend Tasks
1.  **Object Storage Service (`app/services/storage.py`)**
    *   Implement GCS client using `google-cloud-storage`.
    *   Methods: `upload_file`, `generate_presigned_url`, `delete_file`.
    *   Logic for cleaning up temporary files (24h retention).

2.  **Job Management System (`app/services/jobs.py`)**
    *   Create async job runner using `FastAPI BackgroundTasks`.
    *   Implement status tracking (Pending -> Processing -> Completed/Failed).
    *   Create endpoints: `GET /jobs/{id}` for frontend polling.

3.  **LLM Service Foundation (`app/services/llm.py`)**
    *   Initialize Google Gemini client (`google-generativeai`).
    *   Implement retry logic with exponential backoff.
    *   Create base "structured output" parser for JSON responses.

4.  **Document API (`app/api/endpoints/documents.py`)**
    *   `POST /documents/upload`: Handle file upload -> S3 -> MongoDB record.
    *   `GET /documents/{id}/url`: Generate download link.

---

## 🟠 Phase 1.3: ADS Logic & Extraction Engines
*Focus: The "Brain" - Parsing logic and PDF generation.*

### Backend Tasks
1.  **Text Extraction Service**
    *   Implement `pypdf` or `PyPDF2` to read text from uploaded Cover Sheets.
    *   Handle encoding issues and whitespace normalization.

2.  **Cover Sheet Parser (LLM)**
    *   Design Prompt Templates for Inventor Extraction.
    *   Schema: `[Name, Address, Citizenship, Application Title]`.
    *   Implement "Function Calling" or JSON mode for strict output.

3.  **CSV Import Handler**
    *   Parse uploaded CSVs as an alternative input method.
    *   Map columns to the internal `Inventor` model.

4.  **ADS Form Generator**
    *   Use `pypdf` or `reportlab` to fill the official USPTO PDF template.
    *   Map extracted data to specific PDF form fields.
    *   Handle "Continuation Sheets" logic for >10 inventors.

5.  **Application Endpoints (`app/api/endpoints/applications.py`)**
    *   CRUD operations for Patent Applications.
    *   `POST /applications/{id}/generate-ads`: Trigger PDF creation.

---

## 🔵 Phase 1.4: Frontend Workflow Implementation
*Focus: The "Face" - User Interface and User Experience.*

### Frontend Tasks
1.  **Dashboard Components**
    *   **Upload Area:** Drag-and-drop zone with file validation (PDF/CSV).
    *   **Progress Tracker:** Visual step indicator (Upload -> Extracting -> Ready).
    *   **Inventor Table:** Editable table to view/correct extracted data.

2.  **Page: New Application (`/dashboard/upload`)**
    *   Connect to `POST /documents/upload`.
    *   Trigger extraction job upon successful upload.

3.  **Page: Processing (`/dashboard/processing/[jobId]`)**
    *   Implement polling hook to check `GET /jobs/{id}` every 5s.
    *   Auto-redirect to Preview when status is "Completed".
    *   Show error messages if failed.

4.  **Page: Preview & Download (`/dashboard/application/[id]`)**
    *   Display extracted metadata (Title, Inventor Count).
    *   "Download ADS" button linked to presigned URL.
    *   "Start Over" button.

---

## 🟣 Phase 1.5: Production Readiness
*Focus: Reliability and Documentation.*

1.  **Logging & Monitoring**
    *   Add structured JSON logging to Backend.
    *   Track LLM token usage and costs.

2.  **Error Handling**
    *   Refine Frontend error toasts/alerts.
    *   Ensure Backend returns clear error codes (e.g., `413 Payload Too Large`).

3.  **Documentation**
    *   API Reference (Swagger/OpenAPI).
    *   Deployment Guide (Vercel + Cloud Run/EC2).