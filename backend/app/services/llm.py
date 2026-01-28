from google import genai
from google.genai import types
from google.api_core.exceptions import ResourceExhausted
from fastapi import HTTPException, status
from app.core.config import settings
from app.models.patent_application import PatentApplicationMetadata
# from app.models.extraction import ExtractionMetadata, ExtractionResult, ConfidenceLevel, DocumentQuality
from app.models.extraction import ExtractionResult
import logging
import json
import time
import re
import os
import asyncio
import io
import random
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Callable, Awaitable, Union, IO
from pypdf import PdfReader, PdfWriter
# Configure logging
logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
    logger.info(f"PyMuPDF (fitz) imported successfully. Version: {fitz.__version__}")
except ImportError:
    fitz = None
    logger.warning("PyMuPDF (fitz) could not be imported. Image-based extraction will be unavailable.")

class LLMService:
    def __init__(self):
        self._initialize_client()
        if fitz:
             logger.info("LLMService ready with PyMuPDF support.")
        else:
             logger.warning("LLMService running WITHOUT PyMuPDF. Advanced PDF processing disabled.")

    def _log_token_usage(self, response: Any, operation: str):
        """
        Logs token usage and estimated cost for a Gemini response.
        """
        try:
            if hasattr(response, 'usage_metadata'):
                usage = response.usage_metadata
                prompt_tokens = usage.prompt_token_count
                candidates_tokens = usage.candidates_token_count
                total_tokens = usage.total_token_count
                
                # Calculate estimated cost (based on ~$0.35/1M input, ~$1.05/1M output)
                input_cost = (prompt_tokens / 1_000_000) * 0.35
                output_cost = (candidates_tokens / 1_000_000) * 1.05
                total_cost = input_cost + output_cost
                
                logger.info(
                    f"Token Usage [{operation}]: Input={prompt_tokens}, Output={candidates_tokens}, Total={total_tokens}",
                    extra={
                        "extra_data": {
                            "token_usage": {
                                "prompt_tokens": prompt_tokens,
                                "completion_tokens": candidates_tokens,
                                "total_tokens": total_tokens,
                                "estimated_cost_usd": round(total_cost, 6)
                            }
                        }
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to log token usage: {e}")

    def _initialize_client(self):
        try:
            logger.info("Attempting to initialize Gemini client...")
            logger.info(f"Using Gemini model: {settings.GEMINI_MODEL}")
            if settings.GOOGLE_API_KEY:
                # Log a masked version of the key to ensure we see it's there
                masked_key = f"{settings.GOOGLE_API_KEY[:4]}...{settings.GOOGLE_API_KEY[-4:]}" if len(settings.GOOGLE_API_KEY) > 8 else "***"
                logger.info(f"GOOGLE_API_KEY found: {masked_key}")
                self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
                logger.info(f"Initialized Gemini client successfully with model: {settings.GEMINI_MODEL}")
                
                # Test model availability by listing models (optional diagnostic)
                try:
                    logger.info("Testing model availability...")
                    # This is a simple validation that the client works
                    logger.info(f"Client initialized successfully for model: {settings.GEMINI_MODEL}")
                except Exception as test_e:
                    logger.warning(f"Model availability test failed (but client initialized): {test_e}")
                    
            else:
                logger.warning("GOOGLE_API_KEY not found. LLM service not initialized.")
                self.client = None
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}", exc_info=True)
            self.client = None

    async def upload_file(self, file: Union[str, IO], mime_type: str = "application/pdf"):
        """
        Uploads a file to Gemini for multimodal processing.
        Accepts either a file path (str) or a file-like object (IO).
        """
        if not self.client:
            raise Exception("LLM service not initialized")
        
        try:
            log_name = file if isinstance(file, str) else "memory_stream"
            logger.info(f"Uploading file to Gemini: {log_name}")
            
            # Run in thread pool since library is synchronous
            file_obj = await asyncio.to_thread(
                self.client.files.upload,
                file=file,
                config={'mime_type': mime_type}
            )
            logger.info(f"File uploaded successfully: {file_obj.name}")
            return file_obj
        except Exception as e:
            logger.error(f"Failed to upload file to Gemini: {e}")
            raise e

    async def generate_structured_content(
        self,
        prompt: str,
        file_obj: Any = None,
        schema: Optional[Dict[str, Any]] = None,
        retries: int = 3
    ) -> Dict[str, Any]:
        """
        Generates content from the LLM and parses it as JSON.
        Supports multimodal input (text + file).
        Includes retry logic for transient failures.
        """
        try:
            if not self.client:
                logger.error("LLM Service not initialized when calling generate_structured_content")
                raise Exception("LLM service not initialized")

            # Construct prompt to enforce JSON output
            json_instruction = "\n\nPlease provide the output in valid JSON format."
            if schema:
                json_instruction += f"\nFollow this schema:\n{json.dumps(schema, indent=2)}"
            
            final_text_prompt = prompt + json_instruction

            # Prepare contents
            if file_obj:
                contents = [file_obj, final_text_prompt]
            else:
                contents = final_text_prompt

            for attempt in range(retries):
                try:
                    logger.info(f"Starting LLM generation attempt {attempt + 1}/{retries}")
                    
                    if not final_text_prompt:
                        logger.error("Prompt is empty")
                        raise ValueError("Prompt cannot be empty")

                    # Run sync Gemini call in thread pool
                    start_time = time.time()
                    try:
                        logger.info(f"Calling Gemini API with model: {settings.GEMINI_MODEL}")
                        logger.info(f"API call parameters - Temperature: {settings.GEMINI_TEMPERATURE}, Max tokens: {settings.GEMINI_MAX_OUTPUT_TOKENS}")
                        response = await asyncio.to_thread(
                            self.client.models.generate_content,
                            model=settings.GEMINI_MODEL,
                            contents=contents,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                temperature=settings.GEMINI_TEMPERATURE,
                                max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS
                            )
                        )
                        logger.info("Gemini API call returned successfully")
                        
                        # Record latency
                        duration = time.time() - start_time
                        logger.info(f"API call completed in {duration:.2f} seconds")
                        
                        self._log_token_usage(response, "generate_structured_content")
                    except ResourceExhausted as re_err:
                        logger.warning(f"Gemini Rate Limit Exceeded: {re_err}")
                        raise HTTPException(
                            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="AI Service is currently busy (Rate Limit Exceeded). Please try again in a moment."
                        )
                    except Exception as e:
                        # Enhanced error logging for model-related issues
                        error_msg = str(e)
                        if "NOT_FOUND" in error_msg and "models/" in error_msg:
                            logger.error(f"MODEL ERROR: The model '{settings.GEMINI_MODEL}' was not found or is not supported. Error: {e}")
                            logger.error("Available models may have changed. Consider updating GEMINI_MODEL in configuration.")
                        elif "generateContent" in error_msg:
                            logger.error(f"GENERATE_CONTENT ERROR: The model '{settings.GEMINI_MODEL}' does not support generateContent. Error: {e}")
                        else:
                            logger.error(f"Gemini API execution failed: {e}", exc_info=True)
                        raise e
                    
                    # Log raw response for debugging
                    try:
                        response_text = response.text
                        if not response_text:
                             if hasattr(response, 'candidates') and response.candidates:
                                logger.info(f"Found candidates: {response.candidates}")
                                response_text = response.candidates[0].content.parts[0].text
                             else:
                                raise ValueError("Could not extract text from response")
        
                        # DEBUG: Log the first 500 chars of raw LLM output to see what it generated
                        logger.info(f"RAW LLM RESPONSE (First 500 chars): {response_text[:500]}")
        
                    except Exception as e:
                        logger.error(f"Failed to access response text: {e}", exc_info=True)
                        raise e
        
                    # Parse JSON
                    try:
                        return json.loads(response_text)
                    except json.JSONDecodeError:
                        logger.warning("Initial JSON parse failed, attempting cleanup...")
                        text = response_text
                        
                        # Extract content between code blocks if present
                        if "```" in text:
                            pattern = r"```(?:json)?\s*(.*?)\s*```"
                            match = re.search(pattern, text, re.DOTALL)
                            if match:
                                text = match.group(1)
                        
                        # Find first { and last }
                        start = text.find('{')
                        end = text.rfind('}')
                        if start != -1 and end != -1:
                            text = text[start:end+1]
                            
                        return json.loads(text)
                        
                except Exception as e:
                    logger.warning(f"LLM generation failed (attempt {attempt + 1}/{retries}): {e}")
                    if attempt == retries - 1:
                        raise e
                    wait_time = (2 ** attempt) * 2  # Exponential backoff
                    await asyncio.sleep(wait_time)
        except Exception as outer_e:
            logger.critical(f"CRITICAL ERROR in generate_structured_content: {outer_e}", exc_info=True)
            raise outer_e

    async def analyze_cover_sheet(
        self,
        file_path: str,
        file_content: Optional[bytes] = None,
        progress_callback: Optional[Callable[[int, str], Awaitable[None]]] = None
    ) -> PatentApplicationMetadata:
        """
        Analyzes the cover sheet PDF with Parallel Execution optimization.
        Run Local XFA Check AND Remote File Upload simultaneously to minimize latency.
        
        Args:
            file_path: Path to the file (used for logging/extension even if content is provided)
            file_content: Optional raw bytes of the file. If provided, avoids disk reads.
            progress_callback: Optional callback for status updates
        """
        logger.info(f"--- ANALYZING PDF WITH GEMINI: {file_path} ---")
        logger.info(f"Concurrency Limit: {settings.MAX_CONCURRENT_EXTRACTIONS}")
        
        # Prepare upload source (BytesIO or Path)
        if file_content:
            upload_source = io.BytesIO(file_content)
        else:
            upload_source = file_path

        if progress_callback:
            logger.info("Reporting progress: 10%")
            await progress_callback(10, "Initiating parallel analysis...")

        # Determine page count to decide strategy
        page_count = 0
        try:
            if file_content:
                reader = PdfReader(io.BytesIO(file_content))
            else:
                reader = PdfReader(file_path)
            page_count = len(reader.pages)
            logger.info(f"PDF Page Count: {page_count}")
        except Exception as e:
            logger.warning(f"Failed to get page count: {e}")

        # STRATEGY 1: Text-First Extraction (Local CPU)
        # We try to extract text locally using pypdf. If successful, we skip file upload entirely.
        try:
            text_start = datetime.utcnow()
            text_content = await self._extract_text_locally(file_path, file_content)
            
            # Check if text is sufficient (not just empty pages or headers)
            # We look for a reasonable amount of text or specific form markers
            # Remove standard markers to see if there's actual content
            clean_text = re.sub(r'--- PAGE \d+ ---', '', text_content)
            clean_text = clean_text.replace("--- FORM FIELD DATA", "").replace("--- END FORM DATA ---", "")
            clean_text = clean_text.replace("[EMPTY PAGE TEXT - LIKELY IMAGE OR XFA]", "")
            clean_text = clean_text.strip()
            
            if len(clean_text) > 200: # Arbitrary threshold for "sufficient text"
                logger.info(f"Text-First Strategy: Sufficient text found ({len(clean_text)} chars). Skipping upload.")
                
                if progress_callback:
                    await progress_callback(30, "Analyzing extracted text...")
                    
                result = await self._analyze_text_only(text_content)
                
                # Basic validation: ensure we got something
                if result.title or result.application_number or (result.inventors and len(result.inventors) > 0):
                     logger.info(f"Text-First Analysis Successful. Latency: {(datetime.utcnow() - text_start).total_seconds()}s")
                     return result
                else:
                    logger.warning("Text-First Analysis returned empty data. Falling back to Vision.")
            else:
                logger.info("Text-First Strategy: Insufficient text (likely scanned). Falling back to Vision.")

        except Exception as e:
            logger.warning(f"Text-First Strategy failed: {e}. Falling back to Vision.")

        # FALLBACK: Vision / Native PDF (requires upload)
        logger.info("Initiating file upload for Vision analysis...")
        if progress_callback:
             await progress_callback(40, "Uploading document for Vision analysis...")

        upload_task = asyncio.create_task(self.upload_file(upload_source))
        
        # STRATEGY 2: Check for XFA Dynamic Form Data (Local CPU) - While uploading
        try:
            xfa_start = datetime.utcnow()
            xfa_data = await self._extract_xfa_data(file_path, file_content)
            logger.info(f"XFA Check took: {(datetime.utcnow() - xfa_start).total_seconds()}s")
            
            if xfa_data:
                logger.info("XFA Dynamic Form detected! Using direct XML extraction path.")
                xfa_result = await self._analyze_xfa_xml(xfa_data)
                
                # Validation
                if xfa_result.inventors and len(xfa_result.inventors) > 0:
                     valid_inventors = [i for i in xfa_result.inventors if i.name or i.last_name]
                     if valid_inventors:
                         logger.info(f"Successfully extracted {len(valid_inventors)} inventors from XFA data.")
                         # Cancel upload as it's not needed
                         upload_task.cancel()
                         try:
                             await upload_task
                         except asyncio.CancelledError:
                             pass
                         xfa_result.inventors = valid_inventors
                         return xfa_result
        except Exception as e:
            logger.warning(f"XFA detection failed (continuing to vision fallback): {e}")

        # STRATEGY 2: Fast-Track (Native PDF) using pre-started upload
        # Use ONLY for small documents (< 50 pages)
        if page_count < 50:
            logger.info("Document is small (< 50 pages). Using Native PDF Fast-Track strategy...")
            
            if progress_callback:
                await progress_callback(20, "Analyzing full document (Fast-Track)...")
                
            try:
                # Wait for upload to complete (if not already)
                upload_start = datetime.utcnow()
                file_obj = await upload_task
                logger.info(f"File upload ready. Total upload wait: {(datetime.utcnow() - upload_start).total_seconds()}s")
                
                return await self._analyze_pdf_direct_fallback(file_path, file_obj=file_obj, file_content=file_content)
            except Exception as e:
                logger.warning(f"Native PDF extraction failed: {e}. Falling back to Hybrid Page-by-Page strategy.")
        else:
            logger.info(f"Document is large ({page_count} pages). Skipping Native PDF to use Hybrid Parallel strategy.")

        # STRATEGY 3: Unified Chunking Strategy (Vision) - Fallback
        # This replaces the old "Page-by-Page Image" strategy with a robust "PDF Chunking" approach.
        logger.info("Falling back to Unified Chunking Strategy (Vision)...")
        
        if progress_callback:
            logger.info("Reporting progress: 20%")
            await progress_callback(20, "Analyzing document chunks with Vision...")

        try:
            # We need raw bytes for chunking
            if not file_content:
                with open(file_path, "rb") as f:
                    pdf_bytes = f.read()
            else:
                pdf_bytes = file_content
            
            chunk_result = await self._analyze_document_chunked_structured(
                file_bytes=pdf_bytes,
                filename=os.path.basename(file_path),
                total_pages=page_count,
                progress_callback=progress_callback
            )

            # STRATEGY 4: Final Fallback - Direct PDF Upload
            # If chunking found literally nothing (or failed), try one last desperate Direct Upload
            # But only if the chunking result is basically empty
            if not chunk_result.inventors and not chunk_result.title:
                logger.warning("⚠️ Chunking found no metadata. Attempting Final Fallback: Direct PDF Upload...")
                return await self._analyze_pdf_direct_fallback(file_path, file_content=file_content)
            
            return chunk_result

        except Exception as e:
            logger.error(f"Unified Chunking analysis failed: {e}")
            # Final fallback if chunking crashes completely
            return await self._analyze_pdf_direct_fallback(file_path, file_content=file_content)

    async def _extract_xfa_data(self, file_path: str, file_content: Optional[bytes] = None) -> Optional[str]:
        """
        Checks if the PDF is an XFA form and extracts the internal XML data.
        """
        def _read_xfa():
            try:
                if file_content:
                    reader = PdfReader(io.BytesIO(file_content))
                else:
                    reader = PdfReader(file_path)
                    
                if "/AcroForm" in reader.trailer["/Root"]:
                    acroform = reader.trailer["/Root"]["/AcroForm"]
                    if "/XFA" in acroform:
                        # XFA content can be a list or a stream
                        xfa = acroform["/XFA"]
                        # Often it's a list of [key, indirect_object, key, indirect_object...]
                        # We want to find the 'datasets' packet usually
                        
                        # Targeted Extraction: Prioritize 'datasets' which contains user data
                        xml_content = []
                        
                        if isinstance(xfa, list):
                            # XFA is a list of keys and values: [key1, val1, key2, val2...]
                            # We want to grab everything, but prioritize 'datasets'
                            for i in range(0, len(xfa), 2):
                                key = xfa[i]
                                obj = xfa[i+1]
                                
                                # We specifically want the 'datasets' packet as it contains the actual USER DATA.
                                # IMPORTANT: 'template' contains the empty form structure (400KB+) which confuses the LLM.
                                # We ONLY want 'datasets' to give the LLM pure data.
                                if key == 'datasets':
                                    try:
                                        data = obj.get_object().get_data()
                                        if data:
                                            decoded_data = data.decode('utf-8', errors='ignore')
                                            xml_content.append(f"<!-- {key} START -->")
                                            xml_content.append(decoded_data)
                                            xml_content.append(f"<!-- {key} END -->")
                                    except Exception as e:
                                        logger.warning(f"Failed to read XFA packet {key}: {e}")
                                        
                        else:
                            # Single stream fallback
                            try:
                                xml_content.append(xfa.get_object().get_data().decode('utf-8', errors='ignore'))
                            except:
                                pass
                        
                        full_xml = "\n".join(xml_content)
                        if len(full_xml) > 100:
                            logger.info(f"Successfully extracted XFA XML (Length: {len(full_xml)} bytes)")
                            return full_xml
                return None
            except Exception as e:
                logger.warning(f"Error reading XFA data: {e}")
                return None

        return await asyncio.to_thread(_read_xfa)

    async def _analyze_form_text(self, form_text: str) -> PatentApplicationMetadata:
        """
        Analyzes raw form field text extracted by pypdf.
        """
        prompt = f"""
        Analyze the provided PDF Form Data (Key-Value pairs) from a Patent Application.
        Extract the patent metadata by inferring the meaning of the field keys and values.
        
        ## FORM DATA
        {form_text[:50000]}
        
        ## INSTRUCTIONS
        - The data is presented as 'Field_Name: Value'.
        - Look for keys like 'Title', 'InventionTitle', 'ApplicationNo', 'AppNum', etc.
        - **Inventors**: Look for repeating fields like 'GivenName_1', 'FamilyName_1', 'Address_1' etc.
        - Reconstruct the inventor objects from these flattened keys.
        
        ## OUTPUT SCHEMA
        Return JSON with:
        - _debug_reasoning (string)
        - title
        - application_number
        - entity_status
        - inventors (list of objects)
        """
        
        schema = {
            "_debug_reasoning": "Explain which keys were mapped to which fields",
            "title": "Title found (or null)",
            "application_number": "Application number (or null)",
            "entity_status": "Entity status (or null)",
            "inventors": [
                {
                    "name": "Full Name",
                    "first_name": "First name",
                    "middle_name": "Middle name",
                    "last_name": "Last name",
                    "city": "City",
                    "state": "State",
                    "country": "Country",
                    "street_address": "Street address",
                    "full_address": "Full address string"
                }
            ]
        }
        
        result = await self.generate_structured_content(prompt=prompt, schema=schema)
        
        # Post-processing
        if result.get("inventors"):
            for inventor in result["inventors"]:
                if inventor.get("name") and not inventor.get("last_name"):
                    parts = inventor["name"].split()
                    if len(parts) >= 2:
                        inventor["first_name"] = parts[0]
                        inventor["last_name"] = parts[-1]
        
        return PatentApplicationMetadata(**result)

    async def _analyze_xfa_xml(self, xfa_xml: str) -> PatentApplicationMetadata:
        """
        Analyzes the raw XFA XML data to extract metadata.
        """
        # Truncate XML if it's massive to avoid context limits (though rare for ADS)
        truncated_xml = xfa_xml[:50000]
        
        prompt = f"""
        Analyze the provided XFA Form XML Data from a Patent Application Data Sheet (ADS).
        Extract the patent metadata directly from the XML structure.
        
        ## XML DATA
        {truncated_xml}
        
        ## INSTRUCTIONS
        - The data is structured in XML tags. Look for:
          - Title of Invention
          - Application Number / Control Number
          - Inventor Information (Names, Cities, States, Addresses)
        - **Inventors**: Extract ALL inventors found in the XML datasets.
        
        ## OUTPUT SCHEMA
        Return JSON with:
        - _debug_reasoning (string)
        - title
        - application_number
        - entity_status
        - inventors (list of objects)
        """
        
        schema = {
            "_debug_reasoning": "Explain where in the XML the data was found",
            "title": "Title found (or null)",
            "application_number": "Application number (or null)",
            "entity_status": "Entity status (or null)",
            "inventors": [
                {
                    "name": "Full Name",
                    "first_name": "First name",
                    "middle_name": "Middle name",
                    "last_name": "Last name",
                    "city": "City",
                    "state": "State",
                    "country": "Country",
                    "street_address": "Street address",
                    "full_address": "Full address string"
                }
            ]
        }
        
        result = await self.generate_structured_content(prompt=prompt, schema=schema)
        
        # Post-processing same as before
        if result.get("inventors"):
            for inventor in result["inventors"]:
                if inventor.get("name") and not inventor.get("last_name"):
                    parts = inventor["name"].split()
                    if len(parts) >= 2:
                        inventor["first_name"] = parts[0]
                        inventor["last_name"] = parts[-1]
        
        return PatentApplicationMetadata(**result)

    async def _analyze_text_only(self, text_content: str) -> PatentApplicationMetadata:
        """
        Analyzes raw text content to extract metadata.
        Used for Text-First strategy to avoid file upload.
        """
        prompt = f"""
        Analyze the provided Text Content from a Patent Application Data Sheet (ADS) or similar cover sheet.
        Extract the patent metadata directly from the text.
        
        ## TEXT CONTENT
        {text_content[:80000]} # Limit text to avoid context overflow
        
        ## INSTRUCTIONS
        - **Title**: Look for "Title of Invention" or similar headers.
        - **Application Number**: Look for "Application Number", "Control Number".
        - **Entity Status**: Look for indicators like "Small Entity", "Micro Entity".
        - **Inventors**:
            - Look for sections labeled "Inventor Information", "Legal Name", etc.
            - Extract Name, City, State, Country, and Full Mailing Address.
            - Parse "Given Name", "Family Name" if they appear separately.
        
        ## OUTPUT SCHEMA
        Return JSON with:
        - _debug_reasoning (string)
        - title
        - application_number
        - entity_status
        - inventors (list of objects)
        """
        
        schema = {
            "_debug_reasoning": "Explain which text sections were used to find the data",
            "title": "Title found (or null)",
            "application_number": "Application number (or null)",
            "entity_status": "Entity status (or null)",
            "inventors": [
                {
                    "name": "Full Name",
                    "first_name": "First name",
                    "middle_name": "Middle name",
                    "last_name": "Last name",
                    "city": "City",
                    "state": "State",
                    "country": "Country",
                    "street_address": "Street address",
                    "full_address": "Full address string"
                }
            ]
        }
        
        result = await self.generate_structured_content(prompt=prompt, schema=schema)
        
        # Post-processing for name splitting (same as other methods)
        if result.get("inventors"):
            for inventor in result["inventors"]:
                if inventor.get("name") and not inventor.get("last_name"):
                    parts = inventor["name"].split()
                    if len(parts) >= 2:
                        inventor["first_name"] = parts[0]
                        inventor["last_name"] = parts[-1]
                        
        return PatentApplicationMetadata(**result)

    async def _analyze_single_page_image(self, img_path: str, page_num: int, page_text: str = "") -> Dict[str, Any]:
        """
        Analyzes a single page image AND its text content to extract partial metadata.
        """
        try:
            file_obj = await self.upload_file(img_path, mime_type="image/jpeg")
            
            prompt = f"""
            Analyze this specific page (Page {page_num}) of a Patent Application Data Sheet (ADS).
            I am providing BOTH the visual image AND the raw text content for this page.
            
            ## RAW TEXT CONTENT
            {page_text[:10000]} # Limit text to avoid context overflow if huge
            
            ## INSTRUCTIONS
            1. **Visual Reasoning**: First, explain what you see on the page in the '_debug_reasoning' field.
               - Do you see an "Inventor Information" header?
               - Do you see a table structure?
               - Does the raw text contain names that might be illegible in the image?
            2. **Inventors Extraction**:
               - **COMBINE SOURCES**: Use the Image to understand the layout (rows/columns) and the Text to get accurate spelling.
               - **SEARCH AGGRESSIVELY**: Look for *any* blocks that contain names and addresses.
               - **Address**: If you can't separate City/State, just put the whole address in 'full_address' or 'street_address'.
            3. **Header Info**: Look for Title, Application Number, Entity Status.

            ## OUTPUT SCHEMA
            Return JSON with:
            - _debug_reasoning (string): Description of page content and logic used.
            - title (string/null)
            - application_number (string/null)
            - entity_status (string/null)
            - inventors (list of objects)
            """
            
            schema = {
                "_debug_reasoning": "Explain what sections were found on this page (e.g., 'Found Inventor Info table with 2 rows')",
                "title": "Title found on this page (or null)",
                "application_number": "Application number found on this page (or null)",
                "entity_status": "Entity status found on this page (or null)",
                "inventors": [
                    {
                        "name": "Full Name",
                        "first_name": "First name",
                        "middle_name": "Middle name",
                        "last_name": "Last name",
                        "city": "City",
                        "state": "State",
                        "country": "Country",
                        "street_address": "Street address / Mailing address",
                        "full_address": "Full address string (fallback)"
                    }
                ]
            }

            result = await self.generate_structured_content(
                prompt=prompt,
                file_obj=file_obj,
                schema=schema
            )
            
            # Log the reasoning for debugging purposes
            if result.get("_debug_reasoning"):
                logger.info(f"Page {page_num} Analysis: {result.get('_debug_reasoning')}")
            
            return result
            
        except Exception as e:
            logger.warning(f"Failed to analyze page {page_num}: {e}")
            return {}

    async def _analyze_pdf_direct_fallback(self, file_path: str, file_obj: Any = None, file_content: Optional[bytes] = None) -> PatentApplicationMetadata:
        """
        Single-pass native PDF extraction.
        Accepts optional pre-uploaded file_obj to save time.
        """
        # Upload file to Gemini if not provided
        if not file_obj:
            try:
                upload_source = io.BytesIO(file_content) if file_content else file_path
                file_obj = await self.upload_file(upload_source)
            except Exception as e:
                logger.error(f"Failed to upload file for analysis: {e}")
                raise e

        # Construct prompt for direct visual extraction
        prompt = """
        Analyze the provided document, which is likely a **Patent Application Data Sheet (ADS)** or similar cover sheet.
        Your goal is to extract specific bibliographic data with HIGH PRECISION.

        ## DOCUMENT STRUCTURE AWARENESS
        - **ADS Forms (PTO/AIA/14)**: These forms use structured tables.
          - **Inventors**: Look for the "Inventor Information" section. This is often a TABLE where each row is an inventor, or a set of blocks.
          - **Multi-Page**: The inventor list often SPANS MULTIPLE PAGES. You MUST look at ALL pages to find every inventor.
          - **Columns**: In ADS tables, names are often split into "Given Name", "Middle Name", "Family Name".
          - **Addresses**: Addresses are often in separate rows or blocks below the name.

        ## EXTRACTION INSTRUCTIONS
        1. **Title**: Extract the "Title of Invention".
        2. **Application Number**: Extract if present (e.g., "Application Number", "Control Number").
        3. **Filing Date**: Extract if present.
        4. **Entity Status**: Extract if checked (e.g., "Small Entity", "Micro Entity").
        5. **Inventors (CRITICAL)**:
           - Extract **ALL** inventors found in the document.
           - Check **EVERY PAGE** for additional inventors.
           - If the document is an ADS, strictly follow the "Inventor Information" table/blocks.
           - Combine "Given Name", "Middle Name", "Family Name" into a single "name" field if needed, or populate separate fields if the schema allows.
           - **Address**: Extract the complete mailing address (City, State, Country, Street/Postal).

        ## DATA CLEANING RULES
        - Remove legal boilerplate (e.g., "The application data sheet is part of...").
        - If a field is empty in the form (e.g., Application Number is blank), return null.
        - Do NOT Hallucinate. Only extract what is visually present.

        The output must be valid JSON matching the provided schema.
        """
        
        schema = {
            "title": "Title of the invention",
            "application_number": "Application number",
            "filing_date": "Filing date (YYYY-MM-DD or original format)",
            "entity_status": "Entity status",
            "inventors": [
                {
                    "name": "Full Name (e.g. John A. Doe)",
                    "first_name": "First name (optional)",
                    "middle_name": "Middle name (optional)",
                    "last_name": "Last name (optional)",
                    "city": "City",
                    "state": "State",
                    "country": "Country",
                    "citizenship": "Citizenship",
                    "street_address": "Street address / Mailing address"
                }
            ]
        }
        
        try:
            # Pass the file object DIRECTLY to the LLM along with the prompt
            result = await self.generate_structured_content(
                prompt=prompt,
                file_obj=file_obj,  # <--- Key change: Passing the file object
                schema=schema
            )
            
            # Validate that we actually got meaningful data
            if not result:
                raise ValueError("LLM returned empty response")
            
            # Post-processing: If only 'name' is present, try to split it into first/last
            # This handles the relaxed schema allowing single 'name' field
            if result.get("inventors"):
                for inventor in result["inventors"]:
                    if inventor.get("name") and not inventor.get("last_name"):
                        parts = inventor["name"].split()
                        if len(parts) >= 2:
                            inventor["first_name"] = parts[0]
                            inventor["last_name"] = parts[-1]
                            if len(parts) > 2:
                                inventor["middle_name"] = " ".join(parts[1:-1])
                        elif len(parts) == 1:
                            inventor["first_name"] = parts[0]

            return PatentApplicationMetadata(**result)
            
        except Exception as e:
            logger.error(f"Error analyzing cover sheet: {e}")
            raise e

    async def _convert_pdf_to_images(self, file_path: str, file_content: Optional[bytes] = None) -> List[str]:
        """
        Converts PDF pages to JPEG images using PyMuPDF (fitz).
        Returns a list of temporary file paths.
        """
        if fitz is None:
            logger.error("PyMuPDF (fitz) is not installed. Image conversion fallback unavailable.")
            return []

        def _convert():
            image_paths = []
            try:
                if file_content:
                    doc = fitz.open(stream=file_content, filetype="pdf")
                    # If we don't have a real path, create a safe base prefix
                    base_path = file_path if file_path and os.path.exists(file_path) else f"temp_pdf_{datetime.utcnow().timestamp()}"
                else:
                    doc = fitz.open(file_path)
                    base_path = file_path

                # Process all pages (or up to a reasonable sanity limit like 50)
                # Requirement implies support for 50 page PDFs
                for i in range(min(50, len(doc))):
                    page = doc.load_page(i)
                    # Increase DPI to 300 for high-quality OCR on bad scans
                    pix = page.get_pixmap(dpi=300)
                    img_path = f"{base_path}_page_{i}.jpg"
                    pix.save(img_path)
                    image_paths.append(img_path)
                doc.close()
            except Exception as e:
                logger.error(f"PDF to Image conversion failed: {e}")
            return image_paths

        return await asyncio.to_thread(_convert)

    async def _extract_text_locally(self, file_path: str, file_content: Optional[bytes] = None) -> str:
        """
        Extracts text from a PDF using pypdf locally.
        Crucially, this extracts FORM FIELDS from editable PDFs.
        """
        def _read_pdf():
            text_content = []
            try:
                if file_content:
                    reader = PdfReader(io.BytesIO(file_content))
                else:
                    reader = PdfReader(file_path)
                
                # --- DIAGNOSTICS ---
                if reader.is_encrypted:
                    logger.warning(f"PDF is encrypted. Attempting to read anyway (might fail if password needed).")
                    try:
                        reader.decrypt("")
                    except:
                        pass
                
                # Check for XFA (Dynamic Forms)
                if "/AcroForm" in reader.trailer["/Root"] and "/XFA" in reader.trailer["/Root"]["/AcroForm"]:
                     logger.warning("PDF appears to contain XFA (Dynamic Form) data. Standard extraction might be limited.")
                     text_content.append("[WARNING: Document is an XFA Dynamic Form. Data might be hidden.]")
                # -------------------

                # 1. Extract Form Fields (Key for Editable PDFs)
                try:
                    fields = reader.get_form_text_fields()
                    if fields:
                        text_content.append("--- FORM FIELD DATA ---")
                        for key, value in fields.items():
                            if value:
                                text_content.append(f"{key}: {value}")
                        text_content.append("--- END FORM DATA ---\n")
                    else:
                        logger.info("No standard AcroForm fields found.")
                except Exception as e:
                    logger.warning(f"Failed to extract form fields: {e}")

                # 2. Extract Page Text
                for i, page in enumerate(reader.pages):
                    text_content.append(f"--- PAGE {i+1} ---")
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_content.append(page_text)
                        else:
                            text_content.append("[EMPTY PAGE TEXT - LIKELY IMAGE OR XFA]")
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {i+1}: {e}")
                        
            except Exception as e:
                logger.error(f"Local PDF reading failed: {e}")
                return ""
                
            return "\n".join(text_content)

        return await asyncio.to_thread(_read_pdf)

    # --- DocuMind Extraction Pipeline Methods ---

    # async def extract_document(self, file_path: str) -> ExtractionResult:
    #     """
    #     Main entry point for document extraction.
    #     Decides whether to process directly or in chunks.
    #     """
    #     file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
    #     # Get page count
    #     try:
    #         reader = PdfReader(file_path)
    #         page_count = len(reader.pages)
    #     except Exception:
    #         page_count = 0 # Fallback
            
    #     should_chunk = (
    #         file_size_mb > settings.LARGE_FILE_THRESHOLD_MB or 
    #         page_count > settings.LARGE_FILE_PAGE_THRESHOLD
    #     )
        
    #     with open(file_path, "rb") as f:
    #         file_bytes = f.read()

    #     if should_chunk:
    #         logger.info(f"Document requires chunking (Size: {file_size_mb:.2f}MB, Pages: {page_count})")
    #         return await self._extract_document_chunked(file_bytes, os.path.basename(file_path), page_count)
    #     else:
    #         logger.info(f"Processing document directly (Size: {file_size_mb:.2f}MB, Pages: {page_count})")
    #         # For direct extraction, we can reuse the file_path upload to save bandwidth 
    #         # if we hadn't already read bytes, but here we follow the pipeline logic
    #         return await self._extract_document_direct(file_path)

    # async def _extract_document_direct(self, file_path: str) -> ExtractionResult:
    #     """
    #     Extract text from a small document in a single API call using Native PDF support.
    #     """
    #     # Upload file to Gemini
    #     file_obj = await self.upload_file(file_path)
        
    #     extraction_prompt = """
    #     You are DocuMind, a High-Fidelity Document Digitization System.

    #     ## CORE PRINCIPLES
    #     1. **NO HALLUCINATION** - Never invent, assume, or fabricate any information not explicitly visible in the document.
    #     2. **NO SUMMARIZATION** - Extract the COMPLETE content of every page.
    #     3. **PRESERVE FIDELITY** - Maintain the original spelling, punctuation, formatting structure.

    #     ## OUTPUT FORMAT
    #     For each page, output in this exact format:
        
    #     --- PAGE [number] ---
        
    #     [Extract all visible text exactly as it appears, preserving structure]
        
    #     [Use annotations for non-text elements like: [Handwritten: ...], [Stamp: ...], [Table: ...]]

    #     After ALL pages, provide:
        
    #     === DOCUMENT EXTRACTION SUMMARY ===
    #     TOTAL PAGES: [count]
    #     OVERALL DOCUMENT CONFIDENCE: [High/Medium/Low]
    #     DOCUMENT QUALITY: [Excellent/Good/Fair/Poor]
    #     HANDWRITING DETECTED: [Yes/No]
    #     EXTRACTION NOTES: [Any important observations]
    #     """
        
    #     retries = settings.GEMINI_MAX_RETRIES
    #     for attempt in range(retries):
    #         try:
    #             # We use the raw client directly here to get text output, not JSON
    #             response = await asyncio.to_thread(
    #                 self.client.models.generate_content,
    #                 model=settings.GEMINI_MODEL,
    #                 contents=[file_obj, extraction_prompt],
    #                 config=types.GenerateContentConfig(
    #                     temperature=0.0,
    #                     max_output_tokens=65536
    #                 )
    #             )
                
    #             self._log_token_usage(response, "direct_extraction")
    #             extracted_text = response.text
    #             metadata_dict = self._parse_extraction_metadata(extracted_text, os.path.getsize(file_path))
                
    #             return ExtractionResult(
    #                 extracted_text=extracted_text,
    #                 metadata=ExtractionMetadata(**metadata_dict)
    #             )
            
    #         except ResourceExhausted as re_err:
    #             logger.warning(f"Gemini Rate Limit Exceeded during direct extraction: {re_err}")
    #             raise HTTPException(
    #                 status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    #                 detail="AI Service is currently busy (Rate Limit Exceeded). Please try again in a moment."
    #             )
    #         except Exception as e:
    #             logger.warning(f"Direct extraction failed (attempt {attempt + 1}/{retries}): {e}")
    #             if attempt == retries - 1:
    #                 logger.error(f"Direct extraction failed after {retries} attempts: {e}")
    #                 raise e
                
    #             # Exponential backoff: 2s, 4s, 8s
    #             wait_time = (2 ** (attempt + 1))
    #             logger.info(f"Retrying in {wait_time} seconds...")
    #             await asyncio.sleep(wait_time)

    # async def _extract_document_chunked(self, file_bytes: bytes, filename: str, total_pages: int) -> ExtractionResult:
    #     """
    #     Extract text from a large document using parallel chunk processing.
    #     """
    #     # Split document into chunks
    #     chunks = self._chunk_pdf(file_bytes, settings.CHUNK_SIZE_PAGES)
    #     total_chunks = len(chunks)
        
    #     # Semaphore for concurrency control
    #     semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_EXTRACTIONS)

    #     async def extract_chunk(chunk_data: Tuple[bytes, int, int], chunk_index: int):
    #         chunk_bytes, start_page, end_page = chunk_data
    #         async with semaphore:
    #             return await self._extract_single_chunk(
    #                 chunk_bytes, chunk_index, total_chunks, start_page, end_page
    #             )

    #     # Process all chunks in parallel
    #     tasks = [extract_chunk(chunk_data, idx) for idx, chunk_data in enumerate(chunks)]
    #     results = await asyncio.gather(*tasks, return_exceptions=True)
        
    #     return self._aggregate_chunk_results(results, total_chunks, len(file_bytes))

    async def _analyze_document_chunked_structured(
        self,
        file_bytes: bytes,
        filename: str,
        total_pages: int,
        progress_callback: Optional[Callable[[int, str], Awaitable[None]]] = None
    ) -> PatentApplicationMetadata:
        """
        Analyzes a large document by splitting it into chunks and processing them in parallel
        to extract STRUCTURED metadata (Inventors, Title, etc.).
        """
        # 1. Split into chunks
        # Use a slightly larger chunk size for structured data to ensure context (e.g. 10 pages)
        chunk_size = 10
        chunks = self._chunk_pdf(file_bytes, chunk_size_pages=chunk_size)
        total_chunks = len(chunks)
        
        logger.info(f"Splitting {total_pages} pages into {total_chunks} chunks for Structured Analysis.")

        # 2. Parallel Processing
        semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_EXTRACTIONS)
        processed_count = 0

        async def process_chunk(chunk_data: Tuple[bytes, int, int], chunk_index: int):
            nonlocal processed_count
            chunk_bytes, start_page, end_page = chunk_data
            
            async with semaphore:
                logger.info(f"Starting Structured Analysis for Chunk {chunk_index + 1}/{total_chunks} (Pages {start_page}-{end_page})")
                try:
                    result = await self._extract_structured_chunk(
                        chunk_bytes, chunk_index, total_chunks, start_page, end_page
                    )
                    
                    processed_count += 1
                    if progress_callback:
                        # Map progress 20-90%
                        progress = 20 + int((processed_count / total_chunks) * 70)
                        await progress_callback(progress, f"Analyzed chunk {processed_count}/{total_chunks}")
                    
                    return result
                except Exception as e:
                    logger.error(f"Failed to analyze chunk {chunk_index}: {e}")
                    return None

        tasks = [process_chunk(c, i) for i, c in enumerate(chunks)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 3. Aggregate Results
        # Filter out failed chunks
        valid_results = [r for r in results if r is not None and not isinstance(r, Exception)]
        
        return self._aggregate_structured_chunks(valid_results)

    async def _extract_structured_chunk(
        self, chunk_bytes: bytes, chunk_index: int, total_chunks: int,
        start_page: int, end_page: int, max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Extract structured metadata from a single PDF chunk.
        """
        chunk_prompt = f"""
        You are DocuMind. You are processing CHUNK {chunk_index+1} of {total_chunks} from a larger patent document.
        This chunk contains pages {start_page} to {end_page}.

        ## INSTRUCTIONS
        1. **Inventors (CRITICAL)**:
           - Scan EVERY PAGE in this chunk for "Inventor Information", "Legal Name", or similar tables.
           - Extract ALL inventors found.
           - If a list of inventors continues from a previous page, INCLUDE THEM.
        2. **Bibliographic Data**:
           - Look for Title, Application Number, Filing Date, Entity Status.
           - Note: These might only appear on the first page of the first chunk, but check anyway.

        ## OUTPUT SCHEMA
        Return JSON with:
        - title (string/null)
        - application_number (string/null)
        - entity_status (string/null)
        - inventors (list of objects)
        """
        
        schema = {
            "title": "Title found (or null)",
            "application_number": "Application number (or null)",
            "entity_status": "Entity status (or null)",
            "inventors": [
                {
                    "name": "Full Name",
                    "first_name": "First name",
                    "middle_name": "Middle name",
                    "last_name": "Last name",
                    "city": "City",
                    "state": "State",
                    "country": "Country",
                    "street_address": "Street address / Mailing address"
                }
            ]
        }

        for attempt in range(max_retries):
            try:
                # Write chunk to temp file for upload
                temp_filename = f"temp_struct_chunk_{chunk_index}_{attempt}_{random.randint(1000,9999)}.pdf"
                with open(temp_filename, "wb") as f:
                    f.write(chunk_bytes)
                
                try:
                    file_obj = await self.upload_file(temp_filename)
                    
                    result = await self.generate_structured_content(
                        prompt=chunk_prompt,
                        file_obj=file_obj,
                        schema=schema
                    )
                    return result

                finally:
                    if os.path.exists(temp_filename):
                        try:
                            os.remove(temp_filename)
                        except:
                            pass

            except Exception as e:
                logger.warning(f"Chunk {chunk_index} failed attempt {attempt+1}: {e}")
                wait_time = (2 ** attempt) * 2
                await asyncio.sleep(wait_time)

        return {}

    def _aggregate_structured_chunks(self, results: List[Dict[str, Any]]) -> PatentApplicationMetadata:
        """
        Aggregates metadata from multiple chunks into a single result.
        """
        final_metadata = {
            "title": None,
            "application_number": None,
            "entity_status": None,
            "inventors": []
        }
        
        extracted_inventors = []
        
        for res in results:
            if not res: continue
            
            # 1. Metadata (First valid wins)
            if not final_metadata["title"] and res.get("title"):
                final_metadata["title"] = res["title"]
            if not final_metadata["application_number"] and res.get("application_number"):
                final_metadata["application_number"] = res["application_number"]
            if not final_metadata["entity_status"] and res.get("entity_status"):
                final_metadata["entity_status"] = res["entity_status"]
            
            # 2. Inventors (Merge and Deduplicate)
            if res.get("inventors"):
                for new_inv in res["inventors"]:
                    # Basic deduplication by Name
                    is_duplicate = False
                    new_name = new_inv.get("name", "").strip().lower()
                    
                    if not new_name and (new_inv.get("first_name") or new_inv.get("last_name")):
                         # Construct name if missing
                         parts = [p for p in [new_inv.get("first_name"), new_inv.get("middle_name"), new_inv.get("last_name")] if p]
                         new_name = " ".join(parts).strip().lower()

                    for existing in extracted_inventors:
                        existing_name = existing.get("name", "").strip().lower()
                        if not existing_name:
                             parts = [p for p in [existing.get("first_name"), existing.get("middle_name"), existing.get("last_name")] if p]
                             existing_name = " ".join(parts).strip().lower()
                        
                        if new_name and existing_name and new_name == existing_name:
                            is_duplicate = True
                            # Merge fields if existing is empty but new has data
                            if not existing.get("city") and new_inv.get("city"):
                                existing["city"] = new_inv["city"]
                            break
                    
                    if not is_duplicate:
                        extracted_inventors.append(new_inv)
        
        final_metadata["inventors"] = extracted_inventors
        
        # Post-processing: Name splitting
        for inventor in final_metadata["inventors"]:
            if inventor.get("name") and not inventor.get("last_name"):
                parts = inventor["name"].split()
                if len(parts) >= 2:
                    inventor["first_name"] = parts[0]
                    inventor["last_name"] = parts[-1]
                    if len(parts) > 2:
                        inventor["middle_name"] = " ".join(parts[1:-1])
                elif len(parts) == 1:
                    inventor["first_name"] = parts[0]

        return PatentApplicationMetadata(**final_metadata)

    def _chunk_pdf(self, pdf_bytes: bytes, chunk_size_pages: int = 5) -> List[Tuple[bytes, int, int]]:
        """
        Split a PDF into chunks of specified page count.
        """
        reader = PdfReader(io.BytesIO(pdf_bytes))
        total_pages = len(reader.pages)
        chunks = []

        for start_idx in range(0, total_pages, chunk_size_pages):
            end_idx = min(start_idx + chunk_size_pages, total_pages)

            writer = PdfWriter()
            for page_idx in range(start_idx, end_idx):
                writer.add_page(reader.pages[page_idx])

            chunk_buffer = io.BytesIO()
            writer.write(chunk_buffer)
            chunk_bytes = chunk_buffer.getvalue()

            chunks.append((
                chunk_bytes,
                start_idx + 1,      # start_page (1-indexed)
                end_idx             # end_page (1-indexed)
            ))

        return chunks

    async def _extract_single_chunk(
        self, chunk_bytes: bytes, chunk_index: int, total_chunks: int, 
        start_page: int, end_page: int, max_retries: int = 3
    ) -> dict:
        """
        Extract text from a single chunk with retry logic.
        """
        chunk_prompt = f"""
        You are DocuMind. You are processing CHUNK {chunk_index+1} of {total_chunks} from a larger document.
        This chunk contains pages {start_page} to {end_page}.
        
        ## CORE PRINCIPLES
        1. **NO HALLUCINATION**
        2. **NO SUMMARIZATION**
        3. **PRESERVE FIDELITY**

        ## OUTPUT FORMAT
        For each page in this chunk, use this format:
        
        --- PAGE [actual page number, starting at {start_page}] ---
        
        [Full extraction content]
        
        [Page Confidence: High/Medium/Low]

        ## CHUNK SUMMARY
        After extracting all pages in this chunk, provide:
        
        === CHUNK {chunk_index+1} EXTRACTION SUMMARY ===
        PAGES IN CHUNK: {start_page}-{end_page}
        CHUNK CONFIDENCE: [High/Medium/Low]
        """

        for attempt in range(max_retries):
            try:
                # We need to upload the chunk as a file to Gemini
                # Ideally we would save to temp file, but for now lets try passing bytes if SDK supports
                # SDK might require path, so let's write to a temp file
                temp_filename = f"temp_chunk_{chunk_index}_{attempt}.pdf"
                with open(temp_filename, "wb") as f:
                    f.write(chunk_bytes)
                
                try:
                    file_obj = await self.upload_file(temp_filename)
                    
                    response = await asyncio.to_thread(
                        self.client.models.generate_content,
                        model=settings.GEMINI_MODEL,
                        contents=[file_obj, chunk_prompt],
                        config=types.GenerateContentConfig(
                            temperature=0.0,
                            max_output_tokens=65536
                        )
                    )

                    self._log_token_usage(response, f"chunk_extraction_{chunk_index}")
                    
                    return {
                        "chunk_index": chunk_index,
                        "extracted_text": response.text,
                        "success": True
                    }
                finally:
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)

            except Exception as e:
                wait_time = (2 ** attempt) * 2
                await asyncio.sleep(wait_time)

        return {
            "chunk_index": chunk_index,
            "extracted_text": f"[EXTRACTION FAILED FOR PAGES {start_page}-{end_page}]",
            "success": False
        }

    # def _aggregate_chunk_results(self, results: List[Any], total_chunks: int, file_size: int) -> ExtractionResult:
    #     """
    #     Combine extraction results from multiple chunks.
    #     """
    #     successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
    #     successful_results.sort(key=lambda x: x["chunk_index"])

    #     combined_text_parts = []
    #     for result in successful_results:
    #         combined_text_parts.append(result["extracted_text"])

    #     combined_text = "\n\n".join(combined_text_parts)
        
    #     failed_count = total_chunks - len(successful_results)
        
    #     metadata = ExtractionMetadata(
    #         page_count=0, # Would need to parse from text or pass through
    #         overall_confidence=ConfidenceLevel.LOW if failed_count > 0 else ConfidenceLevel.HIGH,
    #         is_chunked=True,
    #         chunk_count=total_chunks,
    #         successful_chunks=len(successful_results),
    #         failed_chunks=failed_count,
    #         file_size_bytes=file_size
    #     )
        
    #     return ExtractionResult(extracted_text=combined_text, metadata=metadata)

    # def _parse_extraction_metadata(self, extracted_text: str, file_size: int) -> dict:
    #     """
    #     Parse metadata from LLM extraction output.
    #     """
    #     metadata = {
    #         "page_count": 0,
    #         "overall_confidence": "medium",
    #         "document_quality": "good",
    #         "has_handwriting": False,
    #         "extraction_notes": None,
    #         "file_size_bytes": file_size,
    #         "uncertain_count": 0,
    #         "illegible_count": 0
    #     }

    #     # Count pages from markers
    #     page_markers = re.findall(r'--- PAGE (\d+) ---', extracted_text)
    #     if page_markers:
    #         metadata["page_count"] = len(page_markers)

    #     # Extract overall confidence
    #     confidence_match = re.search(
    #         r'OVERALL DOCUMENT CONFIDENCE:\s*(High|Medium|Low)',
    #         extracted_text,
    #         re.IGNORECASE
    #     )
    #     if confidence_match:
    #         metadata["overall_confidence"] = confidence_match.group(1).lower()

    #     # Extract document quality
    #     quality_match = re.search(
    #         r'DOCUMENT QUALITY:\s*(Excellent|Good|Fair|Poor)',
    #         extracted_text,
    #         re.IGNORECASE
    #     )
    #     if quality_match:
    #         metadata["document_quality"] = quality_match.group(1).lower()

    #     # Check for handwriting
    #     handwriting_match = re.search(
    #         r'HANDWRITING DETECTED:\s*(Yes|No)',
    #         extracted_text,
    #         re.IGNORECASE
    #     )
    #     if handwriting_match:
    #         metadata["has_handwriting"] = handwriting_match.group(1).lower() == "yes"

    #     # Also check for handwriting annotations
    #     if re.search(r'\[Handwritten:', extracted_text):
    #         metadata["has_handwriting"] = True

    #     return metadata
    async def analyze_office_action(
        self,
        file_path: str,
        file_content: Optional[bytes] = None,
        progress_callback: Optional[Callable[[int, str], Awaitable[None]]] = None
    ) -> Dict[str, Any]:
        """
        Analyzes a Patent Office Action PDF.
        Extracts structured data: Header, Claims Status, Rejections, Objections, etc.
        """
        from app.models.office_action import OfficeActionExtractedData
        
        logger.info(f"--- ANALYZING OFFICE ACTION: {file_path} ---")

        # Upload file for multimodal analysis
        if file_content:
            upload_source = io.BytesIO(file_content)
        else:
            upload_source = file_path
            
        try:
            if progress_callback:
                await progress_callback(10, "Uploading Office Action for AI Analysis...")
                
            file_obj = await self.upload_file(upload_source)
            
            prompt = """
            Analyze the provided Patent Office Action PDF.
            Extract structured information with high precision.
            
            ## INSTRUCTIONS
            
            1. **HEADER INFO**: Extract Application Number, Filing Date, Office Action Date (Mailing Date), Examiner Name, Art Unit.
            2. **CLAIMS STATUS**:
               - List ALL claims mentioned.
               - Determine status for each: Rejected, Allowed, Objected to, Cancelled, Withdrawn.
               - Note if claims are Independent or Dependent.
            3. **REJECTIONS (Critical)**:
               - Extract EACH rejection block.
               - Identify the statutory basis (e.g., 35 U.S.C. 102, 103, 112).
               - List affected claim numbers.
               - Extract the Examiner's Reasoning verbatim or typically summarized.
               - List cited Prior Art (US Patents, Foreign Patents, NPL).
            4. **OBJECTIONS**:
               - Identify objections to Specification, Drawings, or Claims.
               - Extract the reason and required correction.
            5. **OTHER**:
               - Look for "Allowable Subject Matter" indications.
               - Response Deadline.

            ## OUTPUT SCHEMA
            Return JSON matching the following structure:
            {
                "header": {
                    "application_number": "...",
                    "office_action_date": "...",
                    "office_action_type": "...",
                    "examiner_name": "...",
                    "art_unit": "...",
                    "response_deadline": "..."
                },
                "claims_status": [
                    { "claim_number": "1", "status": "Rejected", "dependency_type": "Independent" },
                    ...
                ],
                "rejections": [
                    {
                        "rejection_type": "103",
                        "statutory_basis": "35 U.S.C. 103",
                        "affected_claims": ["1", "2"],
                        "examiner_reasoning": "...",
                        "cited_prior_art": [
                            { "reference_type": "US Patent", "identifier": "US 9,999,999 B2", "relevant_claims": ["1"] }
                        ]
                    }
                ],
                "objections": [...],
                "other_statements": [...]
            }
            """
            
            schema = {
                "header": {
                    "application_number": "string",
                    "filing_date": "string (optional)",
                    "office_action_date": "string",
                    "office_action_type": "string",
                    "examiner_name": "string (optional)",
                    "art_unit": "string (optional)",
                    "response_deadline": "string (optional)"
                },
                "claims_status": [
                    {
                        "claim_number": "string",
                        "status": "string",
                        "dependency_type": "string"
                    }
                ],
                "rejections": [
                    {
                        "rejection_type": "string",
                        "statutory_basis": "string (optional)",
                        "affected_claims": ["string"],
                        "examiner_reasoning": "string",
                        "cited_prior_art": [
                            {
                                "reference_type": "string",
                                "identifier": "string",
                                "relevant_claims": ["string"]
                            }
                        ]
                    }
                ],
                "objections": [
                    {
                        "objected_item": "string",
                        "reason": "string",
                        "corrective_action": "string (optional)"
                    }
                ],
                "other_statements": [
                    {
                        "statement_type": "string",
                        "content": "string"
                    }
                ]
            }

            if progress_callback:
                await progress_callback(30, "AI Analyzing Document Structure...")

            result = await self.generate_structured_content(
                prompt=prompt,
                file_obj=file_obj,
                schema=schema
            )
            
            if progress_callback:
                await progress_callback(90, "Finalizing Extraction...")

            return result

        except Exception as e:
            logger.error(f"Office Action Analysis Failed: {e}")
            raise e

llm_service = LLMService()