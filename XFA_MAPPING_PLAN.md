# XFA XML Mapping Plan for USPTO ADS

## Objective
Map unstructured `PatentApplicationMetadata` (Source Data) into a strict XFA XML Schema extracted from the official USPTO PDF (`../Client attachments/Original ADS from USPTO Website.pdf`) without breaking the file structure.

## Context
The USPTO ADS form uses Adobe XFA (XML Forms Architecture). To fill it programmatically (and correctly), we cannot just fill AcroForm fields; we often need to inject a specific XML dataset into the PDF's XFA structure. The user requires generating this **raw, valid XML string** strictly following the extracted schema.

## Execution Steps

### 1. Schema Extraction & Analysis
*   **Action:** Create a script (`inspect_xfa.py`) to read `../Client attachments/Original ADS from USPTO Website.pdf`.
*   **Goal:** Access the `XFA` dictionary from the PDF.
*   **Output:** Identify the correct XFA key that holds the data structure (usually `datasets`, `template`, or `form`). Extract this empty structure as the **TARGET XML SCHEMA**.
*   **Verification:** Ensure namespaces (`xmlns:xfa`, etc.) and tag hierarchy are preserved.

### 2. Implementation Strategy
*   **File:** Create/Update `backend/app/services/xml_mapper.py` (or similar).
*   **Class:** `XFAMapper`
*   **Method:** `map_metadata_to_xml(metadata: PatentApplicationMetadata, schema_template: str) -> str`

### 3. Mapping Logic (Strict Rules)
*   **Immutable Structure:** Load the empty XML schema as a template (e.g., using `lxml` or string replacement if simple enough, but `lxml` is safer for structure).
*   **Repeating Groups:**
    *   Identify the repeating block for **Inventors**.
    *   If `metadata.inventors` has $N$ items, clone the schema's inventor block $N$ times.
    *   Populate each block with the corresponding inventor data.
*   **Data Formatting:**
    *   Dates: `YYYY-MM-DD`.
    *   Booleans: Convert "0"/"Off"/"False" -> "1"/"On"/"True" based on schema default.
    *   Escaping: Ensure values like `AT&T` become `AT&T`.

### 4. Output
*   Return the raw XML string.
*   No Markdown formatting.
*   No extra whitespace/conversational text.

### 5. Testing
*   Create a test script `tests/test_xfa_generation.py`.
*   Use dummy `PatentApplicationMetadata`.
*   Generate XML.
*   (Optional but recommended) Try to inject this XML back into a PDF to verify it renders correctly (if tools allow), or at least validate it against the extracted XFA schema structure.

## Next Steps
1.  **Switch to Code Mode**.
2.  Run the inspection script to get the Schema.
3.  Implement the mapping logic.
4.  Verify the output.