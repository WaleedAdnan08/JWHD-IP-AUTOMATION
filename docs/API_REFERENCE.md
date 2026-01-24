# API Reference

This document provides a reference for the key API endpoints in the JWHD IP Automation backend.

**Base URL:** `http://localhost:8000/api/v1` (Local Development)

## Authentication

### Login (Seed User / Testing)

Retrieves an access token for authenticated requests. Note: For this phase, we are primarily using a seed user.

*   **URL:** `/auth/login`
*   **Method:** `POST`
*   **Content-Type:** `application/x-www-form-urlencoded`

**Request Body:**

| Field | Type | Description |
| :--- | :--- | :--- |
| `username` | `string` | User email (e.g., `test@example.com`) |
| `password` | `string` | User password (e.g., `password123`) |

**Response Body:**

```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

**Curl Example:**

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -d "username=test@example.com&password=password123"
```

---

## Applications

### Analyze Application (PDF)

Uploads a PDF application file, extracts text, and analyzes it using Gemini to identify metadata and inventors.

*   **URL:** `/applications/analyze`
*   **Method:** `POST`
*   **Content-Type:** `multipart/form-data`

**Request Body:**

| Field | Type | Description |
| :--- | :--- | :--- |
| `file` | `file` | The PDF application file to analyze. |

**Response Body:**

```json
{
  "title": "string",
  "application_number": "string",
  "filing_date": "string",
  "entity_status": "string",
  "inventors": [
    {
      "first_name": "string",
      "last_name": "string",
      "city": "string",
      "country": "string"
      // ... other inventor fields
    }
  ],
  "extraction_confidence": 0.95
}
```

**Curl Example:**

```bash
curl -X POST "http://localhost:8000/api/v1/applications/analyze" \
     -H "Authorization: Bearer <YOUR_TOKEN>" \
     -F "file=@/path/to/your/application.pdf"
```

### Parse CSV (Inventors)

Parses a CSV file containing inventor information.

*   **URL:** `/applications/parse-csv`
*   **Method:** `POST`
*   **Content-Type:** `multipart/form-data`

**Request Body:**

| Field | Type | Description |
| :--- | :--- | :--- |
| `file` | `file` | The CSV file containing inventor data. |

**Response Body:**

A list of inventor objects.

```json
[
  {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com"
    // ...
  }
]
```

**Curl Example:**

```bash
curl -X POST "http://localhost:8000/api/v1/applications/parse-csv" \
     -H "Authorization: Bearer <YOUR_TOKEN>" \
     -F "file=@/path/to/inventors.csv"
```

### Generate ADS

Generates an Application Data Sheet (ADS) document based on the provided metadata.

*   **URL:** `/applications/generate-ads`
*   **Method:** `POST`
*   **Content-Type:** `application/json`

**Request Body:**

A JSON object matching the `PatentApplicationMetadata` schema (see Analyze Application response).

```json
{
  "title": "Invention Title",
  "inventors": [...]
  // ... other metadata
}
```

**Response Body:**

Returns URLs or paths to the generated documents.

```json
{
  "docx_url": "https://storage.googleapis.com/...",
  "pdf_url": "https://storage.googleapis.com/..."
}
```

**Curl Example:**

```bash
curl -X POST "http://localhost:8000/api/v1/applications/generate-ads" \
     -H "Authorization: Bearer <YOUR_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{
           "title": "Test Invention",
           "inventors": [{"first_name": "John", "last_name": "Doe"}]
         }'
```

---

## Documents

### Upload Document

Uploads a generic document (e.g., Office Action, Reference) to the system.

*   **URL:** `/documents/upload`
*   **Method:** `POST`
*   **Content-Type:** `multipart/form-data`

**Request Body:**

| Field | Type | Description |
| :--- | :--- | :--- |
| `file` | `file` | The file to upload. |
| `document_type` | `string` | Type of document (e.g., `office_action`, `assignment`). |

**Response Body:**

```json
{
  "id": "string",
  "filename": "string",
  "document_type": "string",
  "upload_date": "2023-10-27T10:00:00Z"
}
```

**Curl Example:**

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
     -H "Authorization: Bearer <YOUR_TOKEN>" \
     -F "file=@/path/to/doc.pdf" \
     -F "document_type=office_action"
```

### Get Download URL

Retrieves a signed URL to download a specific document.

*   **URL:** `/documents/{document_id}/url`
*   **Method:** `GET`

**Response Body:**

```json
{
  "url": "https://storage.googleapis.com/...",
  "expires_at": "2023-10-27T11:00:00Z"
}
```

---

## Jobs

### Get Job Status

Checks the status of a long-running background job (e.g., validation, complex extraction).

*   **URL:** `/jobs/{job_id}`
*   **Method:** `GET`

**Response Body:**

```json
{
  "id": "string",
  "job_type": "validation",
  "status": "processing", // or "completed", "failed"
  "progress_percentage": 45,
  "created_at": "..."
}