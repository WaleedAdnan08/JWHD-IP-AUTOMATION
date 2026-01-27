import requests
import os

# --- Configuration ---
BASE_URL = "http://localhost:8000" # Assuming the backend is running locally
TEST_FILE_PATH = "test_data/dummy.docx"
TOKEN = os.getenv("TEST_USER_TOKEN") # We'll need a valid JWT token

# --- Verification ---
def verify_upload():
    if not TOKEN:
        print("ERROR: TEST_USER_TOKEN environment variable not set.")
        print("Please log in and set the token to run this test.")
        return

    if not os.path.exists(TEST_FILE_PATH):
        print(f"ERROR: Test file not found at {TEST_FILE_PATH}")
        return

    url = f"{BASE_URL}/api/documents/upload"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    files = {'file': ('dummy.docx', open(TEST_FILE_PATH, 'rb'), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
    data = {'document_type': 'specification'} # Or any other valid DocumentType

    try:
        response = requests.post(url, headers=headers, files=files, data=data)

        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("SUCCESS: DOCX file uploaded successfully.")
            print("Response JSON:", response.json())
        else:
            print("FAILURE: File upload failed.")
            try:
                print("Error Details:", response.json())
            except Exception:
                print("Raw Response:", response.text)

    except requests.exceptions.RequestException as e:
        print(f"ERROR: An exception occurred while making the request: {e}")

if __name__ == "__main__":
    verify_upload()