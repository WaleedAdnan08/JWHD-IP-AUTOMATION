from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import logging

class MongoDB:
    client: AsyncIOMotorClient = None

db = MongoDB()

async def get_database():
    return db.client[settings.DATABASE_NAME]

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
    except Exception as e:
        logging.error(f"Could not connect to MongoDB: {e}")
        raise e

async def close_mongo_connection():
    if db.client:
        db.client.close()
        logging.info("Closed MongoDB connection")