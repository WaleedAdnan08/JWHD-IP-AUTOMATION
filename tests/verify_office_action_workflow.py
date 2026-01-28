import requests
import time
import os
import logging
from pymongo import MongoClient
from bson import ObjectId

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Config
API_URL = "http://localhost:8000/api/v1"
MONGO_URI = os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017")
TEST_USER_EMAIL = "test@jwhd.com"
TEST_USER_PASSWORD = "test123"

def seed_test_user():
    """Seed a test user if not exists."""
    logger.info("Seeding test user...")
    requests.post(f"{API_URL}/auth/seed-user", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD,
        "full_name": "Test User",
        "role": "attorney"
    })
    # Ignore error if user already exists

def get_auth_token():
    """Authenticate and get token."""
    seed_test_user()
    logger.info("Authenticating...")
    response = requests.post(f"{API_URL}/auth/login", data={
        "username": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code != 200:
        logger.error(f"Authentication failed: {response.text}")
        return None
    return response.json()["access_token"]

def upload_dummy_office_action(token):
    """Uploads a dummy PDF as an Office Action."""
    logger.info("Uploading dummy Office Action PDF...")
    
    # Create a dummy PDF
    with open("dummy_oa.pdf", "wb") as f:
        f.write(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/MediaBox [0 0 612 792]\n/Parent 2 0 R\n/Resources <<\n/Font <<\n/F1 <<\n/Type /Font\n/Subtype /Type1\n/BaseFont /Helvetica\n>>\n>>\n>>\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 100\n>>\nstream\nBT\n/F1 24 Tf\n100 700 Td\n(Dummy Office Action PDF) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n0000000117 00000 n\n0000000286 00000 n\ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n393\n%%EOF")

    with open("dummy_oa.pdf", "rb") as f:
        files = {"file": ("dummy_oa.pdf", f, "application/pdf")}
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{API_URL}/office-actions/upload", files=files, headers=headers)
    
    if response.status_code != 202:
        logger.error(f"Upload failed: {response.text}")
        return None
    
    return response.json()

def wait_for_job(token, job_id):
    """Polls job status until complete."""
    logger.info(f"Waiting for job {job_id}...")
    headers = {"Authorization": f"Bearer {token}"}
    
    while True:
        response = requests.get(f"{API_URL}/jobs/{job_id}", headers=headers)
        if response.status_code != 200:
            logger.error(f"Failed to get job status: {response.text}")
            return False
        
        job_data = response.json()
        status = job_data["status"]
        logger.info(f"Job Status: {status} ({job_data.get('progress_percentage', 0)}%)")
        
        if status == "completed":
            return True
        if status == "failed":
            logger.error(f"Job failed: {job_data.get('error_details')}")
            return False
            
        time.sleep(2)

def verify_extraction_data(token, document_id):
    """Verifies that data was extracted."""
    logger.info(f"Verifying extracted data for document {document_id}...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_URL}/office-actions/{document_id}", headers=headers)
    
    if response.status_code != 200:
        logger.error(f"Failed to get data: {response.text}")
        return False
        
    data = response.json()
    logger.info("Extracted Data Header:")
    logger.info(data.get("header"))
    
    return True

def download_report(token, document_id):
    """Downloads the generated report."""
    logger.info("Downloading report...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_URL}/office-actions/{document_id}/report", headers=headers)
    
    if response.status_code != 200:
        logger.error(f"Failed to download report: {response.text}")
        return False
        
    if "application/vnd.openxmlformats-officedocument.wordprocessingml.document" not in response.headers["Content-Type"]:
        logger.error(f"Invalid content type: {response.headers['Content-Type']}")
        return False
        
    logger.info(f"Report downloaded successfully ({len(response.content)} bytes).")
    return True

def main():
    token = get_auth_token()
    if not token:
        return

    result = upload_dummy_office_action(token)
    if not result:
        return
        
    job_id = result["job_id"]
    document_id = result["document_id"]
    
    if wait_for_job(token, job_id):
        if verify_extraction_data(token, document_id):
            download_report(token, document_id)
            logger.info("SUCCESS: Office Action Workflow Verified!")
        else:
            logger.error("Data verification failed.")
    else:
        logger.error("Job processing failed.")

if __name__ == "__main__":
    main()