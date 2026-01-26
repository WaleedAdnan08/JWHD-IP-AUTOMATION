from datetime import datetime
from typing import Optional, Dict, Any
from app.db.mongodb import get_database
from app.models.common import MongoBaseModel
import logging

logger = logging.getLogger(__name__)

class AuditService:
    async def log_event(
        self,
        user_id: str,
        event_type: str,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        """
        Log a security or operational event to the audit_logs collection.
        """
        try:
            db = await get_database()
            
            audit_entry = {
                "user_id": user_id,
                "event_type": event_type,
                "timestamp": datetime.utcnow(),
                "details": details or {},
                "correlation_id": correlation_id
            }
            
            await db.audit_logs.insert_one(audit_entry)
            logger.info(f"Audit Log: [{event_type}] User: {user_id}")
            
        except Exception as e:
            # Audit logging failure should not break the application flow, but must be reported
            logger.error(f"Failed to write audit log: {e}")

audit_service = AuditService()