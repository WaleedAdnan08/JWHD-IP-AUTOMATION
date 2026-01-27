# Project Blueprint: JWHD IP Automation Platform

## Phase 1: High-Level Architectural Decisions

### 1.1. Architecture Pattern Selection

**Decision:** Modular Monolith

**Rationale:** A modular monolith is the optimal choice for this project. It supports a single developer's productivity by simplifying the development environment, deployment, and testing processes. The features described in the PRD are part of a single, cohesive business domain (patent document processing) and do not present any compelling technical reasons—such as disparate runtimes or extreme differences in resource requirements—to justify the added complexity of a microservices architecture.

### 1.2. Technology Stack Selection

The technology stack is selected to prioritize developer productivity, performance, and modern best practices. All versions listed are the latest stable releases.

**Frontend Framework & UI:**

*   **Framework:** Next.js
*   **Version:** ~15.4
*   **Rationale:** Next.js offers a powerful, production-ready framework for building modern React applications. The App Router provides superior data fetching and layout capabilities, which will be essential for creating the dashboard and document management interfaces.
*   **UI Components:** shadcn/ui
*   **Version:** ~0.9.5
*   **Rationale:** shadcn/ui provides a set of unstyled, accessible components that can be easily customized to fit the project's specific design requirements without being locked into a rigid design system.

**Backend Runtime & Framework:**

*   **Runtime:** Python
*   **Version:** ~3.13
*   **Rationale:** Python's extensive libraries for data processing and strong community support make it an excellent choice for the backend.
*   **Framework:** FastAPI
*   **Version:** ~0.116.1
*   **Rationale:** FastAPI is a high-performance Python framework that simplifies the creation of robust APIs. Its automatic data validation and interactive documentation will accelerate backend development.

**Primary Database:**

*   **Database:** MongoDB Atlas (Free Tier)
*   **Rationale:** A NoSQL document database like MongoDB offers the flexibility needed for an agile project where data models may evolve. It maps naturally to Python objects, simplifying data access logic. The free tier provides sufficient resources for development and initial deployment.

### 1.3. Core Infrastructure & Services (Local Development Focus)

*   **Local Development:** The project will be run via simple command-line instructions (`npm run dev` for frontend, `uvicorn main:app --reload` for backend). No containerization is necessary for local setup.
*   **File Storage:** A local file system directory (`./uploads`), which will be git-ignored, will be used for temporary storage of uploaded documents before they are processed and sent to GCP Cloud Storage.
*   **Job Queues:** Celery will be used for managing asynchronous background tasks, such as AI-powered data extraction, ensuring the user interface remains responsive. The worker will be run in a separate terminal during development.
*   **Authentication:** Authentication will be implemented using JSON Web Tokens (JWTs), a standard and lightweight method for securing APIs within a monolithic application.
*   **External Services:**
    *   **Google Cloud Platform (GCP) Cloud Storage:** For secure, persistent storage of all uploaded documents.
    *   **Large Language Model (LLM) API:** An API for a service like OpenAI or Anthropic Claude will be used for the AI-powered data extraction and analysis.

### 1.4. Integration and API Strategy

*   **API Style:** A versioned REST API (e.g., `/api/v1/...`) will be implemented to ensure a stable contract between the frontend and backend.
*   **Standard Formats:** All API responses will use a standardized JSON structure for both successful responses and errors to ensure consistency.

## Phase 2: Detailed Module Architecture

### 2.1. Module Identification

The application will be broken down into the following logical, domain-driven modules:

*   **UserModule:** Manages user authentication, registration, and profile data.
*   **ApplicationModule:** Handles the creation and management of patent application packages, which group related documents.
*   **DocumentModule:** Manages the uploading, processing, and storage of individual documents.
*   **ExtractionModule:** Contains the core logic for AI-powered data extraction from documents.
*   **ValidationModule:** Implements the cross-document name validation service.
*   **RejectionModule:** Implements the rejection analysis service for Office Actions.
*   **SharedModule:** Contains shared utilities, UI components, and data types used across the application.

### 2.2. Module Responsibilities and Contracts

*   **UserModule:**
    *   **Responsibilities:** Handles user registration, login, JWT generation, and management of user data in the database.
    *   **Interface Contract:** Exposes endpoints like `/api/v1/auth/register` and `/api/v1/auth/login`.
*   **DocumentModule:**
    *   **Responsibilities:** Manages file uploads, validation, and storage in GCP Cloud Storage. Tracks document processing status.
    *   **Interface Contract:** Exposes endpoints like `POST /api/v1/documents/upload`.
*   **ExtractionModule:**
    *   **Responsibilities:** Interfaces with the LLM API to extract structured data from documents.
    *   **Interface Contract:** Provides internal services to be called by the `DocumentModule` upon successful upload.

### 2.3. Key Module Design

*   **Folder Structure:** The backend will follow a logical structure (e.g., `/api`, `/services`, `/models`, `/core`). The frontend will be organized by feature (`/app/(dashboard)`, `/app/(auth)`) and shared components (`/components`).
*   **Key Patterns:** The Repository Pattern will be used for data access to decouple business logic from the database implementation.

## Phase 3: Tactical Sprint-by-Sprint Plan

### Sprint S0: Project Foundation & Setup

*   **Project Context:** This project will build the "JWHD IP Automation Platform," a web application designed to automate the manual data entry and analysis tasks of patent paralegals.
*   **Goal:** To establish a fully configured, runnable project skeleton on the local machine with all necessary credentials and basic styling, enabling rapid feature development in subsequent sprints.
*   **Tasks:**
    1.  **Developer Onboarding & Repository Setup:** Ask the developer for the URL of their new, empty GitHub repository.
    2.  **Collect Secrets & Configuration:** Ask for the MongoDB Atlas connection string, GCP service account credentials, LLM API key, and primary/secondary color hex codes for the UI theme.
    3.  **Project Scaffolding:** Create a monorepo with `frontend` and `backend` directories and initialize Git.
    4.  **Backend Setup (Python/FastAPI):** Set up a Python virtual environment, install dependencies (`FastAPI`, `Uvicorn`, `Pydantic`, `python-dotenv`, `google-cloud-storage`, `celery`), and create a basic file structure.
    5.  **Frontend Setup (Next.js & shadcn/ui):** Scaffold the Next.js application, initialize shadcn/ui, and configure `tailwind.config.js` with the provided theme colors.
    6.  **Documentation:** Create a `README.md` file with project context, technology stack, and setup instructions.
    7.  **"Hello World" Verification:** Create a `/api/v1/health` endpoint on the backend and a frontend page to display its status, verifying the frontend-backend and database connections.
    8.  **Final Commit:** After user confirmation of the "Hello World" test, commit the initial project structure and push it to the `main` branch on GitHub.
*   **Verification Criteria:** A developer can clone the repository, run the frontend and backend, see a "Status: ok" message, and the backend successfully connects to MongoDB Atlas. All code is on the `main` branch.

### Sprint S1: User Authentication & Core Document Management

*   **Project Context:** JWHD IP Automation Platform.
*   **Previous Sprint's Accomplishments:** A local development environment is set up and running, with the codebase in a GitHub repository.
*   **Goal:** To implement a secure user registration and login system and the core functionality for uploading and managing documents.
*   **Relevant Requirements:** FR-007 (User Authentication), FR-001 (Document Upload and Management).
*   **Tasks:**
    1.  **Database Model:** Define the `User` and `Document` models.
    2.  **Backend: Auth Logic:** Implement `/api/v1/auth/register` and `/api/v1/auth/login` endpoints and a protected `/api/v1/users/me` route.
    3.  **Frontend: Auth UI & State:** Build login and registration pages and set up global state management for the user session.
    4.  **Backend: Document Upload:** Implement the `POST /api/v1/documents/upload` endpoint to handle file uploads and storage in GCP Cloud Storage.
    5.  **Frontend: Document UI:** Create a file upload component and a dashboard page to list uploaded documents and their statuses.
    6.  **User Test:** Ask the user to perform an end-to-end test: register, log in, upload a document, and see it appear on the dashboard.
    7.  **Final Commit:** Commit all changes with a descriptive message and push to `main`.
*   **Verification Criteria:** A user can register, log in, upload a document, and view its status. The document is securely stored in GCP Cloud Storage.

### Sprint S2: Core MVP - AI Extraction & Cross-Document Validation

*   **Project Context:** JWHD IP Automation Platform.
*   **Previous Sprint's Accomplishments:** User authentication and document upload functionalities are implemented.
*   **Goal:** To implement the core MVP features: AI-powered data extraction from documents and the cross-document name validation service.
*   **Relevant Requirements:** FR-002 (AI-Powered Data Extraction), FR-006 (Cross-Document Name Validation Service).
*   **Tasks:**
    1.  **Backend: Extraction Service:** Create an `ExtractionService` that integrates with the LLM API. Implement logic to process documents asynchronously using Celery.
    2.  **Backend: Name Validation Service:** Create a `ValidationService` that compares inventor and applicant names across all documents within a given application package.
    3.  **Frontend: Display Extracted Data:** Update the dashboard to display the extracted data and any name validation warnings for processed documents.
    4.  **User Test:** Ask the user to upload a set of documents (e.g., Cover Sheet, Declaration) for a single application and verify that the data is extracted correctly and any name discrepancies are flagged.
    5.  **Final Commit:** Commit all changes and push to `main`.
*   **Verification Criteria:** The system can automatically extract data from uploaded documents and flag inconsistencies in inventor/applicant names across related documents.

### Sprint S3: Rejection Analysis Service

*   **Project Context:** JWHD IP Automation Platform.
*   **Previous Sprint's Accomplishments:** The core data extraction and name validation services are functional.
*   **Goal:** To implement the Rejection Analysis Service to extract specific rejection types from Office Action documents.
*   **Relevant Requirements:** FR-005 (Rejection Analysis Service).
*   **Tasks:**
    1.  **Backend: Update Extraction Logic:** Enhance the `ExtractionService` to identify documents as Office Actions and apply specific logic to extract §101, §102, §103, and §112 rejections, including claims, reasoning, and prior art.
    2.  **Database Model:** Update the `ExtractedData` model to store the structured rejection analysis data.
    3.  **Frontend: Display Rejection Analysis:** Update the UI to present the extracted rejection information in a clear, structured format when viewing an Office Action's data.
    4.  **User Test:** Ask the user to upload an Office Action document and verify that all specified rejection types are correctly identified and displayed.
    5.  **Final Commit:** Commit all changes and push to `main`.
*   **Verification Criteria:** The system correctly extracts and displays all §101, §102, §103, and §112 rejections from an Office Action document.