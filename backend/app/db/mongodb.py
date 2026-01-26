from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import logging

class MongoDB:
    client: AsyncIOMotorClient = None

db = MongoDB()

async def get_database():
    return db.client[settings.DATABASE_NAME]

async def create_indexes():
    """
    Create database indexes on startup to ensure query performance and data integrity.
    """
    database = db.client[settings.DATABASE_NAME]
    
    try:
        logging.info("Creating database indexes...")
        
        # Users
        await database.users.create_index("email", unique=True)
        
        # Patent Applications
        await database.patent_applications.create_index("application_number", unique=True)
        
        # Documents
        await database.documents.create_index("application_id")
        await database.documents.create_index("document_type")
        await database.documents.create_index("user_id")
        
        # Processing Jobs
        await database.processing_jobs.create_index("user_id")
        await database.processing_jobs.create_index("status")
        
        # Audit Logs
        await database.audit_logs.create_index("created_at")
        await database.audit_logs.create_index("user_id")
        
        logging.info("Database indexes created successfully.")
    except Exception as e:
        logging.error(f"Failed to create indexes: {e}")
        # We don't raise here to allow startup even if some indexes fail (e.g. conflicts)

async def connect_to_mongo():
    try:
        db.client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            maxPoolSize=20,
            minPoolSize=5
        )
        # Verify connection
        await db.client.admin.command('ping')
        logging.info("Connected to MongoDB")
        
        # Initialize Indexes
        await create_indexes()
        
    except Exception as e:
        logging.error(f"Could not connect to MongoDB: {e}")
        raise e

async def close_mongo_connection():
    if db.client:
        db.client.close()
        logging.info("Closed MongoDB connection")