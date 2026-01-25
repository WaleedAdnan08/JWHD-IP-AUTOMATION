import sys
import os
import asyncio
import logging
from pathlib import Path

# Configure logging to see EVERYTHING
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Add backend to sys.path
backend_path = os.path.join(os.getcwd(), "backend")
sys.path.append(backend_path)

# Mock Environment for standalone run BEFORE importing app modules
# These are required by app.core.config.Settings
if "MONGODB_URL" not in os.environ:
    os.environ["MONGODB_URL"] = "mongodb://localhost:27017/test_db"
if "SECRET_KEY" not in os.environ:
    os.environ["SECRET_KEY"] = "debug_secret_key_12345"

# Try to load .env from backend if available
env_path = os.path.join(backend_path, ".env")
if os.path.exists(env_path):
    logger.info(f"Loading environment from {env_path}")
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                if key not in os.environ:
                    os.environ[key] = value.strip('"').strip("'")

if "GOOGLE_API_KEY" not in os.environ:
    # try to load from backend/.env.example or warn user
    logger.warning("GOOGLE_API_KEY not found in environment. Please ensure it is set.")

try:
    from app.services.llm import llm_service
    from app.models.patent_application import PatentApplicationMetadata
except ImportError as e:
    logger.error(f"Failed to import backend services. Make sure you are running from the root directory. Error: {e}")
    sys.exit(1)

async def debug_extraction(file_path: str):
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return

    logger.info(f"--- STARTING DEBUG EXTRACTION FOR: {file_path} ---")
    
    # --- DEEP INSPECTION MODE ---
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        print("\n" + "="*50)
        print("DEEP XFA INSPECTION")
        print("="*50)
        
        if "/AcroForm" in reader.trailer["/Root"]:
            acro = reader.trailer["/Root"]["/AcroForm"]
            print(f"AcroForm Keys: {acro.keys()}")
            if "/XFA" in acro:
                xfa = acro["/XFA"]
                print(f"XFA Object Type: {type(xfa)}")
                if isinstance(xfa, list):
                    print("XFA is a LIST. Dumping keys (even indices)...")
                    for i in range(0, len(xfa), 2):
                        key = xfa[i]
                        print(f"  - {key}")
                        # Dump content length of the value
                        try:
                            val = xfa[i+1].get_object().get_data()
                            print(f"    Content Length: {len(val)} bytes")
                            if len(val) < 2000:
                                print(f"    Preview: {val[:200]}")
                        except Exception as e:
                            print(f"    Error reading content: {e}")
    except Exception as e:
        logger.error(f"Inspection failed: {e}")
    # ----------------------------

    try:
        # Force the service to use the file provided
        result = await llm_service.analyze_cover_sheet(file_path)
        
        print("\n" + "="*50)
        print("EXTRACTION RESULT")
        print("="*50)
        
        # Pretty print the Pydantic model
        import json
        print(json.dumps(result.model_dump(), indent=2, default=str))
        
        print("\n" + "="*50)
        
        if not result.inventors:
            print("❌ FAILURE: No inventors extracted.")
        else:
            print(f"✅ SUCCESS: Found {len(result.inventors)} inventors.")
            
    except Exception as e:
        logger.exception("Extraction process crashed:")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_extraction_local.py <path_to_pdf>")
        print("Example: python debug_extraction_local.py my_document.pdf")
        
        # Interactive mode fallback
        file_input = input("\nEnter path to PDF file: ").strip().strip('"').strip("'")
        if file_input:
            asyncio.run(debug_extraction(file_input))
    else:
        asyncio.run(debug_extraction(sys.argv[1]))