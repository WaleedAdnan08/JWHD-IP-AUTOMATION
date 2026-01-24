from google import genai
from google.genai import types
from google.api_core.exceptions import ResourceExhausted
from fastapi import HTTPException, status
from app.core.config import settings
from app.models.patent_application import PatentApplicationMetadata
from app.models.extraction import ExtractionMetadata, ExtractionResult, ConfidenceLevel, DocumentQuality
import logging
import json
import re
import os
import asyncio
import io
import random
from typing import Dict, Any, Optional, List, Tuple
from pypdf import PdfReader, PdfWriter

# Configure logging
logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self._initialize_client()

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
                    extra_data={
                        "token_usage": {
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": candidates_tokens,
                            "total_tokens": total_tokens,
                            "estimated_cost_usd": round(total_cost, 6)
                        }
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to log token usage: {e}")

    def _initialize_client(self):
        try:
            logger.info("Attempting to initialize Gemini client...")
            if settings.GOOGLE_API_KEY:
                # Log a masked version of the key to ensure we see it's there
                masked_key = f"{settings.GOOGLE_API_KEY[:4]}...{settings.GOOGLE_API_KEY[-4:]}" if len(settings.GOOGLE_API_KEY) > 8 else "***"
                logger.info(f"GOOGLE_API_KEY found: {masked_key}")
                self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
                logger.info(f"Initialized Gemini client successfully")
            else:
                logger.warning("GOOGLE_API_KEY not found. LLM service not initialized.")
                self.client = None
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}", exc_info=True)
            self.client = None

    async def upload_file(self, file_path: str, mime_type: str = "application/pdf"):
        """
        Uploads a file to Gemini for multimodal processing.
        """
        if not self.client:
            raise Exception("LLM service not initialized")
        
        try:
            logger.info(f"Uploading file to Gemini: {file_path}")
            # Run in thread pool since library is synchronous
            file_obj = await asyncio.to_thread(
                self.client.files.upload,
                file=file_path,
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
                    try:
                        logger.info(f"Calling Gemini API with model: {settings.GEMINI_MODEL}")
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
                        logger.info("Gemini API call returned")
                        self._log_token_usage(response, "generate_structured_content")
                    except ResourceExhausted as re_err:
                        logger.warning(f"Gemini Rate Limit Exceeded: {re_err}")
                        raise HTTPException(
                            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="AI Service is currently busy (Rate Limit Exceeded). Please try again in a moment."
                        )
                    except Exception as e:
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

    async def analyze_cover_sheet(self, file_path: str) -> PatentApplicationMetadata:
        """
        Analyzes the cover sheet PDF to extract patent application metadata using Gemini Native PDF support.
        This uses the DocuMind extraction pipeline.
        """
        logger.info(f"--- ANALYZING PDF WITH GEMINI: {file_path} ---")

        # 1. First, extract the raw text and metadata using the robust extraction pipeline
        extraction_result = await self.extract_document(file_path)
        
        # 2. Use the extracted text to parse structured data
        # We use the text extracted by Gemini (which is high fidelity) to fill the schema
        prompt = """
        Analyze the provided Patent Application Cover Sheet text and extract the metadata specified below.
        
        Instructions:
        - Extract the Title of Invention.
        - Extract Application Number, Filing Date, and Entity Status if they appear in the text.
        - Extract all Inventors listed.
        - For each inventor, extract: First Name, Middle Name, Last Name, City, State, Country, Citizenship, and Mailing Address.
        
        Important Guidelines:
        - If an exact field is missing, try to infer it from context if possible (e.g., infer Country from City/State if not explicitly stated).
        - Look for labels like "Inventor:", "Applicant:", "Title:", "Residence:", "Address:", "Citizenship:".
        - If a field is definitely not present, return null.
        - The output must be valid JSON matching the provided schema.
        """
        
        schema = {
            "title": "Title of the invention",
            "application_number": "Application number",
            "filing_date": "Filing date (YYYY-MM-DD or original format)",
            "entity_status": "Entity status",
            "inventors": [
                {
                    "first_name": "First name",
                    "middle_name": "Middle name",
                    "last_name": "Last name",
                    "city": "City",
                    "state": "State",
                    "country": "Country",
                    "citizenship": "Citizenship",
                    "street_address": "Street address / Mailing address"
                }
            ]
        }
        
        full_input = f"{prompt}\n\nTEXT CONTENT:\n{extraction_result.extracted_text[:50000]}" # Use extracted text
        
        try:
            result = await self.generate_structured_content(
                prompt=full_input,
                schema=schema
            )
            
            # Validate that we actually got meaningful data
            if not result:
                raise ValueError("LLM returned empty response")
                
            has_inventors = result.get("inventors") and len(result.get("inventors")) > 0
            has_title = result.get("title") and str(result.get("title")).strip()
            
            if not has_inventors and not has_title:
                logger.error(f"Extraction validation failed. Input text length: {len(extraction_result.extracted_text)}")
                logger.error(f"LLM Result: {json.dumps(result)}")
                raise ValueError("LLM failed to extract any inventors or title from the document")
            
            return PatentApplicationMetadata(**result)
        except Exception as e:
            logger.error(f"Error analyzing cover sheet: {e}")
            raise e

    # --- DocuMind Extraction Pipeline Methods ---

    async def extract_document(self, file_path: str) -> ExtractionResult:
        """
        Main entry point for document extraction.
        Decides whether to process directly or in chunks.
        """
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        # Get page count
        try:
            reader = PdfReader(file_path)
            page_count = len(reader.pages)
        except Exception:
            page_count = 0 # Fallback
            
        should_chunk = (
            file_size_mb > settings.LARGE_FILE_THRESHOLD_MB or 
            page_count > settings.LARGE_FILE_PAGE_THRESHOLD
        )
        
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        if should_chunk:
            logger.info(f"Document requires chunking (Size: {file_size_mb:.2f}MB, Pages: {page_count})")
            return await self._extract_document_chunked(file_bytes, os.path.basename(file_path), page_count)
        else:
            logger.info(f"Processing document directly (Size: {file_size_mb:.2f}MB, Pages: {page_count})")
            # For direct extraction, we can reuse the file_path upload to save bandwidth 
            # if we hadn't already read bytes, but here we follow the pipeline logic
            return await self._extract_document_direct(file_path)

    async def _extract_document_direct(self, file_path: str) -> ExtractionResult:
        """
        Extract text from a small document in a single API call using Native PDF support.
        """
        # Upload file to Gemini
        file_obj = await self.upload_file(file_path)
        
        extraction_prompt = """
        You are DocuMind, a High-Fidelity Document Digitization System.

        ## CORE PRINCIPLES
        1. **NO HALLUCINATION** - Never invent, assume, or fabricate any information not explicitly visible in the document.
        2. **NO SUMMARIZATION** - Extract the COMPLETE content of every page.
        3. **PRESERVE FIDELITY** - Maintain the original spelling, punctuation, formatting structure.

        ## OUTPUT FORMAT
        For each page, output in this exact format:
        
        --- PAGE [number] ---
        
        [Extract all visible text exactly as it appears, preserving structure]
        
        [Use annotations for non-text elements like: [Handwritten: ...], [Stamp: ...], [Table: ...]]

        After ALL pages, provide:
        
        === DOCUMENT EXTRACTION SUMMARY ===
        TOTAL PAGES: [count]
        OVERALL DOCUMENT CONFIDENCE: [High/Medium/Low]
        DOCUMENT QUALITY: [Excellent/Good/Fair/Poor]
        HANDWRITING DETECTED: [Yes/No]
        EXTRACTION NOTES: [Any important observations]
        """
        
        retries = settings.GEMINI_MAX_RETRIES
        for attempt in range(retries):
            try:
                # We use the raw client directly here to get text output, not JSON
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=settings.GEMINI_MODEL,
                    contents=[file_obj, extraction_prompt],
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        max_output_tokens=65536
                    )
                )
                
                self._log_token_usage(response, "direct_extraction")
                extracted_text = response.text
                metadata_dict = self._parse_extraction_metadata(extracted_text, os.path.getsize(file_path))
                
                return ExtractionResult(
                    extracted_text=extracted_text,
                    metadata=ExtractionMetadata(**metadata_dict)
                )
            
            except ResourceExhausted as re_err:
                logger.warning(f"Gemini Rate Limit Exceeded during direct extraction: {re_err}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="AI Service is currently busy (Rate Limit Exceeded). Please try again in a moment."
                )
            except Exception as e:
                logger.warning(f"Direct extraction failed (attempt {attempt + 1}/{retries}): {e}")
                if attempt == retries - 1:
                    logger.error(f"Direct extraction failed after {retries} attempts: {e}")
                    raise e
                
                # Exponential backoff: 2s, 4s, 8s
                wait_time = (2 ** (attempt + 1))
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)

    async def _extract_document_chunked(self, file_bytes: bytes, filename: str, total_pages: int) -> ExtractionResult:
        """
        Extract text from a large document using parallel chunk processing.
        """
        # Split document into chunks
        chunks = self._chunk_pdf(file_bytes, settings.CHUNK_SIZE_PAGES)
        total_chunks = len(chunks)
        
        # Semaphore for concurrency control
        semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_EXTRACTIONS)

        async def extract_chunk(chunk_data: Tuple[bytes, int, int], chunk_index: int):
            chunk_bytes, start_page, end_page = chunk_data
            async with semaphore:
                return await self._extract_single_chunk(
                    chunk_bytes, chunk_index, total_chunks, start_page, end_page
                )

        # Process all chunks in parallel
        tasks = [extract_chunk(chunk_data, idx) for idx, chunk_data in enumerate(chunks)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return self._aggregate_chunk_results(results, total_chunks, len(file_bytes))

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

    def _aggregate_chunk_results(self, results: List[Any], total_chunks: int, file_size: int) -> ExtractionResult:
        """
        Combine extraction results from multiple chunks.
        """
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        successful_results.sort(key=lambda x: x["chunk_index"])

        combined_text_parts = []
        for result in successful_results:
            combined_text_parts.append(result["extracted_text"])

        combined_text = "\n\n".join(combined_text_parts)
        
        failed_count = total_chunks - len(successful_results)
        
        metadata = ExtractionMetadata(
            page_count=0, # Would need to parse from text or pass through
            overall_confidence=ConfidenceLevel.LOW if failed_count > 0 else ConfidenceLevel.HIGH,
            is_chunked=True,
            chunk_count=total_chunks,
            successful_chunks=len(successful_results),
            failed_chunks=failed_count,
            file_size_bytes=file_size
        )
        
        return ExtractionResult(extracted_text=combined_text, metadata=metadata)

    def _parse_extraction_metadata(self, extracted_text: str, file_size: int) -> dict:
        """
        Parse metadata from LLM extraction output.
        """
        metadata = {
            "page_count": 0,
            "overall_confidence": "medium",
            "document_quality": "good",
            "has_handwriting": False,
            "extraction_notes": None,
            "file_size_bytes": file_size,
            "uncertain_count": 0,
            "illegible_count": 0
        }

        # Count pages from markers
        page_markers = re.findall(r'--- PAGE (\d+) ---', extracted_text)
        if page_markers:
            metadata["page_count"] = len(page_markers)

        # Extract overall confidence
        confidence_match = re.search(
            r'OVERALL DOCUMENT CONFIDENCE:\s*(High|Medium|Low)',
            extracted_text,
            re.IGNORECASE
        )
        if confidence_match:
            metadata["overall_confidence"] = confidence_match.group(1).lower()

        # Extract document quality
        quality_match = re.search(
            r'DOCUMENT QUALITY:\s*(Excellent|Good|Fair|Poor)',
            extracted_text,
            re.IGNORECASE
        )
        if quality_match:
            metadata["document_quality"] = quality_match.group(1).lower()

        # Check for handwriting
        handwriting_match = re.search(
            r'HANDWRITING DETECTED:\s*(Yes|No)',
            extracted_text,
            re.IGNORECASE
        )
        if handwriting_match:
            metadata["has_handwriting"] = handwriting_match.group(1).lower() == "yes"

        # Also check for handwriting annotations
        if re.search(r'\[Handwritten:', extracted_text):
            metadata["has_handwriting"] = True

        return metadata

llm_service = LLMService()