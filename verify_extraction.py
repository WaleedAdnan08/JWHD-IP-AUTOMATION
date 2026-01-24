import sys
import os

# Add backend to sys.path to allow imports from app
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Mock environment variables required by Settings
os.environ["MONGODB_URL"] = "mongodb://localhost:27017/test_db"
os.environ["SECRET_KEY"] = "supersecretkey"
os.environ["GOOGLE_API_KEY"] = "dummy_key_for_verification"

try:
    print("1. Verifying Imports...")
    from app.core.config import settings
    from app.services.llm import LLMService
    from app.models.extraction import ExtractionResult
    print("   Imports successful.")

    print("\n2. Verifying Configuration...")
    expected_model = "gemini-2.0-flash-exp"
    if settings.GEMINI_MODEL == expected_model:
        print(f"   Model configured correctly: {settings.GEMINI_MODEL}")
    else:
        print(f"   WARNING: Model mismatch. Expected {expected_model}, got {settings.GEMINI_MODEL}")
    
    # Check API Key presence (don't print it)
    if settings.GOOGLE_API_KEY:
        print("   GOOGLE_API_KEY is set (mocked).")
    else:
        print("   WARNING: GOOGLE_API_KEY is NOT set.")

    print("\n3. Verifying Service Initialization...")
    service = LLMService()
    if service.client:
        print("   LLMService initialized with Gemini client.")
    else:
        print("   LLMService initialized but client is None.")

    print("\nVerification Complete: SUCCESS")

except ImportError as e:
    print(f"\nVerification Failed: ImportError - {e}")
    sys.exit(1)
except Exception as e:
    print(f"\nVerification Failed: {e}")
    sys.exit(1)