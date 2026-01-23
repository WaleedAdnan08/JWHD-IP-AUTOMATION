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
    GCS_BUCKET_NAME: str = "jwhd-ip-automation"
    
    # Gemini LLM
    GOOGLE_API_KEY: str
    GEMINI_MODEL: str = "gemini-3-pro-preview"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()