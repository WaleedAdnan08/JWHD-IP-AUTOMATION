import asyncio
import os
import sys
from passlib.context import CryptContext

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Load .env
env_path = os.path.join(os.getcwd(), "backend", ".env")
if os.path.exists(env_path):
    print(f"Loading environment from {env_path}")
    with open(env_path, "r") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value

# Fallbacks
if "MONGODB_URL" not in os.environ:
    os.environ["MONGODB_URL"] = "mongodb://localhost:27017" # Base URL without DB

# Import settings after env load to get configured DB name
try:
    from app.core.config import settings
    DB_NAME = settings.DATABASE_NAME
except ImportError:
    DB_NAME = "jwhd_ip_automation"

from motor.motor_asyncio import AsyncIOMotorClient

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def seed():
    print(f"Connecting to MongoDB at {os.environ['MONGODB_URL']}...")
    client = AsyncIOMotorClient(os.environ["MONGODB_URL"])
    
    # Explicitly use the correct database
    db = client[DB_NAME]
    print(f"Using database: {DB_NAME}")
    
    email = "test@jwhd.com"
    password = "test123"
    
    # 1. Delete existing
    print(f"Deleting existing user: {email}...")
    await db.users.delete_many({"email": email})
    
    # 2. Create new
    print(f"Creating new user: {email}...")
    hashed_password = pwd_context.hash(password)
    
    user_doc = {
        "email": email,
        "hashed_password": hashed_password,
        "full_name": "Test User",
        "role": "attorney",
        "firm_name": "JWHD Law",
        "is_active": True
    }
    
    await db.users.insert_one(user_doc)
    print(f"SUCCESS: User {email} created with password '{password}' in DB '{DB_NAME}'")

if __name__ == "__main__":
    asyncio.run(seed())