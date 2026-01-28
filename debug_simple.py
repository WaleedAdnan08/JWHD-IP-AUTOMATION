import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

async def debug_documents():
    # Use the same MongoDB URI as the backend
    mongo_uri = "mongodb+srv://WaleedAdnan:cricketislife@cluster0.8l71z.mongodb.net/?appName=Cluster0"
    
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(mongo_uri)
        db = client.jwhd_ip_automation
        
        print(f"Connecting to: {mongo_uri}")
        print(f"Database: jwhd_ip_automation")
        
        print("=== RECENT DOCUMENTS ===")
        async for doc in db.documents.find().sort("created_at", -1).limit(5):
            print(f"Document ID: {doc['_id']}")
            print(f"User ID: {doc.get('user_id')} (type: {type(doc.get('user_id'))})")
            print(f"Filename: {doc.get('filename')}")
            print(f"Document Type: {doc.get('document_type')}")
            print(f"Status: {doc.get('processed_status')}")
            print(f"Has extraction_data: {bool(doc.get('extraction_data'))}")
            print("---")
            
        print("\n=== RECENT JOBS ===")
        async for job in db.processing_jobs.find().sort("created_at", -1).limit(3):
            print(f"Job ID: {job['_id']}")
            print(f"User ID: {job.get('user_id')} (type: {type(job.get('user_id'))})")
            print(f"Status: {job.get('status')}")
            print(f"Progress: {job.get('progress_percentage')}%")
            print(f"Job Type: {job.get('job_type')}")
            print("---")
            
        print("\n=== USERS ===")
        async for user in db.users.find().limit(3):
            print(f"User ID: {user['_id']} (type: {type(user['_id'])})")
            print(f"Email: {user.get('email')}")
            print("---")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(debug_documents())