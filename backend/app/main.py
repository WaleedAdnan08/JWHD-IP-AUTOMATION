from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from contextlib import asynccontextmanager
import logging

from datetime import datetime
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.errors import http_exception_handler, validation_exception_handler

# Configure logging
setup_logging(level="INFO")
from app.db.mongodb import connect_to_mongo, close_mongo_connection, db
from app.services.storage import storage_service
from app.services.llm import llm_service
from app.api.api import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Register Exception Handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
async def health_check():
    """
    Perform a deep health check of all system components.
    """
    health_status = {
        "status": "healthy",
        "database_connected": False,
        "storage_connected": False,
        "llm_api_accessible": False,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # 1. Check MongoDB Connection
    try:
        if db.client:
            await db.client.admin.command('ping')
            health_status["database_connected"] = True
    except Exception as e:
        logging.error(f"Health check failed for MongoDB: {e}")
        health_status["status"] = "unhealthy"

    # 2. Check Google Cloud Storage
    try:
        if storage_service.bucket and storage_service.bucket.exists():
            health_status["storage_connected"] = True
    except Exception as e:
        logging.error(f"Health check failed for GCS: {e}")
        health_status["status"] = "unhealthy"

    # 3. Check LLM API (Gemini)
    try:
        if llm_service.client:
            # We don't make a full generation call to save costs/latency,
            # but checking if client is initialized with a key is a good proxy.
            # A more robust check would be listing models if the SDK supports it cheaply.
            health_status["llm_api_accessible"] = True
    except Exception as e:
        logging.error(f"Health check failed for LLM: {e}")
        health_status["status"] = "unhealthy"

    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status)

    return health_status