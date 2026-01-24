import os
import sys
from dotenv import load_dotenv

# Load env file from backend/.env
env_path = os.path.join(os.path.dirname(__file__), "backend", ".env")
load_dotenv(env_path)

# Add backend to python path
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from app.services.storage import storage_service
from app.core.config import settings

def verify_storage_connection():
    print("=== Verifying Google Cloud Storage Connection ===")
    print(f"Project ID: {settings.GCP_PROJECT_ID}")
    print(f"Bucket Name: {settings.GCP_BUCKET_NAME}")
    print(f"Client Email: {settings.GCP_CLIENT_EMAIL}")
    
    if not settings.GCP_PRIVATE_KEY or "YOUR_PRIVATE_KEY_HERE" in settings.GCP_PRIVATE_KEY:
        print("\n[ERROR] GCP_PRIVATE_KEY is missing or contains placeholder values in .env")
        print("Please update backend/.env with your actual Private Key.")
        return

    test_filename = "test_connection.txt"
    test_content = b"This is a test file to verify GCP Storage connection."

    # Step 1: Upload
    try:
        print(f"\n[1/3] Attempting to upload {test_filename}...")
        storage_service.upload_file(test_content, test_filename, "text/plain")
        print("✅ Upload successful!")
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return

    # Step 2: Generate Signed URL
    try:
        print(f"\n[2/3] Attempting to generate signed URL...")
        url = storage_service.generate_presigned_url(test_filename)
        print(f"✅ Signed URL generated successfully: {url[:50]}...")
    except Exception as e:
        print(f"❌ Failed to generate signed URL: {e}")
        # Continue to delete attempt

    # Step 3: Delete
    try:
        print(f"\n[3/3] Attempting to delete {test_filename}...")
        storage_service.delete_file(test_filename)
        print("✅ Delete successful!")
    except Exception as e:
        print(f"❌ Delete failed: {e}")

    print("\n=== Verification Complete ===")

if __name__ == "__main__":
    verify_storage_connection()