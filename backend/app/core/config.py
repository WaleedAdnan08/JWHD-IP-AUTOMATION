from pydantic_settings import BaseSettings
from typing import Optional, List
import os

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "JWHD IP Automation"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Database
    MONGODB_URL: str
    DATABASE_NAME: str = "jwhd_ip_automation"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Google Cloud Storage
    GOOGLE_APPLICATION_CREDENTIALS_JSON: Optional[str] = None
    GCP_BUCKET_NAME: str = "jwhd-ip-automation"
    GCP_STORAGE_BUCKET: Optional[str] = None

    # GCP Service Account Details
    GCP_TYPE: Optional[str] = None
    GCP_PROJECT_ID: Optional[str] = None
    GCP_PRIVATE_KEY_ID: Optional[str] = None
    GCP_PRIVATE_KEY: Optional[str] = None
    GCP_CLIENT_EMAIL: Optional[str] = None
    GCP_CLIENT_ID: Optional[str] = None
    GCP_AUTH_URI: Optional[str] = None
    GCP_TOKEN_URI: Optional[str] = None
    GCP_AUTH_PROVIDER_X509_CERT_URL: Optional[str] = None
    GCP_CLIENT_X509_CERT_URL: Optional[str] = None
    GCP_UNIVERSE_DOMAIN: Optional[str] = None
    
    # Gemini LLM
    GOOGLE_API_KEY: str
    GEMINI_MODEL: str = "gemini-3-pro-preview"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

settings = Settings()