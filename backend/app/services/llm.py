import google.generativeai as genai
from app.core.config import settings
import logging
import json
from typing import Dict, Any, Optional
import time
import asyncio
from app.models.patent_application import PatentApplicationMetadata

class LLMService:
    def __init__(self):
        self._initialize_client()

    def _initialize_client(self):
        try:
            if settings.GOOGLE_API_KEY:
                genai.configure(api_key=settings.GOOGLE_API_KEY)
                self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
                logging.info(f"Initialized Gemini model: {settings.GEMINI_MODEL}")
            else:
                logging.warning("GOOGLE_API_KEY not found. LLM service not initialized.")
                self.model = None
        except Exception as e:
            logging.error(f"Failed to initialize Gemini client: {e}")
            self.model = None

    async def generate_structured_content(
        self, 
        prompt: str, 
        schema: Optional[Dict[str, Any]] = None,
        retries: int = 3
    ) -> Dict[str, Any]:
        """
        Generates content from the LLM and parses it as JSON.
        Includes retry logic for transient failures.
        """
        if not self.model:
            raise Exception("LLM service not initialized")

        # Construct prompt to enforce JSON output
        full_prompt = f"{prompt}\n\nPlease provide the output in valid JSON format."
        if schema:
            full_prompt += f"\nFollow this schema:\n{json.dumps(schema, indent=2)}"

        for attempt in range(retries):
            try:
                # Run sync Gemini call in thread pool since library is synchronous
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    full_prompt,
                    generation_config=genai.types.GenerationConfig(
                        response_mime_type="application/json"
                    )
                )
                
                # Parse JSON
                try:
                    return json.loads(response.text)
                except json.JSONDecodeError:
                    # Fallback cleanup if raw text contains markdown code blocks
                    cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
                    return json.loads(cleaned_text)
                    
            except Exception as e:
                logging.warning(f"LLM generation failed (attempt {attempt + 1}/{retries}): {e}")
                if attempt == retries - 1:
                    raise e
                await asyncio.sleep(2 ** attempt) # Exponential backoff

    async def analyze_cover_sheet(self, text: str) -> PatentApplicationMetadata:
        """
        Analyzes the cover sheet text to extract patent application metadata.
        """
        prompt = """
        Extract the following metadata from the Patent Application Cover Sheet text provided below.
        
        Required Information:
        1. Title of Invention
        2. Application Number (if present)
        3. Filing Date (if present)
        4. Entity Status (if present)
        5. List of Inventors, including:
            - First Name
            - Middle Name (if present)
            - Last Name
            - City
            - State
            - Country
            - Citizenship
            - Mailing Address (street address)
            
        Output must be valid JSON matching the schema structure.
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
        
        try:
            # Construct the full prompt with text
            full_input = f"{prompt}\n\nTEXT CONTENT:\n{text[:30000]}" # Limit context if extremely large
            
            result = await self.generate_structured_content(
                prompt=full_input,
                schema=schema
            )
            
            return PatentApplicationMetadata(**result)
            
        except Exception as e:
            logging.error(f"Error analyzing cover sheet: {e}")
            # Return empty metadata with default values rather than failing
            return PatentApplicationMetadata()

llm_service = LLMService()