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
            else:
                # Initialize from default environment (file path)
                self.client = storage.Client()
            
            self.bucket = self.client.bucket(settings.GCS_BUCKET_NAME)
            logging.info(f"Initialized GCS client for bucket: {settings.GCS_BUCKET_NAME}")
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

storage_service = StorageService()