# Phase 2: XFA Injection & File Delivery Plan

## Objective
Implement the Injection Layer and Delivery Layer to inject the generated XFA XML into the USPTO PDF template and serve it directly to the client via an API endpoint, using `pikepdf` for in-memory manipulation.

## Technical Requirements
*   **Library:** `pikepdf` (Must be added to `backend/requirements.txt`).
*   **Memory Management:** Use `io.BytesIO` for all PDF operations. No disk writes.
*   **Browser Handling:** Force download via `Content-Disposition: attachment`.

## Implementation Steps

### 1. Dependency Management
*   **Action:** Add `pikepdf` to `backend/requirements.txt`.

### 2. The Injection Service (`backend/app/services/pdf_injector.py`)
*   **Class:** `PDFInjector`
*   **Method:** `inject_xml(template_path: str, xml_data: str) -> io.BytesIO`
*   **Logic:**
    1.  Open template using `pikepdf.Pdf.open(template_path)`.
    2.  Access `pdf.Xfa`.
    3.  Update the `datasets` key in `pdf.Xfa` with the encoded XML data.
        *   Note: `pikepdf` handles XFA as a dictionary-like object where keys are stream names.
    4.  Save to `io.BytesIO`.
    5.  Return the stream.

### 3. The API Endpoint (`backend/app/api/endpoints/applications.py`)
*   **Route:** `POST /applications/generate-pdf` (or similar, maybe replace or augment existing `generate-ads`).
*   **Flow:**
    1.  Accept `PatentApplicationMetadata`.
    2.  Call `XFAMapper.map_metadata_to_xml(data)`.
    3.  Call `PDFInjector.inject_xml(template_path, xml_string)`.
    4.  Return `StreamingResponse` (from `fastapi.responses`) with:
        *   `content=stream`
        *   `media_type="application/pdf"`
        *   `headers={"Content-Disposition": 'attachment; filename="ads_filled.pdf"'}`

### 4. Validation
*   **Script:** `tests/verify_xfa_injection.py`
    *   Manually calls Mapper -> Injector.
    *   Writes output to `test_output_ads.pdf` on disk (only for verification).
    *   Developer checks if it opens in Adobe Reader.

## Next Steps
1.  Switch to Code Mode.
2.  Add `pikepdf` to requirements.
3.  Implement `PDFInjector`.
4.  Update API endpoint.
5.  Create verification script.