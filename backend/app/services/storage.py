from google.cloud import storage
from app.core.config import settings
import datetime
import logging
import json
from typing import Optional

class StorageService:
    def __init__(self):
        self.client = None
        self.bucket = None
        self._initialize_client()

    def _initialize_client(self):
        try:
            if settings.GOOGLE_APPLICATION_CREDENTIALS_JSON:
                # Initialize from JSON string in env var
                credentials_info = json.loads(settings.GOOGLE_APPLICATION_CREDENTIALS_JSON)
                self.client = storage.Client.from_service_account_info(credentials_info)
            elif settings.GCP_PROJECT_ID and settings.GCP_CLIENT_EMAIL and settings.GCP_PRIVATE_KEY:
                # Initialize from individual env vars
                credentials_info = {
                    "type": "service_account",
                    "project_id": settings.GCP_PROJECT_ID,
                    "private_key_id": "unknown",  # Not strictly required for basic auth
                    "private_key": settings.GCP_PRIVATE_KEY.replace('\\n', '\n'),
                    "client_email": settings.GCP_CLIENT_EMAIL,
                    "client_id": "unknown",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{settings.GCP_CLIENT_EMAIL}"
                }
                self.client = storage.Client.from_service_account_info(credentials_info)
            else:
                # Initialize from default environment (file path)
                self.client = storage.Client()
            
            self.bucket = self.client.bucket(settings.GCP_BUCKET_NAME)
            logging.info(f"Initialized GCS client for bucket: {settings.GCP_BUCKET_NAME}")
        except Exception as e:
            logging.error(f"Failed to initialize GCS client: {e}")
            # Don't raise here to allow app startup, but operations will fail

    def upload_file(self, file_content: bytes, destination_blob_name: str, content_type: str = "application/pdf") -> str:
        """
        Uploads a file to the bucket and returns the storage key (blob name).
        """
        try:
            blob = self.bucket.blob(destination_blob_name)
            blob.upload_from_string(file_content, content_type=content_type)
            logging.info(f"File uploaded to {destination_blob_name}")
            return destination_blob_name
        except Exception as e:
            logging.error(f"Failed to upload file {destination_blob_name}: {e}")
            raise e

    def generate_presigned_url(self, blob_name: str, expiration_minutes: int = 15) -> str:
        """
        Generates a temporary download URL for a blob.
        """
        try:
            blob = self.bucket.blob(blob_name)
            url = blob.generate_signed_url(
                version="v4",
                expiration=datetime.timedelta(minutes=expiration_minutes),
                method="GET",
            )
            return url
        except Exception as e:
            logging.error(f"Failed to generate presigned URL for {blob_name}: {e}")
            raise e

    def delete_file(self, blob_name: str):
        """
        Deletes a blob from the bucket.
        """
        try:
            blob = self.bucket.blob(blob_name)
            blob.delete()
            logging.info(f"Blob {blob_name} deleted.")
        except Exception as e:
            logging.warning(f"Failed to delete blob {blob_name} (might not exist): {e}")

    def download_to_filename(self, blob_name: str, filename: str):
        """
        Downloads a blob to a local file.
        """
        try:
            blob = self.bucket.blob(blob_name)
            blob.download_to_filename(filename)
            logging.info(f"Downloaded blob {blob_name} to {filename}")
        except Exception as e:
            logging.error(f"Failed to download blob {blob_name}: {e}")
            raise e

    def download_as_bytes(self, blob_name: str) -> bytes:
        """
        Downloads a blob as bytes.
        """
        try:
            blob = self.bucket.blob(blob_name)
            content = blob.download_as_bytes()
            logging.info(f"Downloaded blob {blob_name} as bytes (Size: {len(content)})")
            return content
        except Exception as e:
            logging.error(f"Failed to download blob {blob_name} as bytes: {e}")
            raise e

storage_service = StorageService()