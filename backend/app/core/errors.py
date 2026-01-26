from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handler for standard HTTP Exceptions.
    """
    correlation_id = str(uuid.uuid4())
    logger.error(f"HTTP Error {exc.status_code}: {exc.detail} (Correlation ID: {correlation_id})")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status_code": exc.status_code,
            "error_code": _get_error_code(exc.status_code),
            "message": exc.detail,
            "correlation_id": correlation_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handler for Pydantic Validation Errors (400).
    """
    correlation_id = str(uuid.uuid4())
    logger.error(f"Validation Error: {exc.errors()} (Correlation ID: {correlation_id})")
    
    # Simplify validation errors
    messages = []
    for error in exc.errors():
        field = ".".join(str(x) for x in error.get("loc", []))
        messages.append(f"{field}: {error.get('msg')}")
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "status_code": status.HTTP_400_BAD_REQUEST,
            "error_code": "VALIDATION_ERROR",
            "message": "; ".join(messages),
            "correlation_id": correlation_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

def _get_error_code(status_code: int) -> str:
    """
    Map status codes to error codes.
    """
    mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        413: "PAYLOAD_TOO_LARGE",
        422: "VALIDATION_ERROR",
        500: "INTERNAL_SERVER_ERROR"
    }
    return mapping.get(status_code, "UNKNOWN_ERROR")