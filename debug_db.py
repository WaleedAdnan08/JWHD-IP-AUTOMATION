import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient

# Add backend to python path to import config
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from dotenv import load_dotenv
load_dotenv('backend/.env')

from app.core.config import settings

async def inspect_db():
    print(f"--- MongoDB Inspection Tool ---")
    print(f"configured MONGODB_URL: {settings.MONGODB_URL.split('@')[1]}") # Hide credentials
    print(f"configured DATABASE_NAME: {settings.DATABASE_NAME}")
    
    try:
        client = AsyncIOMotorClient(settings.MONGODB_URL)
        
        # 1. List all databases
        print("\n[1] Listing All Databases on Cluster:")
        dbs = await client.list_database_names()
        for db_name in dbs:
            print(f" - {db_name}")
            
        # 2. Inspect the configured database specifically
        print(f"\n[2] Inspecting Configured Database: '{settings.DATABASE_NAME}'")
        db = client[settings.DATABASE_NAME]
        collections = await db.list_collection_names()
        
        if not collections:
            print(f"   WARNING: No collections found in '{settings.DATABASE_NAME}'!")
        else:
            for col_name in collections:
                count = await db[col_name].count_documents({})
                print(f"   - Collection: {col_name:<25} Count: {count}")

        # 3. Check 'ridetribe' just in case (from connection string)
        if 'ridetribe' in dbs and settings.DATABASE_NAME != 'ridetribe':
             print(f"\n[3] Checking 'ridetribe' (found in connection string):")
             db_rt = client['ridetribe']
             cols_rt = await db_rt.list_collection_names()
             for col_name in cols_rt:
                count = await db_rt[col_name].count_documents({})
                print(f"   - Collection: {col_name:<25} Count: {count}")

        # 4. Check 'test' (default for some drivers)
        if 'test' in dbs:
             print(f"\n[4] Checking 'test' database:")
             db_test = client['test']
             cols_test = await db_test.list_collection_names()
             for col_name in cols_test:
                count = await db_test[col_name].count_documents({})
                print(f"   - Collection: {col_name:<25} Count: {count}")

    except Exception as e:
        print(f"\nERROR: Could not connect to MongoDB. Details: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(inspect_db())